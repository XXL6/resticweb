import os
import subprocess
import traceback
'''
This class is meant to run in the foreground and should not be put into the job queue
'''
class Forget():

    def __init__(self, **kwargs):
        self.repository_interface = kwargs['repository']
        self.snapshot_id = kwargs['snapshot_id']

    def run(self):
        with self.repository_interface.get_credential_context():
            command = self.repository_interface.repo_command + ["forget", self.snapshot_id]
            try:
                self.task = subprocess.run(
                    command,
                    capture_output=True,
                    encoding='utf-8',
                    shell=False)
                # stdout, stderr = self.task.communicate()
            except Exception as e:
                return e
            if len(self.task.stderr) > 0:
                return self.task.stderr
            return 0