from resticweb.tools.rv_process import RVProcess
from resticweb.tools.repository_tools import sync_snapshots, sync_snapshot_objects, sync_repository_info
import os
import subprocess
import traceback
import json
import re

class Repository(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        #self.address = kwargs['address']
        #self.repo_password = kwargs['repo_password']
        #self.global_parameters = kwargs.get('global_parameters')
        self.field_dict = kwargs['field_dict']
        #self.engine_location = kwargs.get('engine_location')
        self.repository_interface = kwargs['repository']
        self.repository_id_found = False

    # field_list[{'name': name, 'data': data}]
    def run(self):
        super().run()
        with self.repository_interface.get_credential_context():
            command = self.repository_interface.repo_command + ['--json', 'init']
            self.step('Creating the repository')
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
            self.parse_input(self.task.stdout)
            if len(self.task.stderr) > 0:
                self.log(f"Errors: {self.task.stderr}")
            # repo id has been found so we can put the repo information into the
            # database
            if self.repository_id_found:
                self.status('success')
                return
            else:
                self.log('Unable to create repository at the specified location.')
                if "config file already exists" in self.task.stderr:
                    self.log('However this location does appear to have a pre-existing repository.')
                    self.log('Will attempt to import the repository.')
                else:
                    self.status('error')
                    return
            self.step("Importing the specified repository.")
            command = self.repository_interface.repo_command + ['stats']
            try:
                self.task = subprocess.run(
                    command,
                    capture_output=True,
                    encoding='utf-8',
                    shell=False)
            except Exception as e:
                self.log(f'Exception 1: {e}')
                self.log(f'Traceback: {traceback.format_exc()}')
                self.status('error')
                return
            self.parse_input(self.task.stdout, repo_import=True)
            if len(self.task.stderr) > 0:
                self.log(f"Errors: {self.task.stderr}")
            if self.repository_id_found:
                self.log("Imported repo successfully.")
                self.status('success')
                return
            else:
                self.log('Unable to import repository from the specified location.')
                self.status('error')
                return
        
    def parse_input(self, input, repo_import=False):
        # temp = os.read(input.fileno(), 128)
        if len(input) > 0:
            try:
                if not repo_import:
                    potential_repo_id = re.search(r"(?:created restic repository )(\w+)", input)
                else:
                    # potential_repo_id = re.search(r"(\w+)(?: opened successfully, password is correct)", input)
                    if "Stats for all snapshots in restore-size mode" in input:
                        potential_repo_id = "Unknown"
                        self.log("Unable to capture the repo id for imports at the moment.")
                        self.repository_id_found = True
                        return
                
            except ValueError:
                # print('value error')
                self.log(f'VALUEERROR FOR: {input}')
                return
            except Exception as e:
                self.log(f"Caught error: {e}")
                return
            if potential_repo_id:
                self.send_data('repo_id', potential_repo_id.group(1))
                self.log(f"Repo id captured: {potential_repo_id.group(1)}")
                self.repository_id_found = True


class RepositorySync(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.repo_id = kwargs.get('repo_id')

    def run(self):
        super().__init__()
        self.log("Started repository sync")
        self.step("Syncing repository")
        try:
            sync_repository_info(self.repo_id)
            snapshots = sync_snapshots(self.repo_id)
            for snapshot in snapshots:
                sync_snapshot_objects(self.repo_id, snapshot['snap_id'])
        except Exception:
            self.log("Failed to sync repository objects")
            self.log(f'TRACE: {traceback.format_exc()}')
            self.status("error")
            return
        self.log("Sync successful")
        self.status('success')
