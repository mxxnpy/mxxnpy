#!/usr/bin/env python3
"""
Autoriza o card "Now playing" a ler o seu Spotify e grava as credenciais
como Secrets do repositório no GitHub. Rode uma vez (ou quando trocar o secret):

    python spotify_auth.py

Requisitos: gh logado (gh auth status) e um app em developer.spotify.com/dashboard
com o Redirect URI http://127.0.0.1:8888/callback cadastrado.
Nenhum token é impresso nem salvo em arquivo.
"""
import base64
import getpass
import http.server
import json
import secrets
import subprocess
import urllib.parse
import urllib.request
import webbrowser

REPO = 'mxxnpy/mxxnpy'
REDIRECT_URI = 'http://127.0.0.1:8888/callback'
SCOPES = 'user-read-currently-playing user-read-recently-played'


def wait_for_code(state):
    """
    Sobe um servidor local de uso único e devolve o 'code' que o Spotify manda no redirect
    """
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ok = query.get('state', [''])[0] == state and 'code' in query
            result['code'] = query['code'][0] if ok else None
            result['error'] = query.get('error', [None])[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            message = 'Pronto, pode fechar esta aba.' if ok else 'Autorização falhou, volte ao terminal.'
            self.wfile.write(f'<p style="font-family:monospace">{message}</p>'.encode())

        def log_message(self, *args):
            pass

    with http.server.HTTPServer(('127.0.0.1', 8888), Handler) as server:
        server.handle_request()
    if not result.get('code'):
        raise SystemExit(f"Autorização não concluída ({result.get('error') or 'state inválido'}).")
    return result['code']


def exchange(code, client_id, client_secret):
    data = urllib.parse.urlencode({
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI,
    }).encode()
    request = urllib.request.Request('https://accounts.spotify.com/api/token', data=data)
    basic = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    request.add_header('Authorization', f'Basic {basic}')
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)['refresh_token']


def set_secret(name, value):
    # Valor vai pelo stdin, nunca pela linha de comando
    subprocess.run(['gh', 'secret', 'set', name, '-R', REPO], input=value.encode(), check=True,
                   stdout=subprocess.DEVNULL)
    print(f'  ✓ {name}')


def main():
    client_id = input('Spotify Client ID: ').strip()
    client_secret = getpass.getpass('Spotify Client Secret (não aparece ao digitar): ').strip()
    state = secrets.token_urlsafe(16)
    url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
        'client_id': client_id, 'response_type': 'code', 'redirect_uri': REDIRECT_URI,
        'scope': SCOPES, 'state': state,
    })
    print('\nAbrindo o navegador para você autorizar. Se não abrir, acesse:\n' + url + '\n')
    webbrowser.open(url)
    refresh_token = exchange(wait_for_code(state), client_id, client_secret)

    print(f'Gravando secrets em {REPO}:')
    set_secret('SPOTIFY_CLIENT_ID', client_id)
    set_secret('SPOTIFY_CLIENT_SECRET', client_secret)
    set_secret('SPOTIFY_REFRESH_TOKEN', refresh_token)

    subprocess.run(['gh', 'workflow', 'run', 'spotify-update.yaml', '-R', REPO], check=False)
    print('\nFeito. O card atualiza em ~1 minuto e depois a cada execução agendada do GitHub.')


if __name__ == '__main__':
    main()
