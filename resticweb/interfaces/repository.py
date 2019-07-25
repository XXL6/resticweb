from resticweb.tools.rv_process import RVProcessFG
from resticweb.dictionary.resticweb_variables import Config
import subprocess
import re
import json
import os

# this is a low level restic repository interface that can be used
# by functions that need to retrieve such things as stats, and snapshots

class ResticRepository(RVProcessFG):

    def __init__(self, address, password):
        super().__init__()
        self.address = address
        self.restic_location = Config.ENGINE_COMMAND
        self.password = password

    def is_online(self):
        # os.environ["RESTIC_PASSWORD"] = self.password
        command = [self.restic_location, '--repo', self.address, 'list', 'keys', '--json']
        task = subprocess.run(
                command,
                capture_output=True,
                input=self.password,
                encoding='utf-8',
                shell=False)
        if len(task.stderr) > 0:
            return False
        else:
            return True

    # returns "total_size", "total_file_count"
    def get_stats(self):
        return_json = {}
        # os.environ["RESTIC_PASSWORD"] = self.password
        command = [self.restic_location, '--repo', self.address, 'stats', '--json']
        task = subprocess.run(
                command,
                capture_output=True,
                input=self.password,
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
        return_json = []
        # os.environ["RESTIC_PASSWORD"] = self.password
        command = [self.restic_location, '--repo', self.address, 'snapshots', '--json']
        task = subprocess.run(
                command,
                capture_output=True,
                input=self.password,
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
        return_json = []
        # os.environ["RESTIC_PASSWORD"] = self.password
        command = [self.restic_location, '--repo', self.address, 'ls', snapshot_id, '--json']
        task = subprocess.run(
                command,
                capture_output=True,
                input=self.password,
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