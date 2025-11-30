# AI-Ops Log Anomaly Detector — demo repo

An end-to-end demo of an AI-Ops pipeline:
- **app** produces logs
- **promtail** ships logs to **Loki**
- **detector** queries logs from Loki, runs **IsolationForest** for anomaly detection,
  sends **Slack** alerts and performs simple auto-remediation (creates a GitHub issue or writes a remediation log).

This is a small, production-oriented demo you can present on LinkedIn to show practical AI-Ops skills.

---

## Quick start (local, using Docker Compose)

1. Copy `.env.example` to `.env` and populate:

2. Start services:

docker compose up --build 

This will start:
- `loki` on `http://localhost:3100`
- `promtail` pushing logs to Loki
- `app` writing logs to /var/log/app/app.log
- `detector` (container will run the detector script once on start)

3. Trigger anomalies:
- App randomly produces errors; to force anomalies, you can manually append error lines to `./app/log/app.log`.

4. View alerts:
- Slack messages will be posted to your configured webhook.
- If `GITHUB_TOKEN` and `GITHUB_REPO` are set, an issue will be created when anomalies are detected.

---

## Files & Components

- `app/` — small Python log generator.
- `promtail/` — Promtail config to send logs to Loki.
- `loki/` — Loki config.
- `detector/` — Python detector using scikit-learn IsolationForest; alerts to Slack and auto-remediates.

---

## How the detector works (summary)
1. Query Loki for the last N minutes of logs.
2. Build sliding windows of lines (size `WINDOW_SIZE`).
3. Extract numeric features per window: avg length, error count, warn count, unique messages.
4. Fit `IsolationForest` and detect anomalous windows (outliers).
5. If anomalies found: post Slack alert, then run remediation (create GH issue or write log).

---

## Customize / Improve (ideas)
- Add Grafana and a dashboard to visualize anomalies and log rate.
- Replace IsolationForest with a sequence model (LSTM/Transformer) for more nuanced patterns.
- Hook remediation into Kubernetes (restart pods), PagerDuty, or an incident management system.
- Add model training pipeline with versioning and model metrics recording.

---
