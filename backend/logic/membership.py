"""
Fungsi keanggotaan (membership function) fuzzy untuk tiga himpunan
linguistik: Rendah, Sedang, Tinggi.

Rumus mengikuti PERSIS formulasi pada Bab III proposal (subbab
"Teknik Analisis Data" - Fuzzifikasi Variabel Input, Profil RIASEC):

    mu_Rendah(x) = 1                    , x <= 0.25
                 = (0.5 - x) / 0.25      , 0.25 < x < 0.5
                 = 0                    , x >= 0.5

    mu_Sedang(x) = 0                    , x <= 0.25 atau x >= 0.75
                 = (x - 0.25) / 0.25     , 0.25 < x <= 0.5
                 = (0.75 - x) / 0.25     , 0.5 < x < 0.75

    mu_Tinggi(x) = 0                    , x <= 0.5
                 = (x - 0.5) / 0.25      , 0.5 < x < 0.75
                 = 1                    , x >= 0.75

Pada proposal, domain variabel input (Profil RIASEC) adalah 0.0 - 1.0.
Di implementasi ini skor RIASEC user & target jurusan dipakai pada skala
0-100 (lihat logic/scoring.py) semata-mata agar enak ditampilkan sebagai
persen di UI (bar chart dsb) -- SECARA MATEMATIS ekuivalen, karena 0-100
hanyalah 0.0-1.0 dikali 100, sehingga titik potong (breakpoint) yang
dipakai di sini pun ikut dikali 100: 0.25 -> 25, 0.5 -> 50, 0.75 -> 75.

Fungsi keanggotaan output (tingkat kecocokan jurusan, semesta 0-100
sesuai penjelasan Bab III bagian Defuzzifikasi: "rentang skala kelayakan
0 hingga 100") memakai BENTUK KURVA YANG SAMA, hanya diberi nama
tingkat keluaran Kurang / Cukup / Sangat (alias di logic/fuzzy_engine.py).
Nama itu penanda tingkat keluaran perhitungan fuzzy tambahan, bukan kategori
kesesuaian jurusan yang tervalidasi.
"""

BATAS_BAWAH = 25   # 0.25 * 100
BATAS_TENGAH = 50  # 0.5  * 100
BATAS_ATAS = 75    # 0.75 * 100
LEBAR = 25         # 0.25 * 100


def rendah(x: float) -> float:
    """mu_Rendah(x) -- bahu kiri, sesuai formula Bab III (image4)."""
    if x <= BATAS_BAWAH:
        return 1.0
    if x >= BATAS_TENGAH:
        return 0.0
    return (BATAS_TENGAH - x) / LEBAR


def sedang(x: float) -> float:
    """mu_Sedang(x) -- segitiga, sesuai formula Bab III (image5)."""
    if x <= BATAS_BAWAH or x >= BATAS_ATAS:
        return 0.0
    if x <= BATAS_TENGAH:
        return (x - BATAS_BAWAH) / LEBAR
    return (BATAS_ATAS - x) / LEBAR


def tinggi(x: float) -> float:
    """mu_Tinggi(x) -- bahu kanan, sesuai formula Bab III (image6)."""
    if x <= BATAS_TENGAH:
        return 0.0
    if x >= BATAS_ATAS:
        return 1.0
    return (x - BATAS_TENGAH) / LEBAR


def fuzzify(x: float) -> dict:
    """Kembalikan derajat keanggotaan x pada ketiga himpunan sekaligus."""
    return {
        "rendah": rendah(x),
        "sedang": sedang(x),
        "tinggi": tinggi(x),
    }


def kategori_dominan(mu: dict) -> str:
    """Kategori (rendah/sedang/tinggi) dengan derajat keanggotaan
    tertinggi -- dipakai untuk menentukan label linguistik yang paling
    mewakili sebuah nilai crisp (mis. level RIASEC yang dibutuhkan
    suatu jurusan)."""
    return max(mu, key=mu.get)
