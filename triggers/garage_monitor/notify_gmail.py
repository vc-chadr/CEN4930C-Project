"""
gmail notifier

notify usage example

    notifier = Notify_Gmail()
    if not notifier.notify("Subject", "Text"):
        logging.info('- send failed')


Example config.py file

class Config(object):
    MAIL_RECIPIENT = "to@gmail.com"
    MAIL_SENDERNAME = "myname"
    MAIL_USERNAME = "from@gmail.com"
    MAIL_PASSWORD = "xxxxx"
    MAIL_HOST = "smtp.gmail.com"
    MAIL_PORT = "587"


"""

from config import Config
from nutil import Nutil

import json
import logging
import os
import sys

# gmail notify
import smtplib
from email import encoders
from email.utils import formatdate
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

# configuration
ENABLE_SEND_EMAIL = True


class Notify_Gmail():
    def notify(self, subject, message, **kwargs):
        """
        Notifies the recipient at the given email address by sending an email
        with the subject and message in it. Meant to be used sparingly.
        """
        logging.info('Gmail notify')

        logging.info('Gmail post config')

        # Get the arguments from the settings
        sender   = kwargs.get('sender', Config.MAIL_SENDERNAME )
        recipient = kwargs.get('recipient', Config.MAIL_RECIPIENT)
        username = kwargs.get('username', Config.MAIL_USERNAME)
        password = kwargs.get('password', Config.MAIL_PASSWORD)
        host     = kwargs.get('host', Config.MAIL_HOST)
        port     = kwargs.get('port', Config.MAIL_PORT)
        mimetype = kwargs.get('mimetype', 'plain')
        fail_silent = True # kwargs.get('fail_silent', False)

        # Create the email message
        msg = MIMEMultipart()
        msg['From']= sender
        msg['To'] = recipient
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        logging.info('Gmail prepmime')

        # Attach the mime text to the message
        msg.attach(MIMEText(message, mimetype))

        # Attach any files to the email
        #for fpath in kwargs.get('files', []):
        fpath   = kwargs.get('files', '')
        if fpath != '':
            logging.info('-- {}'.format(fpath))
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(open(fpath, 'rb').read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename={}'.format(os.path.basename(fpath)))
            msg.attach(part)

        logging.info('- preparing to send email')

        if not ENABLE_SEND_EMAIL:
            logging.info('Send email disabled in notify gmail script')
            return True

        # Attempt to send the message
        try:

            # Do the smtp thing
            server = smtplib.SMTP(host, port)
            server.starttls()
            server.login(username, password)
            server.sendmail(sender, recipient, msg.as_string())
            server.quit()

            logging.info('- gmail sent good')

            # Return message success
            return True

        except Exception as e:
            if not fail_silent:
                raise e
            else:
                logging.exception('Caught an error')

            logging.info('- gmail NOT SENT BAD')

            # Return message failure
            return False
