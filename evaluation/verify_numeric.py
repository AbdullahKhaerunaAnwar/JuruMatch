"""Verifikasi numerik terpadu JuruMatch.

Fungsi yang diuji (logic/scoring.py, membership.py, fuzzy_engine.py) dibandingkan
dengan implementasi referensi independen yang ditulis ulang di sini memakai
aritmetika pecahan eksak (fractions.Fraction), bukan memanggil kode yang diuji.

Cakupan: normalisasi, keanggotaan, overlap, pemilihan dimensi utama (termasuk
kasus seri), firing strength, agregasi, centroid, skor jarak, kode Holland
(termasuk seri), pita kemiripan, urutan seri, deteksi profil seragam, serta
perbandingan presisi penuh vs presisi tersimpan (dibulatkan 2 desimal).

Jalankan:  python evaluation/verify_numeric.py [--app-dir ../backend] [--out logs/final]
"""
import json
import os
import random
import sys
from fractions import Fraction as F

from common import Recorder, parse_args, setup_path

args = parse_args("Verifikasi numerik JuruMatch")
APP_DIR = setup_path(args.app_dir)

from logic import fuzzy_engine as fe  # noqa: E402
from logic import membership as mb  # noqa: E402
from logic import scoring as sc  # noqa: E402

DIM = ["R", "I", "A", "S", "E", "C"]
with open(os.path.join(APP_DIR, "data", "majors.json"), encoding="utf-8") as fh:
    MAJORS = json.load(fh)
TARGET = {m["nama"]: m["target"] for m in MAJORS}

rec = Recorder("numeric")


# ----------------------------------------------------------------- referensi eksak
def D(x):
    """Angka desimal apa adanya (59.38 -> 5938/100), tanpa galat biner float."""
    return F(str(x)) if not isinstance(x, F) else x


def r_low(x):
    x = D(x)
    return F(1) if x <= 25 else (F(0) if x >= 50 else (50 - x) / 25)


def r_med(x):
    x = D(x)
    if x <= 25 or x >= 75:
        return F(0)
    return (x - 25) / 25 if x <= 50 else (75 - x) / 25


def r_high(x):
    x = D(x)
    return F(0) if x <= 50 else (F(1) if x >= 75 else (x - 50) / 25)


R_SETS = (r_low, r_med, r_high)


def r_overlap(u, t):
    return sum(min(f(u), f(t)) for f in R_SETS)


def r_main(target):
    return [d for d, _ in sorted(((d, D(target[d])) for d in DIM), key=lambda kv: (-kv[1], DIM.index(kv[0])))[:2]]


def r_alphas(user, target):
    o = {d: r_overlap(user[d], D(target[d]) * 100) for d in DIM}
    main = r_main(target)
    return (1 - sum(o.values()) / 6, min(o[d] for d in main), min(o.values())), o


def r_agg(alphas):
    aL, aM, aH = alphas
    return [max(min(aL, r_low(z)), min(aM, r_med(z)), min(aH, r_high(z))) for z in range(101)]


def r_centroid(mu):
    den = sum(mu)
    return float(sum(z * m for z, m in enumerate(mu)) / den) if den else 0.0


def r_similarity(user, target):
    d = sum(abs(D(user[k]) - D(target[k]) * 100) for k in DIM) / 6
    return 100 - d  # Fraction, presisi penuh


def r_norm(s):
    return float(round(F((s - 8) * 100, 32), 2)) if 8 <= s <= 40 else (0.0 if s < 8 else 100.0)


# ----------------------------------------------------------------- A. normalisasi
for s in range(8, 41):
    rec.check(f"A1.{s}", "Normalisasi", f"S={s}", r_norm(s), sc.normalisasi(s))
for s, exp in ((7, 0.0), (41, 100.0)):
    rec.check(f"A2.{s}", "Normalisasi (batas/clip)", f"S={s}", exp, sc.normalisasi(s))
rec.check("A3", "Normalisasi (pembulatan separuh)", "S=17 (28.125 eksak)", 28.12, sc.normalisasi(17),
          note="round-half-even; 28.125 tepat representable")
rec.check("A4", "Normalisasi (pembulatan separuh)", "S=31 (71.875 eksak)", 71.88, sc.normalisasi(31))

# ----------------------------------------------------------------- B. keanggotaan
grid = [x / 2 for x in range(0, 201)] + [24.999, 25.001, 49.999, 50.001, 74.999, 75.001]
worst = 0.0
partition_ok = True
for x in grid:
    got = (mb.rendah(x), mb.sedang(x), mb.tinggi(x))
    exp = tuple(float(f(x)) for f in R_SETS)
    worst = max(worst, max(abs(a - b) for a, b in zip(got, exp)))
    partition_ok &= abs(sum(got) - 1.0) < 1e-12
rec.check("B1", "Keanggotaan (grid 0-100 + sekitar breakpoint)", f"{len(grid)} titik",
          "selisih maks <= 1e-12", f"selisih maks = {worst:.2e}", ok=worst <= 1e-12)
rec.check("B2", "Keanggotaan (partisi satuan)", f"{len(grid)} titik", "rendah+sedang+tinggi = 1 di semua titik",
          "terpenuhi" if partition_ok else "dilanggar", ok=partition_ok)
for x, exp in ((0, (1, 0, 0)), (25, (1, 0, 0)), (37.5, (.5, .5, 0)), (50, (0, 1, 0)),
               (62.5, (0, .5, .5)), (75, (0, 0, 1)), (100, (0, 0, 1))):
    rec.check(f"B3.{x}", "Keanggotaan (titik tabel naskah)", f"x={x}", exp,
              (mb.rendah(x), mb.sedang(x), mb.tinggi(x)))

# ----------------------------------------------------------------- C. overlap
def dep_overlap(u, t):
    return fe._kecocokan_dimensi(mb.fuzzify(u), mb.fuzzify(t))


for u, t, exp in ((37.5, 37.5, 1), (0, 100, 0), (37.5, 62.5, .5), (50, 50, 1), (25, 75, 0),
                  (0, 25, 1), (25, 50, 0), (50, 75, 0), (75, 100, 1), (10, 90, 0)):
    rec.close(f"C1.{u}-{t}", "Overlap per dimensi", f"U={u}, T={t}", exp, dep_overlap(u, t))
worst = 0.0
for u in grid[::3]:
    for t in (10, 20, 30, 40, 50, 60, 70, 80, 90):
        worst = max(worst, abs(dep_overlap(u, t) - float(r_overlap(u, t))))
rec.check("C2", "Overlap vs referensi eksak", "U pada grid x T in {10..90}",
          "selisih maks <= 1e-12", f"selisih maks = {worst:.2e}", ok=worst <= 1e-12)
_c3 = all(abs(dep_overlap(x, x) - 1.0) < 1e-12 for x in grid)
rec.check("C3", "Overlap identik", "U = T pada grid", "overlap = 1 di semua titik",
          "terpenuhi" if _c3 else "dilanggar", ok=_c3)

# ----------------------------------------------------------------- D. dimensi utama (seri)
def tgt(**kw):
    base = {d: 0.1 for d in DIM}
    base.update(kw)
    return base


cases = {
    "tanpa seri (Teknik Mesin)": TARGET["Teknik Mesin"],
    "seri di urutan ke-2 (Ilmu Hukum: I=S=0.5)": TARGET["Ilmu Hukum"],
    "seri di urutan ke-1": tgt(R=.5, I=.5),
    "semua sama": {d: .5 for d in DIM},
    "tiga seri teratas": tgt(A=.9, S=.9, E=.9),
    "seri R vs I di bawah C": tgt(C=.9, R=.5, I=.5),
    "urutan kunci dict diacak": {d: v for d, v in reversed(list(tgt(A=.9, S=.9, E=.9).items()))},
}
for name, t in cases.items():
    rec.check(f"D1.{name}", "Dimensi utama", t, r_main(t), fe._top_dimensi(t, 2))
exp_law = ["E", "I"]
rec.check("D2", "Dimensi utama (Ilmu Hukum)", "E=0.9; I=S=0.5", exp_law, fe._top_dimensi(TARGET["Ilmu Hukum"], 2),
          note="seri I vs S diputus oleh urutan R,I,A,S,E,C -> I")
ties = [n for n, t in TARGET.items() if sorted(t.values(), reverse=True)[1] == sorted(t.values(), reverse=True)[2]]
rec.check("D3", "Dimensi utama (20 program vs referensi)", "20 target",
          "identik", "identik" if all(fe._top_dimensi(t, 2) == r_main(t) for t in TARGET.values()) else "berbeda")
rec.check("D4", "Program dengan seri pada batas dimensi utama", "20 target", "(informasi)", ties, ok=True,
          note="program-program ini mengandalkan aturan seri R,I,A,S,E,C")

# ----------------------------------------------------------------- E. firing strength
def dep_alphas(u, t):
    _, _, aM, aH = fe._detail_kecocokan(u, t)
    aL, aM2, aH2 = fe._evaluasi_rules(u, t)
    assert (aM, aH) == (aM2, aH2)
    return aL, aM, aH


def check_alphas(tid, comp, u, t, expect=None, tol=1e-9):
    ref, _ = r_alphas(u, t)
    got = dep_alphas(u, t)
    ok = all(abs(float(a) - b) <= tol for a, b in zip(ref, got))
    if expect is not None:
        ok &= all(abs(round(g, 4) - e) <= 1e-9 for g, e in zip(got, expect))
    rec.check(tid, comp, f"U={u}; T={t}",
              tuple(round(float(a), 4) for a in ref) if expect is None else expect,
              tuple(round(g, 4) for g in got), ok=ok)


IS = TARGET["Sistem Informasi"]
EXACT = dict(zip(DIM, (21.875, 59.375, 59.375, 50.0, 28.125, 71.875)))   # presisi penuh
STORED = {d: round(v, 2) for d, v in EXACT.items()}                         # nilai tersimpan
rec.check("E0", "Contoh kerja: nilai tersimpan", "S=(15,27,27,24,17,31)",
          [21.88, 59.38, 59.38, 50.0, 28.12, 71.88], [sc.normalisasi(s) for s in (15, 27, 27, 24, 17, 31)])
check_alphas("E1", "Firing strength: U = T (semua overlap 1)", {d: IS[d] * 100 for d in DIM}, IS, expect=(0.0, 1.0, 1.0))
check_alphas("E2", "Firing strength: tidak beririsan sama sekali", {d: 0.0 for d in DIM}, {d: 1.0 for d in DIM}, expect=(1.0, 0.0, 0.0))
check_alphas("E3", "Firing strength: contoh kerja, presisi penuh", EXACT, IS, expect=(0.4708, 0.8750, 0.0))
check_alphas("E4", "Firing strength: contoh kerja, nilai tersimpan", STORED, IS, expect=(0.4708, 0.8752, 0.0))
for lvl in (25.0, 50.0, 75.0):
    check_alphas(f"E5.{lvl}", "Firing strength: U = T tepat di breakpoint", {d: lvl for d in DIM}, {d: lvl / 100 for d in DIM}, expect=(0.0, 1.0, 1.0))
# alphaModerate hanya melihat dua dimensi utama; alphaHigh melihat semua
t = TARGET["Teknik Mesin"]  # utama: R, I
u = {d: t[d] * 100 for d in DIM}; u["S"] = 100.0  # S bukan dimensi utama, target S=10 -> tidak beririsan
check_alphas("E6", "Firing strength: dimensi non-utama tak beririsan", u, t, expect=(round(1 - (5 + 0) / 6, 4), 1.0, 0.0))
# seri: Ilmu Hukum -> utama {E, I}; I vs S diputus ke I
t = TARGET["Ilmu Hukum"]; u = {d: t[d] * 100 for d in DIM}
u_i_bad = dict(u, I=100.0)   # I utama menjauh -> alphaModerate turun
u_s_bad = dict(u, S=100.0)   # S bukan utama (kalah seri) -> alphaModerate tetap 1
a_i = dep_alphas(u_i_bad, t)[1]; a_s = dep_alphas(u_s_bad, t)[1]
rec.check("E7", "Firing strength: aturan seri menentukan alphaModerate (Ilmu Hukum)",
          "I menjauh vs S menjauh", "alphaModerate(I menjauh) < 1 dan alphaModerate(S menjauh) = 1",
          f"{a_i:.4f} ; {a_s:.4f}", ok=a_i < 1.0 and abs(a_s - 1.0) < 1e-12)

# ----------------------------------------------------------------- F. agregasi
ALPHA_SETS = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (.4708, .875, 0), (.3, .3, .3), (0, 0, 0), (1, 1, 1),
              (.5, .2, .9), (.25, .75, .5), (0, .5, 1)]
for a in ALPHA_SETS:
    got = fe._agregasi_max(*a)
    exp = r_agg(tuple(D(x) for x in a))
    worst = max(abs(g - float(e)) for g, e in zip(got, exp))
    rec.check(f"F1.{a}", "Agregasi MIN/MAX (101 titik z)", f"alpha(Less,Moderate,High)={a}",
              "selisih maks <= 1e-12", f"{worst:.2e}", ok=worst <= 1e-12 and len(got) == 101)

# ----------------------------------------------------------------- G. centroid
for a in ALPHA_SETS:
    got = fe._defuzzifikasi_centroid(fe._agregasi_max(*a))
    exp = r_centroid(r_agg(tuple(D(x) for x in a)))
    rec.close(f"G1.{a}", "Centroid vs referensi eksak", f"alpha={a}", exp, got, tol=1e-9)
for a, exp in (((0, 0, 1), 80.82), ((1, 0, 0), 19.18), ((0, 1, 0), 50.0), ((1, 0, 1), 50.0)):
    rec.close(f"G2.{a}", "Centroid (nilai tabel naskah)", f"alpha={a}", exp, round(fe._defuzzifikasi_centroid(fe._agregasi_max(*a)), 2), tol=1e-9)
rec.check("G3", "Centroid: penyebut nol", "mu = 0 di semua z", 0.0, fe._defuzzifikasi_centroid([0.0] * 101))
for name, uu, exp4 in (("presisi penuh", EXACT, 37.0078), ("nilai tersimpan", STORED, 37.0089)):
    c = fe._defuzzifikasi_centroid(fe._agregasi_max(*fe._evaluasi_rules(uu, IS)))
    rec.check(f"G4.{name}", "Centroid contoh kerja (4 desimal)", f"U={name}; T=Sistem Informasi",
              exp4, round(c, 4), ok=abs(round(c, 4) - exp4) <= 1e-9)
    rec.check(f"G5.{name}", "Centroid contoh kerja setelah pembulatan tampilan", f"U={name}", 37.01,
              fe.hitung_mamdani_proposal(uu, IS))

# ----------------------------------------------------------------- H. skor jarak, kode Holland, pita, urutan
sim_full = r_similarity(EXACT, IS)
rec.check("H1", "Skor jarak contoh kerja, presisi penuh (4 desimal)", "U=EXACT; T=Sistem Informasi", 81.9792,
          round(float(sim_full), 4), ok=abs(round(float(sim_full), 4) - 81.9792) < 1e-9)
rec.check("H2", "Skor jarak contoh kerja, nilai tersimpan", "U=STORED", 81.98, fe._skor_kecocokan_profil(STORED, IS))
rec.check("H3", "Skor jarak U = T", "U=T", 100.0, fe._skor_kecocokan_profil({d: IS[d] * 100 for d in DIM}, IS))
rec.check("H4", "Skor jarak U=0 vs T=0.5", "", 50.0, fe._skor_kecocokan_profil({d: 0.0 for d in DIM}, {d: .5 for d in DIM}))
rec.check("H5", "Skor jarak U=100 vs T=0.1", "", 10.0, fe._skor_kecocokan_profil({d: 100.0 for d in DIM}, {d: .1 for d in DIM}))
rec.check("H6", "Skor jarak: clip batas bawah", "U=250 vs T=0", 0.0, fe._skor_kecocokan_profil({d: 250.0 for d in DIM}, {d: 0.0 for d in DIM}))
for name, sk, exp in (
    ("semua sama", {d: 50.0 for d in DIM}, "RIA"),
    ("seri di posisi 2-4", {"R": 50, "I": 80, "A": 80, "S": 80, "E": 10, "C": 10}, "IAS"),
    ("seri di batas posisi ke-3", {"R": 90, "I": 50, "A": 50, "S": 50, "E": 10, "C": 10}, "RIA"),
    ("seri C vs E", {"R": 0, "I": 0, "A": 0, "S": 0, "E": 70, "C": 70}, "ECR"),
    ("contoh kerja (I=A=59.38)", STORED, "CIA"),
    ("kunci dict diacak, semua sama", {d: 40.0 for d in reversed(DIM)}, "RIA"),
):
    rec.check(f"H7.{name}", "Kode Holland (seri)", sk, exp, sc.kode_holland_dominan(sk))
for x, exp in ((100, "Kemiripan Sangat Tinggi"), (85, "Kemiripan Sangat Tinggi"), (84.99, "Kemiripan Tinggi"),
               (70, "Kemiripan Tinggi"), (69.99, "Kemiripan Sedang"), (55, "Kemiripan Sedang"),
               (54.99, "Kemiripan Rendah"), (40, "Kemiripan Rendah"), (39.99, "Kemiripan Sangat Rendah"), (0, "Kemiripan Sangat Rendah")):
    rec.attempt(f"H8.{x}", "Pita kemiripan (batas)", f"skor={x}", exp, lambda x=x: fe.kategori_kecocokan(x))
twin = [{"id": 1, "nama": "Zeta", "rumpun": "x", "target": tgt(R=.6)},
        {"id": 2, "nama": "Alfa", "rumpun": "x", "target": tgt(R=.6)},
        {"id": 3, "nama": "Mega", "rumpun": "x", "target": tgt(R=.6)}]
rec.check("H9", "Urutan seri skor (abjad nama)", "3 program bertarget identik", ["Alfa", "Mega", "Zeta"],
          [r["nama"] for r in fe.rekomendasikan_jurusan({d: 60.0 for d in DIM}, twin, top_n=3)])
rec.check("H10", "top_n memotong daftar", "20 program, top_n=5", 5,
          len(fe.rekomendasikan_jurusan(STORED, MAJORS, top_n=5)))
for name, sk, exp in (("semua sama (0)", {d: 0.0 for d in DIM}, True), ("semua sama (28.12)", {d: 28.12 for d in DIM}, True),
                      ("beda 0.01", dict({d: 50.0 for d in DIM}, C=50.01), False), ("contoh kerja", STORED, False)):
    rec.attempt(f"H11.{name}", "Deteksi profil seragam", sk, exp, lambda sk=sk: sc.profil_seragam(sk))

# ----------------------------------------------------------------- I. terpadu: 20 program x banyak profil
rng = random.Random(20260427)
profiles = {"semua 0": {d: 0.0 for d in DIM}, "semua 25": {d: 25.0 for d in DIM}, "semua 50": {d: 50.0 for d in DIM},
            "semua 75": {d: 75.0 for d in DIM}, "semua 100": {d: 100.0 for d in DIM}, "contoh kerja": STORED}
for i in range(34):
    profiles[f"acak-{i}"] = {d: round(sc.normalisasi(rng.randint(8, 40)), 2) for d in DIM}
sim_bad = cen_bad = alpha_bad = ov_bad = 0
cen_worst = 0.0
n = 0
for pname, U in profiles.items():
    for mname, T in TARGET.items():
        n += 1
        det = fe.hitung_detail_kecocokan(U, T)
        ref_sim = float(round(r_similarity(U, T), 2)) if 0 <= r_similarity(U, T) <= 100 else None
        if abs(det["persentase_kecocokan"] - ref_sim) > 0.0101:
            sim_bad += 1
        ref_a, ref_o = r_alphas(U, T)
        if abs(det["alpha_cukup"] - float(ref_a[1]) * 100) > 0.0101 or abs(det["alpha_sangat"] - float(ref_a[2]) * 100) > 0.0101:
            alpha_bad += 1
        if any(abs(det["per_dimensi"][d] - float(ref_o[d]) * 100) > 0.0101 for d in DIM):
            ov_bad += 1
        rc = r_centroid(r_agg(ref_a))
        cen_worst = max(cen_worst, abs(det["mamdani_centroid"] - rc))
        if abs(det["mamdani_centroid"] - rc) > 0.0101:
            cen_bad += 1
rec.check("I1", "Terpadu: skor kemiripan", f"{n} pasangan profil x program", 0, sim_bad, note="toleransi 0,0101 (pembulatan 2 desimal)")
rec.check("I2", "Terpadu: overlap per dimensi", f"{n} pasangan", 0, ov_bad)
rec.check("I3", "Terpadu: alphaModerate dan alphaHigh", f"{n} pasangan", 0, alpha_bad)
rec.check("I4", "Terpadu: centroid", f"{n} pasangan", 0, cen_bad, note=f"selisih maks {cen_worst:.4f}")

print(rec.summary())
rec.print_failures()
if args.out:
    rec.save(args.out, args.label, APP_DIR)
sys.exit(0 if rec.passed == len(rec.rows) else 1)
