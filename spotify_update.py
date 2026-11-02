#!/usr/bin/env python3
"""
Atualiza o card "Now playing" (assets/now-playing-*.svg) com a música do Spotify.
"""

import time
from brand import write_now_playing
from spotify_tracker import format_current_playing, MissingCredentials


def main():
    print("🎵 Starting Spotify update...")
    start_time = time.time()

    try:
        spotify_data = format_current_playing() or {'track': 'Nothing'}
    except MissingCredentials as e:
        print(f"⚠️ Spotify secrets not configured ({e}); run spotify_auth.py. Card shows off air.")
        spotify_data = {'track': 'Nothing'}
    except Exception as e:
        # Sem a API, mantém o último card publicado em vez de mostrar erro no perfil
        print(f"❌ Spotify unavailable, keeping current card: {e}")
        return

    changed = write_now_playing(spotify_data)
    elapsed = time.time() - start_time
    print(f"[DEBUG] Spotify data: {spotify_data.get('track')} - {spotify_data.get('artist')} "
          f"(playing={spotify_data.get('is_playing', False)})")
    print(f"✅ Done in {elapsed:.2f}s, card {'updated' if changed else 'unchanged'}")


if __name__ == '__main__':
    main()
