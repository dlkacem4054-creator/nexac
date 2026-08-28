from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "nexac_super_secure_random_secret_key_2026"  # مفتاح تشفير الجلسات

# تهيئة قاعدة البيانات وإنشاء الجداول وحساب الأدمن الافتراضي
def init_db():
    conn = sqlite3.connect('nexac_system.db')
    cursor = conn.cursor()
    
    # جدول التقارير
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            hwid TEXT,
            status TEXT,
            files TEXT,
            timestamp TEXT
        )
    ''')
    
    # جدول المديرين (Admin Users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # التحقق هل يوجد أدمن مسجل، وإذا لم يوجد نقوم بإنشاء حساب افتراضي
    cursor.execute('SELECT * FROM admins WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        # كلمة المرور الافتراضية هنا هي: Admin@12345 (يمكنك تغييرها لاحقاً)
        hashed_pw = generate_password_hash('Admin@12345')
        cursor.execute('INSERT INTO admins (username, password) VALUES (?, ?)', ('admin', hashed_pw))
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

# صفحة تسجيل الدخول الآمنة
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('nexac_system.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM admins WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        # التحقق من كلمة المرور المشفرة
        if row and check_password_hash(row[0], password):
            session['logged_in'] = True
            session['admin_user'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid Username or Password!'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# API استقبال التقارير من السكانر
@app.route('/api/report', methods=['POST'])
def receive_report():
    data = request.json
    username = data.get('username', 'Unknown')
    hwid = data.get('hwid', 'UNKNOWN_HWID')
    status = data.get('status', 'Clean')
    files_list = data.get('files', [])
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    files_json = json.dumps(files_list)

    conn = sqlite3.connect('nexac_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reports (username, hwid, status, files, timestamp) 
        VALUES (?, ?, ?, ?, ?)
    ''', (username, hwid, status, files_json, current_time))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'message': 'Report securely stored'})

# API إرسال التقارير للـ Dashboard (محمي)
@app.route('/api/get-reports', methods=['GET'])
def get_reports():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect('nexac_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, hwid, status, files, timestamp FROM reports ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    reports = []
    for row in rows:
        reports.append({
            'username': row[0],
            'hwid': row[1],
            'status': row[2],
            'files': json.loads(row[3]) if row[3] else [],
            'time': row[4]
        })

    return jsonify(reports)

from flask import send_from_directory

@app.route('/download')
def download_scanner():
    return send_from_directory('dist', 'nexac_scanner.exe', as_attachment=True)

# API مسح التقارير (محمي)
@app.route('/api/clear-reports', methods=['POST'])
def clear_reports():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect('nexac_system.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reports')
    conn.commit()
    conn.close()

    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)