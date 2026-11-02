"""
Lê a música atual (ou a última tocada) direto da API do Spotify.

Credenciais vêm de variáveis de ambiente (no GitHub: Settings → Secrets → Actions):
    SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
Para gerar o refresh token e gravar os secrets: python spotify_auth.py
"""
import base64
import os

import requests

TOKEN_URL = 'https://accounts.spotify.com/api/token'
API = 'https://api.spotify.com/v1'


class MissingCredentials(RuntimeError):
    pass


def get_access_token():
    """
    Troca o refresh token por um access token novo (vale 1 hora)
    """
    keys = ('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN')
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise MissingCredentials(f"missing {', '.join(missing)}")
    client = f"{os.environ['SPOTIFY_CLIENT_ID']}:{os.environ['SPOTIFY_CLIENT_SECRET']}"
    response = requests.post(
        TOKEN_URL,
        headers={'Authorization': 'Basic ' + base64.b64encode(client.encode()).decode()},
        data={'grant_type': 'refresh_token', 'refresh_token': os.environ['SPOTIFY_REFRESH_TOKEN']},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()['access_token']


def _track_info(track):
    return {
        'track': track['name'],
        'artist': ', '.join(artist['name'] for artist in track['artists']),
        'album': track['album']['name'],
        'url': track['external_urls'].get('spotify'),
    }


def format_current_playing():
    """
    Formata a música atual para exibição; sem nada tocando, devolve a última tocada
    """
    headers = {'Authorization': f'Bearer {get_access_token()}'}

    current = requests.get(f'{API}/me/player/currently-playing', headers=headers, timeout=15)
    current.raise_for_status()
    # 204 = nada tocando; podcasts e anúncios chegam sem 'item' de música
    if current.status_code == 200 and current.content:
        data = current.json()
        if data.get('is_playing') and data.get('currently_playing_type') == 'track' and data.get('item'):
            return {'is_playing': True, **_track_info(data['item'])}

    recent = requests.get(f'{API}/me/player/recently-played', headers=headers, params={'limit': 1}, timeout=15)
    recent.raise_for_status()
    items = recent.json().get('items') or []
    if items:
        return {'is_playing': False, **_track_info(items[0]['track'])}
    return {'track': 'Nothing'}


if __name__ == '__main__':
    playing = format_current_playing()
    print(f"Track: {playing['track']}")
    print(f"Artist: {playing.get('artist', '')}")
