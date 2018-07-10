# Voice HAT and Voice Bonnet

## Hardware

**Voice HAT**

* Audio Amplifier: MAX98357A
* Microphone: ICS-43432 x 2

**Voice Bonnet**

* Audio Codec: ALC5645
* MCU: ATSAMD09D14
* LED Driver: KTD2027B
* Crypto: ATECC608A (optional)
* Microphone: SPH1642HT5H-1 x 2

## Drivers

**Voice HAT**

* [googlevoicehat-codec.c](https://github.com/raspberrypi/linux/blob/rpi-4.14.y/sound/soc/bcm/googlevoicehat-codec.c)
* [googlevoicehat-soundcard.c](https://github.com/raspberrypi/linux/blob/rpi-4.14.y/sound/soc/bcm/googlevoicehat-soundcard.c)
* [googlevoicehat-soundcard-overlay.dts](https://github.com/raspberrypi/linux/blob/rpi-4.14.y/arch/arm/boot/dts/overlays/googlevoicehat-soundcard-overlay.dts)

Manual overlay load:
```
sudo dtoverlay googlevoicehat-soundcard
```

Load overlay on each boot:
```
echo "dtoverlay=googlevoicehat-soundcard" | sudo tee -a /boot/config.txt
```

**Voice Bonnet**

Manual overlay load (EEPROM overlay must be disabled):
```
sudo dtoverlay aiy-voicebonnet
```

## Pinout (40-pin header)

**Voice HAT**
```
       3.3V --> 1    2 <-- 5V
                3    4 <-- 5V
                5    6 <-- GND
                7    8
        GND --> 9   10
                11  12 <-- I2S_BCLK
                13  14 <-- GND
                15  16 <-- BUTTON_GPIO (GPIO_23)
       3.3V --> 17  18
                19  20 <-- GND
                21  22 <-- LED_GPIO (GPIO_25)
                23  24
        GND --> 25  26
     ID_SDA --> 27  28 <-- ID_SCL
                29  30 <-- GND
                31  32
  I2S_LRCLK --> 33  34 <-- GND
                35  36 <-- AMP_ENABLE
                37  38 <-- I2S_DIN
        GND --> 39  40 <-- I2S_DOUT
```

**Voice Bonnet**
```
       3.3V --> 1    2 <-- 5V
    I2C_SDA --> 3    4 <-- 5V
    I2C_SCL --> 5    6 <-- GND
                7    8
        GND --> 9   10
                11  12 <-- I2S_BCLK
                13  14 <-- GND
                15  16 <-- BUTTON_GPIO (GPIO_23)
       3.3V --> 17  18
                19  20 <-- GND
                21  22
                23  24
        GND --> 25  26
     ID_SDA --> 27  28 <-- ID_SCL
                29  30 <-- GND
                31  32
  I2S_LRCLK --> 33  34 <-- GND
                35  36
                37  38 <-- I2S_DIN
        GND --> 39  40 <-- I2S_DOUT
```
