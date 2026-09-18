import os
import json
import tempfile

def atomic_write(path, data):
    dir_ = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    os.replace(tmp_path, path)

def load_cache(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None