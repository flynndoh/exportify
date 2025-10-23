from flask import Flask, jsonify, send_from_directory
import json
from collections import Counter
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')

# Load Spotify data
def load_spotify_data():
    with open('spotify_liked_songs_20251023_233359.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/songs')
def get_songs():
    """Return all songs"""
    data = load_spotify_data()
    return jsonify(data)

@app.route('/api/statistics')
def get_statistics():
    """Return general statistics about the library"""
    data = load_spotify_data()
    
    # Calculate statistics
    total_songs = len(data)
    total_duration_ms = sum(song['duration_ms'] for song in data)
    total_hours = total_duration_ms / (1000 * 60 * 60)
    
    avg_popularity = sum(song['popularity'] for song in data) / total_songs if total_songs > 0 else 0
    avg_duration_min = sum(song['duration_minutes'] for song in data) / total_songs if total_songs > 0 else 0
    
    explicit_count = sum(1 for song in data if song['explicit'])
    
    # Artists
    all_artists = []
    for song in data:
        artists = song['artist_names'].split(', ') if isinstance(song['artist_names'], str) else [song['artist_names']]
        all_artists.extend(artists)
    
    artist_counts = Counter(all_artists)
    top_artists = [{'name': artist, 'count': count} for artist, count in artist_counts.most_common(10)]
    
    # Albums
    album_counts = Counter(song['album_name'] for song in data)
    top_albums = [{'name': album, 'count': count} for album, count in album_counts.most_common(10)]
    
    # Years
    years = []
    for song in data:
        if song['album_release_date']:
            year = song['album_release_date'][:4]
            years.append(year)
    
    year_counts = Counter(years)
    decades = Counter()
    for year in years:
        try:
            decade = (int(year) // 10) * 10
            decades[f"{decade}s"] += 1
        except:
            pass
    
    decade_distribution = [{'decade': decade, 'count': count} for decade, count in sorted(decades.items())]
    
    # Popularity distribution
    popularity_ranges = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    }
    
    for song in data:
        pop = song['popularity']
        if pop <= 20:
            popularity_ranges['0-20'] += 1
        elif pop <= 40:
            popularity_ranges['21-40'] += 1
        elif pop <= 60:
            popularity_ranges['41-60'] += 1
        elif pop <= 80:
            popularity_ranges['61-80'] += 1
        else:
            popularity_ranges['81-100'] += 1
    
    popularity_distribution = [{'range': k, 'count': v} for k, v in popularity_ranges.items()]
    
    return jsonify({
        'total_songs': total_songs,
        'total_hours': round(total_hours, 2),
        'avg_popularity': round(avg_popularity, 1),
        'avg_duration_min': round(avg_duration_min, 2),
        'explicit_count': explicit_count,
        'explicit_percentage': round((explicit_count / total_songs) * 100, 1) if total_songs > 0 else 0,
        'total_artists': len(artist_counts),
        'total_albums': len(album_counts),
        'top_artists': top_artists,
        'top_albums': top_albums,
        'decade_distribution': decade_distribution,
        'popularity_distribution': popularity_distribution
    })

@app.route('/api/graph-data')
def get_graph_data():
    """Return data formatted for node graph visualization"""
    try:
        data = load_spotify_data()
        
        nodes = []
        links = []
        node_ids = set()
        
        # Create artist nodes
        artist_songs = {}
        for song in data:
            # Handle different artist name formats
            artist_names = song.get('artist_names', '')
            if not artist_names:
                continue
                
            # Split by comma, semicolon, or keep as single artist
            if isinstance(artist_names, str):
                # Try multiple delimiters
                if ', ' in artist_names:
                    artists = [a.strip() for a in artist_names.split(', ')]
                elif '; ' in artist_names:
                    artists = [a.strip() for a in artist_names.split('; ')]
                else:
                    artists = [artist_names.strip()]
            else:
                artists = [str(artist_names)]
            
            for artist in artists:
                if artist and artist.strip():  # Skip empty artists
                    artist = artist.strip()
                    if artist not in artist_songs:
                        artist_songs[artist] = []
                    artist_songs[artist].append(song)
        
        # Add top artists only (to keep graph manageable)
        sorted_artists = sorted(artist_songs.items(), key=lambda x: len(x[1]), reverse=True)[:50]
        
        for artist, songs in sorted_artists:
            avg_popularity = sum(s.get('popularity', 0) for s in songs) / len(songs) if songs else 0
            nodes.append({
                'id': f'artist_{artist}',
                'name': artist,
                'type': 'artist',
                'size': max(5, min(len(songs) * 2, 30)),  # Cap size between 5-30
                'popularity': round(avg_popularity, 1)
            })
            node_ids.add(f'artist_{artist}')
        
        # Add album nodes and links
        album_data = {}
        for song in data:
            album = song.get('album_name', 'Unknown Album')
            if not album or album.strip() == '':
                album = 'Unknown Album'
            
            album = album.strip()
            
            if album not in album_data:
                album_data[album] = {
                    'artists': set(),
                    'songs': [],
                }
            
            # Get artists for this song
            artist_names = song.get('artist_names', '')
            if isinstance(artist_names, str):
                if ', ' in artist_names:
                    artists = [a.strip() for a in artist_names.split(', ')]
                elif '; ' in artist_names:
                    artists = [a.strip() for a in artist_names.split('; ')]
                else:
                    artists = [artist_names.strip()] if artist_names.strip() else []
            else:
                artists = [str(artist_names)]
            
            for artist in artists:
                if artist and artist.strip():
                    album_data[album]['artists'].add(artist.strip())
            album_data[album]['songs'].append(song)
        
        # Add top albums only (to keep graph manageable)
        sorted_albums = sorted(album_data.items(), key=lambda x: len(x[1]['songs']), reverse=True)[:40]
        
        for album, info in sorted_albums:
            if not info['songs']:
                continue
                
            avg_pop = sum(s.get('popularity', 0) for s in info['songs']) / len(info['songs'])
            album_id = f'album_{album}'
            
            nodes.append({
                'id': album_id,
                'name': album[:50] + '...' if len(album) > 50 else album,  # Truncate long names
                'type': 'album',
                'size': max(5, min(len(info['songs']) + 5, 25)),  # Cap size between 5-25
                'popularity': round(avg_pop, 1)
            })
            node_ids.add(album_id)
            
            # Link album to artists (only if artist is in top 50)
            for artist in info['artists']:
                artist_id = f'artist_{artist}'
                if artist_id in node_ids:
                    links.append({
                        'source': artist_id,
                        'target': album_id,
                        'value': len(info['songs'])
                    })
        
        print(f"Graph data generated: {len(nodes)} nodes, {len(links)} links")
        
        return jsonify({
            'nodes': nodes,
            'links': links,
            'stats': {
                'total_nodes': len(nodes),
                'total_links': len(links),
                'artists': sum(1 for n in nodes if n['type'] == 'artist'),
                'albums': sum(1 for n in nodes if n['type'] == 'album')
            }
        })
    except Exception as e:
        print(f"Error generating graph data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'nodes': [],
            'links': []
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)