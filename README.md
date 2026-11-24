# Student Portal Simulator V3

Independent portal UI and workflow simulator with fictional data. This is not an official university site and does not accept real university credentials.


## Run on macOS/Linux

```bash
cd student_portal_v3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000

## Demo accounts
- Student: `DEMO2026` / `student123`
- Admin: `ADMIN001` / `admin123`

## Included
- Login sessions, hashed demo passwords
- Student dashboard and sample profile
- Results filtered by semester and academic year, grade calculations, average and GPA
- Academic history, printable transcript, fees ledger, registration/drop, timetable and notices
- Admin pages to create demo students, publish results, add units, post fees and notices
- SQLite persistent local storage

All student records, results, fee entries, and notices are fictional demonstration data. For a real deployment, use security review, HTTPS, rate limiting, audit logging, robust access controls, secret management, database migrations, and proper backups.
