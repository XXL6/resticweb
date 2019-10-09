from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback
'''
Since this class creates an exclusive lock on a repository, it needs to be put into the queue
so that the repository resource can be allocated exclusively
'''
class ForgetPolicy(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.name = "ForgetPolicy"
        self.repository_interface = kwargs['repository']
        self.backup_set_tag = kwargs['backup_set_tag']
        # name suggests just policy related parameters, but it's all of the job parameters
        # as other than saved job id, and stuff that's all they are
        self.policy_parameters = kwargs.get('policy_parameters')

    def run(self):
        super().run()
        with self.repository_interface.get_credential_context():
            self.log(f"Forgetting backup set: {self.backup_set_tag}")
            command = self.repository_interface.repo_command + ["forget", "--tag", self.backup_set_tag]
            if self.policy_parameters:
                if self.policy_parameters['keep_last']:
                    command += ['--keep-last', self.policy_parameters['keep_last']]
                if self.policy_parameters['keep_hourly']:
                    command += ['--keep-hourly', self.policy_parameters['keep_hourly']]
                if self.policy_parameters['keep_daily']:
                    command += ['--keep-daily', self.policy_parameters['keep_daily']]
                if self.policy_parameters['keep_weekly']:
                    command += ['--keep-weekly', self.policy_parameters['keep_weekly']]
                if self.policy_parameters['keep_monthly']:
                    command += ['--keep-monthly', self.policy_parameters['keep_monthly']]
                if self.policy_parameters['keep_yearly']:
                    command += ['--keep-yearly', self.policy_parameters['keep_yearly']]
                if self.policy_parameters['keep_within']:
                    command += ['--keep-within', self.policy_parameters['keep_within']]
                if int(self.policy_parameters['prune']) > 0:
                    command += ['--prune']
            self.log(f"Generated command: f{command}")
            self.step(f"Forgetting{'/pruning' if int(self.policy_parameters['prune']) > 0 else ''} in progress")
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
                self.log(f"Error encountered while applying forget policy: {self.task.stderr}")
                self.status('error')
                # return self.task.stderr
            self.log(f"Forget policy has been successfully run on backup set: {self.backup_set_tag}")
            self.log(f'Restic output:\n{self.task.stdout}')
            self.status('success')
            # return 0