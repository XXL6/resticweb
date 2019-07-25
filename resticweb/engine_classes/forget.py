import os
import subprocess
import traceback
'''
This class is meant to run in the foreground and should not be put into the job queue
'''
class Forget():

    def __init__(self, **kwargs):
        self.repo_address = kwargs['address']
        self.repo_password = kwargs['repo_password']
        self.global_parameters = kwargs.get('global_parameters')
        self.snapshot_id = kwargs['snapshot_id']
        self.engine_location = kwargs['engine_location']

    def run(self):
        os.environ["RESTIC_PASSWORD"] = self.repo_password
        if self.global_parameters:
            for key, value in self.global_parameters:
                os.environ[key] = value
        command = [self.engine_location, '--repo', self.repo_address, "forget", self.snapshot_id]
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
        return None