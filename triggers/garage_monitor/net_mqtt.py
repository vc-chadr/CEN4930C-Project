#!/usr/bin/python3
"""
"""

from common import Common
from config import Config

import logging
import time

import paho.mqtt.client as mqtt


class Net_MQTT():
    def __init__(self, parent, client_name='Net_MQTT'):
        logging.debug('creating new MQTT instance')

        self.parent = parent
        self.connected = False

        self.client = mqtt.Client(client_name)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        logging.debug('MQTT connecting to broker: {}:{}'.format(Config.MQTT_BROKER_ADDRESS, Config.MQTT_BROKER_PORT))
        if Config.MQTT_BROKER_USE_USERNAME:
            self.client.username_pw_set(Config.MQTT_BROKER_USER, password=Config.MQTT_BROKER_PASSWORD)
        self.client.connect(Config.MQTT_BROKER_ADDRESS, port=Config.MQTT_BROKER_PORT)
        self.client.loop_start()

        logging.debug('waiting for MQTT connection')
        while self.connected != True:
            time.sleep(0.1)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.debug('MQTT Connected to broker')
            self.connected = True
        else:
            print('Connection failed')

    def on_message(self, client, userdata, message):
        logging.debug('message received:    {}'.format(str(message.payload.decode('utf-8'))))
        logging.debug('message topic:       {}'.format(message.topic))
        logging.debug('message qos:         {}'.format(message.qos))
        logging.debug('message retain flag: {}'.format(message.retain))

        if self.parent != None:
            self.parent.on_mqtt(str(message.payload.decode('utf-8')))

    def publish(self, topic, msg):
        logging.debug('Publishing ''{}'' to MQTT topic: {}'.format(msg, topic))
        self.client.publish(topic, msg)

    def subscribe(self, topic):
        logging.debug('Subscribing to MQTT topic: {}'.format(topic))
        self.client.subscribe(topic)

    def shutdown(self):
        logging.debug('shutting down MQTT instance')
        self.client.loop_stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-10s) %(message)s')

    m = Net_MQTT(None, client_name='Internal_Net_MQTT')
    m.subscribe(Config.MQTT_BROKER_TOPIC)
    m.publish(Config.MQTT_BROKER_TOPIC, 'Internal test\nstarted')

    try:
        while True:
            print('{}'.format('t'), end='', flush=True)
            time.sleep(Common.MAIN_LOOP_DELAY)

    except KeyboardInterrupt:
        logging.debug('KeyboardInterrupt - MQTT')

    m.publish(Config.MQTT_BROKER_TOPIC, 'Internal test\ncomplete')
    m.shutdown()
