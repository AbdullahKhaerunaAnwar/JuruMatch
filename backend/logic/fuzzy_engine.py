"""Mesin rekomendasi RIASEC (jarak profil) + perhitungan fuzzy Mamdani tambahan.

Urutan dan skor yang ditampilkan HANYA berasal dari kemiripan profil (jarak
rata-rata absolut) pada skala 0-100. Alur fuzzy Mamdani (fuzzifikasi -> MIN ->
MAX -> centroid) dihitung secara terpisah sebagai perhitungan fuzzy tambahan
(auxiliary fuzzy calculation); centroidnya disimpan dan ditampilkan di halaman
detail admin, tetapi tidak pernah dipakai untuk mengurutkan atau menilai.

Alasan skor tampilan tidak memakai centroid: desain output fuzzy hanya memiliki
3 himpunan (tingkat keluaran Rendah/Sedang/Tinggi, di kode bernama
KURANG_COCOK/CUKUP_COCOK/SANGAT_COCOK) dan aturan "Kurang" merupakan komplemen,
sehingga centroid mentah dapat berhenti di kisaran 20-60 walaupun program teratas
relatif dekat dengan profil pengguna. Nama-nama itu hanya penanda tingkat
keluaran perhitungan tambahan, bukan kategori kesesuaian yang tervalidasi.
"""

from .membership import fuzzify, rendah, sedang, tinggi

DIMENSI = ["R", "I", "A", "S", "E", "C"]
KATEGORI = ("rendah", "sedang", "tinggi")
KURANG_COCOK = rendah
CUKUP_COCOK = sedang
SANGAT_COCOK = tinggi
Z_SAMPLES = list(range(0, 101))


def _top_dimensi(target: dict, n: int = 2) -> list:
    urut = sorted(target.items(), key=lambda kv: (-kv[1], DIMENSI.index(kv[0])))
    return [d for d, _ in urut[:n]]


def _kecocokan_dimensi(mu_user_d: dict, mu_target_d: dict) -> float:
    return sum(min(mu_user_d[c], mu_target_d[c]) for c in KATEGORI)


def _detail_kecocokan(skor_user: dict, target: dict) -> tuple[dict, float, float, float]:
    mu_user = {d: fuzzify(skor_user[d]) for d in DIMENSI}
    mu_target = {d: fuzzify(target[d] * 100) for d in DIMENSI}
    kecocokan = {d: _kecocokan_dimensi(mu_user[d], mu_target[d]) for d in DIMENSI}
    dim_utama = _top_dimensi(target, 2)
    rata_rata = sum(kecocokan.values()) / len(DIMENSI)
    alpha_cukup = min(kecocokan[d] for d in dim_utama)
    alpha_sangat = min(kecocokan[d] for d in DIMENSI)
    return kecocokan, rata_rata, alpha_cukup, alpha_sangat


def _evaluasi_rules(skor_user: dict, target: dict) -> tuple:
    kecocokan, _, alpha_cukup, alpha_sangat = _detail_kecocokan(skor_user, target)
    alpha_kurang = 1 - (sum(kecocokan.values()) / len(DIMENSI))
    return alpha_kurang, alpha_cukup, alpha_sangat


def _agregasi_max(alpha_kurang: float, alpha_cukup: float, alpha_sangat: float) -> list:
    return [
        max(
            min(alpha_kurang, KURANG_COCOK(z)),
            min(alpha_cukup, CUKUP_COCOK(z)),
            min(alpha_sangat, SANGAT_COCOK(z)),
        )
        for z in Z_SAMPLES
    ]


def _defuzzifikasi_centroid(mu_gabungan: list) -> float:
    penyebut = sum(mu_gabungan)
    if penyebut == 0:
        return 0.0
    return sum(z * m for z, m in zip(Z_SAMPLES, mu_gabungan)) / penyebut


def hitung_mamdani_proposal(skor_user: dict, target_jurusan: dict) -> float:
    """Centroid mentah sesuai formulasi Mamdani yang tertulis di proposal."""
    alpha_kurang, alpha_cukup, alpha_sangat = _evaluasi_rules(skor_user, target_jurusan)
    return round(_defuzzifikasi_centroid(_agregasi_max(alpha_kurang, alpha_cukup, alpha_sangat)), 2)


def kategori_kecocokan(persen: float) -> str:
    """Pita kemiripan heuristik 5 tingkat untuk tampilan pengguna.

    Ini BUKAN himpunan fuzzy, bukan probabilitas, dan bukan kategori kesesuaian
    yang tervalidasi; hanya pita tampilan atas skor kemiripan profil 0-100.
    """
    if persen >= 85:
        return "Kemiripan Sangat Tinggi"
    if persen >= 70:
        return "Kemiripan Tinggi"
    if persen >= 55:
        return "Kemiripan Sedang"
    if persen >= 40:
        return "Kemiripan Rendah"
    return "Kemiripan Sangat Rendah"


def _skor_kecocokan_profil(skor_user: dict, target_jurusan: dict) -> float:
    """Kemiripan profil 0-100 berdasarkan jarak skor RIASEC terhadap target.

    Target jurusan berada pada 0..1, sedangkan skor pengguna 0..100.
    Skor = 100 - rata-rata selisih absolut keenam dimensi.
    """
    jarak = sum(abs(skor_user[d] - target_jurusan[d] * 100) for d in DIMENSI) / len(DIMENSI)
    return round(max(0.0, min(100.0, 100.0 - jarak)), 2)


def hitung_detail_kecocokan(skor_user: dict, target_jurusan: dict) -> dict:
    kecocokan, rata_rata_overlap, alpha_cukup, alpha_sangat = _detail_kecocokan(
        skor_user, target_jurusan
    )
    persen = _skor_kecocokan_profil(skor_user, target_jurusan)
    return {
        "per_dimensi": {d: round(v * 100, 2) for d, v in kecocokan.items()},
        "rata_rata_overlap": round(rata_rata_overlap * 100, 2),
        "persentase_kecocokan": persen,
        "kategori": kategori_kecocokan(persen),
        "alpha_cukup": round(alpha_cukup * 100, 2),
        "alpha_sangat": round(alpha_sangat * 100, 2),
        "mamdani_centroid": hitung_mamdani_proposal(skor_user, target_jurusan),
    }


def hitung_kecocokan_jurusan(skor_user: dict, target_jurusan: dict) -> float:
    return hitung_detail_kecocokan(skor_user, target_jurusan)["persentase_kecocokan"]


def rekomendasikan_jurusan(skor_user: dict, daftar_jurusan: list, top_n: int = 5) -> list:
    hasil = []
    for jurusan in daftar_jurusan:
        detail = hitung_detail_kecocokan(skor_user, jurusan["target"])
        hasil.append({
            "id": jurusan["id"],
            "nama": jurusan["nama"],
            "rumpun": jurusan["rumpun"],
            "skor_kecocokan": detail["persentase_kecocokan"],
            "kategori_kecocokan": detail["kategori"],
            "mamdani_centroid": detail["mamdani_centroid"],
            "detail_kecocokan": detail["per_dimensi"],
        })

    hasil.sort(key=lambda x: (-x["skor_kecocokan"], x["nama"]))
    return hasil[:top_n]
