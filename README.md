# EECS 594 Assignment 3 — Emotion Classification Study

Two conditions implemented in one Flask backend, using the held-out 300-trial A2 dataset and its precomputed DistilBERT predictions. Both conditions have the same label options and task instructions; AI condition shows model prediction and confidence. Each participant receives 10 randomly sampled trials. Stores responses and post-task ratings in SQLite.

## Run locally

```bash
pip install -r requirements.txt
export SECRET_KEY='replace-with-long-random-string'
export ADMIN_TOKEN='replace-with-another-long-random-string'
python app.py
```

Open `http://localhost:5000/start/baseline` and `http://localhost:5000/start/ai` in separate browsers/incognito sessions to test. Each participant must use one condition at a time; the browser session tracks their current condition. The same participant code can be used across conditions. Verify both export files after test submissions:

- `http://localhost:5000/admin/export/participants?token=YOUR_ADMIN_TOKEN`
- `http://localhost:5000/admin/export/responses?token=YOUR_ADMIN_TOKEN`

## Deploy

Use a Python web hosting service with a **persistent writable disk** and HTTPS. Build: `pip install -r requirements.txt`; start: `gunicorn --workers 1 --threads 4 app:app`. Set `SECRET_KEY`, `ADMIN_TOKEN`, and `DATABASE_PATH` (pointing to persistent storage, e.g. `/var/data/study.sqlite3`). On Render, free ephemeral filesystems can **lose collected data on restart/redeploy**: use a persistent disk on an eligible plan or replace SQLite with managed Postgres before collecting real participants. Do **not** assume the default local SQLite database persists on free hosting. If using Render, a persistent disk typically requires a paid service. Do not post export URLs or ADMIN_TOKEN publicly.

Publish these two URLs (replace HOST):
- `https://HOST/start/baseline`
- `https://HOST/start/ai`

## What is collected

`participants`: pseudonymous participant code, condition, start/end times, attention-check pass, workload 1–5, confidence 1–5, optional feedback.

`responses`: participant ID, trial index and ID, selected label, ground truth, correctness, elapsed response milliseconds, displayed AI prediction and confidence (AI condition only), submission time.

The attention check is deliberately easy; participants failing it must retry before starting. Only completed participants with 10 recorded responses should count toward the required minimum of 5 per condition. For within-person comparisons, pair by participant code and analyze condition differences (accuracy, median time, workload, confidence). Note that randomized trials are not identical across conditions; acknowledge this limitation. The precomputed predictions are **asynchronous**, not eligible for the +3 real-time AI bonus.

## Before class

- Deploy to a persistent backend and verify the public HTTPS links.
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

**Critical deployment caveat:** This app still stores responses in SQLite. On Render Free, data is not persistent across restarts or redeploys. Export both CSVs frequently and after each class session, and use a durable database or paid persistent disk for reliable collection. Do not change the app during active data collection.
