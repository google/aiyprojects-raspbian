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
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/pwm.h>

#define AIY_PWM_PIN_COUNT 4

struct aiy_pwm {
	struct pwm_chip chip;
	struct aiy_io_i2c *aiy;
};

#define AIY_PWM_8BIT_TIMER_CLK_FREQ (48000000 / 16)
#define AIY_PWM_NANO_SEC 1000000000
#define AIY_PWM_MAX_CAP 0xFF
#define AIY_50Hz_PERIOD_NS 20000000

static const uint8_t pwm_map[] = {
	AIY_GPIO_PIN_PA04_OFFSET,
	AIY_GPIO_PIN_PA05_OFFSET,
	AIY_GPIO_PIN_PA10_OFFSET,
	AIY_GPIO_PIN_PA11_OFFSET,
};

static const uint8_t base_address_map[] = {
	AIY_REG_PWM_PA04_BASE,
	AIY_REG_PWM_PA05_BASE,
	AIY_REG_PWM_PA10_BASE,
	AIY_REG_PWM_PA11_BASE,
};

static const uint8_t prescaler_address_map[] = {
	AIY_REG_PWM0_PRESCALER,
	AIY_REG_PWM0_PRESCALER,
	AIY_REG_PWM1_PRESCALER,
	AIY_REG_PWM1_PRESCALER,
};

static inline struct aiy_io_i2c *to_aiy(struct pwm_chip *pwm_chip) {
	struct aiy_pwm *aiy_pwm = container_of(pwm_chip, struct aiy_pwm, chip);
	return aiy_pwm->aiy;
}

static int aiy_calculate_8bit_settings(struct pwm_chip *chip,
				       unsigned long long duty_ns,
				       unsigned long long period_ns,
				       uint16_t *period_cyc, uint16_t *duty_cyc,
				       uint8_t *prescaler_index)
{
	/* ATSAMDO9 Timer only supports specifice prescaler values. */
	const int prescalers[] = {1, 2, 4, 8, 16, 64, 256, 1024, 0};
	const int prescaler_count = 9;
	unsigned long long period_cycles = period_ns;
	unsigned long long scaled_period_cycles = period_cycles;
	unsigned long long duty_cycles = duty_ns;
	unsigned long long scaled_duty_cycles = duty_cycles;
	int i;
	period_cycles *= AIY_PWM_8BIT_TIMER_CLK_FREQ;
	do_div(period_cycles, AIY_PWM_NANO_SEC);
	duty_cycles *= AIY_PWM_8BIT_TIMER_CLK_FREQ;
	do_div(duty_cycles, AIY_PWM_NANO_SEC);
	dev_dbg(chip->dev, "Period cycles %llu, duty cycles %llu\n",
		period_cycles, duty_cycles);

	/* Calculate the prescaler then the duty cycle and period in cycles */
	/* Period and duty cycle can only be controlled in 8 bit mode. */
	*prescaler_index = 0xFF;
	for (i = 0; i < prescaler_count; i++) {
		int prescaler = prescalers[i];
		if (prescaler == 0) {
			dev_err(chip->dev,
				"Prescaler exceeds the maximum value\n");
			return -EINVAL;
		}
		scaled_period_cycles = period_cycles;
		scaled_duty_cycles = duty_cycles;
		do_div(scaled_period_cycles, prescaler);
		if (scaled_period_cycles < AIY_PWM_MAX_CAP) {
			*prescaler_index = i;
			if (scaled_period_cycles == 0) {
				dev_warn(chip->dev,
					 "Selected PWM Period too small.\n");
				return -EINVAL;
			}
			*period_cyc = (uint16_t)scaled_period_cycles - 1;
			do_div(scaled_duty_cycles, prescaler);
			*duty_cyc = (uint16_t)scaled_duty_cycles;
			dev_dbg(chip->dev,
				"Prescaler selected %d, period selected %llu, "
				"duty cycle "
				"selected %llu\n",
				prescaler, scaled_period_cycles,
				scaled_duty_cycles);
			break;
		}
	}
	return 0;
}

static int aiy_calculate_16bit_settings(struct pwm_chip *chip,
					unsigned long long duty_ns,
					uint16_t *duty_cyc)
{
	unsigned long long nano_sec_per_cycle = AIY_50Hz_PERIOD_NS;
	unsigned long long duty_cycles = duty_ns;
	/* Atsamd09 does not support changes to period in 16-bit mode */
	/* Use 16-bit mode to support higher resolution for controlling servos,
	 * when period is 20ms */
	do_div(nano_sec_per_cycle, (1 << 16) - 1);
	do_div(duty_cycles, nano_sec_per_cycle);
	if (duty_cycles > ((1 << 16) - 1)) {
		*duty_cyc = (1 << 16) - 1;
	} else {
		*duty_cyc = duty_cycles;
	}
	dev_dbg(chip->dev, "Duty cycles %d\n", *duty_cyc);
	return 0;
}

static int aiy_pwm_request(struct pwm_chip *chip, struct pwm_device *pwm)
{
	int err;
	const int offset = pwm_map[pwm->hwpwm];
	struct aiy_io_i2c *aiy = to_aiy(chip);

	dev_dbg(chip->dev, "PWM request for pin %d (offset=%d)\n", pwm->hwpwm,
		offset);
	err = aiy_io_request_pin(aiy, offset, AIY_PIN_OPTION_USED_PWM);
	if (err < 0) {
		dev_err(chip->dev,
			"PWM request for pin %d (offset=%d) failed: %d\n",
			pwm->hwpwm, offset, err);
	}
	return err;
}

static void aiy_pwm_free(struct pwm_chip *chip, struct pwm_device *pwm)
{
	const int offset = pwm_map[pwm->hwpwm];
	struct aiy_io_i2c *aiy = to_aiy(chip);

	dev_dbg(chip->dev, "PWM free pin %d (offset=%d).\n", pwm->hwpwm,
		offset);

	if (regmap_write(aiy->regmap, AIY_REG_GPIO_BASE_MODE + offset,
			 AIY_GPIO_MODE_INPUT_HIZ) < 0)
		dev_err(chip->dev, "Cannot set HIZ mode for pin %d.\n", offset);

	if (aiy_io_free_pin(aiy, offset, AIY_PIN_OPTION_USED_PWM) < 0)
		dev_err(chip->dev, "Cannot free PWM pin %d.\n", offset);
}

static int aiy_pwm_write_setting(struct pwm_chip *chip, unsigned int hwpwm,
				 uint8_t prescaler, uint16_t duty,
				 uint16_t period)
{
	int err;
	struct aiy_io_i2c *aiy = to_aiy(chip);
	const uint8_t base_address = base_address_map[hwpwm];
	const uint8_t prescaler_address = prescaler_address_map[hwpwm];

	err = regmap_bulk_write(aiy->regmap,
			       base_address + AIY_REG_DUTY_CYCLE_OFFSET,
			       (void *)&duty, sizeof(duty));
	if (err != 0) {
		dev_err(chip->dev, "Failed to set PWM duty cycle.");
		return -EINVAL;
	}

	err = regmap_bulk_write(aiy->regmap,
				base_address + AIY_REG_PERIOD_OFFSET,
				(void *)&period, sizeof(period));
	if (err != 0) {
		dev_err(chip->dev, "Failed to set PWM period.");
		return -EINVAL;
	}

	err = regmap_write(aiy->regmap, prescaler_address, prescaler);
	if (err != 0) {
		dev_err(chip->dev, "Failed to set PWM prescaler.");
		return -EINVAL;
	}
	return 0;
}

static int aiy_pwm_8bit_config(struct pwm_chip *chip, struct pwm_device *pwm,
			       int duty_ns, int period_ns)
{
	int err;
	uint8_t prescaler_value;
	uint16_t period_value = 0;
	uint16_t duty_value = 0;

	dev_dbg(chip->dev, "PWM config duty: %d, period: %d.\n", duty_ns,
		period_ns);

	err = aiy_calculate_8bit_settings(chip, duty_ns, period_ns,
					  &period_value, &duty_value,
					  &prescaler_value);
	if (err != 0) {
		dev_err(chip->dev, "Failed to calculate PWM settings.");
		return -EINVAL;
	}

	err = aiy_pwm_write_setting(chip, pwm->hwpwm, prescaler_value,
				    duty_value, period_value);
	if (err != 0) {
		dev_err(chip->dev, "Failed to write PWM setting.");
		return -EINVAL;
	}

	return 0;
}

static int aiy_pwm_16bit_config(struct pwm_chip *chip, struct pwm_device *pwm,
				int duty_ns, int period_ns)
{
	int err;
	uint16_t duty_value;
	/* In 16-bit mode PWM only supports changing duty cycle */
	/* 16 bit mode is selected when period is set to 20ms */

	dev_dbg(chip->dev, "Servo config duty: %d, period: %d.\n", duty_ns,
		period_ns);

	err = aiy_calculate_16bit_settings(chip, duty_ns, &duty_value);
	if (err != 0) {
		dev_err(chip->dev, "Failed to calculate PWM settings.");
		return -EINVAL;
	}

	err = aiy_pwm_write_setting(chip, pwm->hwpwm, 0, duty_value, 0);
	if (err != 0) {
		dev_err(chip->dev, "Failed to write PWM setting.");
		return -EINVAL;
	}

	return 0;
}

static int aiy_pwm_config(struct pwm_chip *chip, struct pwm_device *pwm,
			  int duty_ns, int period_ns)
{
	int err;
	const int pin_offset = pwm_map[pwm->hwpwm];
	struct aiy_io_i2c *aiy = to_aiy(chip);
	enum aiy_gpio_mode selected_mode = AIY_GPIO_MODE_PWM;

	dev_dbg(chip->dev, "PWM config duty: %d, period: %d.\n", duty_ns,
		period_ns);

	if (pwm->state.enabled) {
		/* Disable PWM mode if necessary before reconfiguring. */
		err = regmap_write(aiy->regmap,
				   AIY_REG_GPIO_BASE_MODE + pin_offset,
				   AIY_GPIO_MODE_UPDATE);
	}

	/* Use 16bit mode to support higher resolution PWM */
	/* 16 bit mode is activated when period is 20msec */
	if (period_ns == AIY_50Hz_PERIOD_NS) {
		err = aiy_pwm_16bit_config(chip, pwm, duty_ns, period_ns);
		selected_mode = AIY_GPIO_MODE_SERVO;
	} else {
		/* All other periods use 8 bit mode */
		err = aiy_pwm_8bit_config(chip, pwm, duty_ns, period_ns);
	}

	if (err != 0) {
		dev_dbg(chip->dev, "Failed to configure PWM\n");
		return -EINVAL;
	}

	if (pwm->state.enabled) {
		/* Reset correct PWM mode if necessary. */
		err = regmap_write(aiy->regmap,
				   AIY_REG_GPIO_BASE_MODE + pin_offset,
				   selected_mode);
	}

	return err;
}

static int aiy_pwm_enable(struct pwm_chip *chip, struct pwm_device *pwm)
{
	int err;
	const int pin_offset = pwm_map[pwm->hwpwm];
	struct aiy_io_i2c *aiy = to_aiy(chip);
	enum aiy_gpio_mode selected_mode = AIY_GPIO_MODE_PWM;

	/* Select correct mode if period is 20 msec */
	if (pwm->state.period == AIY_50Hz_PERIOD_NS) {
		dev_dbg(chip->dev, "SERVO enable.\n");
		selected_mode = AIY_GPIO_MODE_SERVO;
	} else {
		dev_dbg(chip->dev, "PWM enable.\n");
	}

	err = regmap_write(aiy->regmap, AIY_REG_GPIO_BASE_MODE + pin_offset,
			   selected_mode);
	if (err != 0) {
		dev_err(chip->dev, "Failed to enable PWM.");
	}
	return err;
}

static void aiy_pwm_disable(struct pwm_chip *chip, struct pwm_device *pwm)
{
	int err;
	const int pin_offset = pwm_map[pwm->hwpwm];
	struct aiy_io_i2c *aiy = to_aiy(chip);

	dev_dbg(chip->dev, "PWM %d disable.\n", pwm->hwpwm);

	/* Set pin to HIZ when pwm is disabled */
	err = regmap_write(aiy->regmap, AIY_REG_GPIO_BASE_MODE + pin_offset,
			   AIY_GPIO_MODE_INPUT_HIZ);
	if (err != 0) {
		dev_err(chip->dev, "Failed to disable PWM %d.", pwm->hwpwm);
	}
}

static const struct pwm_ops aiy_pwm_ops = {
	.request = aiy_pwm_request,
	.free = aiy_pwm_free,
	.config = aiy_pwm_config,
	.enable = aiy_pwm_enable,
	.disable = aiy_pwm_disable,
	.owner = THIS_MODULE,
};

static int aiy_pwm_probe(struct platform_device *pdev)
{
	int err;
	struct aiy_io_i2c *aiy = dev_get_drvdata(pdev->dev.parent);
	struct aiy_pwm *aiy_pwm;

	aiy_pwm = devm_kzalloc(&pdev->dev, sizeof(*aiy_pwm), GFP_KERNEL);
	if (!aiy_pwm) {
		return -ENOMEM;
	}
	aiy_pwm->aiy = aiy;
	aiy_pwm->chip.dev = &pdev->dev;
	aiy_pwm->chip.ops = &aiy_pwm_ops;
	aiy_pwm->chip.npwm = AIY_PWM_PIN_COUNT;
	platform_set_drvdata(pdev, aiy_pwm);

	err = pwmchip_add(&aiy_pwm->chip);
	if (err < 0) {
		dev_err(&pdev->dev, "Failed to add pwm chip: %d\n", err);
		return err;
	}
	dev_info(&pdev->dev, "Driver loaded\n");
	return 0;
}

static int aiy_pwm_remove(struct platform_device *pdev)
{
	int err;
	struct aiy_pwm *aiy_pwm = platform_get_drvdata(pdev);

	err = pwmchip_remove(&aiy_pwm->chip);
	if (err < 0) {
		dev_err(&pdev->dev, "Failed to remove pwm chip: %d\n", err);
		return err;
	}
	dev_info(&pdev->dev, "Driver removed\n");
	return 0;
}

static const struct of_device_id aiy_pwm_of_match[] = {
	{.compatible = "google,pwm-aiy-io",},
	{}
};
MODULE_DEVICE_TABLE(of, aiy_pwm_of_match);

static const struct platform_device_id aiy_pwm_id_table[] = {
	{"pwm-aiy-io",},
	{},
};
MODULE_DEVICE_TABLE(platform, aiy_pwm_id_table);

static struct platform_driver aiy_pwm_driver = {
	.driver = {
		.name = "pwm-aiy-io",
		.of_match_table = of_match_ptr(aiy_pwm_of_match),
	},
	.probe = aiy_pwm_probe,
	.remove = aiy_pwm_remove,
	.id_table = aiy_pwm_id_table,
};
module_platform_driver(aiy_pwm_driver);

MODULE_DESCRIPTION("AIY PWM Driver");
MODULE_ALIAS("platform:pwm-aiy-io");
MODULE_AUTHOR("Henry Herman <henryherman@google.com>");
MODULE_AUTHOR("Dmitry Kovalev <dkovalev@google.com>");
MODULE_LICENSE("GPL v2");
