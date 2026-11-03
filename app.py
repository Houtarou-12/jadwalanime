from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import html

app = Flask(__name__)

DB_PATH = os.path.join("data", "jadwal_db.json")
MUSIM_DB_PATH = os.path.join("data", "musim_db.json")
PENGGARAP_DB_PATH = os.path.join("data", "penggarap_db.json")

BULAN_ID = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
}

def get_current_anime_season_indo():
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    if month == 3:
        season, season_year = ("Musim Semi", year) if day >= 28 else ("Musim Dingin", year)
    elif 4 <= month <= 5:
        season, season_year = "Musim Semi", year
    elif month == 6:
        season, season_year = ("Musim Panas", year) if day >= 28 else ("Musim Semi", year)
    elif 7 <= month <= 8:
        season, season_year = "Musim Panas", year
    elif month == 9:
        season, season_year = ("Musim Gugur", year) if day >= 28 else ("Musim Panas", year)
    elif 10 <= month <= 11:
        season, season_year = "Musim Gugur", year
    elif month == 12:
        season, season_year = ("Musim Dingin", year + 1) if day >= 28 else ("Musim Gugur", year)
    else:
        season, season_year = "Musim Dingin", year

    return f"{season} {season_year}"

def get_current_anime_season_eng():
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    if month == 3:
        season, season_year = ("Spring", year) if day >= 28 else ("Winter", year)
    elif 4 <= month <= 5:
        season, season_year = "Spring", year
    elif month == 6:
        season, season_year = ("Summer", year) if day >= 28 else ("Spring", year)
    elif 7 <= month <= 8:
        season, season_year = "Summer", year
    elif month == 9:
        season, season_year = ("Fall", year) if day >= 28 else ("Summer", year)
    elif 10 <= month <= 11:
        season, season_year = "Fall", year
    elif month == 12:
        season, season_year = ("Winter", year + 1) if day >= 28 else ("Fall", year)
    else:
        season, season_year = "Winter", year

    return f"{season} {season_year}"

def is_current_season(anime_musim):
    if not anime_musim:
        return False
    am = anime_musim.lower()
    eng_season = get_current_anime_season_eng().lower()
    
    mapping = {
        "fall": ["fall", "gugur"],
        "summer": ["summer", "panas"],
        "spring": ["spring", "semi"],
        "winter": ["winter", "dingin"]
    }
    
    years = re.findall(r'\d{4}', am)
    current_years = re.findall(r'\d{4}', eng_season)
    
    anime_year = years[0] if years else ""
    current_year = current_years[0] if current_years else ""
    
    matched_season = False
    for eng_key, indo_keys in mapping.items():
        if any(k in am for k in [eng_key] + indo_keys):
            if any(k in eng_season for k in [eng_key] + indo_keys):
                matched_season = True
                break
                
    if not matched_season:
        return False
        
    if anime_year and current_year:
        return anime_year == current_year
        
    return matched_season

def format_tanggal_indo(tgl_str):
    if not tgl_str:
        return "-"
    try:
        dt = datetime.strptime(tgl_str, "%Y-%m-%d")
        return f"{dt.day} {BULAN_ID[dt.month]} {dt.year}"
    except ValueError:
        return tgl_str

def load_db(path, default_val):
    if not os.path.exists(path):
        save_db(path, default_val)
        return default_val
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_val

def save_db(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_title(title):
    if not title:
        return ""
    decoded = html.unescape(str(title))
    return re.sub(r'[^a-z0-9]', '', decoded.lower())

def scrape_myanimelist(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
    except Exception:
        return None

    soup = BeautifulSoup(res.text, "html.parser")
    judul_el = soup.find("h1", class_="title-name")
    judul = judul_el.text.strip() if judul_el else "Unknown Title"

    judul_alt_el = soup.find("p", class_="title-english")
    judul_alt = judul_alt_el.text.strip() if judul_alt_el else ""

    poster_el = soup.find("img", itemprop="image")
    poster = poster_el.get("data-src") or poster_el.get("src") if poster_el else ""

    def get_sidebar_info(label_text):
        for span in soup.find_all("span", class_="dark_text"):
            if label_text in span.text:
                parent = span.parent
                return parent.text.replace(span.text, "").strip()
        return "-"

    def get_sidebar_list(label_text):
        results = []
        for span in soup.find_all("span", class_="dark_text"):
            if label_text in span.text:
                parent = span.parent
                for a in parent.find_all("a"):
                    results.append(a.text.strip())
        return results

    tipe = get_sidebar_info("Type:")
    if tipe == "-" or not tipe:
        tipe = "TV"

    musim_el = soup.find("span", class_="information premiered")
    musim = musim_el.text.strip() if musim_el else get_sidebar_info("Premiered:")
    
    if musim == "-" or not musim or musim == "Unknown Season":
        aired_str = get_sidebar_info("Aired:")
        match_year = re.search(r'\d{4}', aired_str)
        if match_year:
            year_val = match_year.group(0)
            aired_lower = aired_str.lower()
            if any(m in aired_lower for m in ["jan", "feb", "mar"]):
                musim = f"Winter {year_val}"
            elif any(m in aired_lower for m in ["apr", "may", "jun"]):
                musim = f"Spring {year_val}"
            elif any(m in aired_lower for m in ["jul", "aug", "sep"]):
                musim = f"Summer {year_val}"
            elif any(m in aired_lower for m in ["oct", "nov", "dec"]):
                musim = f"Fall {year_val}"
            else:
                musim = f"Unknown Season {year_val}"
        else:
            musim = "Unknown Season"

    eps_raw = get_sidebar_info("Episodes:")
    eps = f"{eps_raw} eps" if eps_raw != "-" and eps_raw.isdigit() else (eps_raw if eps_raw != "-" else "Unknown eps")

    status_raw = get_sidebar_info("Status:")
    if "Not yet aired" in status_raw:
        status = "Belum tayang"
    elif "Currently Airing" in status_raw:
        status = "Mengudara"
    elif "Finished Airing" in status_raw:
        status = "Selesai"
    else:
        status = status_raw if status_raw != "-" else "Belum tayang"

    score_el = soup.find("span", itemprop="ratingValue")
    rating = score_el.text.strip() if score_el else "0.00"

    studio_el = soup.find("span", class_="information studio")
    studio = studio_el.text.strip() if studio_el else get_sidebar_info("Studios:")
    if studio == "-" or not studio:
        studio = "Unknown Studio"

    genre = get_sidebar_list("Genres:") or get_sidebar_list("Genre:")
    tema = get_sidebar_list("Themes:") or get_sidebar_list("Theme:")
    demografi = get_sidebar_list("Demographic:") or get_sidebar_list("Demographics:")

    synopsis_el = soup.find("p", itemprop="description")
    sinopsis = synopsis_el.text.strip() if synopsis_el else "Belum ada sinopsis."

    return {
        "judul": judul,
        "judul_alt": judul_alt,
        "musim": musim,
        "poster": poster,
        "eps": eps,
        "status": status,
        "tipe": tipe,
        "rating": rating,
        "studio": studio,
        "genre": genre,
        "tema": tema,
        "demografi": demografi,
        "sinopsis": sinopsis,
        "mal_url": url,
        "proyek_penggarap": []
    }

@app.route("/")
def anime_musim_ini():
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    daftar_musim.sort(key=lambda x: str(x.get("judul", "")).lower())
    
    sub_judul_musim = get_current_anime_season_indo()
    
    current_season_anime = [a for a in daftar_musim if is_current_season(a.get("musim"))]
    
    # Filter anime musim ini yang statusnya Belum Tayang
    anime_segera_tayang_list = [a for a in current_season_anime if "belum" in a.get("status", "").lower() or "not yet" in a.get("status", "").lower()]
    
    # Sisa anime musim ini yang sudah tayang/mengudara/selesai
    anime_musim_ini_list = [a for a in current_season_anime if a not in anime_segera_tayang_list]
    
    # Anime Lainnya (diluar musim saat ini)
    anime_lainnya_list = [a for a in daftar_musim if not is_current_season(a.get("musim"))]
    
    return render_template(
        "musim_ini.html", 
        title="Jadwal Tontonan", 
        sub_title=sub_judul_musim, 
        anime_musim_ini_list=anime_musim_ini_list,
        anime_segera_tayang_list=anime_segera_tayang_list,
        anime_lainnya_list=anime_lainnya_list
    )

@app.route("/search-anime")
def search_anime():
    query = request.args.get("q", "").lower().strip()
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    daftar_musim.sort(key=lambda x: str(x.get("judul", "")).lower())
    
    if not query:
        return jsonify([])
    
    results = []
    for anime in daftar_musim:
        judul = anime.get("judul", "")
        if query in judul.lower():
            results.append({
                "id": anime.get("id"),
                "judul": judul,
                "musim": anime.get("musim", ""),
                "poster": anime.get("poster", ""),
                "studio": anime.get("studio", "")
            })
        if len(results) >= 6:
            break
            
    return jsonify(results)

@app.route("/detail/<anime_id>")
def detail(anime_id):
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    anime_target = next((a for a in daftar_musim if str(a.get("id")) == str(anime_id)), None)
    if not anime_target:
        return redirect(url_for("anime_musim_ini"))
    return render_template("detail.html", title=anime_target.get("judul"), anime=anime_target)

@app.route("/tambah-musim-ini", methods=["POST"])
def tambah_musim_ini():
    mal_url = request.form.get("mal_url")
    if not mal_url:
        return redirect(url_for("anime_musim_ini"))

    mal_url_clean = mal_url.strip().rstrip('/')
    daftar_musim = load_db(MUSIM_DB_PATH, [])

    existing_anime = next((a for a in daftar_musim if str(a.get("mal_url", "")).rstrip('/') == mal_url_clean), None)
    
    if existing_anime:
        return redirect(url_for("detail", anime_id=existing_anime.get("id"), msg="exists"))

    scraped_data = scrape_myanimelist(mal_url)
    if scraped_data:
        new_id = str(len(daftar_musim) + 1)
        scraped_data["id"] = new_id
        scraped_data["mal_url"] = mal_url
        daftar_musim.append(scraped_data)
        save_db(MUSIM_DB_PATH, daftar_musim)
        return redirect(url_for("detail", anime_id=new_id))

    return redirect(url_for("anime_musim_ini"))

@app.route("/tambah-proyek-penggarap/<anime_id>", methods=["GET", "POST"])
def tambah_proyek_penggarap(anime_id):
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    anime_target = next((a for a in daftar_musim if str(a.get("id")) == str(anime_id)), None)
    if not anime_target:
        return redirect(url_for("anime_musim_ini"))

    daftar_master_p = load_db(PENGGARAP_DB_PATH, [])
    daftar_master_p.sort(key=lambda x: str(x.get("nama", "")).lower())

    if request.method == "POST":
        penggarap_nama = request.form.get("penggarap_nama")
        status_proyek = request.form.get("status_proyek")
        tipe_proyek = request.form.get("tipe_proyek")
        takarir = request.form.get("takarir")
        tautan = request.form.get("tautan")
        catatan = request.form.get("catatan")

        if "proyek_penggarap" not in anime_target:
            anime_target["proyek_penggarap"] = []

        proyek_baru = {
            "id": str(len(anime_target["proyek_penggarap"]) + 1),
            "nama": penggarap_nama,
            "status": status_proyek,
            "tipe": tipe_proyek,
            "takarir": takarir,
            "tautan": tautan if tautan else "",
            "catatan": catatan
        }

        anime_target["proyek_penggarap"].append(proyek_baru)
        save_db(MUSIM_DB_PATH, daftar_musim)
        return redirect(url_for("detail", anime_id=anime_id))

    return render_template("tambah_proyek_anime.html", title="Tambah Penggarap Resmi", anime=anime_target, master_penggarap=daftar_master_p, proyek=None)

@app.route("/edit-proyek-penggarap/<anime_id>/<proyek_id>", methods=["GET", "POST"])
def edit_proyek_penggarap(anime_id, proyek_id):
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    anime_target = next((a for a in daftar_musim if str(a.get("id")) == str(anime_id)), None)
    if not anime_target:
        return redirect(url_for("anime_musim_ini"))

    proyek_target = next((p for p in anime_target.get("proyek_penggarap", []) if str(p.get("id")) == str(proyek_id)), None)
    if not proyek_target:
        return redirect(url_for("detail", anime_id=anime_id))

    daftar_master_p = load_db(PENGGARAP_DB_PATH, [])
    daftar_master_p.sort(key=lambda x: str(x.get("nama", "")).lower())

    if request.method == "POST":
        proyek_target["nama"] = request.form.get("penggarap_nama")
        proyek_target["status"] = request.form.get("status_proyek")
        proyek_target["tipe"] = request.form.get("tipe_proyek")
        proyek_target["takarir"] = request.form.get("takarir")
        proyek_target["tautan"] = request.form.get("tautan") or ""
        proyek_target["catatan"] = request.form.get("catatan")

        save_db(MUSIM_DB_PATH, daftar_musim)
        return redirect(url_for("detail", anime_id=anime_id))

    return render_template("tambah_proyek_anime.html", title="Edit Penggarap Resmi", anime=anime_target, master_penggarap=daftar_master_p, proyek=proyek_target)

@app.route("/hapus-proyek-penggarap/<anime_id>/<proyek_id>")
def hapus_proyek_penggarap(anime_id, proyek_id):
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    anime_target = next((a for a in daftar_musim if str(a.get("id")) == str(anime_id)), None)
    if anime_target and "proyek_penggarap" in anime_target:
        anime_target["proyek_penggarap"] = [p for p in anime_target["proyek_penggarap"] if str(p.get("id")) != str(proyek_id)]
        save_db(MUSIM_DB_PATH, daftar_musim)
    return redirect(url_for("detail", anime_id=anime_id))

@app.route("/sinkronkan/<anime_id>", methods=["GET", "POST"])
def sinkronkan(anime_id):
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    anime_target = next((a for a in daftar_musim if str(a.get("id")) == str(anime_id)), None)

    if not anime_target:
        return redirect(url_for("anime_musim_ini"))

    mal_url = request.form.get("mal_url") or anime_target.get("mal_url")

    if mal_url:
        scraped_data = scrape_myanimelist(mal_url)
        if scraped_data:
            scraped_data["id"] = anime_target["id"]
            scraped_data["mal_url"] = mal_url
            scraped_data["proyek_penggarap"] = anime_target.get("proyek_penggarap", [])
            for i, a in enumerate(daftar_musim):
                if str(a.get("id")) == str(anime_id):
                    daftar_musim[i] = scraped_data
                    break
            save_db(MUSIM_DB_PATH, daftar_musim)

    return redirect(url_for("detail", anime_id=anime_id))

@app.route("/jadwal-tayang")
def jadwal_tayang():
    db = load_db(DB_PATH, {"jadwal": []})
    daftar_jadwal = db.get("jadwal", [])
    
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    judul_ke_id = {clean_title(a.get("judul", "")): a.get("id") for a in daftar_musim if a.get("judul")}

    for j in daftar_jadwal:
        nama_kegiatan = clean_title(j.get("kegiatan", ""))
        j["anime_id"] = judul_ke_id.get(nama_kegiatan)

    urutan_hari = {"Senin": 1, "Selasa": 2, "Rabu": 3, "Kamis": 4, "Jumat": 5, "Sabtu": 6, "Minggu": 7}
    daftar_jadwal.sort(key=lambda x: (urutan_hari.get(x.get("hari"), 8), x.get("pukul", "")))
    return render_template("index_2.html", title="Daftar Jadwal Anime", jadwal_list=daftar_jadwal)

@app.route("/daftar-penggarap")
def daftar_penggarap():
    daftar_p = load_db(PENGGARAP_DB_PATH, [])
    daftar_p.sort(key=lambda x: str(x.get("nama", "")).lower())
    return render_template("penggarap.html", title="Daftar Penggarap", penggarap_list=daftar_p)

@app.route("/tambah-penggarap", methods=["GET", "POST"])
def tambah_penggarap():
    if request.method == "POST":
        daftar_p = load_db(PENGGARAP_DB_PATH, [])
        penggarap_baru = {
            "id": str(len(daftar_p) + 1),
            "nama": request.form.get("nama"),
            "deskripsi": request.form.get("deskripsi"),
            "status": request.form.get("status"),
            "website": request.form.get("website"),
            "facebook": request.form.get("facebook"),
            "instagram": request.form.get("instagram"),
            "threads": request.form.get("threads"),
            "twitter": request.form.get("twitter"),
            "youtube": request.form.get("youtube")
        }
        daftar_p.append(penggarap_baru)
        save_db(PENGGARAP_DB_PATH, daftar_p)
        return redirect(url_for("daftar_penggarap"))
    return render_template("tambah_penggarap.html", title="Tambah Penggarap Baru")

@app.route("/tambah", methods=["GET", "POST"])
def tambah():
    daftar_musim = load_db(MUSIM_DB_PATH, [])
    daftar_musim.sort(key=lambda x: str(x.get("judul", "")).lower())
    
    list_musim = sorted(list(set(a.get("musim", "Unknown") for a in daftar_musim)))

    if request.method == "POST":
        db = load_db(DB_PATH, {"jadwal": []})
        daftar_jadwal = db.get("jadwal", [])
        
        kegiatan_baru_judul = request.form.get("kegiatan", "").strip()
        is_duplicate = any(clean_title(j.get("kegiatan", "")) == clean_title(kegiatan_baru_judul) for j in daftar_jadwal)
        
        if is_duplicate:
            return redirect(url_for("tambah", msg="duplicate"))

        tgl_raw = request.form.get("rilis_perdana")
        kegiatan_baru = {
            "id": str(len(daftar_jadwal) + 1),
            "rilis_perdana": format_tanggal_indo(tgl_raw),
            "hari": request.form.get("hari"),
            "kegiatan": kegiatan_baru_judul,
            "pukul": request.form.get("pukul"),
            "keterangan": request.form.get("keterangan") or "-"
        }
        daftar_jadwal.append(kegiatan_baru)
        db["jadwal"] = daftar_jadwal
        save_db(DB_PATH, db)
        return redirect(url_for("jadwal_tayang"))

    return render_template("tambah.html", title="Tambah Jadwal Anime", jadwal=None, daftar_anime=daftar_musim, list_musim=list_musim)

@app.route("/edit/<jadwal_id>", methods=["GET", "POST"])
def edit(jadwal_id):
    db = load_db(DB_PATH, {"jadwal": []})
    daftar_jadwal = db.get("jadwal", [])
    anime_target = next((j for j in daftar_jadwal if str(j.get("id")) == str(jadwal_id)), None)
    
    if not anime_target:
        return redirect(url_for("jadwal_tayang"))

    daftar_musim = load_db(MUSIM_DB_PATH, [])
    daftar_musim.sort(key=lambda x: str(x.get("judul", "")).lower())
    
    list_musim = sorted(list(set(a.get("musim", "Unknown") for a in daftar_musim)))

    if request.method == "POST":
        tgl_raw = request.form.get("rilis_perdana")
        anime_target["rilis_perdana"] = format_tanggal_indo(tgl_raw)
        anime_target["hari"] = request.form.get("hari")
        anime_target["kegiatan"] = request.form.get("kegiatan")
        anime_target["pukul"] = request.form.get("pukul")
        anime_target["keterangan"] = request.form.get("keterangan") or "-"
        save_db(DB_PATH, db)
        return redirect(url_for("jadwal_tayang"))

    anime_data = anime_target.copy()
    tgl_teks = anime_target.get("rilis_perdana", "")
    try:
        parts = tgl_teks.split()
        if len(parts) == 3:
            day, month_str, year = parts
            rev_bulan = {v: k for k, v in BULAN_ID.items()}
            month = rev_bulan.get(month_str)
            if month:
                dt_obj = datetime(int(year), month, int(day))
                anime_data["rilis_perdana"] = dt_obj.strftime("%Y-%m-%d")
    except Exception:
        pass

    return render_template("tambah.html", title="Edit Jadwal Anime", jadwal=anime_data, daftar_anime=daftar_musim, list_musim=list_musim)

@app.route("/hapus/<jadwal_id>")
def hapus(jadwal_id):
    db = load_db(DB_PATH, {"jadwal": []})
    daftar_jadwal = db.get("jadwal", [])
    db["jadwal"] = [j for j in daftar_jadwal if str(j.get("id")) != str(jadwal_id)]
    save_db(DB_PATH, db)
    return redirect(url_for("jadwal_tayang"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2026, debug=True)
