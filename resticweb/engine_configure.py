from resticweb.dictionary.resticweb_variables import Config
import resticweb.engine as local_engine
from resticweb.dictionary.resticweb_exceptions import NoEngineAvailable
import subprocess
import os.path as path

def configure_engine():
    return_value = False
    command = [Config.ENGINE_COMMAND, 'version']
    try:
        finished_process = subprocess.run(
                    command, 
                    shell=False,
                    capture_output=True)
        if finished_process:
            line = finished_process.stdout.decode('utf-8')
            errors = finished_process.stderr.decode('utf-8')
            print(errors)
            if len(line) > 0:
                if "compiled with go" in line:
                    return_value = True
            if return_value:
                return return_value
    except FileNotFoundError:
        pass
    
    location, throwaway = path.split(local_engine.__file__)
    Config.ENGINE_COMMAND = f'{location}{path.sep}restic'
    command = [Config.ENGINE_COMMAND, 'version']
    finished_process = subprocess.run(
                command, 
                shell=False,
                capture_output=True)
    line = finished_process.stdout.decode('utf-8')
    if len(line) > 0:
        if "compiled with go" in line:
            return_value = True
    if return_value:
        return return_value
    else:
        raise NoEngineAvailable("Unable to find a backup engine.")