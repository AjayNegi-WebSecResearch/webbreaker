#!/usr/bin/env python
# -*- coding: utf-8 -*-

from webbreaker.gitapi import GitApi
from webbreaker.webbreakerlogger import Logger
import requests
import requests.exceptions
import requests.packages.urllib3
import os
import json
try:
    import ConfigParser as configparser
except ImportError: #Python3
    import configparser
try:  # Python 2
    config = configparser.SafeConfigParser()
except NameError:  # Python 3
    config = configparser.ConfigParser()

class GitClient(object):
    def __init__(self, host):
        self.host = host
        self.token = self.get_token()

    def get_user_email(self, login):
        gitapi = GitApi(host=self.host, token=self.token, verify_ssl=False)
        response = gitapi.get_user(login)
        if response.success:
            return response.data['email']
        else:
            print(response.message)
            return None

    def get_contributors(self, owner, repo):
        gitapi = GitApi(host=self.host, token=self.token, verify_ssl=False)
        response = gitapi.get_contributors(owner, repo)
        if response.success:
            contributors = []
            for contributor in response.data:
                contributors.append(contributor['login'])
            return contributors
        else:
            print(response.message)
            return None

    def get_all_emails(self, owner, repo):
        emails = []
        logins = self.get_contributors(owner, repo)
        if logins:
            for login in logins:
                email = self.get_user_email(login)
                if email:
                    emails.append(email)
        return emails

    def get_token(self):
        config_file = os.path.abspath(os.path.join('webbreaker', 'etc', 'webbreaker.ini'))
        config.read(config_file)
        return config.get("git", "token")


def write_agent_info(name, value):
    json_file_path = os.path.abspath(os.path.join('webbreaker', 'etc', 'agent.json'))
    try:
        if os.path.isfile(json_file_path):
            with open(json_file_path, 'r') as json_file:
                try:
                    data = json.load(json_file)
                except json.decoder.JSONDecodeError:
                    data = {}
                json_file.close()
        else:
            data = {}
        data[name] = value
        with open(json_file_path, 'w') as json_file:
            json.dump(data, json_file)
    except json.decoder.JSONDecodeError:
        Logger.console.error("Error writing {} to agent.json".format(name))
        exit(1)


class UploadJSON(object):
    def __init__(self, log_file):
        self.git_emails = None
        self.fortify_pv_url = None
        self.fortify_build_id = None
        if os.path.isfile(log_file):
            with open(log_file, 'r') as json_file:
                try:
                    data = json.load(json_file)
                except json.decoder.JSONDecodeError:
                    Logger.console.error("JSONDecodeError reading from agent.json")
                    exit(1)
                json_file.close()
            if self.__verify__(data) == -1:
                exit(1)
            self.git_emails = data['git_emails']
            self.fortify_pv_url = data['fortify_pv_url']
            self.fortify_build_id = data['fortify_build_id']
        else:
            Logger.console.error("Error while reading upload payload")
            exit(1)

    def __verify__(self, data):
        if not 'git_emails' in data:
            Logger.console.error("No emails were found to notify. Please run 'webbreaker git emails --url [REPO URL]'")
            return -1
        if not 'fortify_pv_url' in data:
            Logger.console.error("No Fortify Project Version URL was found. Please run 'webbreaker fortify scan --application <some_value> --version <some_value>'")
            return -1
        if not 'fortify_build_id' in data:
            Logger.console.error("No Fortify Build ID found. Please run 'webbreaker fortify scan --build_id [BUILD_ID]'")
            return -1
        return 1

class GitUploader(object):
    def __init__(self, agent_url=None):
        self.upload_log = UploadJSON(os.path.abspath(os.path.join('webbreaker', 'etc', 'agent.json')))
        self.agent_url = agent_url
        if not agent_url:
            self.agent_url = self.read_ini()


    def read_ini(self):
        config_file = os.path.abspath(os.path.join('webbreaker', 'etc', 'webbreaker.ini'))
        config.read(config_file)
        return config.get("agent", "webbreaker_agent")


    def upload(self):
        data = {}
        data['fortify_pv_url'] = self.upload_log.fortify_pv_url
        data['fortify_build_id'] = self.upload_log.fortify_build_id
        data['git_emails'] = self.upload_log.git_emails
        response = requests.put(self.agent_url, data=data)


