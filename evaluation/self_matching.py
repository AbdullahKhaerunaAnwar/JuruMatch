"""Uji self-matching: tiap profil target (x100) dipakai sebagai profil pengguna.

Invarian implementasi (BUKAN bukti validitas rekomendasi): dengan Persamaan (2),
skor program itu sendiri harus tepat 100,00 dan harus berperingkat pertama.
Keluaran juga mencatat program terdekat lain dan margin, serta memeriksa bahwa
tidak ada dua program yang bertarget identik.
"""
import csv
import json
import os
import sys

from common import Recorder, parse_args, setup_path

args = parse_args("Uji self-matching JuruMatch")
APP_DIR = setup_path(args.app_dir)
from logic.fuzzy_engine import rekomendasikan_jurusan  # noqa: E402

DIM = ["R", "I", "A", "S", "E", "C"]
with open(os.path.join(APP_DIR, "data", "majors.json"), encoding="utf-8") as fh:
    MAJORS = json.load(fh)

rec = Recorder("self_matching")
table = []
for m in MAJORS:
    user = {d: m["target"][d] * 100 for d in DIM}       # sama persis dengan ekspresi di mesin
    ranked = rekomendasikan_jurusan(user, MAJORS, top_n=len(MAJORS))
    own = next(r for r in ranked if r["id"] == m["id"])
    other = next(r for r in ranked if r["id"] != m["id"])
    margin = round(own["skor_kecocokan"] - other["skor_kecocokan"], 2)
    table.append({"program": m["nama"], "own_similarity": own["skor_kecocokan"],
                  "own_rank": ranked.index(own) + 1, "nearest_other": other["nama"],
                  "nearest_similarity": other["skor_kecocokan"], "margin": margin})
    rec.check(f"SM.{m['id']:02d}", "Self-matching", f"target {m['nama']} x100 sebagai profil pengguna",
              "skor sendiri = 100.00; peringkat 1", f"skor={own['skor_kecocokan']}; peringkat={ranked.index(own) + 1}; "
              f"terdekat lain={other['nama']} ({other['skor_kecocokan']}); margin={margin}",
              ok=own["skor_kecocokan"] == 100.0 and ranked.index(own) == 0 and margin > 0)
vecs = [tuple(m["target"][d] for d in DIM) for m in MAJORS]
rec.check("SM.unik", "Keunikan target", "20 vektor target", "tidak ada vektor identik",
          f"{len(set(vecs))} vektor unik dari {len(vecs)}", ok=len(set(vecs)) == len(vecs))
rec.check("SM.margin", "Margin minimum", "20 kasus", "margin minimum > 0",
          f"margin minimum = {min(t['margin'] for t in table)}", ok=min(t["margin"] for t in table) > 0)

print(rec.summary())
rec.print_failures()
if args.out:
    rec.save(args.out, args.label, APP_DIR, extra={"table": table})
    with open(os.path.join(args.out, f"{args.label}_self_matching_table.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys())); w.writeheader(); w.writerows(table)
sys.exit(0 if rec.passed == len(rec.rows) else 1)
