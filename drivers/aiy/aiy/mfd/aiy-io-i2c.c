/*
 * AIY GPIO/PWM Driver
 *
 * Author: Henry Herman <henryherman@google.com>
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
#include "../include/aiy-io.h"
#include <linux/err.h>
#include <linux/firmware.h>
#include <linux/gpio.h>
#include <linux/i2c.h>
#include <linux/init.h>
#include <linux/mfd/core.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/of.h>
#include <linux/slab.h>

static const struct mfd_cell aiy_io_devs[] = {
	{
	 .name = "gpio-aiy-io",
	 .of_compatible = "google,gpio-aiy-io",
	 },
	{
	 .name = "pwm-aiy-io",
	 .of_compatible = "google,pwm-aiy-io",
	 },
	{
	 .name = "aiy-adc",
	 .of_compatible = "google,aiy-adc",
	 },
};

#define MCU_MAX_FIRMWARE_SIZE (16384 - 5120)

#define MCU_BOOTLOADER_ADDR 0x61

#define MCU_REG_RESET 0x00
#define MCU_RESET_CODE 0xA0

#define MCU_BOOT_WRITE 0xAA
#define MCU_BOOT_DONE 0xEE

#define MCU_PAGE_SIZE 64

struct mcu_packet {
	u8 offset;
	u8 control;
	u16 address;
	u16 page_size;
	u8 page[MCU_PAGE_SIZE];
} __attribute__ ((packed, aligned(1)));

static const char MCU_RESET[2] = { MCU_REG_RESET, MCU_RESET_CODE };

static void aiy_io_mcu_packet(struct mcu_packet *packet, u8 control,
			      u16 address, const u8 *page, size_t page_size)
{
	memset(packet, 0, sizeof(*packet));
	packet->offset = 0;
	packet->control = control;
	packet->address = address;
	packet->page_size = page_size;
	if (page != NULL && page_size > 0)
		memcpy(packet->page, page, page_size);
}

static int aiy_io_mcu_write_direct(struct i2c_client *i2c, u16 addr,
				   const void *buf, size_t size)
{
	struct i2c_msg msg = {
		.addr = addr ? addr : i2c->addr,
		.flags = 0,	/* write */
		.len = size,
		.buf = (u8 *) buf,
	};
	return __i2c_transfer(i2c->adapter, &msg, 1);
}

static int aiy_io_mcu_wait_alive(struct i2c_client *i2c)
{
	u8 reg = 0;
	int err = 0;
	int attempts = 50;	/* ~5 seconds of waiting */
	while (attempts > 0) {
		err = aiy_io_mcu_write_direct(i2c, 0, &reg, 1);
		if (err >= 0)
			break;
		msleep(100);
		--attempts;
	}
	return err;
}

static int aiy_io_reset(struct i2c_client *i2c)
{
	int err;

	dev_info(&i2c->dev, "MCU Reset\n");
	i2c_lock_bus(i2c->adapter, I2C_LOCK_ROOT_ADAPTER);
	err = aiy_io_mcu_write_direct(i2c, 0, MCU_RESET, sizeof(MCU_RESET));
	if (err >= 0)
		err = aiy_io_mcu_wait_alive(i2c);
	i2c_unlock_bus(i2c->adapter, I2C_LOCK_ROOT_ADAPTER);
	return err;
}

static ssize_t aiy_io_status_show(struct device *dev,
				  struct device_attribute *attr, char *buf)
{
	char status_message[AIY_STATUS_MESSAGE_SIZE + 1] = { 0 };
	struct aiy_io_i2c *aiy = dev_get_drvdata(dev);
	int err = regmap_bulk_read(aiy->regmap, AIY_REG_MESSAGE_BASE,
				   status_message, AIY_STATUS_MESSAGE_SIZE);
	if (err < 0) {
		dev_err(dev, "Failed to read MCU status: %d\n", err);
		return err;
	}
	return sprintf(buf, "%s\n", status_message);
}

static ssize_t aiy_io_error_code_show(struct device *dev,
				      struct device_attribute *attr, char *buf)
{
	u32 error_code;
	struct aiy_io_i2c *aiy = dev_get_drvdata(dev);
	int err = regmap_bulk_read(aiy->regmap, AIY_REG_ERROR_CODE,
				   &error_code, sizeof(error_code));

	if (err < 0) {
		dev_err(dev, "Failed to read MCU error_code: %d\n", err);
		return err;
	}
	return sprintf(buf, "0x%08x\n", error_code);
}

static ssize_t aiy_io_reset_store(struct device *dev,
				  struct device_attribute *attr,
				  const char *buf, size_t count)
{
	int err = aiy_io_reset(to_i2c_client(dev));

	if (err < 0) {
		dev_err(dev, "Failed to reset MCU: %d\n", err);
		return err;
	}
	return count;
}

static ssize_t aiy_io_update_firmware(struct device *dev,
				      struct device_attribute *attr,
				      const char *buf, size_t count)
{
	int err;
	struct mcu_packet packet;
	size_t remaining_size;
	const struct firmware *fw;
	u16 page_offset, page_size;
	struct i2c_client *i2c = to_i2c_client(dev);

	char fw_name[100 + 1] = { 0 };
	sscanf(buf, "%100s\n", fw_name);

	dev_info(dev, "MCU firmware file: %s", fw_name);
	err = request_firmware_direct(&fw, fw_name, dev);
	if (err < 0) {
		dev_err(dev, "Cannot read firmware file: %d\n", err);
		return err;
	}

	dev_info(dev, "MCU firmware size: %zu", fw->size);
	if (fw->size > MCU_MAX_FIRMWARE_SIZE) {
		dev_err(dev, "MCU firmware size exceeds max allowed %d bytes",
			MCU_MAX_FIRMWARE_SIZE);
		return -EINVAL;
	}

	i2c_lock_bus(i2c->adapter, I2C_LOCK_ROOT_ADAPTER);

	/* Reset MCU */
	err = aiy_io_mcu_write_direct(i2c, 0, MCU_RESET, sizeof(MCU_RESET));
	if (err < 0) {
		dev_err(dev, "Reset failed: %d", err);
		goto error;
	}

	msleep(80);		/* Give MCU some time to boot */

	/* Send firmware */
	remaining_size = fw->size;
	while (remaining_size > 0) {
		page_size = min(remaining_size, (size_t) MCU_PAGE_SIZE);
		page_offset = fw->size - remaining_size;
		aiy_io_mcu_packet(&packet, MCU_BOOT_WRITE, page_offset,
				  &fw->data[page_offset], page_size);

		dev_info(dev, "Firmware page: offset=%d, size=%d", page_offset,
			 page_size);
		err =
		    aiy_io_mcu_write_direct(i2c, MCU_BOOTLOADER_ADDR, &packet,
					    sizeof(packet));
		if (err < 0) {
			dev_err(dev, "Packet write failed: %d", err);
			goto error;
		}
		remaining_size -= page_size;
		msleep(1);	/* MCU writes data to NVM */
	}

	/* Finish update */
	aiy_io_mcu_packet(&packet, MCU_BOOT_DONE, fw->size, NULL, 0);
	err =
	    aiy_io_mcu_write_direct(i2c, MCU_BOOTLOADER_ADDR, &packet,
				    sizeof(packet));
	if (err < 0) {
		dev_err(dev, "Packet write failed: %d", err);
		goto error;
	}

error:
	if (err >= 0)
		err = aiy_io_mcu_wait_alive(i2c);

	i2c_unlock_bus(i2c->adapter, I2C_LOCK_ROOT_ADAPTER);
	release_firmware(fw);

	return err < 0 ? err : count;
}

int aiy_io_request_pin(struct aiy_io_i2c *aiy, unsigned int offset,
		       enum aiy_pin_usage_option pin_usage) {
	int err = 0;

	if (offset >= AIY_GPIO_PIN_COUNT)
		return -EINVAL;

	mutex_lock(&aiy->lock);

	if (aiy->pin_usage[offset] == pin_usage) {
		goto done;
	}

	if (aiy->pin_usage[offset] != AIY_PIN_OPTION_UNUSED) {
		err = -EBUSY;
		goto done;
	}

	aiy->pin_usage[offset] = pin_usage;

done:
	mutex_unlock(&aiy->lock);
	return err;
}
EXPORT_SYMBOL_GPL(aiy_io_request_pin);

int aiy_io_free_pin(struct aiy_io_i2c *aiy, unsigned int offset,
		    enum aiy_pin_usage_option pin_usage) {
	int err = 0;

	if (offset >= AIY_GPIO_PIN_COUNT)
		return -EINVAL;

	mutex_lock(&aiy->lock);

	if (aiy->pin_usage[offset] != pin_usage) {
		err = -EINVAL;
		goto done;
	}

	aiy->pin_usage[offset] = AIY_PIN_OPTION_UNUSED;

done:
	mutex_unlock(&aiy->lock);
	return err;
}
EXPORT_SYMBOL_GPL(aiy_io_free_pin);

static DEVICE_ATTR(status_message, S_IRUGO, aiy_io_status_show, NULL);
static DEVICE_ATTR(error_code, S_IRUGO, aiy_io_error_code_show, NULL);
static DEVICE_ATTR(reset, S_IWUSR, NULL, aiy_io_reset_store);
static DEVICE_ATTR(update_firmware, S_IWUSR, NULL, aiy_io_update_firmware);

static struct attribute *aiy_io_sysfs_entries[] = {
	&dev_attr_status_message.attr,
	&dev_attr_error_code.attr,
	&dev_attr_reset.attr,
	&dev_attr_update_firmware.attr,
	NULL,
};

static const struct attribute_group aiy_io_attr_group = {
	.attrs = aiy_io_sysfs_entries,
};

static const struct regmap_range aiy_io_i2c_volatile_ranges[] = {
	{.range_min = AIY_REG_GPIO_MODE_PA02,
	 .range_max = AIY_REG_GPIO_MODE_PA03},
	{.range_min = AIY_REG_GPIO_INPUT_LEVEL,
	 .range_max = AIY_GPIO_MAX_REGISTERS},
};

static const struct regmap_access_table aiy_io_i2c_volatile_table = {
	.yes_ranges = aiy_io_i2c_volatile_ranges,
	.n_yes_ranges = ARRAY_SIZE(aiy_io_i2c_volatile_ranges),
};

static const struct regmap_config aiy_io_i2c_regmap_config = {
	.reg_bits = 8,
	.val_bits = 8,
	.max_register = AIY_GPIO_MAX_REGISTERS,
	.volatile_table = &aiy_io_i2c_volatile_table,
	.cache_type = REGCACHE_NONE,
	.can_multi_write = true,
};

static int aiy_io_i2c_probe(struct i2c_client *i2c,
			    const struct i2c_device_id *id)
{
	int err;
	struct device *dev = &i2c->dev;
	struct device_node *node;
	struct aiy_io_i2c *aiy = devm_kzalloc(dev, sizeof(*aiy), GFP_KERNEL);
	const char *board_type;

	if (!aiy)
		return -ENOMEM;

	aiy->regmap = devm_regmap_init_i2c(i2c, &aiy_io_i2c_regmap_config);
	if (IS_ERR(aiy->regmap)) {
		err = PTR_ERR(aiy->regmap);
		dev_err(dev, "Failed to initialize regmap: %d\n", err);
		return err;
	}

	mutex_init(&aiy->lock);

	// Check for board type
	node = dev->of_node;
	err = of_property_read_string(node, "type", &board_type);
	// Set the board type
	aiy->type = AIY_BOARD_TYPE_VISIONBONNET;
	if (err < 0) {
		dev_warn(dev, "Board type unset, use default");
	} else if (strcmp(board_type, AIY_BOARD_TYPE_NAME_VOICEBONNET) == 0) {
		dev_info(dev, "Setting board type voice");
		aiy->type = AIY_BOARD_TYPE_VOICEBONNET;
	} else if (strcmp(board_type, AIY_BOARD_TYPE_NAME_VISIONBONNET) == 0) {
		dev_info(dev, "Setting board type vision");
		aiy->type = AIY_BOARD_TYPE_VISIONBONNET;
	} else {
		// Default to vision bonnet
		dev_warn(dev, "Board type unknown, use default");
	}

	i2c_set_clientdata(i2c, aiy);

	err = sysfs_create_group(&dev->kobj, &aiy_io_attr_group);
	if (err) {
		dev_err(dev, "Failed to create sysfs nodes: %d\n", err);
		return err;
	}

	err = mfd_add_devices(dev, PLATFORM_DEVID_NONE, aiy_io_devs,
			      ARRAY_SIZE(aiy_io_devs), NULL, 0, NULL);
	if (err < 0)
		dev_warn(dev, "Failed to add mfd devices: %d\n", err);

	dev_info(dev, "Driver loaded\n");
	return 0;
}

static int aiy_io_i2c_remove(struct i2c_client *i2c)
{
	struct device *dev = &i2c->dev;
	int err = aiy_io_reset(i2c);

	if (err < 0)
		dev_warn(dev, "Failed to reset MCU: %d\n", err);
	mfd_remove_devices(dev);
	sysfs_remove_group(&dev->kobj, &aiy_io_attr_group);

	dev_info(dev, "Driver removed\n");
	return 0;
}

static const struct of_device_id aiy_io_i2c_of_match[] = {
	{
	 .compatible = "google,aiy-io-i2c",
	 },
	{}
};

MODULE_DEVICE_TABLE(of, aiy_io_i2c_of_match);

static const struct i2c_device_id aiy_io_i2c_id[] = {
	{"aiy-io-i2c", 0},
	{},
};

MODULE_DEVICE_TABLE(i2c, aiy_io_i2c_id);

static struct i2c_driver aiy_io_i2c_driver = {
	.driver = {
		   .name = "aiy-io-i2c",
		   .of_match_table = of_match_ptr(aiy_io_i2c_of_match),
		   },
	.probe = aiy_io_i2c_probe,
	.remove = aiy_io_i2c_remove,
	.id_table = aiy_io_i2c_id,
};

module_i2c_driver(aiy_io_i2c_driver);

MODULE_DESCRIPTION("AIY MFD Driver");
MODULE_AUTHOR("Henry Herman <henryherman@google.com>");
MODULE_AUTHOR("Dmitry Kovalev <dkovalev@google.com>");
MODULE_LICENSE("GPL v2");
