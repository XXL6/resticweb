from resticweb.tools.rv_process import RVProcess
import os
import subprocess
import traceback
import json
import re
from time import sleep
from resticweb.dictionary.resticweb_constants import MiscResticConstants
from threading import Thread

class Backup(RVProcess):

    def __init__(self, **kwargs):
        super().__init__()
        self.repository_interface = kwargs['repository']
        object_list = kwargs['object_list']
        self.file_include_list = [file[1:] for file in object_list if file[0] == MiscResticConstants.FILE_INCLUSION_KEY]
        self.file_exclude_list = [file[1:] for file in object_list if file[0] == MiscResticConstants.FILE_EXCLUSION_KEY]
        self.temp_folder_location = os.path.join(os.path.dirname(__file__), os.pardir, '.temp')
        self.errors = []

    # field_list[{'name': name, 'data': data}]
    def run(self):
        super().run()
        if not self.repository_interface.is_online():
            self.log(f"Repository at address {self.repository_interface.address} cannot be reached. Job aborting.")
            self.status('error')
            return
        self.progress_tracker.set_json('percent_done')
        self.progress_tracker.set_multiplier(100)
        self.data_tracker.insert_tracker('total_files', 'total_files')
        self.data_tracker.insert_tracker('files_done', 'files_done')
        self.data_tracker.insert_tracker('total_bytes', 'total_bytes')
        self.data_tracker.insert_tracker('bytes_done', 'bytes_done')
        self.data_tracker.insert_tracker('current_files', 'current_files')
        self.data_tracker.insert_tracker('seconds_elapsed', 'seconds_elapsed')
        self.data_tracker.insert_tracker('seconds_remaining', 'seconds_remaining')
        if len(self.file_include_list) > 0:
            backup_object_filename = self.create_file_list()
        else:
            self.log("Nothing to back up. Job stopping")
            self.status("success")
            return
        exclusion_command = ''
        exclusion_filename = ''
        if len(self.file_exclude_list) > 0:
            exclusion_filename = self.create_exclusions_file()
            exclusion_command = ['--exclude-file', exclusion_filename]
        command = self.repository_interface.repo_command + ['--json', "backup", "--files-from", backup_object_filename]
        if exclusion_command:
            command = command + exclusion_command
        with self.repository_interface.get_credential_context():
            try:
                self.task = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8',
                    shell=False)
                # stdout, stderr = self.task.communicate()
            except Exception as e:
                self.log(f'Exception 1: {e}')
                self.log(f'Traceback: {traceback.format_exc()}')
                self.status('error')
                self.delete_file_list(backup_object_filename)
                return
            Thread(target=self.error_reader, args=[self.task.stderr], daemon=True).start()
            try:
                while self.task.poll() is None:
                    self.parse_input(self.task.stdout)
            except Exception as e:
                self.log(f'Exception 2: {e}')
                self.log(f'Traceback: {traceback.format_exc()}')
                self.status('error')
                self.delete_file_list(backup_object_filename)
                return
            self.delete_file_list(backup_object_filename)
            if (exclusion_filename):
                self.delete_exclusions_file(exclusion_filename)
            # self.log(f'Errors: {self.task.stderr}')
            # self.send_data('progress', self.progress_tracker.get_current_progress())
            self.send_data('result', self.result_tracker.get_result_dictionary())
            if len(self.errors) > 0:
                self.log('Errors encountered while backing up.')
                for error in self.errors:
                    self.log(error)
                self.status('error')
                return
            if self.result_tracker.is_empty():
                self.log('''The job result set is empty. An error might have been encountered while running
                        the job, or the job has been declared finished before the backup could actually be
                        completed''')
                self.status('warning')
                return
            self.status('success')
        
    def parse_input(self, input):
        line = input.readline()
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
            self.progress_tracker.set_progress(line)
            self.data_tracker.update(line)
            self.send_data('progress', self.progress_tracker.get_current_progress())
            self.send_data('tracked_data', self.data_tracker.get_data_values())
            if line.get('message_type') == 'summary':
                self.result_tracker.add_to_tracker('files_new', line.get('files_new'))
                self.result_tracker.add_to_tracker('files_changed', line.get('files_changed'))
                self.result_tracker.add_to_tracker('files_unmodified', line.get('files_unmodified'))
                self.result_tracker.add_to_tracker('dirs_new', line.get('dirs_new'))
                self.result_tracker.add_to_tracker('dirs_changed', line.get('dirs_changed'))
                self.result_tracker.add_to_tracker('dirs_unmodified', line.get('dirs_unmodified'))
                self.result_tracker.add_to_tracker('data_blobs', line.get('data_blobs'))
                self.result_tracker.add_to_tracker('tree_blobs', line.get('tree_blobs'))
                self.result_tracker.add_to_tracker('data_added', line.get('data_added'))
                self.result_tracker.add_to_tracker('total_files_processed', line.get('total_files_processed'))
                self.result_tracker.add_to_tracker('total_bytes_processed', line.get('total_bytes_processed'))
                self.result_tracker.add_to_tracker('total_duration', line.get('total_duration'))
                self.result_tracker.add_to_tracker('snapshot_id', line.get('snapshot_id'))

    def error_reader(self, pipe):
        try:
            with pipe:
                for line in iter(pipe.readline, ''):
                    self.errors.append(line)
        except Exception:
            pass

    def create_file_list(self):
        for i in range(0,100):
            filename = f'backup_file_list_{i}'
            full_path = os.path.join(self.temp_folder_location, filename)
            try:
                with open(full_path, 'x') as f:
                    for bak_object in self.file_include_list:
                        f.write(bak_object + '\n')
            except FileExistsError:
                continue
            except OSError as e:
                self.log(f'Exception while creating the file list: {e}')
                self.status('error')
                self.terminate()
            except Exception as e:
                self.log(f'Exception while creating the file list: {e}')
                self.status('error')
                self.terminate()
            file_list_name = full_path
            break
        if file_list_name:
            return file_list_name
        else:
            self.log(f'Unable to create a file list for Restic to read. Process exiting')
            self.status('error')
            self.terminate()

    def create_exclusions_file(self):
        for i in range(0,100):
            filename = f'exclusion_file_list_{i}'
            full_path = os.path.join(self.temp_folder_location, filename)
            try:
                with open(full_path, 'x') as f:
                    for bak_object in self.file_exclude_list:
                        f.write(bak_object + '\n')
            except FileExistsError:
                continue
            except OSError as e:
                self.log(f'Exception while creating the file list: {e}')
                self.status('error')
                self.terminate()
            except Exception as e:
                self.log(f'Exception while creating the file list: {e}')
                self.status('error')
                self.terminate()
            exclusion_file_list_name = full_path
            break
        if exclusion_file_list_name:
            return exclusion_file_list_name
        else:
            self.log(f'Unable to create an item exclusion file for Restic to read. Process exiting')
            self.status('error')
            self.terminate()

    def delete_file_list(self, file_list_name):
        try:
            os.remove(file_list_name)
        except OSError as e:
            self.log(f'Unable to delete file \'{file_list_name}\'. Program may have still executed as expected. Exception: {e} ')
            self.status('warning')

    def delete_exclusions_file(self, exclusion_file_list_name):
        try:
            os.remove(exclusion_file_list_name)
        except OSError as e:
            self.log(f'Unable to delete file \'{exclusion_file_list_name}\'. Program may have still executed as expected. Exception: {e} ')
            self.status('warning')
