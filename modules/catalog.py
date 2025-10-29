import requests
from bs4 import BeautifulSoup
import json
import os

DATA_FILE = "data/anime_db.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_field(soup, label):
    """
    Cari field berdasarkan label (misal 'Type:', 'Source:', 'Status:', dll).
    Return teks setelah label, atau '-' kalau nggak ketemu.
    """
    for div in soup.select("div.spaceit_pad"):
        text = div.get_text(strip=True)
        if text.startswith(label):
            return text.replace(label, "").strip()
    return "-"

def scrape_anime_details(url):
    """
    Scrape detail anime dari MyAnimeList.
    Ambil: title, poster, type, source, status, episodes, airing,
           genres, themes, demographics, synopsis, score.
    """
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        raise Exception(f"Gagal fetch {url} (status {res.status_code})")

    soup = BeautifulSoup(res.text, "html.parser")

    # Judul
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "-"

    # Poster
    poster_tag = soup.select_one("div.leftside img")
    poster_url = "-"
    if poster_tag:
        if poster_tag.has_attr("data-src"):
            poster_url = poster_tag["data-src"]
        elif poster_tag.has_attr("src"):
            poster_url = poster_tag["src"]

    # Type (TV, Movie, OVA, dll)
    anime_type = extract_field(soup, "Type:")

    # Source (Manga, Web Manga, Light Novel, Original, dll)
    source = extract_field(soup, "Source:")

    # Status
    status = extract_field(soup, "Status:")

    # Episodes
    episodes = extract_field(soup, "Episodes:")

    # Airing (Penayangan)
    airing = extract_field(soup, "Aired:")

    # Genres
    genres = []
    genre_links = soup.select("span:contains('Genres:') ~ a")
    if not genre_links:
        genre_links = soup.select("span:contains('Genre:') ~ a")
    for g in genre_links:
        genres.append(g.get_text(strip=True))

    # Themes
    themes = []
    theme_links = soup.select("span:contains('Themes:') ~ a")
    if not theme_links:
        theme_links = soup.select("span:contains('Theme:') ~ a")
    for t in theme_links:
        themes.append(t.get_text(strip=True))

    # Demographics
    demographics = []
    demo_links = soup.select("span:contains('Demographic:') ~ a")
    if not demo_links:
        demo_links = soup.select("span:contains('Demographics:') ~ a")
    for d in demo_links:
        demographics.append(d.get_text(strip=True))

    # Synopsis
    synopsis_tag = soup.select_one("p[itemprop='description']")
    synopsis = synopsis_tag.get_text(strip=True) if synopsis_tag else "-"

    # Score
    score_tag = soup.select_one("span[itemprop='ratingValue']")
    score = score_tag.get_text(strip=True) if score_tag else "-"

    return {
        "title": title,
        "poster": poster_url,
        "type": anime_type,
        "source": source,
        "status": status,
        "episodes": episodes,
        "airing": airing,
        "genres": genres,
        "themes": themes,
        "demographics": demographics,
        "synopsis": synopsis,
        "score": score,
        "url": url
    }

# Alias untuk kompatibilitas kode lama
def get_anime_data(url=None):
    """
    Alias untuk scrape_anime_details agar kompatibel dengan kode lama.
    - Jika diberikan URL: scrape detail dari MAL.
    - Jika tidak ada URL: return semua data lokal dari database.
    """
    if url:
        return scrape_anime_details(url)
    else:
        return load_data()

def scrape_detail_mal(url):
    """
    Alias untuk kompatibilitas kode lama.
    """
    return scrape_anime_details(url)

def add_anime(url):
    data = load_data()
    anime = scrape_anime_details(url)
    data.append(anime)
    save_data(data)
    return anime

def search_anime(keyword):
    data = load_data()
    results = []
    for anime in data:
        if keyword.lower() in anime["title"].lower():
            results.append(anime)
    return results

def list_all():
    """
    Return semua anime yang sudah tersimpan di database lokal.
    """
    return load_data()
