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
    Formata a música atual (ou a última tocada) e as 3 anteriores a ela
    """
    headers = {'Authorization': f'Bearer {get_access_token()}'}

    recent = requests.get(f'{API}/me/player/recently-played', headers=headers, params={'limit': 6}, timeout=15)
    recent.raise_for_status()
    history = [_track_info(item['track']) for item in recent.json().get('items') or []]

    current = requests.get(f'{API}/me/player/currently-playing', headers=headers, timeout=15)
    current.raise_for_status()
    # 204 = nada tocando; podcasts e anúncios chegam sem 'item' de música
    if current.status_code == 200 and current.content:
        data = current.json()
        if data.get('is_playing') and data.get('currently_playing_type') == 'track' and data.get('item'):
            now = {'is_playing': True, **_track_info(data['item'])}
            return {**now, 'recent': _previous(history, now)}

    if history:
        return {'is_playing': False, **history[0], 'recent': _previous(history[1:], history[0])}
    return {'track': 'Nothing'}


def _previous(history, shown, count=3):
    """Últimas músicas sem repetir a que está no destaque nem duplicatas seguidas"""
    out = []
    for item in history:
        key = (item['track'], item['artist'])
        if key == (shown['track'], shown['artist']) or (out and key == (out[-1]['track'], out[-1]['artist'])):
            continue
        out.append(item)
        if len(out) == count:
            break
    return out


if __name__ == '__main__':
    playing = format_current_playing()
    print(f"Track: {playing['track']}")
    print(f"Artist: {playing.get('artist', '')}")
