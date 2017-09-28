#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import ConfigParser as configparser
except ImportError: #Python3
    import configparser
import os
import sys
import re
from webbreaker.webbreakerlogger import Logger
from subprocess import CalledProcessError
from cryptography.fernet import Fernet

from webbreaker.secretclient import SecretClient

# TODO: Test on Python2
try:  # Python 2
    config = configparser.SafeConfigParser()
except NameError:  # Python 3
    config = configparser.ConfigParser()


class FortifyConfig(object):
    def __init__(self):
        config_file = os.path.abspath(os.path.join('webbreaker', 'etc', 'fortify.ini'))
        try:
            config.read(config_file)
            self.application_name = config.get("fortify", "application_name")
            self.project_template = config.get("fortify", "project_template")
            self.ssc_url = config.get("fortify", "ssc_url")

            secret_client = SecretClient()
            self.secret = secret_client.get('fortify', 'fortify', 'fortify_secret')

        except (configparser.NoOptionError, CalledProcessError) as noe:
            Logger.console.error("{} has incorrect or missing values {}".format(config_file, noe))
        except configparser.Error as e:
            Logger.app.error("Error reading {} {}".format(config_file, e))

    def write_secret(self, secret):
        self.secret = secret

        secret_client = SecretClient()
        secret_client.set('fortify', 'fortify', 'fortify_secret', self.secret)
