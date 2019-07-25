from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback

class Check(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.repo_address = kwargs['repo_address']
        self.repo_password = kwargs['repo_password']
        self.global_parameters = kwargs.get('global_parameters')
        self.engine_location = kwargs['engine_location']

    def run(self):
        super().run()
        os.environ["RESTIC_PASSWORD"] = self.repo_password
        if self.global_parameters:
            for key, value in self.global_parameters:
                os.environ[key] = value
        command = [self.engine_location, '--repo', self.repo_address, "check"]
        self.log(f"Checking repository at address: {self.repo_address}")
        self.step("Checking repository.")
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