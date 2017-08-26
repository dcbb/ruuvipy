from datetime import datetime
import logging


class Timer:

    def __init__(self):
        self.t = None
        self.reset()

    def report(self, message):
        delta_t = datetime.now() - self.t
        logging.debug("{message}, time passed: {dt}".format(message=message, dt=delta_t))
        self.t = datetime.now()

    def reset(self, message=''):
        logging.debug("Timer reset. " + message)
        self.t = datetime.now()
