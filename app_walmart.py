"""
Walmart CoE Analysis Tool — Flask backend
Single upload → 4 outputs: Mastery, Framework, Health, Strategy
Route: /walmart  |  Port: set by Render via $PORT
"""
from __future__ import annotations

import gc
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, Response
from werkzeug.utils import secure_filename

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.resolve()
UPLOAD_DIR  = BASE_DIR / "uploads"
OUTPUT_DIR  = BASE_DIR / "outputs"

TEMPLATE_MASTERY   = BASE_DIR / "CoE_Walmart_Account_Mastery_Analysis_Templates.xlsm"
TEMPLATE_FRAMEWORK = BASE_DIR / "CoE_Walmart_Framework_Analysis_Templates.xlsm"
TEMPLATE_HEALTH    = BASE_DIR / "CoE_Walmart_Account_Health_Analysis_Templates.xlsm"
TEMPLATE_STRATEGY  = BASE_DIR / "CoE_Walmart_Account_Strategy_Analysis_Templates.xlsm"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

MIN_OUTPUT_BYTES = 5_000

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


def _safe_fn(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r'[^a-zA-Z0-9 \-_]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name or "UNKNOWN_ACCOUNT"


# ── Pillar runners — sequential, each fully isolated ─────────────────────────

def _run_mastery(input_path: str, safe_hash: str, ts: str) -> dict:
    from reader_databricks_walmart import load_walmart_context
    from rules_engine_walmart_mastery import evaluate_all, compute_score, interpretation
    from writer_walmart import write_mastery_output

    if not TEMPLATE_MASTERY.exists():
        raise FileNotFoundError(f"Mastery template not found: {TEMPLATE_MASTERY}")

    ctx     = load_walmart_context(input_path)
    results = evaluate_all(ctx)
    penalty, score, grade, findings = compute_score(results)

    fname = f"{safe_hash} - WM Mastery Analysis - {ts}.xlsm"
    fpath = OUTPUT_DIR / fname
    write_mastery_output(str(TEMPLATE_MASTERY), str(fpath), results, ctx)

    size = fpath.stat().st_size if fpath.exists() else 0
    if not fpath.exists() or size < MIN_OUTPUT_BYTES:
        raise RuntimeError(f"Mastery output missing or too small ({size} bytes).")

    ret = {
        'download_filename': fname,
        'grade':  grade,
        'score':  round(score, 1),
        'ok':     sum(1 for r in results.values() if r.status == 'OK'),
        'flag':   sum(1 for r in results.values() if r.status == 'FLAG'),
        'partial':sum(1 for r in results.values() if r.status == 'PARTIAL'),
    }
    del ctx, results
    gc.collect()
    return ret


def _run_framework(input_path: str, safe_hash: str, ts: str) -> dict:
    from reader_databricks_walmart import load_walmart_context
    from rules_engine_walmart_framework import evaluate_all, compute_score, interpretation
    from writer_walmart import write_framework_output

    if not TEMPLATE_FRAMEWORK.exists():
        raise FileNotFoundError(f"Framework template not found: {TEMPLATE_FRAMEWORK}")

    ctx     = load_walmart_context(input_path)
    results = evaluate_all(ctx)
    penalty, score, grade, findings = compute_score(results)

    fname = f"{safe_hash} - WM Framework Analysis - {ts}.xlsm"
    fpath = OUTPUT_DIR / fname
    write_framework_output(str(TEMPLATE_FRAMEWORK), str(fpath), results, ctx)

    size = fpath.stat().st_size if fpath.exists() else 0
    if not fpath.exists() or size < MIN_OUTPUT_BYTES:
        raise RuntimeError(f"Framework output missing or too small ({size} bytes).")

    ret = {
        'download_filename': fname,
        'grade':  grade,
        'score':  round(score, 1),
        'ok':     sum(1 for r in results.values() if r.status == 'OK'),
        'flag':   sum(1 for r in results.values() if r.status == 'FLAG'),
        'partial':sum(1 for r in results.values() if r.status == 'PARTIAL'),
    }
    del ctx, results
    gc.collect()
    return ret


def _run_health(input_path: str, safe_hash: str, ts: str) -> dict:
    from reader_databricks_walmart import load_walmart_context
    from rules_engine_walmart_health import evaluate_all, compute_score, interpretation
    from writer_walmart import write_health_output

    if not TEMPLATE_HEALTH.exists():
        raise FileNotFoundError(f"Health template not found: {TEMPLATE_HEALTH}")

    ctx     = load_walmart_context(input_path)
    results = evaluate_all(ctx)
    penalty, score, grade, findings = compute_score(results)

    fname = f"{safe_hash} - WM Health Analysis - {ts}.xlsm"
    fpath = OUTPUT_DIR / fname
    write_health_output(str(TEMPLATE_HEALTH), str(fpath), results, ctx)

    size = fpath.stat().st_size if fpath.exists() else 0
    if not fpath.exists() or size < MIN_OUTPUT_BYTES:
        raise RuntimeError(f"Health output missing or too small ({size} bytes).")

    ret = {
        'download_filename': fname,
        'grade':  grade,
        'score':  round(score, 1),
        'ok':     sum(1 for r in results.values() if r.status == 'OK'),
        'flag':   sum(1 for r in results.values() if r.status == 'FLAG'),
        'partial':sum(1 for r in results.values() if r.status == 'PARTIAL'),
    }
    del ctx, results
    gc.collect()
    return ret


def _run_strategy(input_path: str, safe_hash: str, ts: str) -> dict:
    from writer_walmart_strategy import write_walmart_strategy
    import glob

    if not TEMPLATE_STRATEGY.exists():
        raise FileNotFoundError(f"Strategy template not found: {TEMPLATE_STRATEGY}")

    write_walmart_strategy(
        export_path=input_path,
        template_path=str(TEMPLATE_STRATEGY),
        output_dir=str(OUTPUT_DIR),
    )

    # writer_walmart_strategy saves with its own filename — find and rename
    candidates = sorted(
        glob.glob(str(OUTPUT_DIR / "* — WM Strategy Analysis *.xlsm")),
        key=os.path.getmtime, reverse=True,
    )
    fname = f"{safe_hash} - WM Strategy Analysis - {ts}.xlsm"
    fpath = OUTPUT_DIR / fname
    if candidates:
        src = Path(candidates[0])
        if src != fpath:
            src.rename(fpath)

    size = fpath.stat().st_size if fpath.exists() else 0
    if not fpath.exists() or size < MIN_OUTPUT_BYTES:
        raise RuntimeError(f"Strategy output missing or too small ({size} bytes).")

    gc.collect()
    return {
        'download_filename': fname,
        'grade':  'Completed',
        'score':  'N/A',
        'ok': 0, 'flag': 0, 'partial': 0,
    }


def run_full_analysis(input_path: str) -> dict:
    """Run all four pillar agents sequentially — Mastery → Framework → Health → Strategy."""

    from reader_databricks_walmart import load_walmart_context
    ctx       = load_walmart_context(input_path)
    hash_name = ctx.hash_name or "UNKNOWN_ACCOUNT"
    safe_hash = _safe_fn(hash_name)
    del ctx
    gc.collect()

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    agents  = {}
    errors  = {}

    for key, runner in [
        ('mastery',   _run_mastery),
        ('framework', _run_framework),
        ('health',    _run_health),
        ('strategy',  _run_strategy),
    ]:
        try:
            agents[key] = {'status': 'ok', **runner(input_path, safe_hash, ts)}
            print(f"  [walmart] {key} done — {agents[key].get('grade', '')}")
        except Exception:
            tb = traceback.format_exc()
            agents[key] = {'status': 'error', 'error': tb}
            print(f"  [walmart] {key} FAILED:\n{tb[:400]}")

    return {'agents': agents, 'account': hash_name}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def root():
    from flask import redirect
    return redirect("/walmart")


@app.route("/walmart")
def index():
    return render_template("walmart_index.html")


@app.route("/walmart/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "No file selected."}), 400

    _, ext = os.path.splitext(uploaded.filename.lower())
    if ext not in {".xlsx", ".xlsm"}:
        return jsonify({"error": "Only .xlsx or .xlsm files accepted."}), 400

    safe_name  = secure_filename(uploaded.filename)
    input_path = str(UPLOAD_DIR / safe_name)
    uploaded.save(input_path)

    try:
        result = run_full_analysis(input_path)
    except Exception:
        traceback.print_exc()
        return jsonify({"error": traceback.format_exc()}), 500
    finally:
        try:
            os.remove(input_path)
        except Exception:
            pass
        gc.collect()

    return jsonify(result)


@app.route("/walmart/download/<path:filename>")
def download(filename):
    from urllib.parse import unquote
    filename = unquote(filename)
    p = OUTPUT_DIR / filename

    if not p.exists():
        xlsm_files = sorted(OUTPUT_DIR.glob("*.xlsm"), key=lambda f: f.stat().st_mtime, reverse=True)
        if xlsm_files:
            p = xlsm_files[0]
            filename = p.name
        else:
            return f"No output files found in {OUTPUT_DIR}", 404

    data = p.read_bytes()
    return Response(
        data,
        mimetype="application/vnd.ms-excel.sheet.macroEnabled.12",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        }
    )


@app.route("/favicon.ico")
@app.route("/walmart/favicon.ico")
def favicon():
    return "", 204


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8503))
    print(f"\n  Walmart CoE Analysis Tool")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Mastery template  : {TEMPLATE_MASTERY} (exists: {TEMPLATE_MASTERY.exists()})")
    print(f"  Framework template: {TEMPLATE_FRAMEWORK} (exists: {TEMPLATE_FRAMEWORK.exists()})")
    print(f"  Health template   : {TEMPLATE_HEALTH} (exists: {TEMPLATE_HEALTH.exists()})")
    print(f"  Strategy template : {TEMPLATE_STRATEGY} (exists: {TEMPLATE_STRATEGY.exists()})")
    print(f"  Outputs           : {OUTPUT_DIR}")
    print(f"  Open → http://127.0.0.1:{port}/walmart\n")
    app.run(host="0.0.0.0", port=port, debug=False)
