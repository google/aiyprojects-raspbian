/*
 * Google Vision Bonnet Driver
 *
 * Author: Jonas Larsson <ljonas@google.com>
 *         Michael Brooks <mrbrooks@google.com>
 *         Alex Van Damme <atv@google.com>
 *         Leonid Lobachev <leonidl@google.com>
 *         Dmitry Kovalev <dkovalev@google.com>
 *
 *         Copyright 2017
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * version 2 as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 */

#include "aiy-vision.h"
#include <asm/uaccess.h>
#include <linux/atomic.h>
#include <linux/cdev.h>
#include <linux/crc32.h>
#include <linux/delay.h>
#include <linux/errno.h>
#include <linux/firmware.h>
#include <linux/fs.h>
#include <linux/gpio.h>
#include <linux/gpio/consumer.h>
#include <linux/interrupt.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/mutex.h>
#include <linux/spi/spi.h>
#include <linux/types.h>
#include <linux/uaccess.h>
#include <linux/vmalloc.h>
#include <linux/wait.h>
#include <linux/workqueue.h>

#define MYRIAD_FIRMWARE "myriad_fw.mvcmd"
#define POLL_INTERVAL_MS (1000 / 60)
#define SPI_BOOT_FREQ (13800 * 1000)
#define SPI_NORMAL_FREQ (SPI_BOOT_FREQ)

#define MAX_READ_ATTEMPTS 100
#define MAX_WRITE_ATTEMPTS 100

#define PI_GPIO_SLAVE_READY_INDEX 0
#define PI_GPIO_MASTER_ERROR_INDEX 1
#define PI_GPIO_UNUSED_INDEX 2
#define PI_GPIO_CHIP_SELECT_INDEX 3

#define AIY_GPIO_RESET_INDEX 0

#define NUM_TRANSACTIONS 16
#define NUM_MMAP_BUFFERS 8

#define SLAVE_READY_TIMEOUT_MS 1000
#define SLAVE_READY_BOOT_TIMEOUT_MS 5000

#define MAX_SPI_TRANSFER_SIZE ((size_t)4095)
#define MAX_SPI_BOOT_TRANSFER_SIZE ((size_t)65535)

#define PAGE_COUNT(len_bytes) \
  (((len_bytes) + PAGE_SIZE - 1) / PAGE_SIZE);

typedef union {
  uint8_t as_byte;
  struct {
    // 0 - Acknowledge. Always 1 for master packets, 0/1 for slave.
    uint8_t ack : 1;
    // 1 - Supported (always 1 when reserved bits are 0).
    uint8_t is_supported : 1;
    // 2 - Transaction ID is valid (always 1 for master headers).
    uint8_t tid_valid : 1;
    // 3 - Indicates if data will follow this packet (in the same direction).
    uint8_t has_data : 1;
    // 4 - Master - 1, Slave - 0
    uint8_t is_master : 1;
    // 5 - Indicates if this packet completes transaction.
    uint8_t complete : 1;
    // 6-7 - Unused in current implementation. Should be 0.
    uint8_t reserved : 2;
  } bits;
} header_start_t;

typedef struct __attribute__((packed)) {
  header_start_t start;
  uint8_t transaction_id;
  uint16_t crc;
  uint32_t size;
} header_t;

typedef struct {
  struct list_head list;
  uint32_t flags;
  // Buffer is at least MAX_SPI_TRANSFER_SIZE bytes regardless of buffer_len.
  char *buffer;
  uint32_t buffer_len;
  uint32_t payload_len;
  struct mutex lock;
  atomic_t refs;
} transaction_t;

typedef struct {
  struct mutex lock;
  int refs;  // 0 - freed, 1 - allocated, 2 - used.
  char *buffer;
  uint32_t buffer_len;
  unsigned long vm_pgoff;
} mmap_buffer_t;

typedef struct {
  struct spi_device *spidev;
  struct class *spicomm_class;
  struct device *spicomm_device;
  struct cdev spicomm_cdev;
  dev_t spicomm_region;

  struct gpio_desc *me_gpio;
  struct gpio_desc *cs_gpio;
  struct gpio_desc *reset_gpio;

  wait_queue_head_t slave_ready_wait_queue;
  atomic_t slave_ready;

  struct mutex lock;
  struct workqueue_struct *workqueue;
  wait_queue_head_t transaction_wait_queue;
  struct work_struct incoming_transaction_work;
  struct delayed_work ongoing_transaction_work;
  struct list_head incoming_transaction_queue;
  struct list_head ongoing_transaction_list;

  transaction_t transactions[NUM_TRANSACTIONS];
} visionbonnet_t;

typedef struct {
  struct mutex lock;
  mmap_buffer_t mmap_buffers[NUM_MMAP_BUFFERS];
  visionbonnet_t *bonnet;
} visionbonnet_instance_t;

static int transaction_id(const visionbonnet_t *bonnet,
                          const transaction_t *transaction) {
  return transaction - bonnet->transactions + 1;
}

static bool mmap_buffer_overlaps(mmap_buffer_t* buf,
                                 struct vm_area_struct *vma) {
  bool overlaps = false;
  unsigned long vma_pg_left = vma->vm_pgoff;
  unsigned long vma_pg_right =
      vma_pg_left + PAGE_COUNT(vma->vm_end - vma->vm_start);
  unsigned long buf_pg_left, buf_pg_right;

  mutex_lock(&buf->lock);
  if (buf->buffer) {
     buf_pg_left = buf->vm_pgoff;
     buf_pg_right = buf_pg_left + PAGE_COUNT(buf->buffer_len);

     if ((buf_pg_left <= vma_pg_left && vma_pg_left < buf_pg_right) ||
         (buf_pg_left < vma_pg_right && vma_pg_right <= buf_pg_right)) {
       overlaps = true;
       goto done;
     }
  }
done:
  mutex_unlock(&buf->lock);
  return overlaps;
}

static bool mmap_buffer_reserve(mmap_buffer_t* buf) {
  bool reserved = false;
  mutex_lock(&buf->lock);
  if (!buf->buffer) {
    buf->buffer = (char*)~0L;  // Prevent others from using this buffer.
    reserved = true;
  }
  mutex_unlock(&buf->lock);
  return reserved;
}

static int mmap_buffer_alloc(mmap_buffer_t *buf, uint32_t len,
                             unsigned long vm_pgoff) {
  int ret = 0;
  mutex_lock(&buf->lock);

  if (buf->refs > 0) {
    ret = -EBUSY;
    goto done;
  }

  buf->buffer = (char *)vmalloc_user(max(MAX_SPI_TRANSFER_SIZE, len));
  if (!buf->buffer) {
    ret = -ENOMEM;
    goto done;
  }
  buf->buffer_len = len;
  buf->vm_pgoff = vm_pgoff;
  buf->refs = 1;

done:
  mutex_unlock(&buf->lock);
  return ret;
}

static int mmap_buffer_use(mmap_buffer_t *buf, unsigned long vm_pgoff) {
  int ret = 0;
  mutex_lock(&buf->lock);

  if (buf->refs != 1 || buf->vm_pgoff != vm_pgoff) {
    ret = -EINVAL;
    goto done;
  }

  buf->refs += 1;

done:
  mutex_unlock(&buf->lock);
  return ret;
}

static int mmap_buffer_release(mmap_buffer_t *buf) {
  int ret = 0;
  mutex_lock(&buf->lock);

  if (buf->refs == 0) {
    ret = -EINVAL;
    goto done;
  }

  if (--buf->refs == 0) {
    vfree(buf->buffer);
    buf->buffer = NULL;
    buf->buffer_len = 0;
    buf->vm_pgoff = 0;
  }

done:
  mutex_unlock(&buf->lock);
  return ret;
}

mmap_buffer_t* visionbonnet_find_mmap_buffer(visionbonnet_instance_t *instance,
                                             unsigned long vm_pgoff) {
  mmap_buffer_t* buf = NULL;
  int i;

  mutex_lock(&instance->lock);
  for (i = 0; i < NUM_MMAP_BUFFERS; ++i) {
    if (mmap_buffer_use(&instance->mmap_buffers[i], vm_pgoff) == 0) {
      buf = &instance->mmap_buffers[i];
      break;
    }
  }
  mutex_unlock(&instance->lock);
  return buf;
}

mmap_buffer_t* visionbonnet_reserve_mmap_buffer(visionbonnet_instance_t *instance,
                                                struct vm_area_struct *vma) {
  mmap_buffer_t* buf = NULL;
  int i;

  mutex_lock(&instance->lock);

  for (i = 0; i < NUM_MMAP_BUFFERS; ++i)
    if (mmap_buffer_overlaps(&instance->mmap_buffers[i], vma))
      goto done;

  for (i = 0; i < NUM_MMAP_BUFFERS; ++i) {
    if (mmap_buffer_reserve(&instance->mmap_buffers[i])) {
      buf = &instance->mmap_buffers[i];
      goto done;
    }
  }

done:
  mutex_unlock(&instance->lock);
  return buf;
}

static int __attribute__((used)) debug = 0;
module_param(debug, int, S_IWUSR | S_IRUGO);
MODULE_PARM_DESC(debug, "Vision Bonnet debug");

static int __attribute__((used)) reset_on_failure = 1;
module_param(reset_on_failure, int, S_IWUSR | S_IRUGO);
MODULE_PARM_DESC(reset_on_failure, "Reset Myriad on fatal failure");

// Conditional debug. Use dev_info to avoid being compiled out.
#define cdebug(bonnet, format, ...)                          \
  do {                                                       \
    if (unlikely(debug)) {                                   \
      dev_info(&bonnet->spidev->dev, format, ##__VA_ARGS__); \
    }                                                        \
  } while (0)

static inline u32 compute_crc32(const uint8_t *data, size_t size) {
  return crc32(0xFFFFFFFF, data, size) ^ 0xFFFFFFFF;
}

static uint16_t xmodem_crc16_cumul(uint16_t crc, const uint8_t *data,
                                   size_t size) {
  const uint16_t kCrc16_CCIT_Poly_MSBF = 0x1021;
  for (size_t i = 0; i < size; ++i) {
    crc ^= (data[i] << 8);
    /* Compute the CRC one input bit at a time. See code fragment 4:
     * http://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks
     */
    for (unsigned bit = 0; bit < 8; ++bit) {
      if (crc & 0x8000) {
        crc = kCrc16_CCIT_Poly_MSBF ^ (crc << 1);
      } else {
        crc <<= 1;
      }
    }
  }
  return crc;
}

static inline uint16_t compute_header_crc16(const header_t *header) {
  u16 crc = 0xFFFF;
  crc = xmodem_crc16_cumul(crc, (uint8_t *)&header->start.as_byte, 2);
  crc = xmodem_crc16_cumul(crc, (uint8_t *)&header->size, sizeof(header->size));
  return crc;
}

// bonnet->lock must already be held.
static void transaction_unref(visionbonnet_t *bonnet,
                              transaction_t *transaction) {
  if (!transaction) {
    return;
  }

  if (atomic_dec_and_test(&transaction->refs)) {
    cdebug(bonnet, "Freeing tid %u\n", transaction_id(bonnet, transaction));
    vfree(transaction->buffer);
    mutex_destroy(&transaction->lock);
    memset(transaction, 0, sizeof(*transaction));
  }
}

// bonnet->lock must already be held.
static int transaction_alloc(visionbonnet_t *bonnet,
                             transaction_t **transaction, size_t buffer_len) {
  const struct device *dev = &bonnet->spidev->dev;
  transaction_t *tr = NULL;
  int i;

  *transaction = NULL;

  for (i = 0; i < NUM_TRANSACTIONS; ++i) {
    if (bonnet->transactions[i].buffer == NULL) {
      tr = &bonnet->transactions[i];
      cdebug(bonnet, "Assigning tid %u\n", transaction_id(bonnet, tr));
      break;
    }
  }

  if (!tr) {
    dev_err(dev, "No transaction id available\n");
    return -EBUSY;
  }

  cdebug(bonnet, "Allocating %d byte buffer for tid=%u\n",
         buffer_len, transaction_id(bonnet, tr));
  tr->buffer = (char *)vmalloc(max(MAX_SPI_TRANSFER_SIZE, buffer_len));
  if (!tr->buffer) {
    dev_err(dev, "Out of memory, %u b buffer\n", buffer_len);
    return -ENOMEM;
  }
  tr->buffer_len = buffer_len;
  INIT_LIST_HEAD(&tr->list);
  mutex_init(&tr->lock);
  atomic_set(&tr->refs, 1);

  *transaction = tr;
  return 0;
}

static void transaction_set_flags(visionbonnet_t *bonnet,
                                  transaction_t *transaction, u32 flags) {
  if (!transaction) {
    return;
  }

  mutex_lock(&transaction->lock);
  transaction->flags |= flags;
  mutex_unlock(&transaction->lock);
  wake_up_interruptible(&bonnet->transaction_wait_queue);
}

static int transaction_done_waiting(transaction_t *transaction,
                                    u32 wait_flags) {
  int ret;
  mutex_lock(&transaction->lock);
  ret = ((transaction->flags & wait_flags) == wait_flags) ||
        (transaction->flags & FLAG_ERROR);
  mutex_unlock(&transaction->lock);
  return ret;
}

static void visionbonnet_alert_success(visionbonnet_t *bonnet) {
  gpiod_set_value(bonnet->cs_gpio, 1);
  gpiod_set_value(bonnet->cs_gpio, 0);
  gpiod_set_value(bonnet->cs_gpio, 1);
}

static void visionbonnet_alert_error(visionbonnet_t *bonnet) {
  gpiod_set_value(bonnet->me_gpio, 0);
  gpiod_set_value(bonnet->me_gpio, 1);
}

// Dumps pending transactions to debug output.
// Note: assumes that bonnet->lock is being held by the caller already.
static void visionbonnet_dump_transactions(visionbonnet_t *bonnet) {
  const struct device *dev = &bonnet->spidev->dev;
  if (unlikely(debug)) {
    transaction_t *transaction = NULL, *t;
    dev_info(dev, "Pending tid(s) = ");
    list_for_each_entry_safe(transaction, t, &bonnet->ongoing_transaction_list,
                             list) {
      dev_info(dev, "%d ", transaction_id(bonnet, transaction));
    }
    dev_info(dev, "\n");
  }
}

static int visionbonnet_validate_header(visionbonnet_t *bonnet,
                                        const header_t *header) {
  const struct device *dev = &bonnet->spidev->dev;
  int ret = 0;

  if (header->crc != compute_header_crc16(header)) {
    // If the slave NACKs or the CRC doesn't match, toggle error line and
    // retry the receive.
    ret = -EBADMSG;
    visionbonnet_alert_error(bonnet);
    dev_err(dev, "CRC mismatch on response, re-reading.\n");
  } else if (header->start.bits.reserved || !header->start.bits.is_supported) {
    // If reserve values are set or supported is false, the header in invalid.
    ret = -ENOTSUPP;
    visionbonnet_alert_success(bonnet);
    dev_err(dev, "Not supported.\n");
  } else if (!header->start.bits.tid_valid) {
    // If the slave Transaction ID doesn't match the master, end transaction.
    ret = -EINVAL;
    visionbonnet_alert_success(bonnet);
    dev_err(dev, "Transaction ID failure.\n");
  } else if (!header->start.bits.ack) {
    ret = -EHOSTDOWN;
    visionbonnet_alert_success(bonnet);
    dev_err(dev, "Slave responded with a NACK, resending header.\n");
  }

  return ret;
}

static bool visionbonnet_wait_slave_ready(visionbonnet_t *bonnet, int timeout) {
  const struct device *dev = &bonnet->spidev->dev;
  int wait_ret = wait_event_interruptible_timeout(
      bonnet->slave_ready_wait_queue, atomic_read(&bonnet->slave_ready),
      msecs_to_jiffies(timeout));
  if (wait_ret == -ERESTARTSYS) {
    dev_err(dev, "visionbonnet_wait_slave_ready interrupted by signal\n");
    return false;
  }

  // Consume slave_ready.
  int slave_ready = atomic_xchg(&bonnet->slave_ready, 0);
  if (!slave_ready) {
    dev_err(dev, "Slave not ready after %d ms\n", timeout);
  }
  return slave_ready;
}

static int visionbonnet_spi_read_impl(visionbonnet_t *bonnet,
                                      void *buf, size_t size, bool inplace) {
  u8 *data = buf;
  size_t transfer_size;
  int ret;

  while (size > 0) {
    cdebug(bonnet, "Waiting before read.\n");
    if (!visionbonnet_wait_slave_ready(bonnet, SLAVE_READY_TIMEOUT_MS)) {
      ret = -ERESTART;  // Fatal error.
      break;
    }
    cdebug(bonnet, "Done waiting, reading.\n");

    transfer_size = min(size, MAX_SPI_TRANSFER_SIZE);
    gpiod_set_value(bonnet->cs_gpio, 0);
    ret = spi_read(bonnet->spidev, data, transfer_size);
    gpiod_set_value(bonnet->cs_gpio, 1);
    if (ret) {
      dev_err(&bonnet->spidev->dev, "Failed to read spi data ret=%d\n", ret);
      break;
    }
    size -= transfer_size;
    data += (inplace ? 0 : transfer_size);
  }
  return ret;
}

static int visionbonnet_spi_read(visionbonnet_t *bonnet,
                                 void *buf, size_t size) {
  return visionbonnet_spi_read_impl(bonnet, buf, size, false);
}

static int visionbonnet_spi_write(visionbonnet_t *bonnet, const void *buf,
                                  size_t size) {
  const u8 *data = buf;
  size_t transfer_size;
  int ret;

  while (size > 0) {
    cdebug(bonnet, "Waiting before write.\n");
    if (!visionbonnet_wait_slave_ready(bonnet, SLAVE_READY_TIMEOUT_MS)) {
      ret = -ERESTART;  // Fatal error.
      break;
    }
    cdebug(bonnet, "Done waiting, writing.\n");

    transfer_size = min(size, MAX_SPI_TRANSFER_SIZE);
    gpiod_set_value(bonnet->cs_gpio, 0);
    ret = spi_write(bonnet->spidev, data, transfer_size);
    gpiod_set_value(bonnet->cs_gpio, 1);
    if (ret) {
      dev_err(&bonnet->spidev->dev, "Failed to write spi data ret=%d\n", ret);
      break;
    }
    size -= transfer_size;
    data += transfer_size;
  }
  cdebug(bonnet, "Spi write complete.\n");
  return ret;
}

static int visionbonnet_set_spi_freq(visionbonnet_t *bonnet, int freq) {
  bonnet->spidev->max_speed_hz = freq;
  return spi_setup(bonnet->spidev);
}

static int visionbonnet_write_firmware(visionbonnet_t *bonnet,
                                       const uint8_t *data, size_t size) {
  const struct device *dev = &bonnet->spidev->dev;
  size_t transfer_size;
  int ret;

  ret = visionbonnet_set_spi_freq(bonnet, SPI_BOOT_FREQ);
  if (ret) {
    dev_err(dev, "Failed to set spi freq: %d\n", ret);
    goto beach;
  }

  gpiod_set_value(bonnet->cs_gpio, 0);
  while (size > 0) {
    transfer_size = min(size, MAX_SPI_BOOT_TRANSFER_SIZE);
    ret = spi_write(bonnet->spidev, data, transfer_size);
    if (ret) {
      dev_err(dev, "spi_write firmware: %d\n", ret);
      goto beach;
    }
    size -= transfer_size;
    data += transfer_size;
  }

  ret = visionbonnet_set_spi_freq(bonnet, SPI_NORMAL_FREQ);
  if (ret) {
    dev_err(dev, "Failed to set spi freq: %d\n", ret);
    goto beach;
  }

beach:
  gpiod_set_value(bonnet->cs_gpio, 1);
  return ret;
}

static void visionbonnet_cancel_transactions(visionbonnet_t *bonnet) {
  transaction_t *transaction = NULL, *t;
  list_for_each_entry_safe(transaction, t, &bonnet->incoming_transaction_queue,
                           list) {
    list_del(&transaction->list);
    transaction->payload_len = 0;
    transaction_set_flags(bonnet, transaction, FLAG_ERROR);
    transaction_unref(bonnet, transaction);
  }
  list_for_each_entry_safe(transaction, t, &bonnet->ongoing_transaction_list,
                           list) {
    list_del(&transaction->list);
    transaction->payload_len = 0;
    transaction_set_flags(bonnet, transaction, FLAG_ERROR);
    transaction_unref(bonnet, transaction);
  }
}

static int visionbonnet_myriad_reset(visionbonnet_t *bonnet) {
  const struct firmware *firmware = NULL;
  struct device *dev = &bonnet->spidev->dev;
  int ret = 0;

  cdebug(bonnet, "Requesting firmware %s\n", MYRIAD_FIRMWARE);
  ret = request_firmware(&firmware, MYRIAD_FIRMWARE, dev);
  if (ret) {
    dev_err(dev, "Failed to request firmware %s: %d\n", MYRIAD_FIRMWARE, ret);
    return ret;
  }

  // Any and all transaction in flight must be aborted.
  mutex_lock(&bonnet->lock);
  visionbonnet_cancel_transactions(bonnet);
  dev_notice(dev, "Resetting myriad\n");
  gpiod_set_value_cansleep(bonnet->reset_gpio, 1);
  msleep(20);
  gpiod_set_value_cansleep(bonnet->reset_gpio, 0);
  msleep(20);
  gpiod_set_value_cansleep(bonnet->reset_gpio, 1);
  // Give Myriad adequate time for boot ROM to execute.
  msleep(2000);

  atomic_set(&bonnet->slave_ready, 0);

  dev_notice(dev, "Writing myriad firmware\n");
  ret = visionbonnet_write_firmware(bonnet, firmware->data, firmware->size);
  if (ret) {
    dev_err(dev, "Failed to write firmware: %d\n", ret);
    goto beach;
  }
  dev_notice(dev, "Myriad booting\n");

  if (!visionbonnet_wait_slave_ready(bonnet, SLAVE_READY_BOOT_TIMEOUT_MS)) {
    dev_err(dev, "Myriad did not boot in a timely fashion\n");
    ret = -EHOSTUNREACH;
    goto beach;
  }
  atomic_set(&bonnet->slave_ready, 1);
  dev_notice(dev, "Myriad ready\n");

beach:
  release_firmware(firmware);
  mutex_unlock(&bonnet->lock);
  return ret;
}

static void visionbonnet_fatal_error(visionbonnet_t *bonnet) {
  const struct device *dev = &bonnet->spidev->dev;
  int ret;

  if (reset_on_failure) {
    dev_err(dev, "Fatal error, resetting\n");
    ret = visionbonnet_myriad_reset(bonnet);
    if (ret) {
      dev_err(dev, "Failed to reset %d:\n", ret);
    }
  } else {
    dev_err(dev, "Fatal error, but reset skipped\n");
  }
}

static irqreturn_t visionbonnet_slave_ready_isr(int irq, void *dev) {
  visionbonnet_t *bonnet = dev;

  atomic_xchg(&bonnet->slave_ready, 1);
  wake_up_interruptible(&bonnet->slave_ready_wait_queue);
  return IRQ_HANDLED;
}

static transaction_t *visionbonnet_get_incoming_transaction(
    visionbonnet_t *bonnet) {
  transaction_t *transaction = NULL;
  mutex_lock(&bonnet->lock);
  if (!list_empty(&bonnet->incoming_transaction_queue)) {
    transaction = list_first_entry(&bonnet->incoming_transaction_queue,
                                   transaction_t, list);
    list_del(&transaction->list);
  }
  mutex_unlock(&bonnet->lock);
  return transaction;
}

static void visionbonnet_put_incoming_transaction(visionbonnet_t *bonnet,
    transaction_t *transaction) {
  mutex_lock(&bonnet->lock);
  list_add_tail(&transaction->list, &bonnet->incoming_transaction_queue);
  mutex_unlock(&bonnet->lock);
}

static void visionbonnet_add_pending_transaction(visionbonnet_t *bonnet,
    transaction_t *transaction) {
  mutex_lock(&bonnet->lock);
  list_add_tail(&transaction->list, &bonnet->ongoing_transaction_list);
  visionbonnet_dump_transactions(bonnet);
  mutex_unlock(&bonnet->lock);
}

static transaction_t *visionbonnet_find_pending_transaction(
    visionbonnet_t *bonnet, u8 tid) {
  transaction_t *transaction = NULL, *t;
  mutex_lock(&bonnet->lock);
  list_for_each_entry_safe(transaction, t, &bonnet->ongoing_transaction_list,
                           list) {
    if (transaction_id(bonnet, transaction) == tid) {
      list_del(&transaction->list);
      break;
    }
  }
  mutex_unlock(&bonnet->lock);
  return transaction;
}

static int visionbonnet_header_exchange(visionbonnet_t *bonnet,
                                        const transaction_t *transaction,
                                        header_t *incoming_header,
                                        header_t *outgoing_header) {
  int ret = 0;
  int write_attempts = 0;
  int read_attempts = 0;

  if (transaction) {
    outgoing_header->start.as_byte = 0b00011111;
    outgoing_header->transaction_id = transaction_id(bonnet, transaction);
    outgoing_header->size = transaction->payload_len;
  } else {
    outgoing_header->start.as_byte = 0b00010111;
    outgoing_header->transaction_id = 0;
    outgoing_header->size = 0;
  }
  outgoing_header->crc = compute_header_crc16(outgoing_header);

  do {
    write_attempts++;
    // Send initial header packet.
    cdebug(bonnet, "Sending initial header\n");
    ret = visionbonnet_spi_write(bonnet, outgoing_header, sizeof(header_t));
    if (ret) {
      dev_err(&bonnet->spidev->dev, "Failed to write header: %d\n", ret);
      return ret;
    }

    // SPI Write will appropriately toggle chip select and wait for the slave to
    // indicate it's ready. Begin a read event that will loop if there is a CRC
    // mismatch on the response.
    do {
      read_attempts++;
      ret = visionbonnet_spi_read(bonnet, incoming_header, sizeof(header_t));
      if (ret) {
        return ret;
      }
      cdebug(bonnet, "Recieved header: %02x size %u crc %04x tid %d\n",
             incoming_header->start.as_byte, incoming_header->size,
             incoming_header->crc, (int)incoming_header->transaction_id);

      // Validate the incoming packet.
      ret = visionbonnet_validate_header(bonnet, incoming_header);
      if (ret == -ENOTSUPP || ret == -EINVAL) {
        // If the response packet indicates TID mismatch or not supported, this
        // transaction is complete.
        return ret;
      }
      // Continue until succesful validation of header, or attempts exhausted.
    } while (ret == -EBADMSG && read_attempts < MAX_READ_ATTEMPTS);
    // Send transactions should continue until the slave validates CRC
    // (i.e. sends an ACK) or attempts exhausted.
  } while (ret == -EHOSTDOWN && write_attempts < MAX_WRITE_ATTEMPTS);

  if (!ret) {
    // With a clean master-slave exchange, toggle slave select to alert slave.
    cdebug(bonnet, "header_exchange succesful\n");
    visionbonnet_alert_success(bonnet);
  }
  return ret;
}

static int visionbonnet_receive_data_buffer(visionbonnet_t *bonnet,
                                            transaction_t *transaction,
                                            const header_t *incoming_header,
                                            const header_t *outgoing_header) {
  int read_attempts = 0;
  uint32_t slave_crc, computed_crc;
  bool overflow;
  int ret;

  do {
    ret = 0;
    read_attempts++;

    cdebug(bonnet, "receive_data_buffer of size %u, buffer_len %u\n",
           incoming_header->size, transaction->buffer_len);

    mutex_lock(&transaction->lock);
    overflow = incoming_header->size > transaction->buffer_len;
    transaction->payload_len = incoming_header->size;
    // transaction->buffer is at least MAX_SPI_TRANSFER_SIZE bytes.
    ret = visionbonnet_spi_read_impl(bonnet, transaction->buffer,
        incoming_header->size, overflow);
    mutex_unlock(&transaction->lock);
    if (ret) {
      return ret;
    }

    // After completing the data receive, read the CRC32 from the slave.
    ret = visionbonnet_spi_read(bonnet, &slave_crc, sizeof(slave_crc));
    if (ret) {
      dev_err(&bonnet->spidev->dev, "Failed on SPI read\n");
      return ret;
    }

    if (overflow) {
      // Don't check the crc, just signal error and break out.
      transaction_set_flags(bonnet, transaction, FLAG_OVERFLOW | FLAG_ERROR);
      break;
    }

    // Compare to calculated CRC32.
    computed_crc = compute_crc32(transaction->buffer, incoming_header->size);
    if (slave_crc == computed_crc) {
      transaction_set_flags(bonnet, transaction, FLAG_RESPONSE);
    } else {
      ret = -EBADMSG;
      dev_err(&bonnet->spidev->dev,
              "Incoming crc mismatch: slave %08x vs computed %08x\n", slave_crc,
              computed_crc);
      visionbonnet_alert_error(bonnet);
    }
    // Loop until CRC32s match, or attempts exhausted.
  } while (slave_crc != computed_crc && read_attempts < MAX_READ_ATTEMPTS);

  if (!ret) {
    cdebug(bonnet, "receive_data_buffer succesful\n");
    visionbonnet_alert_success(bonnet);
  }
  return ret;
}

static int visionbonnet_send_data_buffer(visionbonnet_t *bonnet,
                                         const transaction_t *transaction,
                                         header_t *incoming_header,
                                         const header_t *outgoing_header) {
  const struct device *dev = &bonnet->spidev->dev;
  int ret;
  int write_attempts = 0;
  int read_attempts = 0;
  uint32_t crc = compute_crc32(transaction->buffer, transaction->payload_len);

  do {
    write_attempts++;
    cdebug(bonnet, "Send data of size %u\n", transaction->payload_len);
    ret = visionbonnet_spi_write(bonnet, transaction->buffer,
                                 transaction->payload_len);
    if (ret) {
      dev_err(dev, "Failed on SPI write\n");
      return ret;
    }

    cdebug(bonnet, "Data sent, sending crc\n");
    // Succesful M->S send. Send CRC32
    ret = visionbonnet_spi_write(bonnet, &crc, sizeof(crc));
    if (ret) {
      dev_err(dev, "Failed to write CRC\n");
      return ret;
    }
    do {
      read_attempts++;
      // Validate crc32 via one last packet read. Expect incoming header to be
      // completed.
      cdebug(bonnet, "Reading crc packet\n");
      ret = visionbonnet_spi_read(bonnet, incoming_header, sizeof(header_t));
      if (ret) {
        dev_err(dev, "Failed on SPI read.\n");
        return ret;
      }
      ret = visionbonnet_validate_header(bonnet, incoming_header);
      if (ret == -ENOTSUPP || ret == -EINVAL) {
        // If the response packet indicates TID mismatch or not supported, this
        // transaction is complete.
        return ret;
      }
      // Loop reads until the header is verified, or attempts exhausted.
    } while (ret == -EBADMSG && read_attempts < MAX_READ_ATTEMPTS);
    // Loop writes until slave validates the sent CRC, or attempts exhausted.
  } while (ret == -EHOSTDOWN && write_attempts < MAX_WRITE_ATTEMPTS);

  if (!ret) {
    cdebug(bonnet, "send_data_buffer succesful\n");
    visionbonnet_alert_success(bonnet);
  }
  return ret;
}

static void visionbonnet_incoming_transaction_work_handler(
    struct work_struct *work) {
  int ret;
  header_t outgoing_header = {{0}};
  header_t incoming_header = {{0}};
  visionbonnet_t *bonnet =
      container_of(work, visionbonnet_t, incoming_transaction_work);
  transaction_t *transaction = visionbonnet_get_incoming_transaction(bonnet);

  if (!transaction) {
    return;  // Scheduled without any transactions to handle.
  }

  // We now own a ref to transaction.
  cdebug(bonnet, "processing tid %u\n", transaction_id(bonnet, transaction));

  // Exchange headers.
  ret = visionbonnet_header_exchange(bonnet, transaction, &incoming_header,
                                     &outgoing_header);
  if (ret) {
    goto beach;
  }

  // Send request.
  ret = visionbonnet_send_data_buffer(bonnet, transaction, &incoming_header,
                                      &outgoing_header);
  if (ret) {
    goto beach;
  }

  // We now consider the transaction acked, there may or may not be a response.
  transaction_set_flags(bonnet, transaction, FLAG_ACKED);

  cdebug(bonnet,
         "Data sent. tid %d complete %d is_supported %d has_data %d size %u\n",
         (int)incoming_header.transaction_id,
         (int)incoming_header.start.bits.complete,
         (int)incoming_header.start.bits.is_supported,
         (int)incoming_header.start.bits.has_data, incoming_header.size);

  if (incoming_header.start.bits.complete) {
    if (incoming_header.size) {
      // If the incoming header indicates it's already done and has a non-zero
      // size, read it now.
      cdebug(bonnet, "Slave already has a response, reading.\n");
      ret = visionbonnet_receive_data_buffer(bonnet, transaction,
          &incoming_header, &outgoing_header);
    } else {
      // If the incoming header indicates it complete and the size is zero, this
      // is a write-only transaction. Return.
      cdebug(bonnet, "Completed write-only transaction.\n");
    }
  } else {
    // If the incoming message isn't complete, enqueue work to the ongoing
    // transaction queue.
    cdebug(bonnet, "Slave has no response, deferring tid %d to ongoing queue\n",
           (int)incoming_header.transaction_id);
    visionbonnet_add_pending_transaction(bonnet, transaction);
    queue_delayed_work(bonnet->workqueue, &bonnet->ongoing_transaction_work, 0);
    transaction = NULL;  // Transfer our ref to ongoing_transaction_list.
  }

beach:
  if (ret) {
    // A fatal error occurred. Flag the current transaction with error
    // and let the error handler deal with any others.
    transaction_set_flags(bonnet, transaction, FLAG_ERROR);
    visionbonnet_fatal_error(bonnet);
  }
  mutex_lock(&bonnet->lock);
  if (!list_empty(&bonnet->incoming_transaction_queue)) {
    cdebug(bonnet, "Scheduling more work on incoming transactions\n");
    queue_work(bonnet->workqueue, &bonnet->incoming_transaction_work);
  }
  transaction_unref(bonnet, transaction);
  mutex_unlock(&bonnet->lock);
}

static void visionbonnet_ongoing_transaction_work_handler(
    struct work_struct *work) {
  int ret;
  header_t outgoing_header = {{0}};
  header_t incoming_header = {{0}};
  visionbonnet_t *bonnet =
      container_of(work, visionbonnet_t, ongoing_transaction_work.work);
  transaction_t *transaction = NULL;

  // Do poll 0 exchange.
  cdebug(bonnet, "Polling for completed transaction\n");

  // Exchange headers.
  ret = visionbonnet_header_exchange(bonnet, NULL, &incoming_header,
                                     &outgoing_header);
  if (ret) {
    goto beach;
  }

  if (incoming_header.start.bits.complete) {
    cdebug(bonnet, "tid %d complete\n", (int)incoming_header.transaction_id);
    transaction = visionbonnet_find_pending_transaction(
        bonnet, incoming_header.transaction_id);
    if (!transaction) {
      dev_err(&bonnet->spidev->dev,
              "No transaction with tid %d in pending queue\n",
              (int)incoming_header.transaction_id);
      ret = -ERESTART;
      goto beach;
    }

    if (incoming_header.start.bits.has_data && incoming_header.size) {
      cdebug(bonnet, "Slave has a response for tid %d, reading.\n",
             (int)incoming_header.transaction_id);
      ret = visionbonnet_receive_data_buffer(
          bonnet, transaction, &incoming_header, &outgoing_header);
    } else {
      cdebug(bonnet, "tid %d complete, no data\n",
             (int)incoming_header.transaction_id);
      mutex_lock(&transaction->lock);
      transaction->payload_len = 0;
      mutex_unlock(&transaction->lock);
      transaction_set_flags(bonnet, transaction, FLAG_RESPONSE);
    }
  }

beach:
  if (ret) {
    // A fatal error occurred. Flag the current transaction with error
    // and let the error handler deal with any others.
    transaction_set_flags(bonnet, transaction, FLAG_ERROR);
    visionbonnet_fatal_error(bonnet);
  }
  mutex_lock(&bonnet->lock);
  if (!list_empty(&bonnet->ongoing_transaction_list)) {
    cdebug(bonnet, "Scheduling poll\n");
    visionbonnet_dump_transactions(bonnet);
    queue_delayed_work(bonnet->workqueue, &bonnet->ongoing_transaction_work,
                       msecs_to_jiffies(POLL_INTERVAL_MS));
  }
  transaction_unref(bonnet, transaction);
  mutex_unlock(&bonnet->lock);
}

static int wait_flags(const usr_transaction_t *tr) {
  return tr->flags & USR_FLAG_ONEWAY ? FLAG_ACKED : FLAG_ACKED | FLAG_RESPONSE;
}

static long visionbonnet_transact_ioctl(struct file *filp,
                                        char __user *usr_arg, bool use_mmap) {
  visionbonnet_instance_t *instance = filp->private_data;
  visionbonnet_t *bonnet = instance->bonnet;

  const struct device *dev = &bonnet->spidev->dev;
  transaction_t *transaction = NULL;
  mmap_buffer_t *mmap_buffer = NULL;
  uint32_t buffer_len = 0;
  int ret = 0;
  usr_transaction_t usr_hdr;

  if (copy_from_user(&usr_hdr, usr_arg, sizeof(usr_hdr))) {
    dev_err(dev, "Invalid transaction header\n");
    return -EFAULT;
  }

  if (use_mmap) {
    cdebug(bonnet, "Using buffer for offset %d\n", usr_hdr.buffer_len_or_pgoff);
    mmap_buffer =
        visionbonnet_find_mmap_buffer(instance, usr_hdr.buffer_len_or_pgoff);
    if (!mmap_buffer)
      return -EINVAL;
    buffer_len = mmap_buffer->buffer_len;
  } else {
    buffer_len = usr_hdr.buffer_len_or_pgoff;
  }

  if (usr_hdr.payload_len == 0 || usr_hdr.payload_len > buffer_len) {
    dev_err(dev, "Invalid transaction header: payload_len=%u, buffer_len=%u\n",
        usr_hdr.payload_len, buffer_len);
    return -EINVAL;
  }

  mutex_lock(&bonnet->lock);
  ret = transaction_alloc(bonnet, &transaction, buffer_len);
  mutex_unlock(&bonnet->lock);
  if (ret) {
    return ret;
  }

  if (use_mmap) {
    memcpy(transaction->buffer, mmap_buffer->buffer, usr_hdr.payload_len);
  } else {
    if (copy_from_user(transaction->buffer, usr_arg + sizeof(usr_hdr),
                       usr_hdr.payload_len)) {
      dev_err(dev, "Failed to copy %u b payload\n", usr_hdr.payload_len);
      ret = -EFAULT;
      goto beach;
    }
  }
  transaction->payload_len = usr_hdr.payload_len;

  // Queue transaction work, giving one ref to the queue.
  atomic_inc(&transaction->refs);
  visionbonnet_put_incoming_transaction(bonnet, transaction);
  queue_work(bonnet->workqueue, &bonnet->incoming_transaction_work);

  // Now wait for transaction complete, error, or timeout.
  ret = wait_event_interruptible_timeout(bonnet->transaction_wait_queue,
      transaction_done_waiting(transaction, wait_flags(&usr_hdr)),
      msecs_to_jiffies(usr_hdr.timeout_ms));
  mutex_lock(&transaction->lock);
  if (ret > 0) {
    ret = transaction->flags & FLAG_ERROR ? -EFAULT : 0;
  } else if (ret == 0) {
    transaction->flags |= (FLAG_ERROR | FLAG_TIMEOUT);
    dev_notice(dev, "Transaction timed out, tid=%d\n",
               transaction_id(bonnet, transaction));
    ret = -ETIME;
  } else {
    transaction->flags |= FLAG_ERROR;
    if (ret == -ERESTARTSYS) {
      dev_notice(dev, "Transaction interrupted, tid=%d\n",
                 transaction_id(bonnet, transaction));
    }
  }
  mutex_unlock(&transaction->lock);

beach:
  mutex_lock(&transaction->lock);
  // Only copy the buffer back if we have a response.
  if (transaction->flags & FLAG_RESPONSE && transaction->payload_len) {
    if (use_mmap) {
       memcpy(mmap_buffer->buffer, transaction->buffer,
              transaction->payload_len);
    } else {
      if (copy_to_user(usr_arg + sizeof(usr_hdr), transaction->buffer,
                       transaction->payload_len)) {
        dev_err(dev, "Failed to copy transaction buffer to user\n");
        transaction->flags |= FLAG_ERROR;
        ret = -EFAULT;
      }
    }
  }

  // Lastly copy the updated header back.
  usr_hdr.flags = transaction->flags;
  usr_hdr.payload_len = transaction->payload_len;
  if (copy_to_user(usr_arg, &usr_hdr, sizeof(usr_hdr))) {
    dev_err(dev, "Failed to copy transaction header to user\n");
    ret = -EFAULT;
  }
  mutex_unlock(&transaction->lock);
  mutex_lock(&bonnet->lock);
  transaction_unref(bonnet, transaction);
  mutex_unlock(&bonnet->lock);

  if (use_mmap)
    mmap_buffer_release(mmap_buffer);

  return ret;
}

static long visionbonnet_ioctl(struct file *filp, unsigned int cmd,
                               unsigned long arg) {
  visionbonnet_instance_t *instance = filp->private_data;
  cdebug(instance->bonnet, "visionbonnet_ioctl cmd=%#.4x, arg=%lu", cmd, arg);

  switch (cmd) {
    case AIY_VISION_IOCTL_TRANSACT:
      return visionbonnet_transact_ioctl(filp, (char __user *)arg, false);
    case AIY_VISION_IOCTL_TRANSACT_MMAP:
      return visionbonnet_transact_ioctl(filp, (char __user *)arg, true);
    case AIY_VISION_IOCTL_RESET:
      return visionbonnet_myriad_reset(instance->bonnet);
    default:
      cdebug(instance->bonnet, "Unknown IOCTL %#.8x", cmd);
  }
  return 0;
}

static int visionbonnet_open(struct inode *inode, struct file *filp) {
  visionbonnet_instance_t *instance = NULL;
  visionbonnet_t *bonnet =
      container_of(inode->i_cdev, visionbonnet_t, spicomm_cdev);
  struct device *dev = &bonnet->spidev->dev;
  int i;

  instance = kzalloc(sizeof(*instance), GFP_KERNEL);
  if (!instance)
    return -ENOMEM;

  instance->bonnet = bonnet;
  mutex_init(&instance->lock);
  for (i = 0; i < NUM_MMAP_BUFFERS; ++i)
    mutex_init(&instance->mmap_buffers[i].lock);

  filp->private_data = instance;

  dev_notice(dev, "Device opened: 0x%p", instance);
  return 0;
}

static int visionbonnet_release(struct inode *inode, struct file *filp) {
  visionbonnet_instance_t *instance = filp->private_data;
  struct device *dev = &instance->bonnet->spidev->dev;
  int i;

  for (i = 0; i < NUM_MMAP_BUFFERS; ++i)
    mutex_destroy(&instance->mmap_buffers[i].lock);
  mutex_destroy(&instance->lock);
  kfree(instance);

  filp->private_data = NULL;

  dev_notice(dev, "Device released: 0x%p", instance);
  return 0;
}

static void visionbonnet_vma_close(struct vm_area_struct *vma) {
  mmap_buffer_t *buf = vma->vm_private_data;
  mmap_buffer_release(buf);
}

static vm_fault_t visionbonnet_vma_fault(struct vm_fault *vmf) {
  mmap_buffer_t *buf = vmf->vma->vm_private_data;
  vmf->page = vmalloc_to_page(
      buf->buffer + ((vmf->pgoff - vmf->vma->vm_pgoff) << PAGE_SHIFT));
  get_page(vmf->page);
  return 0;
}

struct vm_operations_struct visionbonnet_vm_ops = {
  .close = visionbonnet_vma_close,
  .fault = visionbonnet_vma_fault,
};

static int visionbonnet_mmap(struct file *filp, struct vm_area_struct *vma) {
  visionbonnet_instance_t *instance = filp->private_data;
  mmap_buffer_t *buf = visionbonnet_reserve_mmap_buffer(instance, vma);

  if (!buf)
    return -EINVAL;

  if (mmap_buffer_alloc(buf, vma->vm_end - vma->vm_start, vma->vm_pgoff) < 0)
    return -EINVAL;

  vma->vm_ops = &visionbonnet_vm_ops;
  vma->vm_flags |= VM_DONTEXPAND | VM_DONTDUMP | VM_DONTCOPY;
  vma->vm_private_data = buf;
  return 0;
}

static struct file_operations visionbonnet_fops = {
  .owner = THIS_MODULE,
  .open = visionbonnet_open,
  .release = visionbonnet_release,
  .unlocked_ioctl = visionbonnet_ioctl,
  .mmap = visionbonnet_mmap,
};

static int visionbonnet_uevent(struct device *dev,
                               struct kobj_uevent_env *env) {
  add_uevent_var(env, "DEVMODE=%#o", 0666);
  return 0;
}

static void visionbonnet_destroy(visionbonnet_t *bonnet) {
  device_destroy(bonnet->spicomm_class,
                 MKDEV(MAJOR(bonnet->spicomm_region), 0));
  class_destroy(bonnet->spicomm_class);
  unregister_chrdev_region(bonnet->spicomm_region, 1);
  cdev_del(&bonnet->spicomm_cdev);
  mutex_destroy(&bonnet->lock);
  destroy_workqueue(bonnet->workqueue);
}

static int visionbonnet_probe(struct spi_device *spi) {
  BUILD_BUG_ON(sizeof(header_start_t) != 1);
  BUILD_BUG_ON(sizeof(header_t) != 8);

  int ret;
  visionbonnet_t *bonnet = NULL;
  struct gpio_descs *vision_gpios = NULL;
  struct gpio_descs *aiy_gpios = NULL;

  dev_notice(&spi->dev, "Initializing\n");

  if (!spi_busnum_to_master(0)) {
    dev_err(&spi->dev, "No spi master found\n");
    return -ENODEV;
  }

  bonnet = devm_kzalloc(&spi->dev, sizeof(*bonnet), GFP_KERNEL);
  if (!bonnet) {
    dev_err(&spi->dev, "Out of memory\n");
    return -ENOMEM;
  }
  spi->dev.platform_data = bonnet;

  bonnet->spidev = spi;
  atomic_set(&bonnet->slave_ready, 0);

  // As all operations are blocking and should be executed serially, use a
  // dedicated driver workqueue.
  bonnet->workqueue = create_singlethread_workqueue("vision_wq");
  mutex_init(&bonnet->lock);
  INIT_LIST_HEAD(&bonnet->incoming_transaction_queue);
  INIT_LIST_HEAD(&bonnet->ongoing_transaction_list);
  init_waitqueue_head(&bonnet->transaction_wait_queue);
  init_waitqueue_head(&bonnet->slave_ready_wait_queue);
  INIT_WORK(&bonnet->incoming_transaction_work,
            visionbonnet_incoming_transaction_work_handler);
  INIT_DELAYED_WORK(&bonnet->ongoing_transaction_work,
                    visionbonnet_ongoing_transaction_work_handler);

  cdev_init(&bonnet->spicomm_cdev, &visionbonnet_fops);
  bonnet->spicomm_cdev.owner = THIS_MODULE;
  alloc_chrdev_region(&bonnet->spicomm_region, 0, 1, "vision_spicomm");
  cdev_add(&bonnet->spicomm_cdev, MKDEV(MAJOR(bonnet->spicomm_region), 0), 1);
  bonnet->spicomm_class = class_create(THIS_MODULE, "spicomm");
  bonnet->spicomm_class->dev_uevent = visionbonnet_uevent;
  bonnet->spicomm_device = device_create(
      bonnet->spicomm_class, NULL, MKDEV(MAJOR(bonnet->spicomm_region), 0),
      NULL, "vision_spicomm");

  vision_gpios = devm_gpiod_get_array(&spi->dev, "vision", GPIOD_ASIS);
  if (IS_ERR(vision_gpios)) {
    ret = PTR_ERR(vision_gpios);
    dev_err(&spi->dev, "Failed to bind vision GPIOs: %d\n", ret);
    goto beach;
  }
  cdebug(bonnet, "Bound %d vision GPIOs\n", vision_gpios->ndescs);

  aiy_gpios = devm_gpiod_get_array(&spi->dev, "aiy", GPIOD_ASIS);
  if (IS_ERR(aiy_gpios)) {
    ret = PTR_ERR(aiy_gpios);
    dev_err(&spi->dev, "Failed to bind reset GPIO: %d\n", ret);
    goto beach;
  }
  cdebug(bonnet, "Bound reset GPIO\n");

  ret = devm_request_irq(&spi->dev,
      gpiod_to_irq(vision_gpios->desc[PI_GPIO_SLAVE_READY_INDEX]),
      visionbonnet_slave_ready_isr, IRQF_TRIGGER_FALLING, "slave_ready_isr",
      bonnet);
  if (ret) {
    dev_err(&spi->dev, "Failed to claim slave ready IRQ: %d\n", ret);
    goto beach;
  }

  ret = gpiod_direction_output(vision_gpios->desc[PI_GPIO_UNUSED_INDEX], 1);
  if (ret) {
    dev_err(&spi->dev, "Failed to set unused GPIO direction: %d\n", ret);
    goto beach;
  }

  bonnet->me_gpio = vision_gpios->desc[PI_GPIO_MASTER_ERROR_INDEX];
  ret = gpiod_direction_output(bonnet->me_gpio, 1);
  if (ret) {
    dev_err(&spi->dev, "Failed to set master error GPIO direction: %d\n", ret);
    goto beach;
  }

  bonnet->cs_gpio = vision_gpios->desc[PI_GPIO_CHIP_SELECT_INDEX];
  ret = gpiod_direction_output(bonnet->cs_gpio, 1);
  if (ret) {
    dev_err(&spi->dev, "Failed to set chip select GPIO direction: %d\n", ret);
    goto beach;
  }

  bonnet->reset_gpio = aiy_gpios->desc[AIY_GPIO_RESET_INDEX];
  ret = gpiod_direction_output(bonnet->reset_gpio, 1);
  if (ret) {
    dev_err(&spi->dev, "Failed to set reset GPIO direction: %d\n", ret);
    goto beach;
  }

  // Re-initialize spi without automatic control of CS.
  // This facilitates large transfers with a single toggling of CS, to
  // make things like booting the bonnet happy.
  spi->mode |= SPI_NO_CS;
  spi->cs_gpio = -1;
  ret = visionbonnet_set_spi_freq(bonnet, SPI_NORMAL_FREQ);
  if (ret) {
    dev_err(&spi->dev, "spi_setup failed: %d\n", ret);
    goto beach;
  }

  // Reset and load the bonnet.
  dev_notice(&spi->dev, "Resetting myriad on probe");
  ret = visionbonnet_myriad_reset(bonnet);
  if (ret) {
    dev_err(&spi->dev, "Initial bonnet boot failed: %d\n", ret);
    goto beach;
  }

beach:
  if (ret) {
    visionbonnet_destroy(bonnet);
  }
  return ret;
}

static int visionbonnet_remove(struct spi_device *spi) {
  visionbonnet_t *bonnet = spi->dev.platform_data;
  mutex_lock(&bonnet->lock);
  visionbonnet_cancel_transactions(bonnet);
  mutex_unlock(&bonnet->lock);
  drain_workqueue(bonnet->workqueue);

  visionbonnet_destroy(bonnet);
  return 0;
}

static const struct of_device_id visionbonnet_of_match[] = {
    {
        .compatible = "google,visionbonnet",
    },
    {},
};
MODULE_DEVICE_TABLE(of, visionbonnet_of_match);

static const struct spi_device_id gvb_id[] = {{"visionbonnet", 0}, {}};
MODULE_DEVICE_TABLE(spi, gvb_id);

static struct spi_driver visionbonnet_driver = {
    .driver =
        {
            .name = "aiy-vision",
            .owner = THIS_MODULE,
            .of_match_table = of_match_ptr(visionbonnet_of_match),
        },
    .probe = visionbonnet_probe,
    .remove = visionbonnet_remove,
};
module_spi_driver(visionbonnet_driver);

MODULE_AUTHOR("Jonas Larsson <ljonas@google.com>");
MODULE_AUTHOR("Michael Brooks <mrbrooks@google.com>");
MODULE_AUTHOR("Alex Van Damme <atv@google.com>");
MODULE_AUTHOR("Leonid Lobachev <leonidl@google.com>");
MODULE_AUTHOR("Dmitry Kovalev <dkovalev@google.com>");
MODULE_ALIAS("spi:visionbonnet");
MODULE_DESCRIPTION("Driver for Google AIY Vision Bonnet");
MODULE_LICENSE("GPL v2");
