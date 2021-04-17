import logging
from config import cfg
import copy
from logging import handlers


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
    log_kwds = copy.deepcopy(logging_params)
    if "handler" in log_kwds:
        handler_params = log_kwds.pop("handler")
        typ = handler_params.pop("__type__")
        cls = getattr(handlers, typ)
        h = cls(**handler_params)
        log_kwds["handlers"] = [h]

    logging.basicConfig(**log_kwds)
    logger = logging.getLogger(name)
    return logger