import os
import random
import requests
from time import sleep
import time
import spotipy
from dotenv import load_dotenv
from celery import Celery
from flask import Flask, session ,redirect, request, url_for, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from celery.contrib.abortable import AbortableTask
from celery import shared_task
import json


@shared_task()
def queue_song(token, artist1, artist2, SleepyTime):
    print(artist1,artist2)
    SleepyTime = round(SleepyTime) -5
    if SleepyTime < 0:
        pass
    else:
     print(f"setting timer for {SleepyTime} seconds")
     time.sleep(SleepyTime)
     #for i in range(0,SleepyTime):
      #    time.sleep(1)
    
          
    ArtistToQueue = random.randrange(1,3,1)
  #  sp = spotipy.Spotify(auth= token)
    url = 'https://api.spotify.com/v1/search'
    
    query1 = f'?q={artist1}&type=artist&limit=1&offset=0'
    query_url1 = url + query1
    
    result1 = requests.get(query_url1, headers={"Authorization": "Bearer "+ token})
    result1 = result1.json()
    artist1 = result1['artists']['items'][0]['name']
    
    query2 = f'?q={artist2}&type=artist&limit=1&offset=0'
    query_url2 = url + query2
    
    result2 = requests.get(query_url2, headers={"Authorization": "Bearer "+ token})
    result2 = result2.json()
    artist2 = result2['artists']['items'][0]['name']
    print(artist1,artist2)
    
    if ArtistToQueue == 1:
        artistId = result1['artists']['items'][0]['id']
        SleepyTime = get_allSongs(artistId,token)
    else:
        artistId = result2['artists']['items'][0]['id']
        SleepyTime = get_allSongs(artistId,token)
    print('here')
    print(artist1,artist2)
    queue_song.delay(token, artist1, artist2, SleepyTime)
    return "success"

    

def get_allSongs(artistId,token):
    #maybe have appears_on?
    url = 'https://api.spotify.com/v1/artists/'
    query= f'{artistId}/albums?include_groups=album%2Csingle&limit=50&offset=0'
    urlquery  =url+query
    allAlbums= requests.get(urlquery,headers={"Authorization": "Bearer "+ token})
    allAlbums= allAlbums.json()
    listOfAlbums  = allAlbums['items']
    i = 1
    while allAlbums['next'] != None:
        url = 'https://api.spotify.com/v1/artists/'
        query= f'{artistId}/albums?include_groups=album%2Csingle&limit=50&offset={50*i}'
        urlquery  =url+query
        allAlbums= requests.get(urlquery,headers={"Authorization": "Bearer "+ token})
        allAlbums = allAlbums.json()
        
        listtoadd = allAlbums['items']
        listOfAlbums.extend(listtoadd)
        i+=1
    
   # for y in listOfAlbums:
     #   print(y['name'])
    counter = 0
    for x in listOfAlbums:
        counter +=1
    numberOfTracks = 0
    for x in listOfAlbums:
        numberOfTracks += x['total_tracks']
        
    
    randNum = random.randrange(1,numberOfTracks+1, 1)
 
    for q in listOfAlbums:
        if randNum >= q['total_tracks']:
            randNum -= q['total_tracks']
        else: 
            q = q['id']
            queryAlbum ='https://api.spotify.com/v1/albums/'
            temp =f'{q}'
            queryAlbum = queryAlbum + temp
            albumd = requests.get(queryAlbum, headers={"Authorization": "Bearer " + token})
            albumd = albumd.json()['id']
        
            queryTracks = f'https://api.spotify.com/v1/albums/'
            temp2 = f'{albumd}/tracks?limit=50&offset=0'
            queryTracks = queryTracks+temp2
            allTracks = requests.get(queryTracks,  headers={"Authorization": "Bearer " + token})
            allTracks= allTracks.json()['items']
           
            #albumd = sp.album(q['id'])['id']
           #allTracks = sp.album_tracks(album_id=albumd, limit=50,offset=0)['items']
            num_to_play = allTracks[randNum]
            uri = allTracks[randNum]['uri']
           
            query = f'https://api.spotify.com/v1/me/player/queue'
       
            params = {'uri' : uri}
            requests.post(query, headers={"Authorization": "Bearer " + token}, params=params)
            print('queing')
            print(uri)
        #    sp.add_to_queue(num_to_play['id'])
            return num_to_play['duration_ms']/1000
            
    
