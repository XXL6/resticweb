from resticweb.tools.rv_process import RVProcessFG
from resticweb.dictionary.resticweb_variables import Config
import subprocess
import re
import json
import os
import logging

# this is a low level restic repository interface that can be used
# by functions that need to retrieve such things as stats, and snapshots

class ResticRepository(RVProcessFG):

    def __init__(self, address, password, global_credentials=None):
        super().__init__()
        logger = logging.getLogger('debugLogger')
        self.address = address
        self.restic_location = Config.ENGINE_COMMAND
        logger.debug(f'addr: {address}')
        logger.debug(f'loc: {self.restic_location}')
        self.password = password
        self.global_credentials = global_credentials
        if not self.global_credentials:
            self.global_credentials = {}
        self.global_credentials["RESTIC_PASSWORD"] = self.password
        self.repo_command = [self.restic_location, '--repo', self.address]

    def get_credential_context(self):
        return ResticCredentials(self.global_credentials)

    def is_online(self):
        with ResticCredentials(self.global_credentials):
            command = self.repo_command + ['list', 'keys', '--json']
            try:
                task = subprocess.run(
                        command,
                        capture_output=True,
                        encoding='utf-8',
                        shell=False,
                        timeout=10)
            except subprocess.TimeoutExpired:
                return False
            if len(task.stderr) > 0:
                return False
            else:
                return True

    # basically identical to is_online but it returns the offline error
    # message if the repo is offline.
    def is_offline(self):
        with ResticCredentials(self.global_credentials):
            command = self.repo_command + ['list', 'keys', '--json']
            try:
                task = subprocess.run(
                        command,
                        capture_output=True,
                        encoding='utf-8',
                        shell=False,
                        timeout=10)
            except subprocess.TimeoutExpired as e:
                return f"Error getting status: {e}"
            if len(task.stderr) > 0:
                return task.stderr
            else:
                return False

    # returns "total_size", "total_file_count"
    def get_stats(self):
        with ResticCredentials(self.global_credentials):
            return_json = {}
            command = self.repo_command + ['stats', '--json']
            task = subprocess.run(
                    command,
                    capture_output=True,
                    encoding='utf-8',
                    shell=False)
            line = task.stdout
            if len(line) > 0:
                try:
                    line = self.clean_json_string(line)
                    return_json = json.loads(line)
                except ValueError:
                    pass
                except Exception:
                    pass
            return return_json

    def get_snapshots(self):
        with ResticCredentials(self.global_credentials):
            return_json = []
            command = self.repo_command + ['snapshots', '--json']
            task = subprocess.run(
                    command,
                    capture_output=True,
                    encoding='utf-8',
                    shell=False)
            line = task.stdout
            if len(line) > 0:
                try:
                    line = self.clean_json_string(line)
                    return_json = json.loads(line)
                except ValueError:
                    pass
                except Exception:
                    pass
            return return_json

    def get_snapshot_ls(self, snapshot_id):
        with ResticCredentials(self.global_credentials):
            return_json = []
            command = self.repo_command + ['ls', snapshot_id, '--json']
            task = subprocess.run(
                    command,
                    capture_output=True,
                    encoding='utf-8',
                    shell=False)
            line = task.stdout
            if len(line) > 0:
                lines = line.split("\n")
                for item in lines:
                    try:
                        item = self.clean_json_string(item)
                        return_json.append(json.loads(item))
                    except ValueError:
                        pass
                    except Exception:
                        pass
            return return_json


# by using this class, we should hopefully avoid having the global
# credentials in the global vars for longer than necessary
class ResticCredentials():
    def __init__(self, credentials):
        self.credentials = credentials

    def __enter__(self):
        for key, value in self.credentials.items():
            os.environ[key] = value
    
    def __exit__(self, type, value, traceback):
        for key, value in self.credentials.items():
            os.environ[key] = ""