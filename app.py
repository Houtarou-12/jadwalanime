from flask import Flask, render_template, request
from modules import catalog

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def halaman_katalog():
    message = ""
    if request.method == "POST":
        mal_url = request.form.get("mal_url")
        try:
            # gunakan fungsi add_anime yang sudah ada di catalog.py
            catalog.add_anime(mal_url)
            message = "✅ Anime berhasil ditambahkan!"
        except Exception as e:
            message = f"❌ Gagal: {e}"
    anime_list = catalog.get_anime_data()
    return render_template("katalog.html", anime_list=anime_list, message=message)

@app.route("/detail/<int:index>")
def halaman_detail_anime(index):
    data = catalog.get_anime_data()
    if index < 0 or index >= len(data):
        return "Anime tidak ditemukan", 404
    anime = data[index]
    # Tidak perlu scrape ulang, karena data sudah lengkap di database
    return render_template("detail_anime.html", anime=anime)

if __name__ == "__main__":
    app.run(debug=True)
