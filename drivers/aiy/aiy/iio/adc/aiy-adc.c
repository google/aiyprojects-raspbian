/*
 * AIY ADC Driver
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
#include "../../include/aiy-io.h"
#include <linux/delay.h>
#include <linux/iio/iio.h>
#include <linux/iio/driver.h>
#include <linux/iio/machine.h>
#include <linux/module.h>
#include <linux/platform_device.h>

enum aiy_adc_channel {
	/* Builtin power rails */
	AIY_ADC_CHAN_V3P3 = 0,  /* PA02 */
	AIY_ADC_CHAN_V1P8,      /* PA03 */
	AIY_ADC_CHAN_V1P2,      /* PA06 */
	AIY_ADC_CHAN_V0P9,      /* PA07 */

	/* User exposed GPIO/ADC */
	AIY_ADC_CHAN_USER0,     /* PA04 */
	AIY_ADC_CHAN_USER1,     /* PA05 */
	AIY_ADC_CHAN_USER2,     /* PA10 */
	AIY_ADC_CHAN_USER3,     /* PA11 */
};

struct aiy_adc_pin_config {
	u8 value_reg;
	u8 pin_offset;
};

static const struct aiy_adc_pin_config aiy_adc_pin_configs[] = {
	[AIY_ADC_CHAN_V3P3] = {AIY_REG_ADC_VALUE_PA02,
			       AIY_GPIO_PIN_PA02_OFFSET},
	[AIY_ADC_CHAN_V1P8] = {AIY_REG_ADC_VALUE_PA03,
			       AIY_GPIO_PIN_PA03_OFFSET},
	[AIY_ADC_CHAN_V1P2] = {AIY_REG_ADC_VALUE_PA06,
			       AIY_GPIO_PIN_PA06_OFFSET},
	[AIY_ADC_CHAN_V0P9] = {AIY_REG_ADC_VALUE_PA07,
			       AIY_GPIO_PIN_PA07_OFFSET},
	[AIY_ADC_CHAN_USER0] = {AIY_REG_ADC_VALUE_PA04,
				AIY_GPIO_PIN_PA04_OFFSET},
	[AIY_ADC_CHAN_USER1] = {AIY_REG_ADC_VALUE_PA05,
				AIY_GPIO_PIN_PA05_OFFSET},
	[AIY_ADC_CHAN_USER2] = {AIY_REG_ADC_VALUE_PA10,
				AIY_GPIO_PIN_PA10_OFFSET},
	[AIY_ADC_CHAN_USER3] = {AIY_REG_ADC_VALUE_PA11,
				AIY_GPIO_PIN_PA11_OFFSET},
};

static int aiy_adc_read_adc(struct device *dev, struct aiy_io_i2c *aiy,
			    int address)
{
	int ret;
	u16 val;
	const struct aiy_adc_pin_config *config = &aiy_adc_pin_configs[address];
	const u8 offset = config->pin_offset;
	const u8 mode_reg = AIY_REG_GPIO_BASE_MODE + offset;
	const u8 value_reg = config->value_reg;

	ret = aiy_io_request_pin(aiy, offset, AIY_PIN_OPTION_USED_ADC);
	if (ret < 0)
		return ret;

	ret = regmap_write(aiy->regmap, mode_reg, AIY_GPIO_MODE_ADC);
	if (ret < 0)
		goto done;
	msleep(10);

	ret = regmap_bulk_read(aiy->regmap, value_reg, &val, sizeof(val));

	if (regmap_write(aiy->regmap, mode_reg, AIY_GPIO_MODE_INPUT_HIZ) < 0)
		dev_err(dev, "Cannot set HIZ mode for pin %d.\n", offset);

done:
	if (aiy_io_free_pin(aiy, offset, AIY_PIN_OPTION_USED_ADC) < 0)
		dev_err(dev, "Cannot free ADC pin %d.\n", offset);

	if (ret < 0) {
		dev_err(dev, "Failed to get ADC value: %d", ret);
		return ret;
	}

	/* ADC is 12 bit, mask bits */
	val &= 0x0FFF;

	/* 3.3V pin has a voltage divider 1/2 */
	return address == AIY_ADC_CHAN_V3P3 ? 2 * val : val;
};

static int aiy_adc_count_to_volts(int val)
{
	/* 1.65 Reference voltage
	   Internal voltage divider set to 1/2
	   12 bit ADC
	   Return answer in miliVolts
	   K = 1.65 * 2.0 / (2 ^ 12 - 1) * 1000
	   K = 0.806
	   V = Counts * 806 / 1000
	 */
	return val * 806 / 1000;
}

static int aiy_adc_read_raw(struct iio_dev *indio_dev,
			    const struct iio_chan_spec *chan, int *val,
			    int *val2, long mask)
{
	struct device *dev = indio_dev->dev.parent;
	struct aiy_io_i2c *aiy = dev_get_drvdata(dev->parent);
	int value = aiy_adc_read_adc(dev, aiy, chan->address);
	if (value < 0) return value;

	switch (mask) {
	case IIO_CHAN_INFO_RAW:
		*val = value;
		return IIO_VAL_INT;
	case IIO_CHAN_INFO_PROCESSED:
		*val = aiy_adc_count_to_volts(value);
		return IIO_VAL_INT;
	default:
		return -EINVAL;
	}
}

static const struct iio_info aiy_adc_info = {
	.read_raw = &aiy_adc_read_raw,
};

#define AIY_ADC_CHANNEL(_ch, _address, _mask, _name)                           \
	{                                                                      \
		.type = IIO_VOLTAGE,                                           \
		.indexed = 1,                                                  \
		.channel = (_ch),                                              \
		.address = (_address),                                         \
		.info_mask_separate = (_mask),                                 \
		.extend_name = (_name)                                         \
	}

#define AIY_ADC_CHANNEL_BOTH(_ch, _address, _name)                             \
	AIY_ADC_CHANNEL(_ch, _address, BIT(IIO_CHAN_INFO_RAW), _name),         \
	AIY_ADC_CHANNEL(_ch, _address, BIT(IIO_CHAN_INFO_PROCESSED), _name)

static const struct iio_chan_spec aiy_adc_channels[] = {
	/* Both Vision and Voice */
	AIY_ADC_CHANNEL_BOTH(0, AIY_ADC_CHAN_USER0, "user0"),
	AIY_ADC_CHANNEL_BOTH(1, AIY_ADC_CHAN_USER1, "user1"),
	AIY_ADC_CHANNEL_BOTH(2, AIY_ADC_CHAN_USER2, "user2"),
	AIY_ADC_CHANNEL_BOTH(3, AIY_ADC_CHAN_USER3, "user3"),

	/* Only Vision */
	AIY_ADC_CHANNEL_BOTH(4, AIY_ADC_CHAN_V3P3, "v3p3"),
	AIY_ADC_CHANNEL_BOTH(5, AIY_ADC_CHAN_V1P8, "v1p8"),
	AIY_ADC_CHANNEL_BOTH(6, AIY_ADC_CHAN_V1P2, "v1p2"),
	AIY_ADC_CHANNEL_BOTH(7, AIY_ADC_CHAN_V0P9, "v0p9"),
};

static int aiy_adc_probe(struct platform_device *pdev)
{
	int ret;
	struct device *dev = &pdev->dev;
	struct aiy_io_i2c *aiy = dev_get_drvdata(dev->parent);
	struct iio_dev *iio_dev;

	iio_dev = devm_iio_device_alloc(dev, 0);
	if (!iio_dev) {
		dev_err(dev, "Failed to allocate IIO device");
		return -ENOMEM;
	}

	iio_dev->name = dev_name(dev);
	iio_dev->driver_module = THIS_MODULE;
	iio_dev->dev.parent = dev;
	iio_dev->dev.of_node = dev->of_node;
	iio_dev->info = &aiy_adc_info;
	iio_dev->modes = INDIO_DIRECT_MODE;
	iio_dev->channels = aiy_adc_channels;

	switch (aiy->type) {
	case AIY_BOARD_TYPE_VOICEBONNET:
		dev_info(dev, "Voice bonnet ADC configuration.");
		iio_dev->num_channels = ARRAY_SIZE(aiy_adc_channels) / 2;
		break;
	case AIY_BOARD_TYPE_VISIONBONNET:
		dev_info(dev, "Vision bonnet ADC configuration.");
		iio_dev->num_channels = ARRAY_SIZE(aiy_adc_channels);
		break;
	default:
		return -EINVAL;
	}

	ret = iio_device_register(iio_dev);
	if (ret < 0) {
		dev_err(dev, "Failed to register IIO device: %d\n", ret);
		return ret;
	}

	platform_set_drvdata(pdev, iio_dev);
	dev_info(dev, "Driver loaded\n");
	return 0;
}

static int aiy_adc_remove(struct platform_device *pdev)
{
	struct iio_dev *iio_dev = platform_get_drvdata(pdev);
	iio_device_unregister(iio_dev);
	dev_info(&pdev->dev, "Driver removed");
	return 0;
}

static const struct of_device_id aiy_adc_of_match[] = {
	{
	 .compatible = "google,aiy-adc",
	 },
	{},
};

MODULE_DEVICE_TABLE(of, aiy_adc_of_match);

static const struct platform_device_id aiy_adc_id_table[] = {
	{
	 "aiy-adc",
	 },
	{},
};

MODULE_DEVICE_TABLE(platform, aiy_adc_id_table);

static struct platform_driver aiy_adc_driver = {
	.driver = {
		   .name = "aiy-adc",
		   .of_match_table = of_match_ptr(aiy_adc_of_match),
		   },
	.probe = aiy_adc_probe,
	.remove = aiy_adc_remove,
	.id_table = aiy_adc_id_table,
};

module_platform_driver(aiy_adc_driver);

MODULE_DESCRIPTION("AIY ADC Driver");
MODULE_ALIAS("platform:aiy-adc");
MODULE_AUTHOR("Henry Herman <henryherman@google.com>");
MODULE_AUTHOR("Dmitry Kovalev <dkovalev@google.com>");
MODULE_LICENSE("GPL v2");
