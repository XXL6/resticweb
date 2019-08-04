from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback

class Prune(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = 'Prune'
        self.repository_interface = kwargs['repository']
        self.description = f'Pruning repository at {self.repository_interface.address}'

    def run(self):
        super().run()
        with self.repository_interface.get_credential_context():
            command = self.repository_interface.repo_command + ["prune"]
            self.log(f"Pruning repository at address: {self.repository_interface.address}")
            self.step("Pruning repository.")
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