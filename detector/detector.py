"""
AI-Ops Detector:
 - Queries Loki for the last N minutes of logs for job=app
 - Builds sliding-window features from recent log lines
 - Uses IsolationForest to detect anomalous windows
 - Alerts Slack, and auto-remediates by creating GH issue or writing remediation log

Environment variables:
 - LOKI_URL (default http://loki:3100)
 - SLACK_WEBHOOK (required to send Slack alerts)
 - GITHUB_TOKEN (optional, for creating issues)
 - GITHUB_REPO (owner/repo for issue creation, required if using GITHUB_TOKEN)
 - LOG_QUERY_RANGE_MINUTES (default 10)
 - WINDOW_SIZE (number of lines per window, default 50)
 - WINDOW_STEP (sliding step, default 25)
 - CONTAMINATION (IsolationForest contamination param, default 0.05)
"""

import os
import time
import requests
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
import dateutil.parser

LOKI_URL = os.environ.get("LOKI_URL", "http://loki:3100")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

LOG_QUERY_RANGE_MINUTES = int(os.environ.get("LOG_QUERY_RANGE_MINUTES", "10"))
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", "50"))
WINDOW_STEP = int(os.environ.get("WINDOW_STEP", "25"))
CONTAMINATION = float(os.environ.get("CONTAMINATION", "0.05"))

def query_loki_for_lines(job="app", minutes=10):
    """
    Query Loki for lines from now - minutes -> now for job label.
    Returns list of (timestamp_iso, line).
    """
    end = datetime.utcnow()
    start = end - timedelta(minutes=minutes)
    # Convert to RFC3339 or nanoseconds? Loki accepts RFC3339 for start/end params. Use RFC3339.
    params = {
        "query": '{job="app"}',
        "limit": 1000,
        "start": int(start.timestamp() * 1e9),  # nanoseconds
        "end": int(end.timestamp() * 1e9),
    }
    url = f"{LOKI_URL}/loki/api/v1/query_range"
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        lines = []
        for stream in data.get("data", {}).get("result", []):
            for ts, line in stream.get("values", []):
                # ts is nanoseconds as string — convert
                ts_ns = int(ts)
                ts_s = ts_ns / 1e9
                ts_iso = datetime.utcfromtimestamp(ts_s).isoformat() + "Z"
                lines.append((ts_iso, line))
        # sort by timestamp
        lines.sort(key=lambda x: x[0])
        return lines
    except Exception as e:
        print("Error querying loki:", e)
        return []

def feature_extraction_from_lines(lines):
    """
    Build sliding windows from raw lines and extract numeric features for each window.

    For each window:
      - avg_length: average line length
      - error_count: number of lines containing 'ERROR'
      - warn_count: number of lines containing 'WARN'
      - unique_messages: count of unique messages (simple proxy for diversity)
    """
    texts = [ln for _, ln in lines]
    n = len(texts)
    if n == 0:
        return np.empty((0, 4))
    windows = []
    for start in range(0, max(1, n - WINDOW_SIZE + 1), max(1, WINDOW_STEP)):
        window = texts[start:start + WINDOW_SIZE]
        lengths = [len(x) for x in window]
        avg_length = float(np.mean(lengths)) if lengths else 0.0
        error_count = sum(1 for x in window if "ERROR" in x or "Error" in x)
        warn_count = sum(1 for x in window if "WARN" in x or "Warning" in x)
        unique_messages = len(set(window))
        windows.append([avg_length, error_count, warn_count, unique_messages])
    return np.array(windows)

def detect_anomalies(features):
    """
    Fit IsolationForest on features and detect which windows are anomalous.
    Returns indices of anomalous windows.
    """
    if features.shape[0] < 3:
        return []  # not enough samples for a model
    model = IsolationForest(contamination=CONTAMINATION, random_state=42)
    preds = model.fit_predict(features)
    anomalies = [i for i, p in enumerate(preds) if p == -1]
    return anomalies

def send_slack_alert(text):
    if not SLACK_WEBHOOK:
        print("No SLACK_WEBHOOK configured; skipping Slack alert. Message would be:", text)
        return
    payload = {"text": f"🚨 AI-Ops Anomaly detected:\n{text}"}
    try:
        r = requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
        r.raise_for_status()
        print("Slack alert sent.")
    except Exception as e:
        print("Failed to send Slack alert:", e)

def auto_remediate(summary):
    """
    Auto remediation action: create a GitHub issue if token + repo provided,
    otherwise append to remediation.log file (local).
    """
    if GITHUB_TOKEN and GITHUB_REPO:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        payload = {"title": "AI-Ops: Anomaly detected — auto remediation", "body": summary}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            r.raise_for_status()
            issue = r.json()
            print("Created GitHub issue:", issue.get("html_url"))
            return {"type": "github_issue", "url": issue.get("html_url")}
        except Exception as e:
            print("Failed to create GitHub issue:", e)
    # fallback: write to /tmp/remediation.log
    try:
        with open("/tmp/remediation.log", "a") as f:
            f.write(f"{datetime.utcnow().isoformat()} - {summary}\n")
        print("Wrote remediation log to /tmp/remediation.log")
        return {"type": "log", "path": "/tmp/remediation.log"}
    except Exception as e:
        print("Failed to write remediation log:", e)
        return None

def summarize_anomalies(anomalies, features):
    parts = []
    for idx in anomalies:
        feats = features[idx]
        parts.append(f"window#{idx}: avg_len={feats[0]:.1f}, errors={int(feats[1])}, warns={int(feats[2])}, uniq={int(feats[3])}")
    return "\n".join(parts)

def main():
    print("AI-Ops Detector starting...")
    lines = query_loki_for_lines(minutes=LOG_QUERY_RANGE_MINUTES)
    print(f"Queried {len(lines)} lines from Loki (last {LOG_QUERY_RANGE_MINUTES} minutes).")
    features = feature_extraction_from_lines(lines)
    print(f"Built {features.shape[0]} windows for detection.")
    anomalies = detect_anomalies(features)
    if anomalies:
        print(f"Detected anomalies in windows: {anomalies}")
        summary = summarize_anomalies(anomalies, features)
        send_slack_alert(summary)
        rem = auto_remediate(summary)
        print("Remediation result:", rem)
    else:
        print("No anomalies detected ✔️")

if __name__ == "__main__":
    main()

