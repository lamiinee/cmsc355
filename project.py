from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import sqlite3
from openai import OpenAI
from datetime import datetime
import os
import random 
import requests
import json

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)

# Removed Dictionary, fixed database
# all mood data is stored in the database.
class MoodTracker:
    def __init__(self):
        self.wellness_activities = {
            'Happy': ["Go for a walk in nature", "Share your joy with someone", "Start a gratitude journal"],
            'Sad': ["Practice self-compassion", "Listen to uplifting music", "Reach out to a friend"],
            'Angry': ["Try deep breathing exercises", "Go for a run", "Write down your feelings"],
            'Anxious': ["Practice 4-7-8 breathing", "Do a grounding exercise", "Try progressive muscle relaxation"],
            'Stressed': ["Take a warm bath", "Do some yoga", "Practice mindfulness meditation"],
            'Calm': ["Enjoy a cup of tea", "Read a book", "Do some light stretching"],
            'Excited': ["Channel energy into a creative project", "Plan something fun", "Share your excitement with others"],
            'Tired': ["Take a power nap", "Drink some water", "Do some gentle movement"],
            'Neutral': ["Try something new", "Check in with yourself", "Plan your next wellness activity"]
        }

    def add_mood_entry(self, user_id, mood, intensity, description=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect('database.db') as conn:
            conn.execute(
                '''INSERT INTO moods (user_id, mood, description, intensity, created_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, mood, description, intensity, timestamp)
            )
            conn.commit()
        return {
            'user_id': user_id,
            'mood': mood,
            'description': description,
            'intensity': intensity,
            'timestamp': timestamp
        }

    def get_mood_history(self, user_id):
        with sqlite3.connect('database.db') as conn:
            conn.row_factory = sqlite3.Row
            history = conn.execute(
                'SELECT mood, intensity, description, created_at FROM moods WHERE user_id = ? ORDER BY created_at ASC',
                (user_id,)
            ).fetchall()
        return [dict(entry) for entry in history]

    def generate_wellness_plan(self, user_id):
        """Generate a personalized 7-Day Wellness Plan using diverse focuses per day."""
        history = self.get_mood_history(user_id)
        if not history:
            return "Track your moods for a few days to generate a personalized wellness plan."
        
        # Analyze recent moods (last 7 entries)
        recent_moods = [entry['mood'] for entry in history[-7:]]
        # count each mood in the last 7 entries
        mood_counts = {mood: recent_moods.count(mood) for mood in set(recent_moods)}
        
        plan = "Your Personalized 7-Day Wellness Plan:\n\n"
        plan_foci = []  # to keep track of each day's focus
        
        #lists for weighted random selection
        available_moods = list(mood_counts.keys())
        weights = [mood_counts[m] for m in available_moods]
        
        for day in range(1, 8):
            if available_moods:
                # For day 1, choose using weighted random selection
                if day == 1:
                    focus_mood = random.choices(available_moods, weights=weights, k=1)[0]
                else:
                    #filter out the previous focus from choice candidates.
                    candidates = []
                    candidate_weights = []
                    for mood, weight in zip(available_moods, weights):
                        if mood != plan_foci[-1]:
                            candidates.append(mood)
                            candidate_weights.append(weight)
                    if candidates:
                        focus_mood = random.choices(candidates, weights=candidate_weights, k=1)[0]
                    else:
                        #if (only one mood available), choose that mood.
                        focus_mood = plan_foci[-1]
            else:
                #if mood_counts is empty, choose any random mood from wellness activities.
                focus_mood = random.choice(list(self.wellness_activities.keys()))
            
            plan_foci.append(focus_mood)
            # 3 random wellness activities for the focus mood.
            activities = random.sample(self.wellness_activities[focus_mood], 3)
            
            plan += f"Day {day} - Focus: {focus_mood}\n"
            plan += f"1. {activities[0]}\n"
            plan += f"2. {activities[1]}\n"
            plan += f"3. {activities[2]}\n\n"
        
        return plan
mood_tracker =  MoodTracker()

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

# Helper function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # So we can access columns by name in the templates
    return conn


def get_ai_response(prompt):
    # Set your API endpoint
    url = "https://openrouter.ai/api/v1/chat/completions"
    # Be sure to secure your API key properly; do not hard-code it in production.
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    # Prepare a conversation including a system message to define the AI's role
    payload = {
        "model": "meta-llama/llama-4-scout:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a compassionate and empathetic AI therapist. "
                    "Your goal is to provide supportive, thoughtful responses and help users feel heard. "
                    "Please be mindful that you are not a substitute for professional mental health advice."
                    "Try to keep messages realively short and sweet."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code != 200:
        raise Exception(f"Request failed with status {response.status_code}: {response.text}")
    
    # Parse the returned JSON response
    response_json = response.json()
    
    # Extract the AI response text from the first choice in the response.
    # Adjust the extraction if your API response structure differs.
    try:
        ai_message = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise Exception("Unexpected response structure: " + json.dumps(response_json, indent=2))
    
    return ai_message


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


@app.route('/moodtracker', methods=['GET', 'POST'])
def moodtracker():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mood = request.form['mood']
        intensity = request.form['intensity']
        description = request.form.get('description', '')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Insert the mood into the moods table in your database.
        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO moods (user_id, mood, description, intensity, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (session['user_id'], mood, description, intensity, timestamp)
        )
        conn.commit()
        conn.close()

        flash('Mood recorded successfully!', 'success')
        return redirect(url_for('moodtracker'))

    # For GET method, fetch the user's mood history
    conn = get_db_connection()
    mood_history = conn.execute(
        'SELECT * FROM moods WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    # Pass the mood_history data to your Jinja2 template.
    return render_template('moodtracker.html', mood_history=mood_history)


@app.route('/wellness')
def wellness():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # wellness plan using the database
    wellness_plan = mood_tracker.generate_wellness_plan(session['user_id'])
    return render_template('wellness.html', wellness_plan=wellness_plan)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
