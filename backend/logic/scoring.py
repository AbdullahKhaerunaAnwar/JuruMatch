"""
Konversi jawaban kuesioner RIASEC (skala Likert 1-5, 8 butir per dimensi,
diadaptasi dari RIASEC Markers Activities - Set A, Armstrong, Allison &
Rounds, 2008) menjadi skor 0-100 per dimensi.

Rentang skor mentah per dimensi: 8 (semua dijawab 1) - 40 (semua dijawab 5).
Dinormalisasi linear ke 0-100 agar sesuai domain fungsi keanggotaan fuzzy.
"""

DIMENSI = ["R", "I", "A", "S", "E", "C"]
MIN_MENTAH = 8    # 8 butir x skor minimal 1
MAKS_MENTAH = 40  # 8 butir x skor maksimal 5


def normalisasi(skor_mentah: int) -> float:
    nilai = (skor_mentah - MIN_MENTAH) / (MAKS_MENTAH - MIN_MENTAH) * 100
    return round(max(0.0, min(100.0, nilai)), 2)


def hitung_skor_riasec(jawaban: dict, daftar_pertanyaan: list) -> dict:
    """
    jawaban: dict {id_pertanyaan (str/int): nilai_likert (1-5)}
    daftar_pertanyaan: list pertanyaan dari data/questions.json,
                        tiap item punya "id" dan "dimensi"

    Mengembalikan dict {"R": skor_0_100, "I": .., ...}
    """
    mentah = {d: 0 for d in DIMENSI}

    for pertanyaan in daftar_pertanyaan:
        pid = pertanyaan["id"]
        dimensi = pertanyaan["dimensi"]
        nilai = int(jawaban.get(str(pid), jawaban.get(pid, 0)))
        mentah[dimensi] += nilai

    return {d: normalisasi(mentah[d]) for d in DIMENSI}


def kode_holland_dominan(skor_riasec: dict, n: int = 3) -> str:
    """Kembalikan n huruf kode Holland dominan, misal 'IRA', diurutkan skor desc.

    Skor yang sama diurutkan menurut urutan tetap R, I, A, S, E, C (eksplisit,
    tidak bergantung pada urutan kunci dict). Akibatnya, bila semua skor sama
    kodenya selalu 'RIA'; kode itu BUKAN tanda minat dominan.
    """
    urut = sorted(skor_riasec.items(), key=lambda kv: (-kv[1], DIMENSI.index(kv[0])))
    return "".join(k for k, _ in urut[:n])


def profil_seragam(skor_riasec: dict) -> bool:
    """True bila keenam skor RIASEC (nilai tersimpan, 2 desimal) identik.

    Profil seperti ini tidak memuat pola minat; kode Holland dan skor
    kemiripan hanya mencerminkan tingkat jawaban secara keseluruhan.
    """
    return len({skor_riasec[d] for d in DIMENSI}) == 1
