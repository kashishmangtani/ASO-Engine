"""Run AI visibility checks for every client. Schedule with cron, e.g. weekly:
   0 6 * * 1  cd /path/to/geo-platform && python3 run_all.py
"""
from app.db import get_db, init_db
from app.tracker import execute_run, start_run

if __name__ == "__main__":
    init_db()
    with get_db() as db:
        clients = [dict(r) for r in db.execute("SELECT id, name FROM clients")]
    for c in clients:
        s = execute_run(start_run(c["id"]))
        print(f"{c['name']}: visibility {s['visibility']}%, share of voice {s['share_of_voice']}%")
