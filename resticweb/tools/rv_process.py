import subprocess
import traceback
from multiprocessing import Process
from resticweb.tools.data_trackers import ProgressTracker, DataTracker, ResultTracker, BasicProgressTracker
from time import sleep
from threading import Thread, Lock
import os


# process object with the ability to deal with subprocesses and parse
# their output as necessary
class RVProcess(Process):

    def __init__(self):
        super().__init__()
        self.name = "Generic RV Process"
        self.description = "Process without a set description."
        self.category = "undefined"
        self.can_update = True
        self.data = {}
        self.job_log = []
        self.progress_tracker = ProgressTracker()
        self.basic_progress_tracker = BasicProgressTracker()
        self.data_tracker = DataTracker()
        self.result_tracker = ResultTracker()
        
        self.logging = None

    def run(self):
        self.update_thread = Thread(target=self.data_update, daemon=True)
        self.update_thread_lock = Lock()
        try:
            self.update_thread.start()
        except Exception as e:
            self.log(f"update_thread exception: {e}")
            return

    def start_subprocess(self, command):
        try:
            self.task = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            # stdout, stderr = self.task.communicate()
        except Exception as e:
            self.log(f'Exception 1: {e}')
            self.log(f'Traceback: {traceback.format_exc()}')
            self.status('error')
            return
        try:
            while self.task.poll() is None:
                self.parse_input(self.task.stdout)
                # self.log(self.progress_tracker.get_current_progress())
        except Exception as e:
            self.log(f'Exception 2: {e}')
            self.log(f'Traceback: {traceback.format_exc()}')
            self.status('error')
            return
        self.send_data('full_output', self.result_tracker.data_set)

    def parse_input(self, input):
        temp = input.readline()
        # we want to only parse the multitude of regexes every once in a while
        # in case they take up a lot of cpu time, hence we have a thread
        # running in the background that lets the regex run every set amount of
        # time at the moment, but can be changed as necessary. We still want to
        # do the os.read so that the process does not halt execution
        if (len(temp) > 0):
            self.update_thread_lock.acquire()
            if self.can_update:
                self.data_tracker.update(temp)
                self.progress_tracker.set_progress(temp)

                self.send_data('progress', self.progress_tracker.get_current_progress())
                temp_values = self.data_tracker.get_data_values()
                if temp_values is not None:
                    for key, value in self.data_tracker.get_data_values().items():
                        self.send_data(key, value)
                self.can_update = False
            self.update_thread_lock.release()
            # self.result_tracker.add_to_tracker(temp)

    def clean_json_string(self, input):
        clean = input.replace('\n', '')
        clean = clean.replace('\x1b', '')
        clean = clean.replace('\r', '')
        clean = clean.replace('\x00', '')
        clean = clean.replace('[2K', '')
        return clean

    def assign_progress_tracker(self, regex=None, json_key=None):
        self.progress_tracker.reset_progress()
        if regex:
            self.progress_tracker.set_regex(regex)
        elif json_key:
            self.progress_tracker.set_json(json_key)

    def assign_data_tracker(self, name, regex=None, json_key=None):
        self.data_tracker.insert_tracker(name, regex, json_key)

    def assign_queue(self, queue):
        self.queue = queue

    def assign_logger(self, logger):
        self.logger = logger

    def assign_data_manager(self, data_manager):
        self.data_manager = data_manager

    def send_data(self, data_name, data):
        self.queue.put(
            {'process_id': self.pid,
             'data_name': data_name,
             'data': data})

    def log(self, data):
        self.send_data('log', data)

    def status(self, data):
        self.send_data('status', data)

    def step(self, data):
        self.send_data('step', data)

    def progress(self, progress):
        self.send_data('progress', progress)

    def data_update(self):
        while True:
            self.update_thread_lock.acquire()
            self.can_update = True
            self.update_thread_lock.release()
            sleep(0.5)


# class designed to run in the foreground and have some tools for talking
# to subprocesses
class RVProcessFG():

    def __init__(self):
        self.progress_tracker = ProgressTracker()
        self.data_tracker = DataTracker()
        self.result_tracker = ResultTracker()
        

    def clean_json_string(self, input):
        clean = input.replace('\n', '')
        clean = clean.replace('\x1b', '')
        clean = clean.replace('\r', '')
        clean = clean.replace('\x00', '')
        clean = clean.replace('[2K', '')
        clean = clean.replace('read password from stdin', '')
        return clean

    def assign_progress_tracker(self, regex=None, json_key=None):
        self.progress_tracker.reset_progress()
        if regex:
            self.progress_tracker.set_regex(regex)
        elif json_key:
            self.progress_tracker.set_json(json_key)

    def assign_data_tracker(self, name, regex=None, json_key=None):
        self.data_tracker.insert_tracker(name, regex, json_key)
