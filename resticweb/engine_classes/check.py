from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback

class Check(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = 'Check'
        self.repository_interface = kwargs['repository']
        self.description = f'Checking repository at {self.repository_interface.address}'
        self.additional_params = kwargs.get('additional_params')

    def run(self):
        super().run()
        with self.repository_interface.get_credential_context():
            command = self.repository_interface.repo_command + ["check"]
            if self.additional_params:
                command += [self.additional_params]
            self.log(f'Command: {" ".join(command)}')
            self.log(f"Checking repository at address: {self.repository_interface.address}")
            self.step("Checking repository.")
            try:
                self.task = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    shell=False)
                self.send_data('children', [self.task.pid])
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