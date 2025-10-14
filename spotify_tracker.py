import requests
import json
import datetime
import os

def get_current_track():
    """
    Busca a música atual tocando no Spotify
    """
    try:
        response = requests.get('https://mxxnpage-bff.vercel.app/backend/spotify/current-track')
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get current track: {e}")
        return None

def get_recently_played():
    """
    Busca as músicas tocadas recentemente
    """
    try:
        response = requests.get('https://mxxnpage-bff.vercel.app/backend/spotify/recently-played')
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get recently played: {e}")
        return None

def format_current_playing():
    """
    Formata a música atual para exibição
    """
    current = get_current_track()
    
    if not current or not current.get('is_playing'):
        recent = get_recently_played()
        if recent and recent.get('items'):
            last_track = recent['items'][0]['track']
            return {
                'status': '🎵 Last played',
                'track': last_track['name'],
                'artist': ', '.join([artist['name'] for artist in last_track['artists']]),
                'album': last_track['album']['name'],
                'image': last_track['album']['images'][0]['url'] if last_track['album']['images'] else None,
                'url': last_track['external_urls']['spotify']
            }
        return {
            'track': 'Nothing',
            'artist': 'Nobody',
            'album': 'Silence',
            'image': None,
            'url': None
        }
    
    track = current['item']
    progress_ms = current.get('progress_ms', 0)
    duration_ms = track.get('duration_ms', 0)
    
    return {
        'track': track['name'],
        'artist': ', '.join([artist['name'] for artist in track['artists']]),
        'album': track['album']['name'],
        'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
        'url': track['external_urls']['spotify'],
        'time': f"{format_time(progress_ms)} / {format_time(duration_ms)}"
    }

def create_progress_bar(percent, length=20):
    """
    Cria uma barra de progresso visual
    """
    filled = int(length * percent / 100)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}] {percent:.1f}%"

def format_time(ms):
    """
    Converte milissegundos para formato MM:SS
    """
    seconds = ms // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def track_listening_stats():
    """
    Rastreia estatísticas de escuta (implementação básica)
    """
    stats_file = 'cache/listening_stats.json'
    
    try:
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    except FileNotFoundError:
        stats = {
            'total_tracks': 0,
            'total_artists': set(),
            'top_artists': {},
            'last_updated': None
        }
    
    current = get_current_track()
    if current and current.get('is_playing'):
        track = current['item']
        artist = track['artists'][0]['name']
        
        stats['total_tracks'] += 1
        stats['total_artists'].add(artist)
        
        if artist in stats['top_artists']:
            stats['top_artists'][artist] += 1
        else:
            stats['top_artists'][artist] = 1
        
        stats['last_updated'] = datetime.datetime.now().isoformat()
        
        # Converte set para list para JSON
        stats['total_artists'] = list(stats['total_artists'])
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Converte de volta para set
        stats['total_artists'] = set(stats['total_artists'])
    
    return stats

if __name__ == '__main__':
    playing = format_current_playing()
    print(f"Track: {playing['track']}")
    print(f"Artist: {playing['artist']}")
