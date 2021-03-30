obj-$(CONFIG_AIY_IO_I2C) := aiy-io-i2c.o
ccflags-y := -std=gnu99 -Wno-declaration-after-statement
KVERSION := $(shell uname -r)

all:
	$(MAKE) -C /lib/modules/$(KVERSION)/build M=$(PWD) modules

clean:
	$(MAKE) -C /lib/modules/$(KVERSION)/build M=$(PWD) clean

