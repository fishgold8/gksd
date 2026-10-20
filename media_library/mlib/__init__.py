import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    cfg["data_dir"] = (ROOT / cfg["data_dir"]).resolve()
    return cfg


def load_people():
    return json.loads((ROOT / "people.json").read_text(encoding="utf-8"))
