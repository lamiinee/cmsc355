from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
from openai import OpenAI
from datetime import datetime
import os
import random 
import requests
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

class MoodTracker:
    def __init__(self):
        # Dictionary to store mood entries {user_id: [mood_entries]}
        self.mood_history = {}
        # Sample wellness activities
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
        """Add a new mood entry for a user"""
        if user_id not in self.mood_history:
            self.mood_history[user_id] = []
            
        entry = {
            'mood': mood,
            'intensity': intensity,
            'description': description,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.mood_history[user_id].append(entry)
        return entry
    
    def get_mood_history(self, user_id):
        """Get all mood entries for a user"""
        return self.mood_history.get(user_id, [])
    
    def generate_wellness_plan(self, user_id):
        """Generate a personalized wellness plan based on mood history"""
        history = self.get_mood_history(user_id)
        if not history:
            return "Track your moods for a few days to generate a personalized wellness plan."
        
        # Analyze recent moods
        recent_moods = [entry['mood'] for entry in history[-7:]]  # Last 7 entries
        mood_counts = {mood: recent_moods.count(mood) for mood in recent_moods}
        
        # Generate plan based on most common moods
        plan = "Your Personalized 7-Day Wellness Plan:\n\n"
        for day in range(1, 8):
            # Select a mood to focus on (either most common or random from recent)
            focus_mood = max(mood_counts, key=mood_counts.get) if mood_counts else random.choice(list(self.wellness_activities.keys()))
            
            # Get 3 random activities for this mood
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

# Initialize OpenAI (replace with your API key)
OpenAI.api_key = 'your-openai-api-key'

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
        "model": "nvidia/llama-3.1-nemotron-nano-8b-v1:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a compassionate and empathetic AI therapist. "
                    "Your goal is to provide supportive, thoughtful responses and help users feel heard. "
                    "Please be mindful that you are not a substitute for professional mental health advice."
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
        intensity = int(request.form.get('intensity', 5))
        description = request.form.get('description', '')
        
        # Add to mood tracker
        mood_tracker.add_mood_entry(session['user_id'], mood, intensity, description)
        return redirect(url_for('moodtracker'))
    
    # Get mood history
    mood_history = mood_tracker.get_mood_history(session['user_id'])
    return render_template('moodtracker.html', mood_history=mood_history)

@app.route('/wellness')
def wellness():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    wellness_plan = mood_tracker.generate_wellness_plan(session['user_id'])
    return render_template('wellness.html', wellness_plan=wellness_plan)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

    # raym5@vcu.edu 