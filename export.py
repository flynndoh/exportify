#!/usr/bin/env python3
"""
Spotify Liked Songs Metadata Fetcher

This script fetches metadata for all songs in your Spotify liked playlist.
You'll need to create a Spotify app at https://developer.spotify.com/dashboard
to get your Client ID and Client Secret.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import csv
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration - Loaded from .env file
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8888/callback')
SCOPE = 'user-library-read'

def get_spotify_client():
    """Initialize and return Spotify client with user authentication."""
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    return spotipy.Spotify(auth_manager=auth_manager)

def fetch_all_liked_songs(sp):
    """Fetch all liked songs from user's library."""
    liked_songs = []
    offset = 0
    limit = 50  # Spotify API limit per request
    
    print("Fetching liked songs...")
    
    while True:
        results = sp.current_user_saved_tracks(limit=limit, offset=offset)
        
        if not results['items']:
            break
        
        liked_songs.extend(results['items'])
        offset += limit
        print(f"Fetched {len(liked_songs)} songs so far...")
        
        if results['next'] is None:
            break
    
    print(f"Total songs fetched: {len(liked_songs)}")
    return liked_songs

def extract_song_metadata(track_item):
    """Extract relevant metadata from a track item."""
    track = track_item['track']
    
    # Get album cover image URL (largest available)
    album_images = track['album'].get('images', [])
    album_cover_url = album_images[0]['url'] if album_images else 'N/A'
    
    metadata = {
        'song_name': track['name'],
        'artist_names': ', '.join([artist['name'] for artist in track['artists']]),
        'album_name': track['album']['name'],
        'album_release_date': track['album']['release_date'],
        'album_cover_url': album_cover_url,
        'duration_ms': track['duration_ms'],
        'duration_minutes': round(track['duration_ms'] / 60000, 2),
        'popularity': track['popularity'],
        'explicit': track['explicit'],
        'track_id': track['id'],
        'track_uri': track['uri'],
        'external_url': track['external_urls']['spotify'],
        'added_at': track_item['added_at'],
        'preview_url': track.get('preview_url', 'N/A'),
        'disc_number': track['disc_number'],
        'track_number': track['track_number'],
        'is_local': track['is_local']
    }
    
    return metadata

def save_to_json(data, filename='spotify_liked_songs.json'):
    """Save metadata to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Data saved to {filename}")

def save_to_csv(data, filename='spotify_liked_songs.csv'):
    """Save metadata to CSV file."""
    if not data:
        print("No data to save")
        return
    
    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Data saved to {filename}")

def main():
    """Main function to orchestrate the metadata fetching."""
    print("=" * 60)
    print("Spotify Liked Songs Metadata Fetcher")
    print("=" * 60)
    print()
    
    # Check if credentials are set
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Spotify API credentials not found in .env file!")
        print("\nTo set up your credentials:")
        print("1. Go to https://developer.spotify.com/dashboard")
        print("2. Create a new app")
        print("3. Copy your Client ID and Client Secret")
        print("4. Set the Redirect URI to: http://127.0.0.1:8888/callback")
        print("5. Create a .env file in the same directory as this script")
        print("6. Add your credentials to the .env file (see .env.example)")
        return
    
    try:
        # Initialize Spotify client
        sp = get_spotify_client()
        
        # Fetch all liked songs
        liked_songs = fetch_all_liked_songs(sp)
        
        if not liked_songs:
            print("No liked songs found!")
            return
        
        # Extract metadata
        print("\nExtracting metadata...")
        metadata_list = [extract_song_metadata(item) for item in liked_songs]
        
        # Save to files
        print("\nSaving data...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_to_json(metadata_list, f'spotify_liked_songs_{timestamp}.json')
        save_to_csv(metadata_list, f'spotify_liked_songs_{timestamp}.csv')
        
        # Print summary statistics
        print("\n" + "=" * 60)
        print("Summary Statistics")
        print("=" * 60)
        print(f"Total songs: {len(metadata_list)}")
        
        total_duration = sum(song['duration_ms'] for song in metadata_list)
        total_hours = total_duration / (1000 * 60 * 60)
        print(f"Total duration: {total_hours:.2f} hours")
        
        explicit_count = sum(1 for song in metadata_list if song['explicit'])
        print(f"Explicit songs: {explicit_count}")
        
        avg_popularity = sum(song['popularity'] for song in metadata_list) / len(metadata_list)
        print(f"Average popularity: {avg_popularity:.2f}")
        
        # Top artists
        artist_counts = {}
        for song in metadata_list:
            artists = song['artist_names'].split(', ')
            for artist in artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1
        
        top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\nTop 10 Artists:")
        for i, (artist, count) in enumerate(top_artists, 1):
            print(f"  {i}. {artist}: {count} songs")
        
        print("\n" + "=" * 60)
        print("Done! Check the generated JSON and CSV files.")
        print("=" * 60)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        print("\nMake sure you have installed spotipy:")
        print("  uv pip install spotipy")

if __name__ == "__main__":
    main()