from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import openai
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
openai.api_key = 'your_openai_api_key'

def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            );
            CREATE TABLE IF NOT EXISTS moods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mood TEXT,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return redirect(url_for('home'))
        except:
            return 'Username already exists!'

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials!'

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('dashboard.html')

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    user_input = request.json['message']
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': user_input}]
    )
    return jsonify({'response': response['choices'][0]['message']['content']})

@app.route('/mood', methods=['POST'])
def mood_tracker():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    mood = request.form['mood']
    description = request.form['description']
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO moods (user_id, mood, description) VALUES (?, ?, ?)", (session['user_id'], mood, description))
        conn.commit()
    return redirect(url_for('dashboard'))

# Frontend templates
@app.route('/templates/index.html')
def index_page():
    return '''
        <!DOCTYPE html>
            <html>
            <head>
                <title>AI Therapist</title>
                <link rel="stylesheet" href="styles.css">
            </head>
            <body>
                <h2>Welcome to AI Therapist Chatbot</h2>
                <form action="/register" method="post">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Register</button>
                </form>
                <form action="/login" method="post">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
            </body>
            </html>
    '''

@app.route('/templates/dashboard.html')
def dashboard_page():
    return '''
        <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard</title>
        <link rel="stylesheet" href="styles.css">
    </head>
    <body>
        <h2>Dashboard</h2>
        <form id="chat-form">
            <input type="text" id="user-input" placeholder="Type your message">
            <button type="submit">Send</button>
        </form>
        <div id="chat-response"></div>
        <script>
            document.getElementById("chat-form").onsubmit = async function(event) {
                event.preventDefault();
                let userInput = document.getElementById("user-input").value;
                let response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: userInput })
                });
                let data = await response.json();
                document.getElementById("chat-response").innerText = data.response;
            };
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
