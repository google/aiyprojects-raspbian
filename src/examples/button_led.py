from aiy.board import Board, Led

def main():
    print('Press button to turn on/off the LED or Ctrl-C for exit.')
    with Board() as board:
        while True:
            board.button.wait_for_press()
            print('ON')
            board.led.state = Led.ON
            board.button.wait_for_press()
            print('OFF')
            board.led.state = Led.OFF

if __name__ == '__main__':
    main()
