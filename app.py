import csv, io, os, random, secrets, sqlite3, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, session, redirect, url_for, render_template, abort, Response

BASE = Path(__file__).parent
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
DB = os.environ.get('DATABASE_PATH', str(BASE / 'study.sqlite3'))
TURSO_DATABASE_URL = os.environ.get('TURSO_DATABASE_URL')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN')
if bool(TURSO_DATABASE_URL) != bool(TURSO_AUTH_TOKEN):
    raise RuntimeError('Set both TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to use Turso.')
if TURSO_DATABASE_URL:
    import libsql

LABELS = ['sadness', 'joy', 'love', 'anger', 'fear', 'surprise']
with open(BASE / 'study_dataset_curated.csv', newline='', encoding='utf-8') as f:
    TRIALS = list(csv.DictReader(f))
TRIAL_BY_ID = {t['trial_id']: t for t in TRIALS}

def connect():
    if TURSO_DATABASE_URL:
        return libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA busy_timeout=30000')
    return c

@contextmanager
def db_connection():
    c = connect()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db():
    with db_connection() as c:
        c.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id TEXT PRIMARY KEY, participant_code TEXT NOT NULL, condition TEXT NOT NULL,
            started_at TEXT NOT NULL, completed_at TEXT, attention_correct INTEGER,
            workload INTEGER, confidence INTEGER, feedback TEXT);
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            participant_id TEXT NOT NULL, trial_index INTEGER NOT NULL,
            trial_id TEXT NOT NULL, selected_label TEXT NOT NULL,
            ground_truth TEXT NOT NULL, is_correct INTEGER NOT NULL,
            response_ms INTEGER NOT NULL, ai_prediction TEXT, ai_confidence REAL,
            submitted_at TEXT NOT NULL,
            PRIMARY KEY (participant_id, trial_index));
        ''')
init_db()

def now(): return datetime.now(timezone.utc).isoformat()

def current():
    pid = session.get('pid')
    if not pid: return None
    with db_connection() as c:
        result = c.execute('SELECT * FROM participants WHERE id=?', (pid,))
        row = result.fetchone()
        if row is None: return None
        return dict(zip((column[0] for column in result.description), row))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/start/<condition>', methods=['GET', 'POST'])
def start(condition):
    if condition not in ('baseline', 'ai'): abort(404)
    if request.method == 'GET': return render_template('start.html', condition=condition)
    code = request.form.get('participant_code', '').strip()[:60]
    if not code: return render_template('start.html', condition=condition, error='Please enter a participant code.'), 400
    attention = request.form.get('attention')
    if attention != 'six': return render_template('start.html', condition=condition, error='Attention check: please read the instructions and try again.'), 400
    pid = secrets.token_urlsafe(18)
    # Two trials per emotion: balanced for every participant, randomized order.
    grouped = {label: [t['trial_id'] for t in TRIALS if t['ground_truth'] == label] for label in LABELS}
    ids = [trial_id for label in LABELS for trial_id in random.sample(grouped[label], 2)]
    random.shuffle(ids)
    session.clear()
    session.update(pid=pid, ids=ids, index=0, shown_at=time.time())
    with db_connection() as c:
        c.execute('INSERT INTO participants (id, participant_code, condition, started_at, attention_correct) VALUES (?,?,?,?,?)', (pid, code, condition, now(), 1))
    return redirect(url_for('trial'))

@app.route('/trial', methods=['GET', 'POST'])
def trial():
    p = current()
    if not p: return redirect(url_for('home'))
    if p['completed_at']: return redirect(url_for('done'))
    idx = session.get('index', 0)
    ids = session.get('ids', [])
    if idx >= len(ids): return redirect(url_for('survey'))
    t = TRIAL_BY_ID[ids[idx]]
    if request.method == 'POST':
        choice = request.form.get('choice', '')
        if choice not in LABELS: return redirect(url_for('trial'))
        elapsed = min(600000, max(0, int((time.time() - session.get('shown_at', time.time())) * 1000)))
        with db_connection() as c:
            c.execute('INSERT OR IGNORE INTO responses VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (p['id'], idx + 1, t['trial_id'], choice, t['ground_truth'], int(choice == t['ground_truth']), elapsed,
                       t['ai_prediction'] if p['condition'] == 'ai' else None,
                       float(t['ai_confidence']) if p['condition'] == 'ai' else None, now()))
        session['index'] = idx + 1
        session['shown_at'] = time.time()
        return redirect(url_for('trial'))
    session['shown_at'] = time.time()
    return render_template('trial.html', t=t, idx=idx, total=len(ids), labels=LABELS, condition=p['condition'])

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    p = current()
    if not p: return redirect(url_for('home'))
    if session.get('index', 0) < len(session.get('ids', [])): return redirect(url_for('trial'))
    if request.method == 'POST':
        try:
            workload = int(request.form['workload']); confidence = int(request.form['confidence'])
            if not (1 <= workload <= 5 and 1 <= confidence <= 5): raise ValueError()
        except (KeyError, ValueError): return render_template('survey.html', error='Please answer both ratings.'), 400
        with db_connection() as c:
            c.execute('UPDATE participants SET workload=?, confidence=?, feedback=?, completed_at=? WHERE id=?',
                      (workload, confidence, request.form.get('feedback', '')[:1000], now(), p['id']))
        return redirect(url_for('done'))
    return render_template('survey.html')

@app.route('/done')
def done():
    p = current()
    if not p: return redirect(url_for('home'))
    return render_template('done.html', completed=bool(p['completed_at']))

@app.route('/admin/export/<table>')
def export(table):
    if not (os.environ.get('ADMIN_TOKEN') or os.environ.get('EXPORT_TOKEN')) or request.args.get('token') != (os.environ.get('ADMIN_TOKEN') or os.environ.get('EXPORT_TOKEN')): abort(403)
    if table not in ('participants', 'responses'): abort(404)
    with db_connection() as c:
        rows = c.execute('SELECT * FROM ' + table).fetchall()
        cols = [column[0] for column in c.execute('SELECT * FROM ' + table + ' LIMIT 0').description]
    out = io.StringIO(); writer = csv.writer(out); writer.writerow(cols)
    writer.writerows([list(r) for r in rows])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={table}.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=os.environ.get('FLASK_DEBUG') == '1', port=int(os.environ.get('PORT', '5000')))
