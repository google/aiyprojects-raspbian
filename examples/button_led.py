from aiy.util import Led, Button

def main():
    print('LED is ON while button is pressed (Ctrl-C for exit).')
    with Led(channel=17) as led, Button(channel=27) as button:
        while True:
            button.wait_for_press()
            print('ON')
            led.state = Led.ON
            button.wait_for_release()
            print('OFF')
            led.state = Led.OFF


if __name__ == '__main__':
    main()
