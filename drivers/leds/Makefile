obj-m := leds-ktd202x.o
KVERSION := $(shell uname -r)

all:
	        $(MAKE) -C /lib/modules/$(KVERSION)/build M=$(PWD) modules

clean:
	        $(MAKE) -C /lib/modules/$(KVERSION)/build M=$(PWD) clean


