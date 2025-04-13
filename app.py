import os
import spotipy
from flask import Flask, render_template, request, redirect
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from sklearn.neighbors import KNeighborsClassifier
import re

load_dotenv()

app = Flask(__name__)

SPOTIPY_CLIENT_ID = "3395bd6dd71448e599805be8255c2437"
SPOTIPY_CLIENT_SECRET = "66431b32b0b04f078991a1486b5b9eb5"
SPOTIPY_REDIRECT_URI = "https://two61272-s-project.onrender.com/callback"

sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                         client_secret=SPOTIPY_CLIENT_SECRET,
                         redirect_uri=SPOTIPY_REDIRECT_URI,
                         scope="user-library-read")

AUDIO_FEATURE_KEYS = [
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo"
]

model = None

def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info["access_token"])

def get_audio_features(song_name):
    try:
        sp = get_spotify_client()
        if not sp:
            return None
        results = sp.search(q=song_name, type='track', limit=1)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            return None
        track_id = tracks[0]["id"]
        features = sp.audio_features([track_id])[0]
        if features:
            return [features[key] for key in AUDIO_FEATURE_KEYS]
    except:
        return None
    return None

def parse_and_extract_features(input_str):
    user_groups = re.split(r"\s*/\s*", input_str.strip())
    all_features = []
    labels = []
    for idx, group in enumerate(user_groups):
        songs = re.split(r"\s*,\s*|\s+", group.strip())
        for song in songs:
            feats = get_audio_features(song)
            if feats:
                all_features.append(feats)
                labels.append(idx)
    return all_features, labels

@app.route("/", methods=["GET", "POST"])
def train():
    global model
    if request.method == "POST":
        user_input = request.form["user_input"]
        X, y = parse_and_extract_features(user_input)
        model = KNeighborsClassifier(n_neighbors=3)
        model.fit(X, y)
        return render_template("predict.html")
    return render_template("train.html")

@app.route("/predict", methods=["POST"])
def predict():
    global model
    song_name = request.form["song_name"]
    if not model:
        return "模型未训练"
    features = get_audio_features(song_name)
    if features:
        group = model.predict([features])[0]
        return render_template("predict.html", group=int(group))
    return render_template("predict.html", group=None)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))