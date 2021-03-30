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
#include <linux/bitops.h>
#include <linux/device.h>
#include <linux/err.h>
#include <linux/gpio.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/slab.h>

static const char *const aiy_gpio_names[AIY_GPIO_PIN_COUNT] = {
	"AIY_PA02",
	"AIY_PA03",
	"AIY_USER0",
	"AIY_USER1",
	"AIY_PA06",
	"AIY_PA07",
	"AIY_PA08",
	"AIY_PA09",
	"AIY_USER2",
	"AIY_USER3",
	"AIY_PA16",
	"AIY_PA17",
	"AIY_PA24",
	"AIY_LED0",
	"AIY_LED1",
};

static struct aiy_io_i2c* to_aiy(struct gpio_chip *chip) {
	struct aiy_io_i2c *aiy = gpiochip_get_data(chip);
	return aiy;
}

static int aiy_gpio_request(struct gpio_chip *chip, unsigned int offset)
{
	struct aiy_io_i2c *aiy = to_aiy(chip);
	int err;

	dev_dbg(chip->parent, "Request GPIO #%d\n", offset);
	err = aiy_io_request_pin(aiy, offset, AIY_PIN_OPTION_USED_GPIO);
	if (err < 0) {
		dev_err(chip->parent, "Request GPIO #%d failed: %d",
			offset, err);
	}
	return err;
}

static void aiy_gpio_free(struct gpio_chip *chip, unsigned int offset)
{
	struct aiy_io_i2c *aiy = to_aiy(chip);
	dev_dbg(chip->parent, "Free GPIO #%d\n", offset);

	if (regmap_write(aiy->regmap, AIY_REG_GPIO_BASE_MODE + offset,
			 AIY_GPIO_MODE_INPUT_HIZ) < 0)
		dev_err(chip->parent, "Cannot set HIZ mode for pin %d.\n",
			offset);

	if (aiy_io_free_pin(aiy, offset, AIY_PIN_OPTION_USED_GPIO) < 0)
		dev_err(chip->parent, "Cannot free GPIO pin %d.\n", offset);
}

static int aiy_gpio_direction_input(struct gpio_chip *chip, unsigned int offset)
{
	struct aiy_io_i2c *aiy = to_aiy(chip);
	int err;

	dev_dbg(chip->parent, "Set GPIO #%d as input\n", offset);
	err = regmap_write(aiy->regmap, AIY_REG_GPIO_BASE_MODE + offset,
			   AIY_GPIO_MODE_INPUT_HIZ);
	if (err < 0) {
		dev_err(chip->parent, "Set GPIO #%d as input failed: %d\n",
			offset, err);
		return err;
	}
	return 0;
}

static int aiy_gpio_get(struct gpio_chip *chip, unsigned int offset)
{
	struct aiy_io_i2c *aiy = to_aiy(chip);
	u8 bytes[2];
	int err;

	dev_dbg(chip->parent, "Get GPIO #%d value\n", offset);
	err = regmap_bulk_read(aiy->regmap, AIY_REG_GPIO_INPUT_LEVEL, bytes,
			       sizeof(bytes));
	if (err < 0) {
		dev_err(chip->parent, "Get GPIO #%d value failed: %d\n",
			offset, err);
		return err;
	}
	return ((bytes[1] << 8) | bytes[0]) & BIT(offset) ? 1 : 0;
}


static int aiy_gpio_set_impl(struct gpio_chip *chip, unsigned int offset,
			     int value) {
	struct aiy_io_i2c *aiy = to_aiy(chip);
	const int is_high = (offset > 7);
	const u16 level = (value ? BIT(offset) : 0) >> (8 * is_high);
	const u16 mask = BIT(offset) >> (8 * is_high);
	const u8 reg = AIY_REG_GPIO_OUTPUT_LEVEL + is_high;
	int err = regmap_update_bits(aiy->regmap, reg, mask, level);
	if (err < 0) {
		dev_err(chip->parent, "Set GPIO #%d to value %d failed: %d\n",
			offset, value, err);
	}
	return err;
}

static void aiy_gpio_set(struct gpio_chip *chip, unsigned int offset, int value)
{
	dev_dbg(chip->parent, "Set GPIO #%d to value %d\n", offset, value);
	aiy_gpio_set_impl(chip, offset, value);
}

static int aiy_gpio_direction_output(struct gpio_chip *chip,
				     unsigned int offset, int value)
{
	struct aiy_io_i2c *aiy = to_aiy(chip);
	int err;

	dev_dbg(chip->parent, "Set GPIO #%d as output to value %d\n",
		offset, value);
	err = regmap_write(aiy->regmap, AIY_REG_GPIO_BASE_MODE + offset,
			   AIY_GPIO_MODE_OUTPUT);
	if (err < 0) {
		dev_err(chip->parent,
			"Set GPIO #%d as output failed: %d\n", offset, err);
		return err;
	}

	return aiy_gpio_set_impl(chip, offset, value);
}

static int aiy_gpio_probe(struct platform_device *pdev)
{
	struct aiy_io_i2c *aiy = dev_get_drvdata(pdev->dev.parent);
	struct gpio_chip *chip;
	int err;

	chip = devm_kzalloc(&pdev->dev, sizeof(*chip), GFP_KERNEL);
	if (!chip) return -ENOMEM;

	chip->label = "gpio-aiy-io",
	chip->owner = THIS_MODULE;
	chip->parent = &pdev->dev;
	chip->request = aiy_gpio_request;
	chip->free = aiy_gpio_free;
	chip->direction_input = aiy_gpio_direction_input;
	chip->direction_output = aiy_gpio_direction_output;
	chip->get = aiy_gpio_get;
	chip->set = aiy_gpio_set;
	chip->base = -1;
	chip->ngpio = ARRAY_SIZE(aiy_gpio_names);
	chip->names = aiy_gpio_names;
	chip->can_sleep = true;

	err = devm_gpiochip_add_data(&pdev->dev, chip, aiy);
	if (err < 0) {
		dev_err(&pdev->dev, "Could not register AIY gpio chip: %d\n",
			err);
		return err;
	}
	dev_info(&pdev->dev, "Driver loaded\n");
	return 0;
}

static int aiy_gpio_remove(struct platform_device *pdev)
{
	dev_info(&pdev->dev, "Driver removed\n");
	return 0;
}

static const struct of_device_id aiy_gpio_of_match[] = {
	{.compatible = "google,gpio-aiy-io",},
	{},
};
MODULE_DEVICE_TABLE(of, aiy_gpio_of_match);

static const struct platform_device_id aiy_gpio_id_table[] = {
	{"gpio-aiy-io",},
	{},
};
MODULE_DEVICE_TABLE(platform, aiy_gpio_id_table);

static struct platform_driver aiy_gpio_driver = {
	.driver = {
		.name = "gpio-aiy-io",
		.of_match_table = of_match_ptr(aiy_gpio_of_match),
	},
	.probe = aiy_gpio_probe,
	.remove = aiy_gpio_remove,
	.id_table = aiy_gpio_id_table,
};
module_platform_driver(aiy_gpio_driver);

MODULE_DESCRIPTION("AIY GPIO Driver");
MODULE_ALIAS("platform:gpio-aiy-io");
MODULE_AUTHOR("Henry Herman <henryherman@google.com>");
MODULE_AUTHOR("Dmitry Kovalev <dkovalev@google.com>");
MODULE_LICENSE("GPL v2");
