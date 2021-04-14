import yaml
import os


def merge_dicts(d1, d2):
    """
    Merge values in d2 into d1 in-place. Dictionaries are traversed, any other data types are overwritten.
    :param d1:
    :param d2:
    :return:
    """
    for k, v in d2.items():
        if k in d1:
            if isinstance(v, dict):
                if isinstance(d1[k], dict):
                    merge_dicts(d1[k], d2[k])
                else:
                    d1[k] = d2[k]
            else:
                d1[k] = d2[k]
        else:
            d1[k] = v


CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FN = os.path.join(CONFIG_DIR, "config.yaml")

with open(CONFIG_FN, "r") as f:
    cfg = yaml.safe_load(f)

PRIVATE_CONFIG_FN = os.path.join(CONFIG_DIR, "private_config.yaml")
if os.path.isfile(PRIVATE_CONFIG_FN):
    with open(PRIVATE_CONFIG_FN, "r") as f:
        _private_cfg = yaml.safe_load(f)
        merge_dicts(cfg, _private_cfg)

VERSION_FN = os.path.join(CONFIG_DIR, "VERSION")

with open(VERSION_FN, "r") as f:
    __version__ = f.readline()
    cfg["env"]["version"] = __version__
