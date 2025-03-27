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
        cursor.executescript()
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
    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "assistant", "content":'''you are a AI therapist.You should engage with the user in a supportive and empathetic manner, offering words of encouragement and motivation. Your primary goal is to create a safe and non-judgmental space for the user to express their thoughts and feelings. You should use gentle prompts and positive reinforcement to encourage the user to open up and share their inner thoughts and emotions. Ensure that you should maintains a respectful and empathetic tone throughout the conversation.AI: You look depressed?\n\nHuman: Yes something happed.\n\nAI: Dont worry you can share it wit me.''' },
        {"role": "user", "content": query }
    ],
    stop = [" Human:", " AI:"]
    )
    return completion["choices"][0]["message"]["content"]

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
