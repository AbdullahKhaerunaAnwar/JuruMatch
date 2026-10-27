"""Utilitas bersama untuk skrip evaluasi JuruMatch.

Setiap skrip dapat dijalankan terhadap folder kode mana pun lewat --app-dir
(misalnya revisi lama untuk log "initial", atau revisi final untuk log "final").
"""
import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from importlib.metadata import version

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_APP_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))


def parse_args(description):
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--app-dir", default=DEFAULT_APP_DIR,
                    help="folder backend yang berisi app.py (default: ../backend)")
    ap.add_argument("--out", default=None, help="folder keluaran log (default: tidak menulis log)")
    ap.add_argument("--label", default="final", help="label log, mis. initial atau final")
    return ap.parse_args()


def setup_path(app_dir):
    app_dir = os.path.abspath(app_dir)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    return app_dir


def environment():
    def v(pkg):
        try:
            return version(pkg)
        except Exception:
            return "tidak terpasang"
    return {
        "python": platform.python_version(),
        "flask": v("flask"),
        "werkzeug": v("werkzeug"),
        "platform": platform.platform(),
    }


def source_manifest(app_dir):
    """SHA-256 tiap berkas kode yang diuji + hash gabungan (identitas revisi yang diuji)."""
    root = os.path.dirname(os.path.abspath(app_dir))
    entries = {}
    for sub in ("backend", "frontend"):
        base = os.path.join(root, sub)
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                if f.endswith((".pyc", ".db", ".sqlite", ".sqlite3", ".log")):
                    continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                with open(p, "rb") as fh:
                    entries[rel] = hashlib.sha256(fh.read()).hexdigest()
    combined = hashlib.sha256(
        "\n".join(f"{k}:{entries[k]}" for k in sorted(entries)).encode()
    ).hexdigest()
    return {"combined_sha256": combined, "files": dict(sorted(entries.items()))}


class Recorder:
    """Mengumpulkan hasil uji (input, expected, observed, status) dan menulis log."""

    def __init__(self, suite):
        self.suite = suite
        self.rows = []

    def check(self, tid, component, inputs, expected, observed, ok=None, note=""):
        if ok is None:
            ok = expected == observed
        self.rows.append({
            "id": tid, "component": component, "input": str(inputs),
            "expected": str(expected), "observed": str(observed),
            "status": "PASS" if ok else "FAIL", "note": note,
        })
        return ok

    def close(self, tid, component, inputs, expected, observed, tol=1e-9, note=""):
        ok = abs(float(expected) - float(observed)) <= tol
        return self.check(tid, component, inputs, expected, observed, ok=ok, note=note)

    def attempt(self, tid, component, inputs, expected, fn, note=""):
        """Jalankan fn(); kegagalan/eksepsi dicatat sebagai FAIL, bukan menghentikan suite."""
        try:
            observed = fn()
            return self.check(tid, component, inputs, expected, observed, note=note)
        except Exception as exc:  # noqa: BLE001 - dicatat apa adanya di log
            return self.check(tid, component, inputs, expected, f"ERROR: {exc!r}", ok=False, note=note)

    @property
    def passed(self):
        return sum(r["status"] == "PASS" for r in self.rows)

    def summary(self):
        return f"{self.suite}: {self.passed}/{len(self.rows)} PASS"

    def save(self, out_dir, label, app_dir, extra=None):
        os.makedirs(out_dir, exist_ok=True)
        stem = os.path.join(out_dir, f"{label}_{self.suite}")
        with open(stem + ".csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(self.rows[0].keys()))
            w.writeheader()
            w.writerows(self.rows)
        meta = {"suite": self.suite, "label": label, "environment": environment(),
                "code_manifest_sha256": source_manifest(app_dir)["combined_sha256"],
                "summary": self.summary()}
        if extra:
            meta.update(extra)
        with open(stem + ".json", "w", encoding="utf-8") as fh:
            json.dump({"meta": meta, "results": self.rows}, fh, ensure_ascii=False, indent=1)
        with open(stem + ".txt", "w", encoding="utf-8") as fh:
            fh.write(f"# {self.suite} | label={label}\n")
            fh.write(f"# env={json.dumps(meta['environment'])}\n")
            fh.write(f"# code_sha256={meta['code_manifest_sha256']}\n")
            for r in self.rows:
                fh.write(f"[{r['status']}] {r['id']} {r['component']} | input={r['input']} | "
                         f"expected={r['expected']} | observed={r['observed']}"
                         f"{' | ' + r['note'] if r['note'] else ''}\n")
            fh.write(f"# {self.summary()}\n")

    def print_failures(self, limit=40):
        bad = [r for r in self.rows if r["status"] != "PASS"]
        for r in bad[:limit]:
            print(f"  FAIL {r['id']} {r['component']}: expected={r['expected']} observed={r['observed']}")
        if len(bad) > limit:
            print(f"  ... {len(bad) - limit} kegagalan lain (lihat log)")
