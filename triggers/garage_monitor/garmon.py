#!/usr/bin/python3
"""
TODO
- change current directory to same path as this description
- if door is stuck in in-between state for awhile, send a photo

"""

from net_mqtt import Net_MQTT
from notify_gmail import Notify_Gmail
from nutil import Nutil

from common import Common
from config import Config
#from time import time #, sleep

import datetime
import logging
import os
import platform
import threading
import time
import wiringpi as wpi

# configuration
ENABLE_NOTIFY_EMAIL = True
ENABLE_NOTIFY_MQTT = True
USE_WIRINGPI_GPIO = False
MQTT_BROKER_SUBTOPIC = '/sec/g/garage'

# constants
VERSION = 0.1
FLAP_THRESHOLD = 500

# globals


if not USE_WIRINGPI_GPIO:
    try:
        import RPi.GPIO as GPIO
    except RuntimeError:
        print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")


def pin_read(pin):
    if USE_WIRINGPI_GPIO:
        return wpi.digitalRead(pin)
    return GPIO.input(pin)


def pin_write(pin, val):
    if USE_WIRINGPI_GPIO:
        wpi.digitalWrite(pin, val)
    else:
        GPIO.output(pin, val)


class Sensor_State:
    def __init__(self, num, pin, name):
        self.name = name
        self.num = num
        self.pin = pin
        self.button_state = 0

        # NOT DEBOUNCE - self.update_door_sensor_state()

    def update_door_sensor_state(self, val=None):
        if val == None:
            val = pin_read(self.pin)

        self.button_state = val
        sensor_triggered = not val      # we are using pull-up resistors (reverse logic)


        # debuging
        logging.debug('- Update door sensor state - name: {} val: {}'.format(self.name, val))

        return sensor_triggered

    def dump_state(self):
        logging.debug('- Sensor state - name: {}  num: {}  pin: {}  button: {}'.format(self.name, self.num, self.pin, self.button_state))


class Garmon():

    def __init__(self):
        #self.led_state = False

        self.next_heartbeat = 0
        self.set_next_heartbeat_time()

        self.sensor_state = []

        self.door_state = [False, False]
        self.last_door_state_change = 0
        self.flap_time = 0

        self.mqtt = Net_MQTT(self, client_name=Config.MQTT_CLIENT_NAME)

        if USE_WIRINGPI_GPIO:
            logging.info('- Using Wiringpi GPIO')
            #wpi.wiringPiSetupGpio()
            wpi.wiringPiSetup()

            wpi.pinMode(Common.PIN_SENSOR_CLOSED, wpi.GPIO.INPUT)
            wpi.pinMode(Common.PIN_SENSOR_OPENED, wpi.GPIO.INPUT)
            wpi.pullUpDnControl(Common.PIN_SENSOR_CLOSED, wpi.GPIO.PUD_UP)
            wpi.pullUpDnControl(Common.PIN_SENSOR_OPENED, wpi.GPIO.PUD_UP)
            wpi.wiringPiISR(Common.PIN_SENSOR_CLOSED, wpi.GPIO.INT_EDGE_BOTH, self.callback_sensor_closed_action)
            wpi.wiringPiISR(Common.PIN_SENSOR_OPENED, wpi.GPIO.INT_EDGE_BOTH, self.callback_sensor_opened_action)

            #wpi.pinMode(Common.PIN_STATUS_LED, wpi.GPIO.OUTPUT)        # Example: LED Test
        else:
            logging.info('- Using RPi GPIO')
            GPIO.setmode(GPIO.BOARD)
            #GPIO.setmode(GPIO.BCM)

            GPIO.setup(Common.PIN_SENSOR_CLOSED, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(Common.PIN_SENSOR_OPENED, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(Common.PIN_SENSOR_CLOSED, GPIO.BOTH, callback=self.callback_sensor_closed_action)
            GPIO.add_event_detect(Common.PIN_SENSOR_OPENED, GPIO.BOTH, callback=self.callback_sensor_opened_action)

        self.sensor_state = [Sensor_State(Common.SENSOR_CLOSED, Common.PIN_SENSOR_CLOSED, 'Closed'),
                             Sensor_State(Common.SENSOR_OPENED, Common.PIN_SENSOR_OPENED, 'Opened')]
        self.update_all_sensor_states()
        self.update_door_state_change_time()

        # debuging
        self.dump_state()
        self.sensor_state[Common.SENSOR_CLOSED].dump_state()
        self.sensor_state[Common.SENSOR_OPENED].dump_state()

        # notify setup
        self.notify_email('starting garmon', 'need text')
        self.notify_mqtt('starting garmon')

        logging.info('- current directory: {}'.format(os.getcwd()))
        logging.info('Init complete')


    def led_status(self, val):
        # Example: LED Test
        if (val) == False:
            pin_write(Common.PIN_STATUS_LED, 1)
            logging.debug('LED on')
        else:
            pin_write(Common.PIN_STATUS_LED, 0)
            logging.debug('LED off')

    def callback_sensor_action(self, sensor_num):
        reading = pin_read(self.sensor_state[sensor_num].pin)
        logging.info("\nGPIO_CALLBACK! - {} action = {}".format(self.sensor_state[sensor_num].name, reading))

        if reading != self.sensor_state[sensor_num].button_state:
            special = 'GOOD'
            if (wpi.millis() - self.flap_time) < FLAP_THRESHOLD:
                special = 'TOO SOON'
                logging.info('- too soon since last state change, ignoring this event')
                return

            self.flap_time = wpi.millis()
            logging.info('- Check for flap = {} : ({} - {}) < {}'.format(special, wpi.millis(), self.flap_time, FLAP_THRESHOLD))
            self.door_state[sensor_num] = self.sensor_state[sensor_num].update_door_sensor_state(reading)
            self.sensor_state[sensor_num].dump_state()

            send_email = False
            if self.sensor_state[sensor_num].button_state == 0:
                logging.info('- new state LOW')

                if sensor_num == Common.SENSOR_CLOSED:
                    send_email = True
                    action = 'CLOSED'
                else:
                    action = 'OPENED'
                    self.notify_email('take a photo, door is Opened', 'need text', delay=3)
            else:
                logging.info('- new state HIGH')

                if sensor_num == Common.SENSOR_CLOSED:
                    send_email = True
                    action = 'opening'
                else:
                    action = 'closing'

            text = '- last state change occured {} ago'.format(Nutil.get_time_delta(self.last_door_state_change))
            logging.info(text)
            self.update_door_state_change_time()

            # Example: LED Test
            #self.led_status(reading)

            subject = 'G.Door is {} : {}'.format(action, special)

            logging.info('- Subject: {}'.format(subject))

            if send_email:
                self.notify_email(subject, text)
            self.notify_mqtt(subject)

    def notify_mqtt(self, subject):
        logging.info('sending MQTT message: {}'.format(subject))
        if ENABLE_NOTIFY_MQTT:
            self.mqtt.publish('{}{}'.format(Config.MQTT_BROKER_TOPIC, MQTT_BROKER_SUBTOPIC), subject)

    def notify_email(self, subject, text, delay=0, use_camera=False):
        dt = datetime.datetime.now()
        subject = '{} - {}{:02}{:02}.{:02}{:02}{:02}'.format(subject, dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        logging.info('sending gmail: {}'.format(subject))
        if ENABLE_NOTIFY_EMAIL:
            notify_thread = Notify_Thread(subject, text, delay, use_camera)
            #notify_thread.start()

    def callback_sensor_closed_action(self, extra):
        logging.info('callback_sensor_closed_action - pin : {}'.format(extra))
        self.callback_sensor_action(Common.SENSOR_CLOSED)

    def callback_sensor_opened_action(self, extra):
        logging.info('callback_sensor_opened_action - pin : {}'.format(extra))
        self.callback_sensor_action(Common.SENSOR_OPENED)

    def get_status_code(self):
        if self.door_state[Common.SENSOR_CLOSED] == True and self.door_state[Common.SENSOR_OPENED] == True:
            return '?'
        elif self.door_state[Common.SENSOR_CLOSED] == True:
            return 'C'
        elif self.door_state[Common.SENSOR_OPENED] == True:
            return 'O'
        else:
            return 'i'

    def is_closed(self):
        if self.door_state[Common.SENSOR_CLOSED] == True:
            return True
        return False

    def is_opened(self):
        if self.door_state[Common.SENSOR_OPENED] == True:
            return True
        return False

    def update_door_state_change_time(self):
        self.last_door_state_change = time.time()

    def update_all_sensor_states(self):
        self.door_state[0] = self.sensor_state[0].update_door_sensor_state()
        self.door_state[1] = self.sensor_state[1].update_door_sensor_state()

    def check_heartbeat_time(self):
        now = datetime.datetime.now()
        if now > self.next_heartbeat:
            self.send_heartbeat()
        '''
            print('- heartbeat time exceeded')
        else:
            print('- next heartbeat in {}'.format(Nutil.get_time_delta(self.next_heartbeat.timestamp())))
        '''

    def set_next_heartbeat_time(self):
        now = datetime.datetime.now()
        self.next_heartbeat = now + datetime.timedelta(days=1, hours=(-now.hour + 6), minutes=(-now.minute + 4))
        logging.info('- next heartbeat set to: {}'.format(repr(self.next_heartbeat)))

    def send_heartbeat(self):
        self.set_next_heartbeat_time()
        logging.info('- sending heartbeat')
        text = '- last state change occured {} ago'.format(Nutil.get_time_delta(self.last_door_state_change))
        self.notify_email('garmon heartbeat', text)

    def dump_state(self):
        logging.debug('- Door state - close: {}  open: {}  status: {}'.format(self.door_state[Common.SENSOR_CLOSED], self.door_state[Common.SENSOR_OPENED], self.get_status_code()))


class Notify_Thread(threading.Thread):

    def __init__(self, subject, text, delay=0, use_camera=False):
        #threading.Thread.__init__(self)
        #self.name = '{}-{}'.format('Notify', subject[-6:])
        #threading.Thread.__init__(self, name=self.name)

        logging.info('Init new notify thread: {}'.format(subject))
        self.subject = subject
        self.text = text
        self.delay = delay
        self.use_camera = use_camera
        #thread = threading.Thread.__init__(self, name='{}-{}'.format('Notify', subject[-6:]))
        thread = threading.Thread(target=self.run, name='{}-{}'.format('Notify', subject[-6:]))
        thread.start()
        logging.info('Init new notify thread: {} DONE'.format(subject))

    def run(self):
        logging.info('Starting "{}" thread - delay: {}  use camera: {}'.format(self.subject, self.delay, self.use_camera))
        time.sleep(self.delay)
        logging.info('Running')
        notifier = Notify_Gmail()
        if not notifier.notify(self.subject, self.text):
            logging.info('- notify failed')
        logging.info('Exiting "' + self.subject + '" thread')


if __name__ == '__main__':
    print('Please do not execute this script directly, use main.py or test_main.py')
    exit()
