#!/usr/bin/env python3
"""
Script para atualizar apenas os dados do Spotify nos SVGs
Executa rapidamente sem fazer todas as consultas do GitHub
"""

import time
from lxml import etree
from spotify_tracker import format_current_playing

def update_spotify_in_svg(filename, spotify_data):
    """
    Atualiza apenas o campo do Spotify no SVG
    """
    print(f"[DEBUG] Updating Spotify in {filename}")
    
    try:
        tree = etree.parse(filename)
        root = tree.getroot()
        
        # Combinar track e artist
        spotify_display = f"{spotify_data.get('track', 'Nothing')} - {spotify_data.get('artist', 'Nobody')}"
        
        # Encontrar e atualizar o elemento spotify_track
        spotify_element = root.find(".//*[@id='spotify_track']")
        if spotify_element is not None:
            spotify_element.text = spotify_display
            print(f"[DEBUG] Updated Spotify: {spotify_display}")
        else:
            print(f"[WARNING] Spotify element not found in {filename}")
        
        # Salvar arquivo
        tree.write(filename, encoding='utf-8', xml_declaration=True)
        print(f"[DEBUG] {filename} updated successfully")
        
    except Exception as e:
        print(f"[ERROR] Failed to update {filename}: {e}")

def main():
    """
    Função principal - atualiza Spotify nos SVGs
    """
    print("🎵 Starting Spotify update...")
    start_time = time.time()
    
    try:
        # Buscar dados do Spotify
        print("[DEBUG] Getting Spotify data...")
        spotify_data = format_current_playing()
        
        if not spotify_data:
            spotify_data = {'track': 'Error', 'artist': 'Connection Failed'}
            
        print(f"[DEBUG] Spotify data: {spotify_data}")
        
        # Atualizar ambos os SVGs
        update_spotify_in_svg('light_mode.svg', spotify_data)
        update_spotify_in_svg('dark_mode.svg', spotify_data)
        
        elapsed = time.time() - start_time
        print(f"✅ Spotify update completed in {elapsed:.2f}s")
        print(f"🎵 Now playing: {spotify_data.get('track', 'Nothing')} - {spotify_data.get('artist', 'Nobody')}")
        
    except Exception as e:
        print(f"❌ Spotify update failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
