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
        self.repo_address = kwargs['repo_address']
        self.destination_address = kwargs['destination_address']
        self.repo_password = kwargs['repo_password']
        self.global_parameters = kwargs.get('global_parameters')
        self.object_list = kwargs.get('object_list')
        self.snapshot_id = kwargs['snapshot_id']
        self.engine_location = kwargs['engine_location']

    # field_list[{'name': name, 'data': data}]
    def run(self):
        super().run()
        os.environ["RESTIC_PASSWORD"] = self.repo_password
        if self.global_parameters:
            for key, value in self.global_parameters:
                os.environ[key] = value
        command = [self.engine_location, '--json', '--repo', self.repo_address, "restore", self.snapshot_id, "--target", self.destination_address]
        if self.object_list:
            for restore_object in self.object_list:
                command.append('--include')
                command.append(restore_object)
        self.step("Restoring data.")
        try:
            self.task = subprocess.run(
                command,
                capture_output=True,
                encoding='utf-8',
                shell=False)
            # stdout, stderr = self.task.communicate()
        except Exception as e:
            self.log(f'Exception 1: {e}')
            self.log(f'Traceback: {traceback.format_exc()}')
            self.status('error')
            return
        # self.send_data('result', self.result_tracker.get_result_dictionary())
        if len(self.task.stderr) > 0:
            self.log(self.task.stderr)
            self.status('error')
            return
        else:
            self.send_data('result', self.task.stdout)
            self.status('success')