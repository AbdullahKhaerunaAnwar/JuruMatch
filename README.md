# JuruMatch — Render Ready

Prototipe eksploratif: tes minat RIASEC (48 butir) dengan peringkat jarak profil terhadap 20 profil target program studi. Perhitungan fuzzy Mamdani dihitung terpisah sebagai perhitungan tambahan dan tidak memengaruhi peringkat. Instrumen berbahasa Indonesia dan matriks target belum divalidasi.

Aplikasi JuruMatch adalah Flask app yang menyajikan frontend dan backend dalam satu service.

## Deploy ke Render Free

Repository ini sudah dilengkapi `render.yaml`.

1. Push folder project ini ke GitHub.
2. Di Render pilih **New → Blueprint** lalu pilih repository tersebut.
3. Render akan membaca `render.yaml` dan membuat:
   - Web Service `jurumatch` (Free)
   - PostgreSQL `jurumatch-db` (Free)
4. Saat diminta, isi environment variable:
   - `ADMIN_EMAIL` — email untuk login admin.
   - `ADMIN_PASSWORD` — password admin.
5. Deploy.

Konfigurasi service mengikuti pola deployment Flask resmi Render: build `pip install -r requirements.txt` dan start dengan Gunicorn. Render juga menyediakan environment variables untuk secret/runtime configuration. citeturn0search0turn0search5

### Catatan database Free

JuruMatch otomatis memakai PostgreSQL jika `DATABASE_URL` tersedia. Tanpa `DATABASE_URL`, aplikasi tetap bisa dijalankan lokal menggunakan SQLite.

Render Free cocok untuk demo/hobi/testing, bukan production. Free PostgreSQL Render saat ini memiliki batas 1 GB dan masa aktif 30 hari. citeturn0search3

## Jalankan lokal

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Tanpa `DATABASE_URL`, database lokal akan dibuat sebagai `backend/sirekomjur.db`.

## Login admin lokal

Jika `ADMIN_EMAIL` dan `ADMIN_PASSWORD` tidak diset, default development adalah:

- Email: `[configure for local development]`
- Password: `[configure for local development]`

Untuk deployment publik, **wajib** mengatur keduanya di Render Environment Variables.

## Struktur

```text
jurumatch/
├── frontend/
│   ├── templates/
│   └── static/
├── backend/
│   ├── app.py
│   ├── database.py
│   ├── run.py
│   ├── wsgi.py
│   ├── requirements.txt
│   ├── data/
│   └── logic/
├── render.yaml
└── README.md
```

## Public Repository Safety

The SQLite database containing runtime/user data is intentionally excluded from this repository.
For local development, configure administrator credentials through the application's supported
configuration rather than committing real credentials or user data.

## Verifikasi dan uji (evaluation/)

Skrip verifikasi numerik, self-matching, dan uji black-box ada di folder `evaluation/`
beserta log keluaran awal dan akhir di `evaluation/logs/`. Petunjuk lengkap:
[evaluation/README.md](evaluation/README.md). Ringkas:

```bash
cd backend && pip install -r requirements.txt && cd ..
python evaluation/run_all.py --label final
```

Daftar perubahan terhadap revisi sebelumnya: [CHANGES.md](CHANGES.md).
