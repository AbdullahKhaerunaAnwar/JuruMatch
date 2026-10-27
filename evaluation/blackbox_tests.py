"""Uji black-box fungsional JuruMatch memakai Flask test client.

Persiapan basis data (didokumentasikan agar dapat diulang):
  1. Folder sementara baru dibuat; database.DB_PATH diarahkan ke berkas SQLite kosong
     di dalamnya SEBELUM app.py diimpor (DATABASE_URL tidak diset).
  2. Mengimpor app.py memanggil database.init_db(): membuat tabel users dan
     hasil_tes serta akun admin dari ADMIN_EMAIL / ADMIN_PASSWORD (diset di sini).
  3. Skenario dijalankan berurutan pada basis data yang sama (urutan = nomor
     skenario). Tiap skenario mencatat jumlah hasil tersimpan sebelum/sesudah.

Setiap skenario mencatat: input, perilaku yang diharapkan, perilaku teramati.
"""
import itertools
import json
import os
import re
import sqlite3
import sys
import tempfile
from unittest import mock

from common import Recorder, parse_args, setup_path

args = parse_args("Uji black-box JuruMatch")
APP_DIR = setup_path(args.app_dir)

TMP = tempfile.mkdtemp(prefix="jurumatch_bb_")
DB_FILE = os.path.join(TMP, "uji.db")
os.environ.pop("DATABASE_URL", None)
os.environ["ADMIN_EMAIL"] = "admin-uji@example.test"
os.environ["ADMIN_PASSWORD"] = "admin-uji-123456"
os.environ["SECRET_KEY"] = "kunci-uji-saja"

import database  # noqa: E402
database.DB_PATH = DB_FILE                      # sebelum impor app (init_db dipanggil saat impor)
import app as jm  # noqa: E402
from logic import fuzzy_engine  # noqa: E402

DIM = ["R", "I", "A", "S", "E", "C"]
QIDS = [p["id"] for p in jm.DAFTAR_PERTANYAAN]
rec = Recorder("blackbox")


# ----------------------------------------------------------------- pembantu
def db(sql, params=()):
    con = sqlite3.connect(DB_FILE)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def n_results():
    return db("SELECT COUNT(*) FROM hasil_tes")[0][0]


def payload(value=3, **override):
    d = {f"q_{i}": str(value) for i in QIDS}
    d.update({k: str(v) for k, v in override.items()})
    return d


def payload_sums(sums):
    """Jawaban 1-5 untuk 8 butir per dimensi dengan jumlah mentah tertentu (8..40)."""
    out = {}
    for dim, s in zip(DIM, sums):
        base, rem = divmod(s, 8)
        ids = [p["id"] for p in jm.DAFTAR_PERTANYAAN if p["dimensi"] == dim]
        for k, i in enumerate(ids):
            out[f"q_{i}"] = str(base + (1 if k < rem else 0))
    return out


def text(resp):
    return resp.get_data(as_text=True)


def last_id(resp):
    m = re.search(r"/hasil/(\d+)", resp.headers.get("Location", ""))
    return int(m.group(1)) if m else None


def stored(rid):
    row = db("SELECT skor_r,skor_i,skor_a,skor_s,skor_e,skor_c,kode_holland,rekomendasi_json FROM hasil_tes WHERE id=?", (rid,))[0]
    return list(row[:6]), row[6], json.loads(row[7])


def indep_rank(scores):
    """Peringkat independen: 100 - rata-rata selisih mutlak, urut (-skor, nama)."""
    out = []
    for m in jm.DAFTAR_JURUSAN:
        d = sum(abs(scores[i] - m["target"][k] * 100) for i, k in enumerate(DIM)) / 6
        out.append((round(max(0.0, min(100.0, 100.0 - d)), 2), m["nama"]))
    return [(n, s) for s, n in sorted(out, key=lambda x: (-x[0], x[1]))][:5]


def register(client, nama, email, password):
    return client.post("/register", data={"nama": nama, "email": email, "password": password})


def post_answers(client, data):
    return client.post("/proses", data=data)


# ----------------------------------------------------------------- S0 inisialisasi basis data
tables = sorted(r[0] for r in db("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
admin_rows = db("SELECT role FROM users WHERE email=?", (os.environ["ADMIN_EMAIL"],))
rec.check("S0", "Inisialisasi basis data", "impor app.py pada berkas SQLite baru",
          "tabel hasil_tes & users ada; 1 akun admin; 0 hasil",
          f"tabel={tables}; admin={[r[0] for r in admin_rows]}; hasil={n_results()}",
          ok=tables == ["hasil_tes", "users"] and [r[0] for r in admin_rows] == ["admin"] and n_results() == 0)

c = jm.app.test_client()           # sesi pengguna 1
c_anon = jm.app.test_client()

# ----------------------------------------------------------------- S1-S4 akses dan registrasi
r = c_anon.get("/")
rec.check("S1", "Akses halaman awal", "GET / tanpa sesi", "200; halaman pilihan akses/login",
          f"{r.status_code}; 'Pilih jenis akses'={'Pilih jenis akses' in text(r)}",
          ok=r.status_code == 200 and "Pilih jenis akses" in text(r))
r = c_anon.get("/tes")
rec.check("S2", "Proteksi rute", "GET /tes tanpa sesi", "302 ke /login?next=/tes",
          f"{r.status_code} -> {r.headers.get('Location')}", ok=r.status_code == 302 and "/login" in r.headers.get("Location", ""))
r = register(c_anon, "Uji Pendek", "pendek@example.test", "abcde")
rec.check("S3", "Registrasi: password 5 karakter", "POST /register", "ditolak (form tampil ulang, tanpa redirect)",
          f"{r.status_code}; pesan 'minimal 6'={'minimal 6' in text(r)}", ok=r.status_code == 200 and "minimal 6" in text(r))
r = register(c, "Penguji Satu", "satu@example.test", "abcdef")
rec.check("S4", "Registrasi valid", "POST /register (password 6 karakter)", "302 dan sesi terbuka",
          f"{r.status_code}", ok=r.status_code == 302)

# ----------------------------------------------------------------- S5 halaman tes
r = c.get("/tes")
t = text(r)
radios = len(re.findall(r'type="radio"', t))
groups = len(set(re.findall(r'name="(q_\d+)"', t)))
rec.check("S5", "Halaman tes", "GET /tes (login)", "200; 48 butir x 5 pilihan = 240 radio",
          f"{r.status_code}; radio={radios}; butir={groups}", ok=r.status_code == 200 and radios == 240 and groups == 48)

# ----------------------------------------------------------------- S6 jawaban tidak lengkap
before = n_results()
data = payload(); data.pop("q_48")
r = post_answers(c, data)
msg = text(c.get("/tes"))
rec.check("S6", "Pengiriman tidak lengkap", "47 dari 48 jawaban (butir 48 hilang)",
          "302 ke /tes; pesan 'nomor 48 belum dijawab'; tidak ada yang tersimpan",
          f"{r.status_code} -> {r.headers.get('Location')}; pesan={'nomor 48 belum dijawab' in msg}; hasil +{n_results() - before}",
          ok=r.status_code == 302 and r.headers.get("Location", "").endswith("/tes") and "nomor 48 belum dijawab" in msg and n_results() == before)

# ----------------------------------------------------------------- S7-S11 pola batas dan profil seragam
UNI = {}
for lvl in (1, 3, 5, 2, 4):
    b = n_results()
    r = post_answers(c, payload(lvl))
    rid = last_id(r)
    UNI[lvl] = rid
    if rid is None:
        rec.check(f"S7.all{lvl}", f"Semua jawaban = {lvl}", "48 x " + str(lvl), "302 ke /hasil/<id>", f"{r.status_code}", ok=False)
        continue
    sk, kode, rek = stored(rid)
    page = text(c.get(f"/hasil/{rid}"))
    exp_score = {1: 0.0, 2: 25.0, 3: 50.0, 4: 75.0, 5: 100.0}[lvl]
    ranked = indep_rank(sk)
    rec.check(f"S7.all{lvl}.hitung", f"Semua jawaban = {lvl}: skor, kode, peringkat", f"48 x {lvl}",
              f"enam skor = {exp_score}; kode RIA; 5 rekomendasi = peringkat independen {ranked[0]}...",
              f"skor={sk}; kode={kode}; top-1=({rek[0]['nama']}, {rek[0]['skor_kecocokan']}); tersimpan={len(rek)}",
              ok=sk == [exp_score] * 6 and kode == "RIA" and len(rek) == 5 and [(x['nama'], x['skor_kecocokan']) for x in rek] == ranked)
    warn = "belum terdiferensiasi" in page
    pill_hidden = not any(lab in page.split("Program Studi")[-1] for lab in
                          ("Kemiripan Sangat Tinggi", "Kemiripan Tinggi", "Kemiripan Sedang", "Kemiripan Rendah", "Kemiripan Sangat Rendah")) if "Program Studi" in page else False
    code_note = "tidak ditampilkan" in page and f'<strong class="kode-holland">{kode}</strong>' not in page
    rec.check(f"S7.all{lvl}.antarmuka", f"Profil seragam (semua = {lvl}): antarmuka",
              f"GET /hasil/{rid}", "peringatan 'belum terdiferensiasi'; kode Holland tidak ditampilkan; label pita disembunyikan",
              f"peringatan={warn}; kode_disembunyikan={code_note}; pita_disembunyikan={pill_hidden}",
              ok=warn and code_note and pill_hidden)

# non-seragam: contoh kerja (S=15,27,27,24,17,31) dan hampir seragam (47x3 + satu 4)
b = n_results()
r = post_answers(c, payload_sums((15, 27, 27, 24, 17, 31)))
rid_work = last_id(r)
sk, kode, rek = stored(rid_work)
page = text(c.get(f"/hasil/{rid_work}"))
rec.check("S8.contoh", "Profil tidak seragam (contoh kerja)", "S=(15,27,27,24,17,31)",
          "skor [21.88,59.38,59.38,50.0,28.12,71.88]; kode CIA; tanpa peringatan; pita tampil; skor 'x / 100'; peringkat = independen",
          f"skor={sk}; kode={kode}; peringatan={'belum terdiferensiasi' in page}; pita={'Kemiripan' in page.split('Program Studi')[-1]}; "
          f"format={'/ 100' in page}",
          ok=sk == [21.88, 59.38, 59.38, 50.0, 28.12, 71.88] and kode == "CIA" and "belum terdiferensiasi" not in page
          and "/ 100" in page and [(x['nama'], x['skor_kecocokan']) for x in rek] == indep_rank(sk))
data = payload(3, q_1=4)
rid_near = last_id(post_answers(c, data))
page = text(c.get(f"/hasil/{rid_near}"))
rec.check("S8.hampir", "Hampir seragam: satu skor berbeda", "47 x 3 dan q_1=4", "tanpa peringatan (skor R = 53.12, lainnya 50.0)",
          f"peringatan={'belum terdiferensiasi' in page}; skor={stored(rid_near)[0]}",
          ok="belum terdiferensiasi" not in page and stored(rid_near)[0] != [50.0] * 6)

# ----------------------------------------------------------------- S9 disclaimer dan label
page = text(c.get(f"/hasil/{UNI[3]}"))
old = [lab for lab in ("Sangat Cocok", "Tidak Cocok", "Cukup Cocok") if lab in page]
page_n = text(c.get(f"/hasil/{rid_work}"))
rec.check("S9", "Disclaimer dan label pada halaman hasil", "GET /hasil/<id>",
          "memuat 'bukan probabilitas' dan 'heuristik'; label 'Kemiripan ...'; tanpa label lama 'Sangat Cocok/Cukup Cocok/Tidak Cocok'",
          f"bukan probabilitas={'bukan probabilitas' in page_n}; heuristik={'heuristik' in page_n}; "
          f"label baru={'Kemiripan Sangat Tinggi' in page_n}; label lama ditemukan={old}",
          ok="bukan probabilitas" in page_n and "heuristik" in page_n and "Kemiripan Sangat Tinggi" in page_n and not old)
rec.check("S10", "Isi halaman hasil", f"GET /hasil/{rid_work}", "200; kode Holland dan 5 program berperingkat",
          f"kode CIA tampil={'CIA' in page_n}; kartu={page_n.count('rekom-card')}", ok="CIA" in page_n and page_n.count('class="rekom-card"') == 5)

# ----------------------------------------------------------------- S12 riwayat
r = c.get("/riwayat")
rec.check("S12", "Riwayat", "GET /riwayat", f"200; {n_results()} hasil terdaftar (semua milik pengguna ini)",
          f"{r.status_code}; tautan={text(r).count('Lihat')}", ok=r.status_code == 200 and text(r).count("Lihat →") == n_results())

# ----------------------------------------------------------------- S13 jawaban tidak valid
bad_values = [("9", "di atas rentang"), ("0", "di bawah rentang"), ("abc", "non-numerik"), ("", "kosong"),
              ("3.5", "desimal"), ("-1", "negatif"), ("+3", "bertanda plus"), ("٣", "digit non-ASCII"), (" 3", "berspasi"), ("6", "di atas rentang")]
for val, why in bad_values:
    b = n_results()
    data = payload(3, q_1=val)
    others_ok = all(str(data[k]).isdigit() and 1 <= int(data[k]) <= 5 for k in data if k != "q_1")
    r = post_answers(c, data)
    msg_page = text(c.get("/tes"))
    expect_msg = "Jawaban pertanyaan nomor 1 tidak valid" in msg_page
    rec.check(f"S13.{why}", f"Jawaban tidak valid ({why})", f"q_1={val!r}; 47 jawaban lain valid ({others_ok})",
              "302 ke /tes; pesan 'Jawaban pertanyaan nomor 1 tidak valid'; tidak ada yang tersimpan",
              f"{r.status_code} -> {r.headers.get('Location')}; pesan={expect_msg}; hasil +{n_results() - b}",
              ok=others_ok and r.status_code == 302 and r.headers.get("Location", "").endswith("/tes") and expect_msg and n_results() == b)
for qid, val in ((25, "abc"), (48, "0")):
    b = n_results()
    r = post_answers(c, payload(3, **{f"q_{qid}": val}))
    msg_page = text(c.get("/tes"))
    rec.check(f"S13.q{qid}", "Jawaban tidak valid (butir lain)", f"q_{qid}={val!r}", f"pesan menyebut nomor {qid}; tidak tersimpan",
              f"{r.status_code}; pesan={f'Jawaban pertanyaan nomor {qid} tidak valid' in msg_page}; hasil +{n_results() - b}",
              ok=r.status_code == 302 and f"Jawaban pertanyaan nomor {qid} tidak valid" in msg_page and n_results() == b)

# ----------------------------------------------------------------- S14 proteksi peran dan isolasi data
r = c.get("/admin")
r2 = c.get(f"/admin/hasil/{rid_work}")
rec.check("S14", "Proteksi peran admin", "GET /admin dan /admin/hasil/<id> dengan sesi pengguna biasa", "tidak dapat diakses (302)",
          f"{r.status_code} -> {r.headers.get('Location')}; {r2.status_code} -> {r2.headers.get('Location')}",
          ok=r.status_code == 302 and r2.status_code == 302)
c2 = jm.app.test_client()
register(c2, "Penguji Dua", "dua@example.test", "abcdef")
r = c2.get(f"/hasil/{rid_work}")
rec.check("S15", "Isolasi data antar pengguna", "pengguna 2 membuka /hasil/<id milik pengguna 1>", "dialihkan ke /riwayat; isi tidak tampil",
          f"{r.status_code} -> {r.headers.get('Location')}", ok=r.status_code == 302 and "/riwayat" in r.headers.get("Location", ""))

# ----------------------------------------------------------------- S16 admin: detail dan centroid
ca = jm.app.test_client()
r = ca.post("/admin/login", data={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
rec.check("S16", "Login admin", "POST /admin/login", "302", f"{r.status_code} -> {r.headers.get('Location')}", ok=r.status_code == 302)
r = ca.get(f"/admin/hasil/{rid_work}")
adm = text(r)
cent_first = stored(rid_work)[2][0]["mamdani_centroid"]
user_page = text(c.get(f"/hasil/{rid_work}"))
rec.check("S17", "Centroid fuzzy tambahan hanya di halaman detail admin", f"GET /admin/hasil/{rid_work} (admin) vs /hasil/{rid_work} (pengguna)",
          f"admin 200 dan memuat centroid {cent_first:.2f} berlabel 'tidak memengaruhi urutan'; halaman pengguna tanpa kata 'centroid'",
          f"admin={r.status_code}; centroid_tampil={f'{cent_first:.2f}' in adm and 'Centroid' in adm}; "
          f"label={'tidak memengaruhi urutan' in adm}; pengguna_bebas_centroid={'entroid' not in user_page}",
          ok=r.status_code == 200 and f"{cent_first:.2f}" in adm and "Centroid" in adm and "tidak memengaruhi urutan" in adm and "entroid" not in user_page)

# ----------------------------------------------------------------- S18 centroid tidak memengaruhi urutan
def rank_sig(scores, variant):
    ranked = fuzzy_engine.rekomendasikan_jurusan(scores, jm.DAFTAR_JURUSAN, top_n=20)
    return [(r["nama"], r["skor_kecocokan"]) for r in ranked], [r["mamdani_centroid"] for r in ranked]


profiles = {"semua 1": [0.0] * 6, "semua 3": [50.0] * 6, "semua 5": [100.0] * 6,
            "contoh kerja": stored(rid_work)[0], "hampir seragam": stored(rid_near)[0],
            "R tinggi": [90.0, 40.0, 10.0, 10.0, 20.0, 40.0], "S & E tinggi": [10.0, 30.0, 20.0, 90.0, 85.0, 40.0]}
variants = {"asli": None, "centroid konstan 0": lambda u, t: 0.0, "centroid dibalik (100 - asli)": "invert", "centroid konstan 100": lambda u, t: 100.0}
orig = fuzzy_engine.hitung_mamdani_proposal
for pname, sk in profiles.items():
    user = dict(zip(DIM, sk))
    base_rank, base_cent = rank_sig(user, "asli")
    same, diff_cent = True, True
    for vname, fn in variants.items():
        if fn is None:
            continue
        repl = (lambda u, t, _o=orig: round(100 - _o(u, t), 2)) if fn == "invert" else fn
        with mock.patch.object(fuzzy_engine, "hitung_mamdani_proposal", repl):
            rk, ct = rank_sig(user, vname)
        same &= rk == base_rank
        diff_cent &= ct != base_cent
    rec.check(f"S18.{pname}", "Centroid tidak memengaruhi peringkat/skor", f"profil {pname}; centroid diganti konstan 0, konstan 100, dan dibalik",
              "peringkat dan skor identik pada keempat varian (centroid memang berubah)",
              f"peringkat_identik={same}; centroid_berubah={diff_cent}", ok=same and diff_cent)
# end-to-end lewat HTTP: jawaban sama, centroid dimanipulasi -> daftar tersimpan identik selain centroid
data = payload_sums((15, 27, 27, 24, 17, 31))
rid_a = last_id(post_answers(c, data))
with mock.patch.object(fuzzy_engine, "hitung_mamdani_proposal", lambda u, t: 0.0):
    rid_b = last_id(post_answers(c, data))
ra, rb = stored(rid_a)[2], stored(rid_b)[2]
strip = lambda L: [(x["nama"], x["skor_kecocokan"], x["kategori_kecocokan"]) for x in L]
rec.check("S19", "Centroid dimanipulasi lewat alur HTTP penuh", "jawaban sama dikirim dua kali; kedua kali centroid diganti 0.0 pada kiriman kedua",
          "daftar 5 program (nama, skor, pita) identik; centroid tersimpan berbeda",
          f"identik={strip(ra) == strip(rb)}; centroid_a={[x['mamdani_centroid'] for x in ra]}; centroid_b={[x['mamdani_centroid'] for x in rb]}",
          ok=strip(ra) == strip(rb) and [x['mamdani_centroid'] for x in ra] != [x['mamdani_centroid'] for x in rb])

print(rec.summary())
rec.print_failures()
if args.out:
    rec.save(args.out, args.label, APP_DIR, extra={"db_file": "berkas SQLite sementara (dibuat ulang tiap run)",
                                                    "urutan_skenario": [r["id"] for r in rec.rows]})
sys.exit(0 if rec.passed == len(rec.rows) else 1)
