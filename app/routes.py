from flask import Blueprint,render_template,redirect,url_for,request,session,flash
from flask_session import Session
from .tasks import queue_song
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
import requests
import random
import json

from pprint import pprint
from logging.config import dictConfig
from celery import current_app

#todo:
#task revoking
#loops, queing,pausing skipping
#stay logged in?
client_id = os.getenv('CLIENT_ID')
client_Secret = os.getenv('CLIENT_SECRET')
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

main = Blueprint('main', __name__)

@main.route('/')
def index():
    print(current_app)
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        print('at index route')
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    if checkDevice() == False:
        return render_template("devicesLogin.html")   
    print('index.html via index route')
    return render_template("index.html", playstate = checkPlayback())
@main.route('/base', methods = ["POST", "GET"])  
def base():
  
    if request.method == "POST":
        
        artist1 = request.form["artist1"]
        artist2 = request.form["artist2"]
        session['artist1'] = artist1
        session['artist2'] = artist2
        playBackState = sp.current_user_playing_track()
        
        print(artist1,artist2)
        if playBackState['is_playing'] is False:
            artist1 = searchartist(artist1)
            artist2 = searchartist(artist2)
        
            return render_template("index.html", artist1=artist1, artist2=artist2, playstate = checkPlayback())
        else:
           artist1 = searchartist(artist1)
           artist2 = searchartist(artist2)
           SleepyTime = (playBackState['item']['duration_ms'] - playBackState['progress_ms'])/1000
        
       #    tasks = session.get('tasks')
           test =  queue_song.delay(sp_oauth.get_access_token(as_dict=False),artist1, artist2, SleepyTime).id
         
        
           session['tasks'] = test
           
           return render_template("index.html", artist1=artist1,artist2=artist2, playstate = checkPlayback())
    else:
        artist1 = "not active"
        artist2 = "not active"
        print("get")
        return render_template("index.html", artist1=artist1,artist2=artist2, playstate = checkPlayback())
@main.route('/pause')
def pause():
    print('pausing')
    playback = sp.current_playback()

    if playback and playback['is_playing']:
       sp.pause_playback()
    else:
      print("No active playback, cannot pause.")
      
    
    
    #pause playback
    id =session.get('tasks')
    print(id)
    print(current_app)
    current_app.control.revoke(session['tasks'], terminate = True)
    print('revoking')
    return render_template("index.html", playstate = checkPlayback)
@main.route('/resume')
def resume():
    sp.start_playback()
    artist1 = session.get('artist1')
    artist2 = session.get('artist2')
    playBackState = sp.current_user_playing_track()
    #start task with remaining time 
    SleepyTime = (playBackState['item']['duration_ms'] - playBackState['progress_ms']) / 1000
    test =queue_song.delay(sp_oauth.get_access_token(as_dict=False),artist1,artist2, SleepyTime = SleepyTime).id
   
    session['tasks'] = test
    print(test)
   # current_app.control.revoke(session['tasks'], terminate = True)
    return render_template("index.html", playstate = checkPlayback())

def checkPlayback():
    state = sp.current_playback()
    if state['is_playing'] == True:
        return 'pause'
    else:
        return 'play_arrow'
@main.route('/callback')
def callback():
   
    try:
     sp_oauth.get_access_token(request.args['code'])
    except:
        return render_template('PermissionsNotGranted.html') 
    if checkDevice() == False:
        return render_template("devicesLogin.html")
    return redirect(url_for('main.index'))
@main.route('/toAuth')
def toAuth():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@main.route('/logout')
def logout():
  session.clear()
  print('why am i')
  return redirect(url_for('main.index'))


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
def checkQueue():
    queue  = sp.queue()
    #todo
    return queue['queue']
def searchartist(artist):
    topArtist = sp.search(q = artist, limit = 1, type = 'artist')
    return topArtist['artists']['items'][0]['name']



#todo randomly select song from artist
#search for all albums of artist 
#add amount of tracks together (n)
#randomly select num randrange (1,n+1)
#loop by subtracting amount of songs from randomnum if not smaller than 0 then continue else undo enter album and go to song


        
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
