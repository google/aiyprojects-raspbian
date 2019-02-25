#!/usr/bin/env python3
import logging

from random import randint
from code.error_code import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)


class Gugudan:
    def __init__(self, limit=(1,9)):
        self.first_operand = None
        self.second_operand = None

        self.lower_limit, self.upper_limit = limit

    def start(self):
        self.first_operand = randint(self.lower_limit, self.upper_limit)
        self.second_operand = randint(self.lower_limit, self.upper_limit)

        logger.info('start with {}, {}'.format(self.first_operand, self.second_operand))

        return (self.first_operand, self.second_operand)

    def check(self, input):
        if type(input) is str:
            try:
                input = int(input)
            except ValueError as e:
                logging.error(e)
                raise ValueError(NOT_NUMBER)

        if self.first_operand is None or self.second_operand is None:
            logging.error('Invalid execution: check run before start')
            raise Exception(TRY_AGAIN)

        result = self.first_operand * self.second_operand == input
        logger.info('{} : {} * {} == {}'.format(result, self.first_operand, self.second_operand, input))
        return result

    def init_operand(self):
        self.first_operand = None
        self.second_operand = None

        logger.info('initialize operand...')