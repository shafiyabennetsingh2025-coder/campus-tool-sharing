from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path(__file__).with_name('campus_tools.db')


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        college_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        year INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tools (
        tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        condition TEXT NOT NULL DEFAULT 'Good',
        status TEXT NOT NULL DEFAULT 'Available',
        location TEXT,
        FOREIGN KEY(owner_id) REFERENCES students(student_id),
        FOREIGN KEY(category_id) REFERENCES categories(category_id)
    );

    CREATE TABLE IF NOT EXISTS borrow_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        borrower_id INTEGER NOT NULL,
        request_date TEXT DEFAULT CURRENT_TIMESTAMP,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        FOREIGN KEY(tool_id) REFERENCES tools(tool_id),
        FOREIGN KEY(borrower_id) REFERENCES students(student_id)
    );

    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active',
        FOREIGN KEY(tool_id) REFERENCES tools(tool_id),
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    );

    CREATE TABLE IF NOT EXISTS maintenance (
        maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        issue TEXT NOT NULL,
        maintenance_date TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'Reported',
        FOREIGN KEY(tool_id) REFERENCES tools(tool_id)
    );

    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tool_id) REFERENCES tools(tool_id),
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    );
    ''')

    # Seed demo data only if empty
    if conn.execute('SELECT COUNT(*) FROM students').fetchone()[0] == 0:
        conn.executemany('INSERT INTO students(college_id,name,email,department,year) VALUES (?,?,?,?,?)', [
            ('25BAI0187','Shivaanie Kumaresan','shivaanie@vitstudent.ac.in','CSE - AI & ML',1),
            ('25BAI0199','Shafiya Bennet Singh','shafiya@vitstudent.ac.in','CSE - AI & ML',1),
            ('25BCS0101','Aarav Kumar','aarav@vitstudent.ac.in','CSE',2)
        ])
        conn.executemany('INSERT INTO categories(name) VALUES (?)', [
            ('Electronics',),('Academic',),('Photography',),('Sports',),('Project Equipment',)
        ])
        cats = {r['name']: r['category_id'] for r in conn.execute('SELECT * FROM categories')}
        students = {r['college_id']: r['student_id'] for r in conn.execute('SELECT * FROM students')}
        conn.executemany('''INSERT INTO tools(owner_id,category_id,name,description,condition,status,location)
                            VALUES (?,?,?,?,?,?,?)''', [
            (students['25BAI0187'],cats['Electronics'],'Arduino Uno','Arduino board for mini projects','Excellent','Available','Tech Block'),
            (students['25BAI0199'],cats['Academic'],'Scientific Calculator','Casio-style scientific calculator','Good','Available','Library'),
            (students['25BCS0101'],cats['Photography'],'DSLR Camera','Camera for events and project documentation','Good','Available','Main Block')
        ])
    conn.commit()
    conn.close()


@app.route('/')
def index():
    conn = get_db()
    q = request.args.get('q','').strip()
    category = request.args.get('category','')
    sql = '''SELECT t.*, c.name AS category, s.name AS owner_name
             FROM tools t JOIN categories c ON t.category_id=c.category_id
             JOIN students s ON t.owner_id=s.student_id WHERE 1=1'''
    params=[]
    if q:
        sql += ' AND (t.name LIKE ? OR t.description LIKE ?)'
        params += [f'%{q}%', f'%{q}%']
    if category:
        sql += ' AND c.name=?'; params.append(category)
    sql += ' ORDER BY t.tool_id DESC'
    tools = conn.execute(sql,params).fetchall()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    stats = {
        'tools': conn.execute('SELECT COUNT(*) FROM tools').fetchone()[0],
        'available': conn.execute("SELECT COUNT(*) FROM tools WHERE status='Available'").fetchone()[0],
        'requests': conn.execute("SELECT COUNT(*) FROM borrow_requests WHERE status='Pending'").fetchone()[0],
        'students': conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    }
    conn.close()
    return render_template('index.html', tools=tools, categories=categories, stats=stats, q=q, selected_category=category)


@app.post('/add-tool')
def add_tool():
    conn = get_db()
    owner = conn.execute('SELECT student_id FROM students ORDER BY student_id LIMIT 1').fetchone()
    cat = conn.execute('SELECT category_id FROM categories WHERE name=?', (request.form['category'],)).fetchone()
    if not cat:
        conn.execute('INSERT INTO categories(name) VALUES (?)',(request.form['category'],))
        cat = conn.execute('SELECT category_id FROM categories WHERE name=?',(request.form['category'],)).fetchone()
    conn.execute('''INSERT INTO tools(owner_id,category_id,name,description,condition,status,location)
                    VALUES (?,?,?,?,?,?,?)''', (owner['student_id'],cat['category_id'],request.form['name'],request.form['description'],request.form['condition'],'Available',request.form['location']))
    conn.commit(); conn.close()
    return redirect(url_for('index'))


@app.post('/request/<int:tool_id>')
def request_tool(tool_id):
    conn=get_db()
    borrower=conn.execute('SELECT student_id FROM students ORDER BY student_id LIMIT 1').fetchone()
    due=request.form.get('due_date')
    tool=conn.execute('SELECT status FROM tools WHERE tool_id=?',(tool_id,)).fetchone()
    if tool and tool['status']=='Available' and due:
        conn.execute('INSERT INTO borrow_requests(tool_id,borrower_id,due_date) VALUES (?,?,?)',(tool_id,borrower['student_id'],due))
        conn.execute("UPDATE tools SET status='Requested' WHERE tool_id=?",(tool_id,))
        conn.commit()
    conn.close(); return redirect(url_for('index'))


@app.get('/api/requests')
def api_requests():
    conn=get_db()
    rows=conn.execute('''SELECT r.request_id,t.name tool,s.name borrower,r.due_date,r.status
                         FROM borrow_requests r JOIN tools t ON r.tool_id=t.tool_id
                         JOIN students s ON r.borrower_id=s.student_id ORDER BY r.request_id DESC''').fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])


@app.post('/approve/<int:request_id>')
def approve(request_id):
    conn=get_db()
    r=conn.execute('SELECT tool_id FROM borrow_requests WHERE request_id=?',(request_id,)).fetchone()
    if r:
        conn.execute("UPDATE borrow_requests SET status='Approved' WHERE request_id=?",(request_id,))
        conn.execute("UPDATE tools SET status='Borrowed' WHERE tool_id=?",(r['tool_id'],))
        conn.commit()
    conn.close(); return redirect(url_for('admin'))


@app.post('/return/<int:tool_id>')
def return_tool(tool_id):
    conn=get_db()
    conn.execute("UPDATE tools SET status='Available' WHERE tool_id=?",(tool_id,))
    conn.execute("UPDATE borrow_requests SET status='Returned' WHERE tool_id=? AND status='Approved'",(tool_id,))
    conn.commit(); conn.close(); return redirect(url_for('admin'))


@app.route('/admin')
def admin():
    conn=get_db()
    requests=conn.execute('''SELECT r.*, t.name tool_name, s.name borrower
                             FROM borrow_requests r JOIN tools t ON r.tool_id=t.tool_id
                             JOIN students s ON r.borrower_id=s.student_id ORDER BY r.request_id DESC''').fetchall()
    tools=conn.execute('''SELECT t.*,c.name category,s.name owner_name FROM tools t
                          JOIN categories c ON t.category_id=c.category_id JOIN students s ON t.owner_id=s.student_id
                          ORDER BY t.tool_id DESC''').fetchall()
    conn.close(); return render_template('admin.html', requests=requests, tools=tools)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
