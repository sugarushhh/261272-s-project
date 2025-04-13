import os
import spotipy
from flask import Flask, render_template, request, redirect
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from sklearn.neighbors import KNeighborsClassifier
import re

# 加载 .env 中的环境变量
load_dotenv()

app = Flask(__name__)

# Spotify 授权配置
sp_oauth = SpotifyOAuth(
    client_id="3395bd6dd71448e599805be8255c2437",
    client_secret="66431b32b0b04f078991a1486b5b9eb5",
    redirect_uri="https://two61272-s-project.onrender.com/callback",
    scope="user-library-read"
)

# 训练好的模型全局变量
trained_model = None

# 音频特征字段
AUDIO_FEATURE_KEYS = [
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo"
]

# 获取 Spotify 客户端
def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info["access_token"])

# 获取歌曲音频特征
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
        return [features[key] for key in AUDIO_FEATURE_KEYS] if features else None
    except Exception as e:
        print(f"❌ 获取特征出错: {e}")
        return None

# 提取训练数据
def parse_and_extract_features(input_str):
    user_groups = re.split(r"\s*/\s*", input_str.strip())
    X, y = [], []
    for idx, group in enumerate(user_groups):
        songs = re.split(r"\s*,\s*|\s+", group.strip())
        for song in songs:
            features = get_audio_features(song)
            if features:
                X.append(features)
                y.append(idx)
    return X, y

# 训练模型
def train_model(X, y):
    model = KNeighborsClassifier(n_neighbors=3)
    model.fit(X, y)
    return model

# 首页：输入训练歌曲
@app.route("/", methods=["GET"])
def index():
    return render_template("train.html")

# 训练模型页面
@app.route("/train", methods=["GET", "POST"])
def train():
    global trained_model
    if request.method == "GET":
        return redirect("/")
    user_input = request.form["user_input"]
    X, y = parse_and_extract_features(user_input)
    if not X:
        return "❌ 无法提取歌曲特征，请检查歌曲名称是否拼写正确。"
    trained_model = train_model(X, y)
    return render_template("predict.html")

# 预测页面
@app.route("/predict", methods=["GET", "POST"])
def predict():
    global trained_model
    if request.method == "GET":
        return render_template("predict.html")
    song_name = request.form["song_name"]
    if not trained_model:
        return "⚠️ 模型尚未训练。请先返回主页进行训练。"
    features = get_audio_features(song_name)
    if features:
        pred = trained_model.predict([features])
        return render_template("predict.html", group=f"该歌曲属于用户组：用户{chr(ord('A') + int(pred[0]))}")
    else:
        return render_template("predict.html", group="⚠️ 未找到该歌曲特征，请检查拼写。")

# Spotify 授权回调
@app.route("/callback")
def callback():
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    return redirect("/")
    
# 运行
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
