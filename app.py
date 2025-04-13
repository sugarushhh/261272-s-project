import os
from flask import Flask, redirect, request, url_for, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sklearn.neighbors import KNeighborsClassifier
import numpy as np
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 设置 Spotify OAuth
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SCOPE = "user-library-read"

sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                         client_secret=SPOTIPY_CLIENT_SECRET,
                         redirect_uri=SPOTIPY_REDIRECT_URI,
                         scope=SCOPE)

# 用于保存 Spotify API 的访问 token
token_info = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    global token_info
    token_info = sp_oauth.get_access_token(request.args['code'])
    if not token_info:
        return "Failed to get access token", 400

    # Check if token was successfully retrieved
    access_token = token_info.get('access_token')
    if not access_token:
        return "Failed to retrieve access token", 400
    
    sp = spotipy.Spotify(auth=access_token)
    
    # Fetch user information to check if authentication is successful
    user_info = sp.current_user()
    if user_info:
        return "Successfully authenticated: " + user_info['display_name']
    else:
        return "Failed to fetch user info", 400

@app.route('/train', methods=['POST'])
def train():
    global token_info
    if token_info is None:
        return redirect(url_for('login'))
    
    # 用户输入的歌曲名称
    user_input = request.form.get('songs_input')

    # 解析歌曲数据
    try:
        X, y = parse_and_extract_features(user_input)
    except ValueError as e:
        return str(e), 400

    # 用KNN训练模型
    model = KNeighborsClassifier(n_neighbors=3)
    model.fit(X, y)
    
    return "Model trained successfully!"

# 解析歌曲并提取特征
def parse_and_extract_features(user_input):
    songs = user_input.split('/')
    
    X = []
    y = []
    
    for genre, song_list in enumerate(songs):
        song_names = song_list.split(',')
        
        for song_name in song_names:
            song_name = song_name.strip()
            features = get_song_features(song_name)
            
            if features is None:
                raise ValueError(f"输入的歌曲 '{song_name}' 数据无效，请检查格式或歌曲名称是否正确。")
            
            X.append(features)
            y.append(genre)
    
    return np.array(X), np.array(y)

# 获取歌曲特征
def get_song_features(song_name):
    access_token = token_info.get('access_token')
    sp = spotipy.Spotify(auth=access_token)
    
    try:
        results = sp.search(q=song_name, limit=1, type='track')
        track = results['tracks']['items'][0]
        
        # 获取特征：如音调、舞蹈感等
        features = sp.audio_features([track['id']])[0]
        return [
            features['danceability'],
            features['energy'],
            features['key'],
            features['loudness'],
            features['mode'],
            features['speechiness'],
            features['acousticness'],
            features['instrumentalness'],
            features['liveness'],
            features['valence'],
            features['tempo'],
            features['type'],
            features['id']
        ]
    except Exception as e:
        print(f"Error fetching features for {song_name}: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True)
