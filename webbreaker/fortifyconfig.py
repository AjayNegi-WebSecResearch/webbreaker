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
            encrypted_token = config.get("fortify", "fortify_secret")

            if encrypted_token and encrypted_token[:2] == "e$":
                encryption_version = re.search('e\$(.*)\$.*', encrypted_token).group(1)
                if encryption_version == 'Fernet':
                    encrypted_token = encrypted_token.split(encryption_version + "$", 1)[1]
                    try:
                        with open(".webbreaker", 'r') as secret_file:
                            fernet_key = secret_file.readline().strip()
                        Logger.app.debug("Fernet key found. Attempting decryption of Fortify token")
                    except IOError:
                        Logger.console.error("Error retrieving Fernet key, file does not exist. Please run 'python "
                                               "setup.py secret' to reset")
                        sys.exit(1)

                    try:
                        cipher = Fernet(fernet_key)
                        self.secret = cipher.decrypt(encrypted_token.encode()).decode()
                        Logger.app.debug("Token decrypted with no errors")
                    except ValueError as e:
                        Logger.console.error("Error decrypting the Fortify token.  Exiting now, see log {}!".format(Logger.app_logfile))
                        Logger.app.debug(e)
                        sys.exit(1)
                else:
                    Logger.console.error("Error decrypting the Fortify token.  Unsupported encryption version")
                    sys.exit(1)
            else:
                self.secret = None

        except (configparser.NoOptionError, CalledProcessError) as noe:
            Logger.console.error("{} has incorrect or missing values {}".format(config_file, noe))
        except configparser.Error as e:
            Logger.app.error("Error reading {} {}".format(config_file, e))

    def write_secret(self, secret):
        self.secret = secret

        try:
            with open(".webbreaker", 'r') as secret_file:
                fernet_key = secret_file.readline().strip()
            Logger.app.debug("Fernet key found. Attempting encryption of new Fortify token.")
        except IOError:
            Logger.console.error("Error retrieving Fernet key, file does not exist. Please run 'python setup.py "
                                   "secret' to reset")
            sys.exit(1)

        # Add proper padding to secret
        # aes_secret = "{:<24}".format(aes_secret)

        try:
            cipher = Fernet(fernet_key)
            encrypted_token = cipher.encrypt(self.secret.encode())
            Logger.console.debug("Token encrypted and saved to fortify.ini")
        except ValueError as e:
            Logger.console.error("Error encrypting Fortify token...exiting without completeing command."
                                 "Please see log {}".fortify(Logger.app_logfile))
            Logger.app.error(e)
            sys.exit(1)
        config_file = os.path.abspath(os.path.join('webbreaker', 'etc', 'fortify.ini'))
        try:
            config.read(config_file)
            config.set('fortify','fortify_secret', "e$Fernet$" + encrypted_token.decode())
            with open(config_file, 'w') as new_config:
                config.write(new_config)

        except (configparser.NoOptionError, CalledProcessError) as noe:
            Logger.app.error("{} has incorrect or missing values, see log file {}".format(config_file, Logger.app_logfile))
            Logger.app.error("{} has incorrect or missing values {}".format(config_file, noe))
        except configparser.Error as e:
            Logger.console.error("Error reading {}, see log file: {}".format(config_file, Logger.app_logfile))
            Logger.app.error("Error reading {} {}".format(config_file, e))