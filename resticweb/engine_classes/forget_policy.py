from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback
import json
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
        self.additional_params = kwargs.get('additional_params')
        self.snapshot_list = []

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
            if self.additional_params:
                command += [self.additional_params]
            command.append('--json')
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
                return
            self.snapshot_list = self.parse_input(self.task.stdout)
            self.send_data('snapshot_list', self.snapshot_list)
            self.log(f"Forget policy has been successfully run on backup set: {self.backup_set_tag}")
            # self.log(f'Restic output:\n{self.task.stdout}')
            self.log(f"Following snapshots have been removed: {self.snapshot_list}")
            self.status('success')
            # return 0

    def parse_input(self, line):
        if len(line) > 0:
            try:
                line = self.clean_json_string(line)
                line = json.loads(line)
            except ValueError as e:
                if len(line) > 0:
                    self.log(f"Restic: {line}")
                return
            except Exception as e:
                self.log(f"A non ValueError exception occured trying to parse a string to json: {e}")
                self.log(f'TRACE: {traceback.format_exc()}')
                self.log(line)
                return
            removals = line[0].get('remove')
            snapshot_list = []
            for item in removals:
                snapshot_list.append(item['short_id'])
        return snapshot_list