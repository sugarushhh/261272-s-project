import os
import re
import spotipy
from flask import Flask, render_template, request, redirect
from spotipy.oauth2 import SpotifyOAuth
from sklearn.neighbors import KNeighborsClassifier
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Spotify 配置
SPOTIPY_CLIENT_ID = "3395bd6dd71448e599805be8255c2437"
SPOTIPY_CLIENT_SECRET = "66431b32b0b04f078991a1486b5b9eb5"
SPOTIPY_REDIRECT_URI = "https://two61272-s-project.onrender.com/callback"

sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="user-library-read"
)

AUDIO_FEATURE_KEYS = [
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo"
]

trained_model = None

def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info["access_token"])

def get_audio_features(song_name):
    sp = get_spotify_client()
    if not sp:
        return None
    try:
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

def train_model(X, y):
    model = KNeighborsClassifier(n_neighbors=3)
    model.fit(X, y)
    return model

@app.route("/")
def home():
    return render_template("train.html")

@app.route("/train", methods=["POST"])
def train():
    global trained_model
    user_input = request.form["user_input"]
    X, y = parse_and_extract_features(user_input)

    if not X:
        return "❌ 无法获取歌曲特征，请确认歌曲名称拼写正确。"

    trained_model = train_model(X, y)
    return render_template("predict.html")

@app.route("/predict", methods=["POST"])
def predict():
    global trained_model
    song_name = request.form["song_name"]
    if not trained_model:
        return "⚠️ 模型尚未训练。请先返回主页进行训练。"

    features = get_audio_features(song_name)
    if features:
        pred = trained_model.predict([features])
        return render_template("predict.html", group=f"该歌曲属于用户组: 用户{chr(ord('A') + int(pred[0]))}")
    else:
        return render_template("predict.html", group="未找到该歌曲特征，请检查名称。")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    sp_oauth.get_access_token(code)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
