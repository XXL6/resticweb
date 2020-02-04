import logging
import logging.handlers
from logging.config import fileConfig
import os

def initialize_logging():
    config_file_dir = os.path.realpath(__name__)
    head, tail = os.path.split(config_file_dir)
    config_file_dir = os.path.join(head, 'resticweb', 'ub_logging')
    config_file_name = 'logging.conf'
    config_file = os.path.join(config_file_dir, config_file_name)
    try:
        fileConfig(fname=config_file)
        logger = logging.getLogger('debugLogger')
        logger.debug('Logger initialized.')
    except Exception:
        pass
