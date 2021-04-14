import logging
from config import cfg
import copy


DEFAULT_LOGGING = {
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
    "level": "INFO",
}

if "logging" in cfg:
    logging_params = cfg["logging"]
else:
    logging_params = DEFAULT_LOGGING


def get_logger(name):
    """Returns logger object with given name"""
    logging.basicConfig(**logging_params)
    logger = logging.getLogger(name)
    return logger