MDIR := aiy

KVER ?= $(shell uname -r)
KDIR ?= /lib/modules/$(KVER)/build

export CONFIG_AIY_IO_I2C = m
export CONFIG_GPIO_AIY_IO = m
export CONFIG_PWM_AIY_IO = m
export CONFIG_AIY_ADC = m
export CONFIG_AIY_VISION = m

ifneq ($(KERNELRELEASE),)

ifeq ($(CONFIG_AIY_IO_I2C), m)
KBUILD_CFLAGS += -DCONFIG_AIY_IO_I2C
endif
ifeq ($(CONFIG_GPIO_AIY_IO), m)
KBUILD_CFLAGS += -DCONFIG_GPIO_AIY_IO
endif
ifeq ($(CONFIG_PWN_AIY_IO), m)
KBUILD_CFLAGS += -DCONFIG_PWM_AIY_IO
endif
ifeq ($(CONFIG_AIY_ADC), m)
KBUILD_CFLAGS += -DCONFIG_AIY_ADC
endif
ifeq ($(CONFIG_AIY_VISION), m)
KBUILD_CFLAGS += -DCONFIG_AIY_VISION
endif



obj-y := $(MDIR)/

else

all: modules

modules:
	$(MAKE) -C $(KDIR) M="$(CURDIR)" modules

install: modules
	$(MAKE) INSTALL_MOD_PATH=$(DESTDIR) INSTALL_MOD_DIR=$(MDIR) \
		-C $(KDIR) M="$(CURDIR)" modules_install

clean:
	$(MAKE) -C $(KDIR) M="$(CURDIR)" clean

help:
	$(MAKE) -C $(KDIR) M="$(CURDIR)" help

endif
