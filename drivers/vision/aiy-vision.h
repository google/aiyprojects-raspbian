#ifndef _STAGING_MYRIAD_AIY_VISION_H
#define _STAGING_MYRIAD_AIY_VISION_H

#include <linux/bitops.h>
#include <linux/ioctl.h>
#include <linux/types.h>

#define AIY_VISION_IOCTL_RESET _IO(0x89, 1)
#define AIY_VISION_IOCTL_TRANSACT _IOWR(0x89, 3, usr_transaction_t)
#define AIY_VISION_IOCTL_TRANSACT_MMAP _IOWR(0x89, 4, usr_transaction_t)

#define USR_FLAG_ONEWAY BIT(31)

#define FLAG_ERROR BIT(0)
#define FLAG_TIMEOUT BIT(1)
#define FLAG_OVERFLOW BIT(2)
#define FLAG_ACKED BIT(3)
#define FLAG_RESPONSE BIT(4)

typedef struct {
  uint32_t flags;
  uint32_t timeout_ms;
  uint32_t buffer_len_or_pgoff;
  uint32_t payload_len;
} usr_transaction_t;

#endif  // _STAGING_MYRIAD_AIY_VISION_H
