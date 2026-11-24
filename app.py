from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3, hashlib, secrets, datetime

BASE=Path(__file__).parent; DB=BASE/'portal.db'
app=FastAPI(title='Student Portal Simulator V3',description='Independent fictional academic portal simulator')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')

def hash_pw(pw,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',pw.encode(),salt.encode(),160000).hex()
def verify_pw(pw,saved):
    salt,digest=saved.split(':',1)
    return secrets.compare_digest(hash_pw(pw,salt).split(':',1)[1],digest)
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def grade(m):
    if m>=70:return 'A'
    if m>=60:return 'B'
    if m>=50:return 'C'
    if m>=40:return 'D'
    return 'E'
def gp(g): return {'A':4.0,'B':3.0,'C':2.0,'D':1.0,'E':0.0}.get(g,0)
def init_db():
  with db() as c:
    c.executescript('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,regno TEXT UNIQUE,name TEXT,course TEXT,year INTEGER,email TEXT,password_hash TEXT,role TEXT DEFAULT 'student');
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,student_id INTEGER,role TEXT);
    CREATE TABLE IF NOT EXISTS units(id INTEGER PRIMARY KEY,code TEXT UNIQUE,title TEXT,semester TEXT,credits INTEGER DEFAULT 3);
    CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY,student_id INTEGER,unit_id INTEGER,marks REAL,grade TEXT,semester TEXT,academic_year TEXT DEFAULT '2025/2026');
    CREATE TABLE IF NOT EXISTS fees(id INTEGER PRIMARY KEY,student_id INTEGER,description TEXT,amount REAL,date TEXT,kind TEXT);
    CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY,student_id INTEGER,unit_id INTEGER,semester TEXT,academic_year TEXT DEFAULT '2025/2026',UNIQUE(student_id,unit_id,semester));
    CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY,title TEXT,body TEXT,date TEXT);
    CREATE TABLE IF NOT EXISTS timetable(id INTEGER PRIMARY KEY,unit_id INTEGER,day TEXT,start_time TEXT,end_time TEXT,venue TEXT);''')
    if c.execute('SELECT count(*) FROM students').fetchone()[0]==0:
      c.execute('INSERT INTO students(regno,name,course,year,email,password_hash,role) VALUES(?,?,?,?,?,?,?)',('DEMO2026','Alex Demo Student','BSc Data Science',3,'alex.demo@example.test',hash_pw('student123'),'student'))
      c.execute('INSERT INTO students(regno,name,course,year,email,password_hash,role) VALUES(?,?,?,?,?,?,?)',('ADMIN001','Portal Demo Administrator','Portal Administration',1,'admin@example.test',hash_pw('admin123'),'admin'))
      unitdata=[('DSC310','Data Mining','Semester 1',3),('DSC312','Statistical Learning','Semester 1',3),('DSC314','Database Systems','Semester 1',3),('DSC316','Data Visualization','Semester 1',3),('DSC318','Research Methods','Semester 1',3),('DSC320','Machine Learning','Semester 2',3),('DSC322','Big Data Analytics','Semester 2',3),('DSC324','Data Ethics','Semester 2',3)]
      for u in unitdata:c.execute('INSERT INTO units(code,title,semester,credits) VALUES(?,?,?,?)',u)
      sid=c.execute("SELECT id FROM students WHERE regno='DEMO2026'").fetchone()['id']; units=c.execute('SELECT * FROM units ORDER BY id').fetchall()
      for u,m in zip(units,[76,68,72,81,64,79,71,88]):
        c.execute('INSERT INTO results(student_id,unit_id,marks,grade,semester,academic_year) VALUES(?,?,?,?,?,?)',(sid,u['id'],m,grade(m),u['semester'],'2025/2026'))
        c.execute('INSERT INTO registrations(student_id,unit_id,semester,academic_year) VALUES(?,?,?,?)',(sid,u['id'],u['semester'],'2025/2026'))
      for f in [('Tuition fees',78000,'2026-09-01','charge'),('Library fee',2500,'2026-09-01','charge'),('Student payment',30000,'2026-09-12','payment'),('Student payment',15000,'2026-10-10','payment')]:c.execute('INSERT INTO fees(student_id,description,amount,date,kind) VALUES(?,?,?,?,?)',(sid,*f))
      c.execute("INSERT INTO notices(title,body,date) VALUES('Demo results available','Sample examination results have been added. This is a fictional demonstration portal.','2026-11-20')")
      # Demo timetable entries
      for u,day,start,end,venue in [(units[0],'Monday','09:00','11:00','Lab 2'),(units[1],'Tuesday','11:00','13:00','Room B14'),(units[2],'Wednesday','14:00','16:00','Lab 1'),(units[3],'Thursday','10:00','12:00','Room C03')]:c.execute('INSERT INTO timetable(unit_id,day,start_time,end_time,venue) VALUES(?,?,?,?,?)',(u['id'],day,start,end,venue))
init_db()

class Login(BaseModel): regno:str; password:str
class StudentIn(BaseModel): regno:str; name:str; course:str; year:int=Field(ge=1,le=8); password:str; email:str=''
class ResultIn(BaseModel): regno:str; code:str; title:str; marks:float=Field(ge=0,le=100); semester:str; academic_year:str='2025/2026'; credits:int=Field(default=3,ge=1,le=10)
class ResultEditIn(BaseModel): marks:float=Field(ge=0,le=100)
class FeeIn(BaseModel): regno:str; description:str; amount:float=Field(gt=0); kind:str='charge'
class NoticeIn(BaseModel): title:str; body:str
class UnitIn(BaseModel): code:str; title:str; semester:str; credits:int=Field(default=3,ge=1,le=10)

def auth(authorization:str=Header(default='')):
 token=authorization.replace('Bearer ','').strip()
 if not token:raise HTTPException(401,'Login required')
 with db() as c:r=c.execute('SELECT s.*,ss.token FROM sessions ss JOIN students s ON s.id=ss.student_id WHERE ss.token=?',(token,)).fetchone()
 if not r:raise HTTPException(401,'Session expired')
 return r
def admin(u=Depends(auth)):
 if u['role']!='admin':raise HTTPException(403,'Administrator access required')
 return u
@app.get('/')
def index():return FileResponse(BASE/'static/index.html')
@app.post('/api/login')
def login(data:Login):
 with db() as c:r=c.execute('SELECT * FROM students WHERE regno=?',(data.regno.upper(),)).fetchone()
 if not r or not verify_pw(data.password,r['password_hash']):raise HTTPException(401,'Incorrect demo ID or password')
 token=secrets.token_urlsafe(32)
 with db() as c:c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,r['id'],r['role']))
 return {'token':token,'role':r['role'],'student':dict(regno=r['regno'],name=r['name'],course=r['course'],year=r['year'],email=r['email'])}
@app.post('/api/logout')
def logout(u=Depends(auth),authorization:str=Header(default='')):
 with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(authorization.replace('Bearer ','').strip(),))
 return {'ok':True}
@app.get('/api/me')
def me(u=Depends(auth)):return dict(regno=u['regno'],name=u['name'],course=u['course'],year=u['year'],email=u['email'],role=u['role'])
@app.get('/api/results')
def results(u=Depends(auth)):
 with db() as c:rows=c.execute('SELECT un.code,un.title,un.credits,r.marks,r.grade,r.semester,r.academic_year FROM results r JOIN units un ON un.id=r.unit_id WHERE r.student_id=? ORDER BY r.academic_year DESC,r.semester,un.code',(u['id'],)).fetchall()
 return [dict(x) for x in rows]
@app.get('/api/fees')
def fees(u=Depends(auth)):
 with db() as c:r=c.execute('SELECT description,amount,date,kind FROM fees WHERE student_id=? ORDER BY date',(u['id'],)).fetchall()
 return [dict(x) for x in r]
@app.get('/api/registrations')
def registrations(u=Depends(auth)):
 with db() as c:
  regs=c.execute('SELECT un.code,un.title,un.credits,r.semester,r.academic_year FROM registrations r JOIN units un ON un.id=r.unit_id WHERE r.student_id=? ORDER BY r.semester,un.code',(u['id'],)).fetchall()
  cat=c.execute('SELECT code,title,credits,semester FROM units ORDER BY semester,code').fetchall()
 return {'registered':[dict(x) for x in regs],'catalog':[dict(x) for x in cat]}
@app.post('/api/registrations/{code}')
def register(code:str,u=Depends(auth)):
 with db() as c:
  unit=c.execute('SELECT * FROM units WHERE code=?',(code.upper(),)).fetchone()
  if not unit:raise HTTPException(404,'Unit not found')
  try:c.execute('INSERT INTO registrations(student_id,unit_id,semester) VALUES(?,?,?)',(u['id'],unit['id'],unit['semester']))
  except sqlite3.IntegrityError:raise HTTPException(400,'Already registered for this unit')
 return {'ok':True}
@app.delete('/api/registrations/{code}')
def unregister(code:str,u=Depends(auth)):
 with db() as c:c.execute('DELETE FROM registrations WHERE student_id=? AND unit_id=(SELECT id FROM units WHERE code=?)',(u['id'],code.upper()))
 return {'ok':True}
@app.get('/api/notices')
def notices(u=Depends(auth)):
 with db() as c:r=c.execute('SELECT title,body,date FROM notices ORDER BY date DESC').fetchall()
 return [dict(x) for x in r]
@app.get('/api/timetable')
def timetable(u=Depends(auth)):
 with db() as c:r=c.execute('SELECT un.code,un.title,t.day,t.start_time,t.end_time,t.venue FROM timetable t JOIN units un ON un.id=t.unit_id ORDER BY CASE t.day WHEN "Monday" THEN 1 WHEN "Tuesday" THEN 2 WHEN "Wednesday" THEN 3 WHEN "Thursday" THEN 4 WHEN "Friday" THEN 5 ELSE 6 END,t.start_time').fetchall()
 return [dict(x) for x in r]
# Admin APIs
@app.get('/api/admin/students')
def list_students(a=Depends(admin)):
 with db() as c:r=c.execute('SELECT regno,name,course,year,email,role FROM students ORDER BY regno').fetchall()
 return [dict(x) for x in r]
@app.post('/api/admin/students')
def create_student(d:StudentIn,a=Depends(admin)):
 with db() as c:
  try:c.execute('INSERT INTO students(regno,name,course,year,email,password_hash,role) VALUES(?,?,?,?,?,?,?)',(d.regno.upper(),d.name,d.course,d.year,d.email or (d.regno.lower()+'@demo.test'),hash_pw(d.password),'student'))
  except sqlite3.IntegrityError:raise HTTPException(400,'Registration number already exists')
 return {'ok':True}
@app.post('/api/admin/results')
def add_result(d:ResultIn,a=Depends(admin)):
 with db() as c:
  s=c.execute('SELECT id FROM students WHERE regno=?',(d.regno.upper(),)).fetchone()
  if not s:raise HTTPException(404,'Student not found')
  unit=c.execute('SELECT id FROM units WHERE code=?',(d.code.upper(),)).fetchone()
  if unit:
   c.execute('UPDATE units SET title=?,semester=?,credits=? WHERE id=?',(d.title,d.semester,d.credits,unit['id']));uid=unit['id']
  else:uid=c.execute('INSERT INTO units(code,title,semester,credits) VALUES(?,?,?,?)',(d.code.upper(),d.title,d.semester,d.credits)).lastrowid
  c.execute('INSERT INTO results(student_id,unit_id,marks,grade,semester,academic_year) VALUES(?,?,?,?,?,?)',(s['id'],uid,d.marks,grade(d.marks),d.semester,d.academic_year))
 return {'ok':True,'grade':grade(d.marks)}

@app.get('/api/admin/results')
def admin_results(a=Depends(admin)):
 with db() as c:
  rows=c.execute('SELECT r.id,s.regno,s.name,un.code,un.title,r.marks,r.grade,r.semester,r.academic_year FROM results r JOIN students s ON s.id=r.student_id JOIN units un ON un.id=r.unit_id ORDER BY r.academic_year DESC,r.semester,s.regno,un.code').fetchall()
 return [dict(x) for x in rows]
@app.patch('/api/admin/results/{result_id}')
def edit_result(result_id:int,d:ResultEditIn,a=Depends(admin)):
 with db() as c:
  row=c.execute('SELECT id FROM results WHERE id=?',(result_id,)).fetchone()
  if not row: raise HTTPException(404,'Demo result not found')
  c.execute('UPDATE results SET marks=?,grade=? WHERE id=?',(d.marks,grade(d.marks),result_id))
 return {'ok':True,'grade':grade(d.marks)}
@app.delete('/api/admin/results/{result_id}')
def delete_result(result_id:int,a=Depends(admin)):
 with db() as c:
  cur=c.execute('DELETE FROM results WHERE id=?',(result_id,))
  if cur.rowcount==0: raise HTTPException(404,'Demo result not found')
 return {'ok':True}

@app.post('/api/admin/fees')
def add_fee(d:FeeIn,a=Depends(admin)):
 with db() as c:
  s=c.execute('SELECT id FROM students WHERE regno=?',(d.regno.upper(),)).fetchone()
  if not s:raise HTTPException(404,'Student not found')
  c.execute('INSERT INTO fees(student_id,description,amount,date,kind) VALUES(?,?,?,?,?)',(s['id'],d.description,d.amount,datetime.date.today().isoformat(),d.kind))
 return {'ok':True}
@app.post('/api/admin/units')
def add_unit(d:UnitIn,a=Depends(admin)):
 with db() as c:
  try:c.execute('INSERT INTO units(code,title,semester,credits) VALUES(?,?,?,?)',(d.code.upper(),d.title,d.semester,d.credits))
  except sqlite3.IntegrityError:raise HTTPException(400,'Unit code already exists')
 return {'ok':True}
@app.post('/api/admin/notices')
def add_notice(d:NoticeIn,a=Depends(admin)):
 with db() as c:c.execute('INSERT INTO notices(title,body,date) VALUES(?,?,?)',(d.title,d.body,datetime.date.today().isoformat()))
 return {'ok':True}
