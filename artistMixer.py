import os
import random
import requests
import time
from time import sleep
from celery import Celery
from flask import Flask, session ,redirect, request,request, url_for, render_template
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

artists = ["none", "none"]
app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(64)
scheduler = BackgroundScheduler()
client_id = 'da9dea17abe94684a2cfacfa56725d21'
client_Secret = '89499e6c644344359e14982078514ee4'
redirect_uri = 'http://localhost:5000/callback'
scope = 'playlist-read-private, user-modify-playback-state, user-read-playback-state, user-read-currently-playing'
cache_handler = FlaskSessionCacheHandler(session)

sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_Secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)
sp = Spotify(auth_manager=sp_oauth)

@app.route('/')
def home():  
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    if checkDevice() == False:
        return render_template("devicesLogin.html")   
    
    return render_template("index.html")

@app.route('/base', methods=['GET', 'POST'])
def base():
    
    if request.method == "POST":
        
        artist1 = request.form["artist1"]
        artist2 = request.form["artist2"]
        playBackState = sp.current_user_playing_track()
        
        if playBackState['is_playing'] is False:
            artist1, artist2 = queue_song(artist1,artist2)
            sp.start_playback()
            return render_template("index.html", artist1=artist1, artist2=artist2)
        else:
           artist1 = searchartist(artist1)
           artist2 = searchartist(artist2) 
           SleepyTime = playBackState['item']['duration_ms'] - playBackState['progress_ms']
           scheduler.add_job(id='timer', func = lambda:  timer(SleepyTime/1000, artist1, artist2), trigger = DateTrigger())
           scheduler.start()
           return render_template("index.html", artist1=artist1,artist2=artist2)
    else:
        return render_template("index.html", artist1=artist1,artist2=artist2)
    
@app.route('/logout')
def logout():
  session.clear()
  return redirect(url_for('home'))

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('home'))   
        
def timer(sleepytime,artist1,artist2):
    
    print(f"timer set for{sleepytime}")
    time.sleep(sleepytime-10)
    print("calling queue") 
 #   scheduler.remove_job('timer')
    return redirect(url_for('home'))
    queue_song(artist1,artist2)

def searchartist(artist):
    topArtist = sp.search(q = artist, limit = 1, type = 'artist')
    return topArtist['artists']['items'][0]['name']

def queue_song(artist1,artist2): 
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    #todo make work for n artists
    ArtistToQueue = random.randrange(1,3,1)
    #artist 1
    name1 = artist1
    result1 = sp.search(q = name1, limit = 1,  type ='artist')
    artist1 = result1['artists']['items'][0]['name']
    #artist 2
    name2 = artist2
    result2 = sp.search(q = name2, limit = 1,type ='artist')
    artist2 = result2['artists']['items'][0]['name']
    print(artist1)
    if ArtistToQueue == 1:
        artistId = result1['artists']['items'][0]['id']
        SleepyTime = get_allSongs(artistId)
    else:
        artistId = result2['artists']['items'][0]['id']
        SleepyTime = get_allSongs(artistId)
        
    scheduler.add_job(id='timer', func = lambda:  timer(SleepyTime,artist1,artist2), trigger = 'interval', seconds = SleepyTime/1000)
    print("added job")
    scheduler.start()
   # print(nameOfArtist)
    return artist1,artist2

#todo randomly select song from artist
#search for all albums of artist 
#add amount of tracks together (n)
#randomly select num randrange (1,n+1)
#loop by subtracting amount of songs from randomnum if not smaller than 0 then continue else undo enter album and go to song

def checkDevice():
    #if active device return true
    #if no active device return false
    tot = False
    for x in sp.devices()['devices']:
        if x['is_active'] == True:
            tot = True
            break
    if tot == False:
        return False
    else:
        return True
        
def get_allSongs(artistId):
    #maybe have appears_on?
    allAlbums = sp.artist_albums(artist_id = artistId, include_groups='album,single', limit = 50, offset =0)
    listOfAlbums  = allAlbums['items']
    i = 1
    while allAlbums['next'] != None:
        allAlbums = sp.artist_albums(artist_id= artistId, include_groups='album,single', limit=50, offset=50*i)
        listtoadd = allAlbums['items']
        listOfAlbums.extend(listtoadd)
        i+=1
    
    for y in listOfAlbums:
        print(y['name'])
    counter = 0
    for x in listOfAlbums:
        counter +=1
    numberOfTracks = 0
    for x in listOfAlbums:
        numberOfTracks += x['total_tracks']
        
    print(numberOfTracks)
    print(counter)
    randNum = random.randrange(1,numberOfTracks+1, 1)
    index = 0
    for q in listOfAlbums:
        if randNum >= q['total_tracks']:
            randNum -= q['total_tracks']
        else: 
            albumd = sp.album(q['id'])['id']
            allTracks = sp.album_tracks(album_id=albumd, limit=50,offset=0)['items']
            num_to_play = allTracks[randNum]
            sp.add_to_queue(num_to_play['id'])
            return num_to_play['duration_ms']
            
    

#change
#@app.route('/get_playlists')
def get_playlists():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    playlists= sp.current_user_playlists()
    playlists_info = [(pl['name'], pl['external_urls']['spotify']) for pl in playlists['items']]
    playlists_html = '<br>'.join([f'{name}: {url}' for name,url in playlists_info])
    return playlists_html



if __name__ == '__main__':
    app.run(debug=True)