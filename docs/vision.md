# Vision Bonnet

## Hardware

* SOC: Myriad 2450
* MCU: ATSAMD09D14 [I2C address: 0x51]
* LED Driver: KTD2027A [I2C address: 0x30]
* Crypto (optional): ATECC608A [I2C address: 0x60]
* IMU: BMI160

## Drivers

* MCU driver: `modinfo aiy-io-i2c`
* MCU PWM driver: `modinfo pwm-aiy-io`
* MCU GPIO driver: `modinfo gpio-aiy-io`
* MCU ADC driver: `modinfo aiy-adc`
* LED driver: `modinfo leds-ktd202x`
* Software PWM driver for buzzer: `modinfo pwm-soft`
* Myriad driver: `modinfo aiy-vision`

To reset MCU:
```
echo 1 | sudo tee /sys/bus/i2c/devices/1-0051/reset
```

To get MCU status message (including firmware version) and last error code:
```
cat /sys/bus/i2c/devices/1-0051/{status_message,error_code}
```

## Pinout (40-pin header)

```
                   3.3V --> 1    2 <-- 5V
                I2C_SDA --> 3    4 <-- 5V
                I2C_SCL --> 5    6 <-- GND
                            7    8
                    GND --> 9   10
                            11  12
                            13  14 <-- GND
  (GPIO_22) BUZZER_GPIO --> 15  16 <-- BUTTON_GPIO (GPIO_23)
                   3.3V --> 17  18
               SPI_MOSI --> 19  20 <-- GND
               SPI_MISO --> 21  22
               SPI_SCLK --> 23  24 <-- SPI_CE_MRD
                    GND --> 25  26
                 ID_SDA --> 27  28 <-- ID_SCL
                            29  30 <-- GND
          PI_TO_MRD_IRQ --> 31  32
          MRD_TO_PI_IRQ --> 33  34 <-- GND
                            35  36
             MRD_UNUSED --> 37  38
                    GND --> 39  40
```

## Troubleshooting

Sometimes Pi Zero doesn't work stable and fails with different kernel errors,
e.g. [Issue #346]. Run
```
echo "over_voltage=4" | sudo tee -a /boot/config.txt
```
and then reboot.

[Issue #346]: https://github.com/google/aiyprojects-raspbian/issues/346