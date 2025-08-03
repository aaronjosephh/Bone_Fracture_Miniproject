from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import sqlite3
import os
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from predictions import predict 

app = Flask(__name__)
#app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, 'processed')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Serve processed heatmap images
@app.route('/uploads/processed/<filename>')
def serve_heatmap(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)

#Database Initialization
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            bone_type TEXT,
            fracture_result TEXT,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('index.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/upload')
def upload_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('upload.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        username, password = data.get('username'), data.get('password')

        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400
        if len(password) < 8:
            return jsonify({'message': 'Password too short'}), 400

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'message': 'Username already exists'}), 400

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        return jsonify({'message': 'User registered successfully'})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username, password = data.get('username'), data.get('password')

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return jsonify({'message': 'Login successful', 'redirect': '/upload'})
        return jsonify({'message': 'Invalid login credentials'}), 401

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user' not in session:
        return jsonify({'message': 'Unauthorized access'}), 403

    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    username = session['user']

    #Bone Type Classification
    bone_type = predict(filepath, "Parts")

    #Fracture Prediction
    fracture_result = predict(filepath, bone_type) if bone_type in ["Elbow", "Hand", "Shoulder"] else "Unknown"

    heatmap_filename = None

    # Generate Heatmap if Fractured
    if fracture_result == 'fractured':
        heatmap_filename = f"heatmap_{filename}"
        heatmap_path = os.path.join(PROCESSED_FOLDER, heatmap_filename)

        # Load Image
        image_gray = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        image_color = cv2.imread(filepath)

        # Contrast Enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        image_gray = clahe.apply(image_gray)
        blurred = cv2.medianBlur(image_gray, 5)

        # HoughCircles for Fracture Detection
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.3, minDist=8,
            param1=50, param2=30, minRadius=5, maxRadius=25
        )

        # Heatmap Processing
        heatmap = np.zeros_like(image_gray, dtype=np.float32)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for circle in circles[0, :]:
                x, y, r = circle
                cv2.circle(heatmap, (x, y), r, 255, -1)
                cv2.GaussianBlur(heatmap, (15, 15), 10, dst=heatmap)

        heatmap = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

        overlay = cv2.addWeighted(image_color, 0.7, heatmap, 0.3, 0)
        cv2.imwrite(heatmap_path, overlay)

    #  Store Prediction in Database (Re-added)
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO results (username, bone_type, fracture_result) VALUES (?, ?, ?)", 
                       (username, bone_type, 'Fractured' if fracture_result == 'fractured' else 'Normal'))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Database Insert Error:", str(e))

    return jsonify({
        'bone_type': bone_type,
        'result': 'Fractured' if fracture_result == 'fractured' else 'Normal',
        'heatmap_image': url_for('serve_heatmap', filename=heatmap_filename) if heatmap_filename else None
    })

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'message': 'Logged out successfully'})

if __name__ == '__main__':
    app.run(debug=True)
