from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import sqlite3
from datetime import datetime
import os
import random 
import requests
import json

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)

# Define the set of tables for use in deletion functions.
__tables = {"moods", "users", "chat_history", "wellness_plans"}

class MoodTracker:
    """
    A class for managing mood entries and generating a personalized wellness plan.
    
    This class stores a collection of sample wellness activities for each mood and 
    provides methods to add a mood entry, retrieve a user's mood history, and generate a 7-day wellness plan.
    """
    def __init__(self):
        """
        Initializes the MoodTracker with predefined wellness activities.
        """
        self.wellness_activities = {
            'Happy': ["Go for a walk in nature", "Share your joy with someone", "Start a gratitude journal", "Keep it up!"],
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
        """
        Adds a new mood entry to the database.

        Parameters:
            user_id (int): The ID of the user.
            mood (str): The mood being recorded.
            intensity (int): The intensity of the mood.
            description (str): (Optional) Additional notes about the mood.

        Returns:
            dict: A dictionary containing the details of the inserted mood entry.
        """
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
        """
        Retrieves the mood history for a given user.

        Parameters:
            user_id (int): The ID of the user whose mood history is needed.

        Returns:
            list: A list of mood entries, where each entry is represented as a dictionary.
        """
        with sqlite3.connect('database.db') as conn:
            conn.row_factory = sqlite3.Row
            history = conn.execute(
                'SELECT mood, intensity, description, created_at FROM moods WHERE user_id = ? ORDER BY created_at ASC',
                (user_id,)
            ).fetchall()
        return [dict(entry) for entry in history]

    def generate_wellness_plan(self, user_id):
        """
        Generates a personalized 7-Day Wellness Plan based on the user's recent mood history.

        The plan is built by analyzing the most recent mood entries and then creating a plan with
        a diverse set of daily focuses and associated wellness activities.

        Parameters:
            user_id (int): The ID of the user.

        Returns:
            str: A formatted wellness plan.
        """
        history = self.get_mood_history(user_id)
        if not history:
            return "Track your moods for a few days to generate a personalized wellness plan."
        
        # Analyze recent moods (last 7 entries)
        recent_moods = [entry['mood'] for entry in history[-7:]]
        mood_counts = {mood: recent_moods.count(mood) for mood in set(recent_moods)}
        
        plan = "Your Personalized 7-Day Wellness Plan:\n\n"
        plan_foci = []  # to track each day's focus
        
        # Build lists for weighted random selection
        available_moods = list(mood_counts.keys())
        weights = [mood_counts[m] for m in available_moods]
        
        for day in range(1, 8):
            if available_moods:
                if day == 1:
                    focus_mood = random.choices(available_moods, weights=weights, k=1)[0]
                else:
                    # Filter out the previous day's focus from the candidate moods
                    candidates = []
                    candidate_weights = []
                    for mood, weight in zip(available_moods, weights):
                        if mood != plan_foci[-1]:
                            candidates.append(mood)
                            candidate_weights.append(weight)
                    if candidates:
                        focus_mood = random.choices(candidates, weights=candidate_weights, k=1)[0]
                    else:
                        focus_mood = plan_foci[-1]
            else:
                # If no mood data is available, choose a random activity from the default set
                focus_mood = random.choice(list(self.wellness_activities.keys()))
            
            plan_foci.append(focus_mood)
            # Select 3 random activities for the day's focus mood
            activities = random.sample(self.wellness_activities[focus_mood], 3)
            plan += f"Day {day} - Focus: {focus_mood}\n"
            plan += f"1. {activities[0]}\n"
            plan += f"2. {activities[1]}\n"
            plan += f"3. {activities[2]}\n\n"
        
        return plan

# Create an instance of MoodTracker for use in routes
mood_tracker = MoodTracker()

def init_db():
    """
    Initializes the database by creating necessary tables if they do not already exist.
    
    Tables created:
        - users: Stores user credentials and metadata.
        - moods: Records user mood entries.
        - chat_history: Stores the conversation history between the user and the AI.
        - wellness_plans: Stores generated wellness plans.
    """
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                isAdmin INTEGER DEFAULT 0,
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

def __get_db_connection():
    """
    Returns a new connection to the SQLite database with the row_factory set to access columns by name.

    Returns:
        sqlite3.Connection: The database connection.
    """
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_chat_history(user_id, limit=10):
    """
    Retrieves the most recent chat messages for the specified user.

    Parameters:
        user_id (int): The ID of the user.
        limit (int): The maximum number of messages to retrieve (default is 10).

    Returns:
        list: A list of messages formatted as dictionaries with "role" and "content" keys.
    """
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        history = conn.execute(
            'SELECT user_message, ai_response FROM chat_history WHERE user_id = ? ORDER BY created_at ASC LIMIT ?',
            (user_id, limit)
        ).fetchall()
    messages = []
    for entry in history:
        messages.append({"role": "user", "content": entry["user_message"]})
        messages.append({"role": "assistant", "content": entry["ai_response"]})
    return messages

def get_ai_response(prompt, conversation_context=None):
    """
    Sends a prompt and (optionally) conversation history to the AI API and returns the AI's response.

    Parameters:
        prompt (str): The user's new message.
        conversation_context (list): (Optional) A list of previous messages for context.

    Returns:
        str: The response generated by the AI.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    # Begin the conversation with a system message defining the AI's role.
    messages = [{
        "role": "system",
        "content": (
            "You are a compassionate and empathetic AI therapist. "
            "Your goal is to provide supportive, thoughtful responses and help users feel heard. "
            "Please be mindful that you are not a substitute for professional mental health advice."
        )
    }]
    
    if conversation_context:
        messages.extend(conversation_context)
    
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "google/gemini-2.5-pro-exp-03-25:free",
        "messages": messages
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code != 200:
        raise Exception(f"Request failed with status {response.status_code}: {response.text}")
    
    response_json = response.json()
    
    try:
        ai_message = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise Exception("Unexpected response structure: " + json.dumps(response_json, indent=2))
    
    return ai_message

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """
    Handles the chat functionality with the AI therapist.
    
    GET: Renders the chat interface.
    POST: Processes the user's chat input, retrieves previous conversation history, sends the data to the AI,
          saves the exchange in the database, and returns the AI response as JSON.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_message = request.json.get('message')
        conversation_context = get_chat_history(session['user_id'], limit=4)
        ai_response = get_ai_response(user_message, conversation_context)
        
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
    """
    Renders the home page for users who are not logged in; otherwise, redirects logged-in users to the dashboard.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

def __get_all_users():
    """
    Retrieves all users from the database.

    Returns:
        list: A list of dictionaries, each representing a user row from the 'users' table.
    """
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT * FROM users').fetchall()
    return [dict(row) for row in rows]

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    if 'user_id' in session:
        user_data = __get_all_from_db("users", "id");
        isAdmin = user_data[0]['isAdmin']
        if isAdmin == 0:
            return redirect(url_for('home'))

    all_users = __get_all_users()    

    return render_template('admin.html', all_users=all_users)
 
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Manages user registration.
    
    GET: Renders the registration form.
    POST: Processes form data, attempts to create a new user, and redirects to the login page on success.
    """
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
    """
    Manages user login.
    
    GET: Renders the login form.
    POST: Verifies user credentials and initiates a session if valid, then redirects to the dashboard.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, isAdmin FROM users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()
            
            if user is None:
                return render_template('login.html', error="Invalid username or password")
            user_id = user[0]
            if user:
                session['user_id'] = user_id
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """
    Logs out the current user by clearing their session and redirecting to the home page.
    """
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/account', methods=['GET', 'POST'])
def account():
    """
    Manages account settings for the logged-in user.
    
    GET: Renders the account page displaying current user data.
    POST: Updates the user's username and/or password and redirects back to the account page.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_data = __get_all_from_db("users", "id")

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            try:
                if username:
                    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (username, session['user_id']))
                if password:
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (password, session['user_id']))
                conn.commit()
            except sqlite3.IntegrityError:
                return render_template('account.html', user_data=user_data, error="Username already exists")

        return redirect(url_for('account'))
    
    return render_template('account.html', user_data=user_data)

def __delete_all_data():
    """
    Deletes all data associated with the current user from all tables except the 'users' table.
    
    Iterates through the defined __tables and executes a DELETE command on each,
    using the session's user_id as the filter.
    """
    for table in __tables:
        if table != "users":
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                query = f"DELETE FROM {table} WHERE user_id = ?"
                cursor.execute(query, (session['user_id'],))
                conn.commit()

@app.route('/remove_user_data', methods=['POST'])
def remove_user_data():
    """
    Endpoint for removing all data associated with the current user (except the user account itself).
    
    After deletion, the user is redirected back to the account page.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    __delete_all_data()
    return redirect(url_for('account'))

def __delete_account(id: int):
    """
    Deletes the current user's account from the 'users' table.
    """
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        query = "DELETE FROM users WHERE id = ?"
        cursor.execute(query, (id,))
        conn.commit()

@app.route('/remove_user_account', methods=['POST'])
def remove_user_account():
    """
    Endpoint for deleting the current user's account.
    
    Upon deletion, the user session is cleared and the user is redirected to the home page.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    target_id = request.form.get('target_user_id')
    if not target_id:
        flash("No user specified.", "danger")
        return redirect(url_for('dashboard'))
    
    
    user_data = __get_all_from_db("users", "id");
    isAdmin = user_data[0]['isAdmin']
    __delete_account(target_id)
    if isAdmin:
        return redirect(url_for('admin'))
    session.pop('user_id', None)
    return redirect(url_for('home'))

def __get_all_from_db(table: str, user_col: str = 'user_id', data_col: str = '*'):
    """
    Retrieves all rows from the specified table for the current user.

    Parameters:
        table (str): The name of the database table.
        user_col (str): The column that stores the user identifier (default is 'user_id').

    Returns:
        list: A list of rows (each as a dictionary) ordered by created_at in descending order.
    """
    conn = __get_db_connection()
    query = f"SELECT {data_col} FROM {table} WHERE {user_col} = ? ORDER BY created_at DESC"
    ret = conn.execute(query, (session['user_id'],)).fetchall()
    conn.close()
    return ret

@app.route('/dashboard')
def dashboard():
    """
    Renders the dashboard for the logged-in user.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    isAdmin = __get_all_from_db("users","id", "isAdmin")[0]['isAdmin']
    if isAdmin:
            return render_template('dashboard.html', isAdmin=isAdmin)

    return render_template('dashboard.html')

@app.route('/resources')
def resources():
    """
    Renders a mental health resources page with a list of available resources.

    Requires the user to be logged in.
    """
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
        },
        {
            'title': 'VCU Student Health',
            'description': 'VCU student mental health resources',
            'url': 'https://health.students.vcu.edu/patient-resources/mental-health/'
        },
        {
            'title': 'University Counseling Services (UCS)',
            'description': 'Free individual, group, and couple\'s therapy services to VCU students.',
            'phone': '1-804-828-6200',
            'url': 'https://counseling.vcu.edu/'
        }
    ]
    
    return render_template('resources.html', resources=mental_health_resources)

@app.route('/moodtracker', methods=['GET', 'POST'])
def moodtracker():
    """
    Handles mood tracking functionalities.

    GET: Fetches and displays the user's mood history.
    POST: Inserts a new mood entry based on form input and displays a success message.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mood = request.form['mood']
        intensity = request.form['intensity']
        description = request.form.get('description', '')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = __get_db_connection()
        conn.execute(
            '''INSERT INTO moods (user_id, mood, description, intensity, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (session['user_id'], mood, description, intensity, timestamp)
        )
        conn.commit()
        conn.close()

        flash('Mood recorded successfully!', 'success')
        return redirect(url_for('moodtracker'))

    conn = __get_db_connection()
    mood_history = conn.execute(
        'SELECT * FROM moods WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('moodtracker.html', mood_history=mood_history)

@app.route('/wellness')
def wellness():
    """
    Generates and renders a personalized 7-day wellness plan based on the user's mood history.

    Requires the user to be logged in.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    wellness_plan = mood_tracker.generate_wellness_plan(session['user_id'])
    return render_template('wellness.html', wellness_plan=wellness_plan) 

def makeAdmin(username, password):
    with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, isAdmin) VALUES (?, ?, ?)", (username, password, 1))
            conn.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
