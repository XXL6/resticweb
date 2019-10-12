from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback
'''
Since this class creates an exclusive lock on a repository, it needs to be put into the queue
so that the repository resource can be allocated exclusively
'''
class Forget(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = 'Forget'
        self.repository_interface = kwargs['repository']
        self.snapshot_id = kwargs['snapshot_id']

    def run(self):
        super().run()
        with self.repository_interface.get_credential_context():
            self.log(f"Forgetting snapshot id: {self.snapshot_id}")
            self.step("Forgetting in progress")
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
                self.log(f"Error encountered while forgetting snapshot: {self.task.stderr}")
                self.status('error')
                # return self.task.stderr
            self.log(f"Successfully forgot snapshot: {self.snapshot_id}")
            self.status('success')
            # return 0