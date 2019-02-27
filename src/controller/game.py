import random
import logging
import code.game as GAME_CODE

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)


def check_word(text, words):
    return any(word in text for word in words)


def updown(say, recognize, success, fail):
    # 듣기 위해 setup 해줘야하는 환경을 전역으로 선언해야할 듯

    final_ans = random.randint(1, 100)
    count = 1

    say("Random number from one to one hundred is set")
    say("Start to guess")

    while True:
        # 잘 못 알아 들었을 경우 예외 처리 해야함
        guess_ans = recognize()
        logger.info('You said: "%d"' % guess_ans)

        # updown 의 경우에는 답을 맞출때까지 끝낼 수 없다고 가정
        if guess_ans > final_ans:
            fail()
            say(GAME_CODE.UP)
            count += 1

        elif guess_ans < final_ans:
            fail()
            say(GAME_CODE.DOWN)
            count += 1

        elif guess_ans == final_ans:
            success()
            say("Correct answer")
            say("You are correct by %d times", count)
            break


def gugudan(say, recognize, success, fail):
    upper_limit = 15
    lower_limit = 2
    while True:  # 일단 2~15단 안에서???
        n1 = random.randint(lower_limit, upper_limit)
        n2 = random.randint(lower_limit, upper_limit)
        ans = n1 * n2

        # n1곱하기n2는? 이라고 말해야하는데 저 숫자 어떻게말하지
        say(GAME_CODE.GUGUDAN.EXPRESSION.format(n1, n2))

        text = recognize()
        logging.info('You said: "%s"' % text)

        if check_word(text, GAME_CODE.MAIN.END):
            break

        elif text == ans:  # 이거도 어떻게.....??
            success()
            say(GAME_CODE.MAIN.SUCCESS)

        else:
            fail()
            say(GAME_CODE.MAIN.WRONG)


def deohagi(say, recognize, success, fail):
    upper_limit = 999
    lower_limit = 1

    while True:
        n1 = random.randint(lower_limit, upper_limit)
        n2 = random.randint(lower_limit, upper_limit)
        ans = n1 + n2

        # n1더하기n2는?
        say(GAME_CODE.DEOHAGI.EXPRESSION.format(n1, n2))

        text = recognize()
        logging.info('You said: "%s"' % text)

        if check_word(text, GAME_CODE.MAIN.END):
            break

        elif text == ans:
            success()
            say(GAME_CODE.MAIN.SUCCESS)

        else:
            fail()
            say(GAME_CODE.MAIN.WRONG)



