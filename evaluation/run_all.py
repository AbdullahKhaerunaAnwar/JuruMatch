"""Menjalankan ketiga suite (numerik, self-matching, black-box) dan menulis log + manifest.

Contoh:
  python evaluation/run_all.py --label final                       # kode di ../backend
  python evaluation/run_all.py --label initial --app-dir /jalur/ke/revisi_lama/backend
"""
import json
import os
import subprocess
import sys

from common import DEFAULT_APP_DIR, HERE, environment, parse_args, source_manifest

args = parse_args("Jalankan seluruh evaluasi JuruMatch")
out = args.out or os.path.join(HERE, "logs", args.label)
os.makedirs(out, exist_ok=True)

suites = ["verify_numeric.py", "self_matching.py", "blackbox_tests.py"]
codes = {}
for s in suites:
    print(f"=== {s}")
    codes[s] = subprocess.run([sys.executable, s, "--app-dir", args.app_dir, "--out", out, "--label", args.label],
                              cwd=HERE).returncode

summary = {}
for stem in ("numeric", "self_matching", "blackbox"):
    with open(os.path.join(out, f"{args.label}_{stem}.json"), encoding="utf-8") as fh:
        summary[stem] = json.load(fh)["meta"]["summary"]
manifest = {"label": args.label, "environment": environment(), "app_dir": os.path.abspath(args.app_dir),
            "code_manifest": source_manifest(args.app_dir), "summary": summary, "exit_codes": codes,
            "catatan": "Catat juga `git rev-parse HEAD` pada saat menjalankan agar revisi kode yang diuji dapat dilacak."}
with open(os.path.join(out, f"{args.label}_manifest.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=1, ensure_ascii=False)
print("\nRINGKASAN", args.label, json.dumps(summary, ensure_ascii=False))
print("code_sha256 =", manifest["code_manifest"]["combined_sha256"])
sys.exit(0 if all(c == 0 for c in codes.values()) else 1)
