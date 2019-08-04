from multiprocessing import current_process, Queue
from queue import Empty as QueueEmptyException
from multiprocessing import Lock as P_lock
from threading import Thread
from threading import Lock as T_lock
import logging
from time import sleep
# https://docs.python.org/3/library/multiprocessing.html

# class keeps track of all ub processes started by this application
# so that it can easily kill any of them in case the application exits
# has a purger thread running to trim the process list of any
# non-essential processes that have stopped


class ProcessManager:

    # queue format. {process_id: int, data_name: name, data: data itself}
    queue = Queue()
    p_lock = P_lock()
    t_lock = T_lock()
    _process_list = []

    def __init__(self):
        self.logger = logging.getLogger("debugLogger")
        self.manager_exiting = False
        # we only create the helpers in the parent process
        if current_process().name == "MainProcess":
            self.create_purger()
            self.create_queue_monitor()

    def add_process(self, input_process):
        self.logger.debug(f"Starting process {input_process.name}")
        self.t_lock.acquire()
        self._process_list.append(input_process)
        self.t_lock.release()
        try:
            input_process.assign_queue(self.queue)
            input_process.assign_logger(self.logger)
        except AttributeError:
            pass  # don't actually need to do anything
            # if the methods don't exist

        # ALL class initializations/assignments must be done
        # before the start() method because after start()
        # the only way to communicate with the class is through
        # shared memory objects like the Queue
        input_process.start()

    # returns a dictionary of processes and their statuses
    # useful when trying to relay this information to a user
    # via some front-end
    def get_process_list(self):
        return_list = []
        self.t_lock.acquire()
        for process in self._process_list:
            return_list.append({
                'name': process.name,
                'category': process.category,
                'status': "running" if process.is_alive()
                else "stopped",
                'id': process.pid
            })
        self.t_lock.release()
        return return_list

    def get_process_object(self, pid):
        return_object = None
        self.t_lock.acquire()
        for process in self._process_list:
            if process.pid == pid:
                return_object = process
                break
        self.t_lock.release()
        return return_object

    def get_process_object_name(self, name):
        return_object = None
        self.t_lock.acquire()
        for process in self._process_list:
            if process.name == name:
                return_object = process
                break
        self.t_lock.release()
        return return_object

    def get_description(self, pid):
        return_val = self.get_process_object(pid)
        if return_val:
            return_val = return_val.description
        return return_val

    def get_info(self, pid, data_name):
        info = None
        temp = self.get_process_object(pid)
        if temp:
            info = getattr(temp, data_name)
        return info

    def get_status(self, pid):
        status = None
        process = self.get_process_object(pid)
        if process:
            status = ("running" if process.is_alive()
                      else "stopped")
        return status

    def kill_process(self, pid):
        pid = int(pid)
        process = self.get_process_object(pid)
        process.terminate()

    # is there a process with a certain name?
    def process_exists(self, name):
        self.t_lock.acquire()
        for process in self._process_list:
            if process.name == name:
                self.t_lock.release()
                return True
        self.t_lock.release()
        return False

    # if process is not alive or no longer in the queue
    # we can assume that it's no longer running
    def process_running(self, name):
        for process in self._process_list:
            if process.name == name:
                return process.isAlive()
        return False

    # terminates all known child processes
    def kill_all_processes(self):
        self.t_lock.acquire()
        for process in self._process_list:
            process.terminate()
        self.t_lock.release()

    # kills all worker processes. Basically processes that aren't system
    # processes
    # unnecessary now since what used to be the system processes will
    # now be running as threads instead
    def kill_all_workers(self):
        self.t_lock.acquire()
        for process in self._process_list:
            if process.category == "worker":
                process.terminate()
        self.t_lock.release()

    # originally intended to be used with python's 'with' statement
    # but this class will probably never be used that way
    def DEL___enter__(self):
        return self

    def DEL___exit__(self):
        # by setting the following flag, we can indicate to the
        # process purger thread that we're exiting and it can stop
        # purging processes
        self.manager_exiting = True
        self.kill_all_processes()
        # we wait a bit for the process_purger thread to shut down
        # so don't just leave it hanging
        try:
            while (self.process_purger.is_alive() or
                   self.queue_monitor.is_alive()):
                sleep(5)
                self.logger.debug("Waiting for proc manager "
                                  "helper threads to exit")
        except AttributeError:
            self.logger.info("Tried waiting on the process purger "
                             "and queue monitor to exit, but they "
                             "don't appear to exist.")

    # creates the purger process and adds it to the list
    def create_purger(self, purger_name="Process Purger"):
        # if not self.process_exists(purger_name):
        self.process_purger = Thread(target=self.purge_processes,
                                     name=purger_name, daemon=True)
        self.process_purger.start()

    # periodically removes all stopped non-system processes
    # from the process list. System processes should stay in the list
    # in case they fault and need to be started up again
    def purge_processes(self):
        while not self.manager_exiting:
            self.t_lock.acquire()
            # recreates the process list only with system processes and
            # processes that haven't stopped yet
            self._process_list[:] = [process for process in self._process_list if
                                    (process.category == "system" or
                                     process.is_alive() is True)]
            self.t_lock.release()
            sleep(10)

    # multiple processes will be putting stuff in the queue all the time
    # so we create a thread to manage all the data coming in and assign it
    # to their respective processes
    # currently the data is mainly just different status variables
    # of the process
    def create_queue_monitor(self, monitor_name="Queue Monitor"):
        self.queue_monitor = Thread(target=self.monitor_queue,
                                    name=monitor_name, daemon=True)
        self.queue_monitor.start()

    def monitor_queue(self):
        while not self.manager_exiting:
            # we set a timeout on the queue so that it doesn't keep blocking
            # in case the application needs to exit
            # probably unnecessary since the thread is now a daemon
            try:
                temp_dict = self.queue.get(timeout=10)
            except QueueEmptyException:
                continue
            process = self.get_process_object(temp_dict['process_id'])
            self.t_lock.acquire()
            # we update the locally known process class instance with the
            # data that we get from the actual process of the said instance
            if temp_dict['data_name'] == 'log':
                process.job_log.append(temp_dict['data'])
            elif temp_dict['data_name'] == 'progress':
                # print('progress' + str(temp_dict['data']))
                process.data['progress'] = temp_dict['data']
            else:
                process.data[temp_dict['data_name']] = temp_dict['data']
            self.t_lock.release()
            sleep(0.01)
