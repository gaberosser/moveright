import yaml
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FN = os.path.join(CONFIG_DIR, "config.yaml")

with open(CONFIG_FN, "r") as f:
    cfg = yaml.safe_load(f)