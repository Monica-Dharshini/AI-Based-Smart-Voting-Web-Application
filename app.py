from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
import os, smtplib, sqlite3, random
import face_recognition
import cv2
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = 'static/uploads'
KNOWN_FOLDER = 'known_faces'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(KNOWN_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ------------------- DB SETUP -------------------
def init_db():
    conn = sqlite3.connect('voters.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, age INTEGER, gender TEXT, email TEXT,
            aadhaar TEXT, voter_id TEXT, address TEXT,
            image_path TEXT, otp TEXT, has_voted INTEGER DEFAULT 0
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_name TEXT,
            votes INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ------------------- UTILS -------------------
def send_otp(email):
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login("techprosolutioncse@gmail.com", "panctgprzcgsdyht")
    s.sendmail("techprosolutioncse@gmail.com", email, f"Subject: Voting OTP\n\nYour OTP is: {otp}")
    s.quit()
    return otp

def verify_face(uploaded_img_path, name):
    known_img_path = os.path.join(KNOWN_FOLDER, name + '.jpg')
    if not os.path.exists(known_img_path):
        return False
    known_img = face_recognition.load_image_file(known_img_path)
    unknown_img = face_recognition.load_image_file(uploaded_img_path)
    try:
        known_encoding = face_recognition.face_encodings(known_img)[0]
        unknown_encoding = face_recognition.face_encodings(unknown_img)[0]
        results = face_recognition.compare_faces([known_encoding], unknown_encoding)
        return results[0]
    except IndexError:
        return False

# ------------------- ROUTES -------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        age = int(request.form['age'])
        if age < 18:
            return "Underage. Voting not allowed."

        gender = request.form['gender']
        email = request.form['email']
        aadhaar = request.form['aadhaar']
        voter_id = request.form['voter_id']
        address = request.form['address']
        file = request.files['image']
        filename = secure_filename(name + ".jpg")
        filepath = os.path.join(KNOWN_FOLDER, filename)
        file.save(filepath)

        conn = sqlite3.connect('voters.db')
        conn.execute('''INSERT INTO users (name, age, gender, email, aadhaar, voter_id, address, image_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (name, age, gender, email, aadhaar, voter_id, address, filepath))
        conn.commit()
        conn.close()
        return "Registered Successfully!"
    return render_template('register.html')

import base64

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        session['voter_name'] = name

        # Save captured base64 image
        img_data = request.form['live_image_data'].split(',')[1]
        img_bytes = base64.b64decode(img_data)
        filepath = os.path.join(UPLOAD_FOLDER, "live.jpg")
        with open(filepath, 'wb') as f:
            f.write(img_bytes)

        # Face verification
        if verify_face(filepath, name):
            conn = sqlite3.connect('voters.db')
            cur = conn.cursor()
            cur.execute("SELECT email FROM users WHERE name=?", (name,))
            user = cur.fetchone()
            if user:
                send_otp(user[0])
                return redirect(url_for('otp_verification'))
            return "Email not found"
        return "Face Not Recognized"
    return render_template('login.html')


@app.route('/face_verification', methods=['GET', 'POST'])
def face_verification():
    if request.method == 'POST':
        file = request.files['live_image']
        filename = secure_filename("live.jpg")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        name = session.get('voter_name')
        if verify_face(filepath, name):
            conn = sqlite3.connect('voters.db')
            cur = conn.cursor()
            cur.execute("SELECT email FROM users WHERE name=?", (name,))
            user = cur.fetchone()
            if user:
                send_otp(user[0])
                return redirect(url_for('otp_verification'))
        return "Face Not Recognized"
    return render_template('face_verification.html')

@app.route('/otp_verification', methods=['GET', 'POST'])
def otp_verification():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if entered_otp == session.get('otp'):
            return redirect(url_for('vote'))
        return "Invalid OTP"
    return render_template('otp_verification.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    name = session.get('voter_name')
    conn = sqlite3.connect('voters.db')
    cur = conn.cursor()
    cur.execute("SELECT has_voted FROM users WHERE name=?", (name,))
    user = cur.fetchone()
    if user[0] == 1:
        return "You have already voted."

    if request.method == 'POST':
        selected_party = request.form['party']
        cur.execute("UPDATE parties SET votes = votes + 1 WHERE party_name = ?", (selected_party,))
        cur.execute("UPDATE users SET has_voted = 1 WHERE name=?", (name,))
        conn.commit()
        conn.close()
        return "Vote Submitted Successfully!"
    cur.execute("SELECT party_name FROM parties")
    parties = cur.fetchall()
    return render_template('vote.html', parties=parties)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Admin Credentials", "danger")
    return render_template('admin_login.html')


@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == 'POST':
        party_name = request.form['party']
        conn = sqlite3.connect('voters.db')
        conn.execute("INSERT INTO parties (party_name) VALUES (?)", (party_name,))
        conn.commit()
        conn.close()
    conn = sqlite3.connect('voters.db')
    parties = conn.execute("SELECT party_name, votes FROM parties").fetchall()
    conn.close()
    return render_template('admin_dashboard.html', parties=parties)

if __name__ == "__main__":
    app.run(debug=True)
