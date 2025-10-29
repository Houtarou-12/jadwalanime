import json, os
DATA_FILE = "data/penggarap_db.json"

def get_penggarap_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
