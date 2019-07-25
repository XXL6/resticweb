import subprocess
import time
import os
import re
from resticweb.tools.data_trackers import ProgressTracker
# from pywin32 import O_NONBLOCK, F_GETFL, F_SETFL
# import pywin32


def execute():
    start = time.clock()
    server = subprocess.Popen(
            ['robocopy', 'C:\\Users\\Arnas\\Downloads\\test',
                'C:\\Users\\Arnas\\Downloads\\test2'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    progress = ProgressTracker()
    progress.set_regex(('(?<=\r ).*(?=%)'))
    while server.poll() is None:
        # print(os.read(server.stdout.fileno(), 128))
        # get_percentage is the thingy
        print(get_percentage(os.read(server.stdout.fileno(), 64)), end="\r")
        # time.sleep(0.1)
        # i += 1
        print(progress.parse_progress(
            os.read(server.stdout.fileno(), 64).decode('utf-8')))
        print(progress.get_current_progress())
        # print(server.stdout.read())
    print(time.clock() - start)
    # flags = pywin32(server.stdout, pywin32.F_GETFL)
    # pywin32(server.stdout, pywin32.F_SETFL, flags | pywin32.O_NONBLOCK)
    # while True:
    #    print(os.read(server.stdout.fileno(), 1024))
    # flags = functools(out.stdout, functools.F_GETFL)
    # functools(out.stdout, functools.F_SETFL, flags | os.O_NONBLOCK)
    # while out.poll() is None:
    #    print(os.read(out.stdout.fileno(), 1024))
#    for stdout in iter(server.stdout.read, b''):
#        if b"C:\\Users\\tops" in stdout:
#            print("entered if statement")
#        print(stdout)


def get_percentage(input):
    input = input.decode('utf-8')
    regex = re.search("(?<=\r ).*(?=%)", input)
    if regex:
        return regex.group()
    else:
        return ""
