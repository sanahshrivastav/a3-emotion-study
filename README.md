# EECS 594 Assignment 3 — Emotion Classification Study

Two conditions implemented in one Flask backend, using the held-out 300-trial A2 dataset and its precomputed DistilBERT predictions. Both conditions have the same label options and task instructions; AI condition shows model prediction and confidence. Each participant receives 12 randomly sampled trials, two per emotion. Stores responses and post-task ratings in SQLite or Turso libSQL.

## Run locally

```bash
pip install -r requirements.txt
export SECRET_KEY='replace-with-long-random-string'
export ADMIN_TOKEN='replace-with-another-long-random-string'
python app.py
```

Without Turso credentials, the app uses a local SQLite database at `study.sqlite3` (or `DATABASE_PATH` if set).

Open `http://localhost:5000/start/baseline` and `http://localhost:5000/start/ai` in separate browsers/incognito sessions to test. Each participant must use one condition at a time; the browser session tracks their current condition. The same participant code can be used across conditions. Verify both export files after test submissions:

- `http://localhost:5000/admin/export/participants?token=YOUR_ADMIN_TOKEN`
- `http://localhost:5000/admin/export/responses?token=YOUR_ADMIN_TOKEN`

## Deploy

For a remote Turso libSQL database, set both `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` in the hosting provider's secret environment-variable settings. The URL is the database URL from Turso, such as `libsql://proj1-sanah.aws-us-west-2.turso.io`; create a read-write token for the database and keep it secret. For example, the Turso CLI can create a token with `turso db tokens create proj1 --expiration 7d`. Set `SECRET_KEY` and `ADMIN_TOKEN` as well. If only one of the two Turso variables is set, the app exits with an error. When both are set, the app connects to Turso and creates the `participants` and `responses` tables if they do not already exist. Otherwise, it uses local SQLite; do not set `DATABASE_PATH` to a Turso URL.

Use a Python web hosting service with HTTPS. Build: `pip install -r requirements.txt`; start: `gunicorn --workers 1 --threads 4 app:app`. Turso stores the data remotely, so the app does not require a persistent writable disk for the database. Verify the app can connect and create its schema in a separate test database before collecting real participant data. Do not post export URLs or `ADMIN_TOKEN` publicly.

Publish these two URLs (replace HOST):
- `https://HOST/start/baseline`
- `https://HOST/start/ai`

### Verify the deployed database

Before sharing participant links, complete a test run in each condition using synthetic participant codes. Complete all 12 trials and the survey for each run. Download the participant and response exports using the private `ADMIN_TOKEN` URLs above; expect 2 completed participants and 24 responses total. Confirm that AI prediction/confidence values are present only for the AI condition. Restart or redeploy the app, then verify the same records remain available. Use a separate Turso database for smoke tests when possible.

## What is collected

`participants`: pseudonymous participant code, condition, start/end times, attention-check pass, workload 1–5, confidence 1–5, optional feedback.

`responses`: participant ID, trial index and ID, selected label, ground truth, correctness, elapsed response milliseconds, displayed AI prediction and confidence (AI condition only), submission time.

The attention check is deliberately easy; participants failing it must retry before starting. Only completed participants with 12 recorded responses should count toward the required minimum of 5 per condition. For within-person comparisons, pair by participant code and analyze condition differences (accuracy, median time, workload, confidence). Note that randomized trials are not identical across conditions; acknowledge this limitation. The precomputed predictions are **asynchronous**, not eligible for the +3 real-time AI bonus.

## Before class

- Deploy the backend and verify the public HTTPS links.
- Complete one test run in each condition; export both CSVs and verify data.
- Check mobile layout and the survey; keep backend online throughout class.
- Enter both URLs in the A3 HIT spreadsheet before 10:00 AM Nov 12.
- Collect at least five completed participants in **each** condition and complete required classmates' tasks.

## Privacy

Do not collect names, passwords, emails or sensitive identifying information. Use participant-selected pseudonymous codes; avoid public exports. The A2 text dataset may contain emotionally sensitive content; inspect trials before public deployment. Classroom human-subject research policies may apply; follow course instructions.


## Updated November 12 — curated trial pool

The original `study_dataset_final.csv` is unchanged and included for provenance. The app reads `study_dataset_curated.csv`: 120 selected examples (20 per emotion) from the original dataset. Selection uses text length/readability and filters certain distressing/markup terms; **AI correctness and confidence were not used to select items**. The original trial IDs, labels, predictions and confidences are retained. Each session now samples 2 trials per emotion (12 total), randomized. This is a change from the original 10-trial design; document this change in the final report.

Participant entry now asks for a pseudonymous participant code rather than a UMich uniqname. If a participant has already completed the previous version, keep their data separate for analysis.

Exports accept either `ADMIN_TOKEN` or `EXPORT_TOKEN` as the environment variable name. For security, do not publish the token or export links.

With Turso configured, responses are stored in the remote database and survive app restarts or redeploys. If Turso credentials are absent, the app uses local SQLite instead; local files on ephemeral hosting may be lost on restart or redeploy. Verify the deployed environment variables and exports before collecting real data. Do not change the app during active data collection.
