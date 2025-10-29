import json, os

DATA_FILE = "data/proyek_db.json"
REQUIRED_FIELDS = ["id", "judul", "status", "tahun"]

def simpan_proyek(form):
    new_entry = {
        "id": form.get("id"),
        "judul": form.get("judul"),
        "status": form.get("status"),
        "tahun": form.get("tahun")
    }
    if all(new_entry.get(field) for field in REQUIRED_FIELDS):
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.append(new_entry)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
