from flask import Flask, request, redirect, session, jsonify
import requests
import os
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "random_secret_key")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "your_client_id")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "your_client_secret")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")
SCOPE = "user-library-read user-read-private"

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

@app.route("/")
def index():
    return "<h1>Spotify OAuth Demo</h1><a href='/login'>Login with Spotify</a>"

@app.route("/login")
def login():
    auth_query = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "client_id": CLIENT_ID
    }
    return redirect(f"{SPOTIFY_AUTH_URL}/?{urlencode(auth_query)}")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: No code received"

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=payload)
    response_data = response.json()

    session["access_token"] = response_data.get("access_token")
    return redirect("/profile")

@app.route("/profile")
def profile():
    token = session.get("access_token")
    if not token:
        return redirect("/login")

    headers = {"Authorization": f"Bearer {token}"}
    user_data = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers).json()
    return f"<h2>Welcome, {user_data.get('display_name')}</h2><pre>{user_data}</pre><a href='/'>Back to Home</a>"

if __name__ == "__main__":
    app.run(debug=True)