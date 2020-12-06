#!/usr/bin/python3
"""
NOTES
- wpi.millis() is a 32bit int and wraps after 49days

Example config.py file

class Config(object):
    MAIL_RECIPIENT = "to@gmail.com"
    MAIL_SENDERNAME = "myname"
    MAIL_USERNAME = "from@gmail.com"
    MAIL_PASSWORD = "xxxxx"
    MAIL_HOST = "smtp.gmail.com"
    MAIL_PORT = "587"

"""

from common import Common
from garmon import Garmon

import logging
import platform
import time

'''
if platform.system() == 'Windows':
    import wpi_dummy_env as wpi
else:
    import wiringpi as wpi
'''

# configuration
logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s')

# constants
VERSION = 0.1

# globals
g_gmon = 0


def main():
    print("garmon {}".format(VERSION))
    init()

    while True:
        print('{}'.format(g_gmon.get_status_code()), end='', flush=True)
        time.sleep(Common.MAIN_LOOP_DELAY)
        g_gmon.check_heartbeat_time()

def init():
    global g_gmon

    g_gmon = Garmon()


if __name__ == '__main__':
    main()
