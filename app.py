import os
import spotipy
from flask import Flask, render_template, request, redirect, url_for
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Flask 配置
app = Flask(__name__)

# Spotify API 配置
SPOTIPY_CLIENT_ID = "3395bd6dd71448e599805be8255c2437"  # 你的 client_id
SPOTIPY_CLIENT_SECRET = "66431b32b0b04f078991a1486b5b9eb5"  # 你的 client_secret
SPOTIPY_REDIRECT_URI = "https://two61272-s-project.onrender.com/callback"  # 更新后的重定向 URI

# Spotify OAuth 设置
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                         client_secret=SPOTIPY_CLIENT_SECRET,
                         redirect_uri=SPOTIPY_REDIRECT_URI,
                         scope="user-library-read")

# 音频特征字段
AUDIO_FEATURE_KEYS = [
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo"
]

# 获取 Spotify API 客户端
def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    sp = spotipy.Spotify(auth=token_info["access_token"])
    return sp

# 获取歌曲特征
def get_audio_features(song_name):
    try:
        sp = get_spotify_client()
        results = sp.search(q=song_name, type='track', limit=1)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            print(f"未找到歌曲: {song_name}")
            return None
        track_id = tracks[0]["id"]
        features = sp.audio_features([track_id])[0]
        if features:
            return [features[key] for key in AUDIO_FEATURE_KEYS]
    except Exception as e:
        print(f"获取歌曲特征出错: {song_name} -> {e}")
    return None

# 训练 KNN 模型
def train_model(X, y, n_neighbors=3):
    from sklearn.neighbors import KNeighborsClassifier
    model = KNeighborsClassifier(n_neighbors=n_neighbors)
    model.fit(X, y)
    return model

# 预测歌曲归属
def predict_user_group(model, song_name):
    features = get_audio_features(song_name)
    if features:
        pred = model.predict([features])
        return int(pred[0])
    return None

# 主页路由，展示训练页面
@app.route("/", methods=["GET", "POST"])
def train():
    if request.method == "POST":
        user_input = request.form["user_input"]
        # 解析和提取特征
        X, y = parse_and_extract_features(user_input)
        model = train_model(X, y)
        return render_template("predict.html", model=model)
    return render_template("train.html")

# 预测页面
@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "POST":
        song_name = request.form["song_name"]
        model = request.form["model"]
        group = predict_user_group(model, song_name)
        return render_template("predict.html", group=group)
    return render_template("predict.html")

# 解析和提取特征
def parse_and_extract_features(input_str):
    import re
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

# 授权 callback 路由
@app.route("/callback")
def callback():
    try:
        # 获取 code 参数
        code = request.args.get("code")
        if not code:
            return "⚠️ 未获取到授权 code，请确保你点击了授权链接"

        # 获取 access token
        token_info = sp_oauth.get_access_token(code, as_dict=False)
        if not token_info:
            return "❌ 获取 access token 失败，可能需要重新授权"

        # 缓存 token 到本地文件
        with open(".cache", "w") as f:
            f.write(token_info['access_token'])

        return redirect(url_for("train"))
    except Exception as e:
        print("❌ /callback 授权出错:", str(e))
        return f"Internal Server Error: {e}"

# 运行 Flask 应用
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
