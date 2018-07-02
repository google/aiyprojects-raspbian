# Voice HAT and Voice Bonnet

## Pinout (40-pin header)

Voice HAT
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

Voice Bonnet
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
