from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import openai
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database
def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS moods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mood TEXT NOT NULL,
                description TEXT,
                intensity INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS wellness_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        conn.commit()

# Initialize OpenAI (replace with your API key)
openai.api_key = 'your-openai-api-key'

def get_ai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a compassionate AI therapist. Provide supportive, empathetic responses that encourage mental wellness. Keep responses professional but warm."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return "I'm having trouble responding right now. Please try again later."

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                return render_template('register.html', error="Username already exists")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user[0]
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_message = request.json.get('message')
        ai_response = get_ai_response(user_message)
        
        # Save conversation to database
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, user_message, ai_response) VALUES (?, ?, ?)",
                (session['user_id'], user_message, ai_response)
            )
            conn.commit()
        
        return jsonify({'response': ai_response})
    
    return render_template('chat.html')

@app.route('/moodtracker', methods=['GET', 'POST'])
def moodtracker():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mood = request.form['mood']
        description = request.form.get('description', '')
        intensity = request.form.get('intensity', 5)
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO moods (user_id, mood, description, intensity) VALUES (?, ?, ?, ?)",
                (session['user_id'], mood, description, intensity)
            )
            conn.commit()
        
        return redirect(url_for('moodtracker'))
    
    # Get mood history
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mood, description, intensity, created_at FROM moods WHERE user_id = ? ORDER BY created_at DESC",
            (session['user_id'],)
        )
        mood_history = cursor.fetchall()
    
    return render_template('moodtracker.html', mood_history=mood_history)

@app.route('/resources')
def resources():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    mental_health_resources = [
        {
            'title': 'National Suicide Prevention Lifeline',
            'description': '24/7 free and confidential support for people in distress',
            'phone': '1-800-273-8255',
            'url': 'https://suicidepreventionlifeline.org'
        },
        {
            'title': 'Crisis Text Line',
            'description': 'Text HOME to 741741 for free, 24/7 crisis counseling',
            'phone': 'Text HOME to 741741',
            'url': 'https://www.crisistextline.org'
        },
        {
            'title': 'NAMI Helpline',
            'description': 'National Alliance on Mental Illness information and support',
            'phone': '1-800-950-NAMI (6264)',
            'url': 'https://www.nami.org'
        },
        {
            'title': 'Mindfulness Exercises',
            'description': 'Free guided mindfulness and meditation exercises',
            'url': 'https://www.mindful.org/free-mindfulness-resources/'
        },
        {
            'title': '7 Cups',
            'description': 'Free online therapy and counseling with trained listeners',
            'url': 'https://www.7cups.com'
        }
    ]
    
    return render_template('resources.html', resources=mental_health_resources)

@app.route('/wellness')
def wellness():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate or fetch wellness plan
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        
        # Check if we have a recent wellness plan
        cursor.execute(
            "SELECT plan_text FROM wellness_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (session['user_id'],)
        )
        plan = cursor.fetchone()
        
        if not plan:
            # Generate a new wellness plan based on mood history
            cursor.execute(
                "SELECT mood, description FROM moods WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
                (session['user_id'],)
            )
            moods = cursor.fetchall()
            
            if moods:
                mood_summary = "\n".join([f"Mood: {m[0]}, Note: {m[1]}" for m in moods])
                prompt = f"Based on the following mood history:\n{mood_summary}\n\nCreate a personalized 7-day wellness plan with daily activities, coping strategies, and self-care suggestions. Format it clearly with days of the week."
                plan_text = get_ai_response(prompt)
                
                # Save the new plan
                cursor.execute(
                    "INSERT INTO wellness_plans (user_id, plan_text) VALUES (?, ?)",
                    (session['user_id'], plan_text)
                )
                conn.commit()
            else:
                plan_text = "Track your moods for a few days to generate a personalized wellness plan."
        else:
            plan_text = plan[0]
    
    return render_template('wellness.html', wellness_plan=plan_text)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)