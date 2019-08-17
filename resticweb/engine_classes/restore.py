from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback
import json
import re
from resticweb.dictionary.resticweb_constants import MiscResticConstants

class Restore(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = 'Restore'
        self.repository_interface = kwargs['repository']
        self.description = f'Restoring from {self.repository_interface.address}'
        self.destination_address = kwargs['destination_address']
        self.object_list = kwargs.get('object_list')
        self.snapshot_id = kwargs['snapshot_id']

    # field_list[{'name': name, 'data': data}]
    def run(self):
        super().run()
        with self.repository_interface.get_credential_context():
            command = self.repository_interface.repo_command + ['--json', "restore", self.snapshot_id, "--target", self.destination_address]
            self.log(f'Restore to: {self.destination_address}')
            self.log(f'Using snapshot id: {self.snapshot_id}')
            self.log(f'From repository at: {self.repository_interface.address}')
            if self.object_list:
                for restore_object in self.object_list:
                    self.log(f'Restore: {restore_object}')
                    command.append('--include')
                    command.append(f'{restore_object}')
            self.step("Restoring data.")
            try:
                self.task = subprocess.Popen(
                    command,
                    # capture_output=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    shell=False)
                stdout, stderr = self.task.communicate()
            except Exception as e:
                self.log(f'Exception 1: {e}')
                self.log(f'Traceback: {traceback.format_exc()}')
                self.status('error')
                return
            # self.send_data('result', self.result_tracker.get_result_dictionary())
            if len(stderr) > 0:
                self.log(stderr)
                self.status('error')
                return
            else:
                self.send_data('result', stdout)
                self.status('success')