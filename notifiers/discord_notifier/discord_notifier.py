#!/usr/bin/python3
"""
Discord bot that relays MQTT messages into a private Discord channel

To use this script a config.py file must be created with your network configuration.

Example config.py file

class Config(object):
    DISCORD_TOKEN = 'N18dfd01604fcd97cc0b0877aeed8c759c4fd2f71133e8e1d3642eb4614'
    DISCORD_MAIN_CHANNEL = 6f8005507316059344

    MQTT_BROKER_ADDRESS = '127.0.0.1'
    MQTT_BROKER_PORT = 1883

"""

from config import Config

from discord.ext import commands
from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1, QOS_2

import asyncio
import discord
import logging
import time


# constants
TOPICS = [('hm/#', QOS_1)]
TEST_TOPIC = 'hm/test/discord'

# globals
client = discord.Client()
logger = logging.getLogger(__name__)
mqtt = None


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await message.channel.send(msg)

    if message.content.startswith('!mqtt'):
        if mqtt == None:
            await message.channel.send('MQTT is down')
        else:
            try:
                await mqtt.publish(TEST_TOPIC, b'MQTT RNG', qos=0x01)
                await message.channel.send('MQTT message sent')
            except Exception as ce:
                await message.channel.send('MQTT publish failed: {}'.format(ce))
                logger.error('publish failed: {}'.format(ce))

@client.event
async def on_ready():
    logging.info('Logged in as {} - id: {}'.format(client.user.name, client.user.id))
    channel = client.get_channel(id=Config.DISCORD_MAIN_CHANNEL)
    await channel.send('Logged in')

async def post_message_to_channel(msg):
    logging.info('Posting message to channel: {}'.format(msg))
    try:
        channel = client.get_channel(id=Config.DISCORD_MAIN_CHANNEL)
        await channel.send('{} -- {}'.format(time.strftime('%m/%d %H:%M:%S'), msg))
    except Exception as e:
        logging.info('Error posting to channel: {}'.format(e))

async def discord_task():
    while True:
        logging.info('starting Discord task')
        #await client.run(Config.DISCORD_TOKEN)    # don't use run as it abstracts asyncio loop

        try:
            await client.start(Config.DISCORD_TOKEN)
        except Exception as e:
            logging.info('Exception: {}'.format(e))
            logging.exception('Caught an error')

        logging.info('STOPPING Discord task')

async def mqtt_task():
    global mqtt

    logging.info('starting MQTT')
    mqtt = MQTTClient()
    await mqtt.connect('mqtt://{}:{}/'.format(Config.MQTT_BROKER_ADDRESS, Config.MQTT_BROKER_PORT))
    await mqtt.subscribe(TOPICS)
    logger.info("Subscribed")
    try:
        while True:
            message = await mqtt.deliver_message()
            packet = message.publish_packet
            logging.info("mqtt: %s => %s" % (packet.variable_header.topic_name, str(packet.payload.data)))
            msg = packet.payload.data.decode()
            #logging.info('msg format: {}'.format(repr(msg)))
            await post_message_to_channel(msg)

        await mqtt.unsubscribe([x[0] for x in TOPICS])
        logger.info("UnSubscribed")
        await mqtt.disconnect()

    except ClientException as ce:
        logger.error("Client exception: %s" % ce)

    logging.info('STOPPING MQTT task')


if __name__ == '__main__':
    formatter = "[%(asctime)s] %(name)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    #formatter = "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    #formatter = "[%(asctime)s] %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=formatter)

    loop = asyncio.get_event_loop()
    loop.create_task(discord_task())
    loop.create_task(mqtt_task())
    loop.run_forever()

    logging.info('[DONE]')
