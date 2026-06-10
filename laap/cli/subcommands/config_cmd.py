"""Config management"""
import json, os
def run(args):
    cfg_path = os.path.expanduser("~/.laap/config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
    else:
        print("No config file")
