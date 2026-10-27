"""
JuruMatch — Sistem Rekomendasi Jurusan Kuliah Berbasis Web
Peringkat berdasarkan jarak profil RIASEC; perhitungan fuzzy Mamdani bersifat tambahan

Cara jalankan:
    pip install -r requirements.txt
    python app.py
Lalu buka http://127.0.0.1:5000
"""

import json
import os

from flask import Flask, render_template, request, redirect, url_for, flash, session

from logic.scoring import hitung_skor_riasec, kode_holland_dominan, profil_seragam
from logic.fuzzy_engine import rekomendasikan_jurusan
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static", static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me")

# --- muat data statis sekali di awal ---
with open(os.path.join(BASE_DIR, "data", "questions.json"), encoding="utf-8") as f:
    DAFTAR_PERTANYAAN = json.load(f)

with open(os.path.join(BASE_DIR, "data", "majors.json"), encoding="utf-8") as f:
    DAFTAR_JURUSAN = json.load(f)

# Urutan tampil dimensi RIASEC, dan metadata lengkapnya (ikon, label ID,
# deskripsi singkat) dipakai di halaman tes (dikelompokkan per dimensi)
# maupun halaman hasil.
URUTAN_DIMENSI = ["R", "I", "A", "S", "E", "C"]
JAWABAN_MIN, JAWABAN_MAKS = 1, 5  # skala Likert yang sah

DIMENSI_INFO = {
    "R": {
        "nama": "Realistic", "label": "Praktis & Teknis", "icon": "🔧", "kelas": "r",
        "deskripsi": "Cenderung menikmati aktivitas praktis yang melibatkan alat, mesin, benda konkret, atau pekerjaan lapangan.",
    },
    "I": {
        "nama": "Investigative", "label": "Analitis & Riset", "icon": "🔬", "kelas": "i",
        "deskripsi": "Cenderung menikmati kegiatan mengamati, meneliti, menganalisis, dan memecahkan masalah.",
    },
    "A": {
        "nama": "Artistic", "label": "Kreatif & Ekspresif", "icon": "🎨", "kelas": "a",
        "deskripsi": "Cenderung menikmati kegiatan kreatif seperti seni, musik, tulisan, atau desain.",
    },
    "S": {
        "nama": "Social", "label": "Sosial & Membantu", "icon": "🤝", "kelas": "s",
        "deskripsi": "Cenderung menikmati kegiatan mengajar, membimbing, membantu, dan berinteraksi dengan orang lain.",
    },
    "E": {
        "nama": "Enterprising", "label": "Memimpin & Bisnis", "icon": "📈", "kelas": "e",
        "deskripsi": "Cenderung menikmati kegiatan memimpin, meyakinkan, bernegosiasi, dan mengelola usaha.",
    },
    "C": {
        "nama": "Conventional", "label": "Administratif & Terstruktur", "icon": "🗂️", "kelas": "c",
        "deskripsi": "Cenderung menikmati pekerjaan yang rapi, terstruktur, dan berkaitan dengan data atau angka.",
    },
}

# dipertahankan untuk kompatibilitas (dipakai di halaman hasil sebagai label bar)
DESKRIPSI_DIMENSI = {
    kode: f"{info['nama']} ({info['label']})" for kode, info in DIMENSI_INFO.items()
}



def _kelompokkan_pertanyaan():
    kelompok=[]
    for kode in URUTAN_DIMENSI:
        item=[p for p in DAFTAR_PERTANYAAN if p["dimensi"]==kode]
        kelompok.append({"kode":kode,**DIMENSI_INFO[kode],"daftar_soal":item})
    return kelompok

def hash_password(password):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

def verify_password(stored,password):
    from werkzeug.security import check_password_hash
    return check_password_hash(stored,password)

def current_user():
    uid=session.get("user_id")
    return database.get_user(uid) if uid else None

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def w(*a,**kw):
        if not current_user(): return redirect(url_for("login",next=request.path))
        return fn(*a,**kw)
    return w

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def w(*a,**kw):
        u=current_user()
        if not u: return redirect(url_for("admin_login"))
        if u["role"]!="admin":
            flash("Halaman ini khusus admin."); return redirect(url_for("index"))
        return fn(*a,**kw)
    return w

@app.context_processor
def inject_user(): return {"current_user":current_user()}

@app.route("/")
def index():
    if not current_user(): return render_template("login.html")
    return render_template("index.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if current_user():
        return redirect(url_for("index"))
    error=None
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        u=database.get_user_by_email(email)
        if u and u["role"]=="user" and verify_password(u["password_hash"],password):
            session.clear()
            session["user_id"]=u["id"]
            return redirect(url_for("index"))
        error="Email atau password pengguna tidak sesuai."
    # /login without mode shows the user login form; / is the role chooser.
    return render_template("user_login.html",error=error)

@app.route("/register",methods=["GET","POST"])
def register():
    if current_user(): return redirect(url_for("index"))
    error=None
    if request.method=="POST":
        nama=request.form.get("nama","").strip(); email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if len(nama)<2 or "@" not in email: error="Nama dan email harus diisi dengan benar."
        elif len(password)<6: error="Password minimal 6 karakter."
        elif database.get_user_by_email(email): error="Email sudah terdaftar."
        else:
            uid=database.create_user(nama,email,hash_password(password))
            session.clear(); session["user_id"]=uid; return redirect(url_for("index"))
    return render_template("register.html",error=error)

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if current_user() and current_user()["role"]=="admin": return redirect(url_for("admin_dashboard"))
    error=None
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        u=database.get_user_by_email(email,"admin")
        if u and verify_password(u["password_hash"],password):
            session.clear(); session["user_id"]=u["id"]; return redirect(url_for("admin_dashboard"))
        error="Email atau password admin tidak sesuai."
    return render_template("admin_login.html",error=error)

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        users=database.semua_pengguna(),
        results=database.semua_hasil(),
        user_count=database.count_users(),
        result_count=database.count_results()
    )


@app.route("/admin/hasil/<int:hasil_id>")
@admin_required
def admin_detail_hasil(hasil_id):
    d = database.ambil_hasil(hasil_id, admin=True)

    if d is None:
        flash("Hasil tes tidak ditemukan.")
        return redirect(url_for("admin_dashboard"))

    skor = {
        "R": d["skor_r"],
        "I": d["skor_i"],
        "A": d["skor_a"],
        "S": d["skor_s"],
        "E": d["skor_e"],
        "C": d["skor_c"]
    }

    return render_template(
    "admin_hasil_detail.html",
    hasil=d,
    skor_riasec=skor,
    rekomendasi=d["rekomendasi"],
    profil_seragam=profil_seragam(skor)
)

@app.route("/tes")
@login_required
def tes():
    return render_template(
        "test.html",
        kelompok_pertanyaan=_kelompokkan_pertanyaan(),
        total_pertanyaan=len(DAFTAR_PERTANYAAN),
        nama_pengguna=current_user()["nama"]
    )
@app.route("/proses",methods=["POST"])
@login_required
def proses():
    u=current_user(); jawaban={}
    for p in DAFTAR_PERTANYAAN:
        v=request.form.get(f"q_{p['id']}")
        if v is None:
            flash(f"Pertanyaan nomor {p['id']} belum dijawab, silakan lengkapi semua.")
            return redirect(url_for("tes"))
        if not (v.isascii() and v.isdigit() and JAWABAN_MIN <= int(v) <= JAWABAN_MAKS):
            flash(f"Jawaban pertanyaan nomor {p['id']} tidak valid; pilih angka {JAWABAN_MIN} sampai {JAWABAN_MAKS}.")
            return redirect(url_for("tes"))
        jawaban[str(p["id"])]=v
    skor=hitung_skor_riasec(jawaban,DAFTAR_PERTANYAAN)
    kode=kode_holland_dominan(skor,n=3)
    rekom=rekomendasikan_jurusan(skor,DAFTAR_JURUSAN,top_n=5)
    hid=database.simpan_hasil(u["id"],u["nama"],skor,kode,rekom)
    return redirect(url_for("hasil",id_hasil=hid))

@app.route("/hasil/<int:id_hasil>")
@login_required
def hasil(id_hasil):
    u=current_user(); d=database.ambil_hasil(id_hasil,user_id=u["id"])
    if d is None:
        flash("Hasil tidak ditemukan atau bukan milik akun Anda."); return redirect(url_for("riwayat"))
    skor={"R":d["skor_r"],"I":d["skor_i"],"A":d["skor_a"],"S":d["skor_s"],"E":d["skor_e"],"C":d["skor_c"]}
    return render_template("result.html",nama=d["nama"],skor_riasec=skor,deskripsi_dimensi=DESKRIPSI_DIMENSI,
        dimensi_info=DIMENSI_INFO,urutan_dimensi=URUTAN_DIMENSI,kode_holland=d["kode_holland"],rekomendasi=d["rekomendasi"],
        profil_seragam=profil_seragam(skor))

@app.route("/riwayat")
@login_required
def riwayat():
    return render_template("history.html",daftar=database.riwayat_user(current_user()["id"]))

database.init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
