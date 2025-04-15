import os
import random
import sqlite3
import pytest
import json
from project import app, init_db  # Adjust the import if your file name is different

# Fixture to set up a test client and initialize a fresh database for testing.
@pytest.fixture
def client():
    # Configure app for testing
    app.config['TESTING'] = True
    # Use a temporary database file for tests if you prefer; here we simply reinitialize the current db.
    with app.test_client() as client:
        # Within the app context, initialize the database.
        with app.app_context():
            init_db()
        yield client

def register(client, username, password):
    """Helper function to register a new user."""
    return client.post(
        '/register',
        data={'username': username, 'password': password},
        follow_redirects=True
    )

def login(client, username, password):
    """Helper function to log in."""
    return client.post(
        '/login',
        data={'username': username, 'password': password},
        follow_redirects=True
    )

def test_register_and_login(client):
    # Test user registration.
    response = register(client, 'testuser', 'testpass')
    # Registration should redirect to login. Check for a sign of the login template.
    assert b'Login' in response.data or b'login' in response.data

    # Now try logging in.
    response = login(client, 'testuser', 'testpass')
    # After successful login, the dashboard should be rendered.
    # You may check for keywords in your dashboard page.
    assert b'dashboard' in response.data.lower() or b'Welcome' in response.data

def test_redirect_protected_routes(client):
    # For a user not logged in, ensure protected routes redirect to /login.
    protected_routes = ['/dashboard', '/moodtracker', '/wellness', '/chat']
    for route in protected_routes:
        response = client.get(route, follow_redirects=False)
        # Expect a redirect (HTTP status code 302 or 301)
        assert response.status_code in (301, 302)
        # The Location header should include '/login'.
        assert '/login' in response.headers['Location']

def test_moodtracker_post(client):
    # Create and log in a test user.
    register(client, 'testuser2', 'testpass')
    login(client, 'testuser2', 'testpass')

    # Post a mood entry.
    response = client.post(
        '/moodtracker',
        data={
            'mood': 'Happy',
            'intensity': '7',
            'description': 'Feeling good!'
        },
        follow_redirects=True
    )
    # Check that a flash message indicates the mood was recorded successfully.
    assert b'Mood recorded successfully!' in response.data

def test_wellness_plan_generation(client):
    # Create and log in a test user.
    register(client, 'testuser3', 'testpass')
    login(client, 'testuser3', 'testpass')

    # Add several mood entries.
    moods = ['Happy', 'Sad', 'Angry', 'Calm', 'Happy', 'Neutral', 'Excited']
    for mood in moods:
        client.post(
            '/moodtracker',
            data={
                'mood': mood,
                'intensity': str(random.randint(1, 10)),
                'description': f'{mood} mood'
            },
            follow_redirects=True
        )
    # Generate the wellness plan.
    response = client.get('/wellness')
    assert response.status_code == 200
    # Check that the generated plan includes the expected header.
    assert b'Your Personalized 7-Day Wellness Plan:' in response.data

def test_chat_route_anonymous(client):
    # Attempt to use the chat route without logging in.
    response = client.post('/chat', json={'message': 'Hello'}, follow_redirects=False)
    # Without login, it should redirect (or return a 302) to login.
    # Some routes may return JSON errors; adjust the assertion if needed.
    assert response.status_code in (301, 302)
    assert '/login' in response.headers['Location']

def test_chat_route_authenticated(client):
    # Register and log in.
    register(client, 'testuser4', 'testpass')
    login(client, 'testuser4', 'testpass')

    # Post a message to the chat route.
    response = client.post('/chat', json={'message': 'Hello, how are you?'})
    # Expect a JSON response that contains the AI reply.
    data = json.loads(response.data)
    assert 'response' in data
    # You might check that the AI response is a string.
    assert isinstance(data['response'], str)
