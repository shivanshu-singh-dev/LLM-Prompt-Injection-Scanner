import os
import sys
import json
import subprocess
import threading
from pathlib import Path
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, template_folder="templates")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_JSON_PATH = PROJECT_ROOT / "results" / "report.json"
MAIN_PY_PATH = PROJECT_ROOT / "main.py"

scan_lock = threading.Lock()
scan_state = {
    "running": False,
    "error": None
}

def run_scan_worker():
    global scan_state
    try:
        res = subprocess.run(
            [sys.executable, str(MAIN_PY_PATH)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            scan_state["error"] = res.stderr or f"Scan failed with exit code {res.returncode}"
        else:
            scan_state["error"] = None
    except Exception as e:
        scan_state["error"] = str(e)
    finally:
        scan_state["running"] = False

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/results")
def get_results():
    if not REPORT_JSON_PATH.exists():
        return jsonify({"results": []})
    try:
        with open(REPORT_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return jsonify({"results": data})
        elif isinstance(data, dict):
            if "results" in data:
                return jsonify(data)
            return jsonify({"results": [data]})
        return jsonify({"results": []})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)})

@app.route("/api/scan", methods=["POST"])
def start_scan():
    global scan_state
    with scan_lock:
        if scan_state["running"]:
            return jsonify({"error": "A scan is already in progress"}), 409
        scan_state["running"] = True
        scan_state["error"] = None

    thread = threading.Thread(target=run_scan_worker, daemon=True)
    thread.start()
    return jsonify({"status": "Scan started"}), 202

@app.route("/api/status")
def get_status():
    return jsonify(scan_state)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
