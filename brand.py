"""
Marca do perfil: lua crescente em ASCII, hero e card "Now playing".

    python brand.py            # regenera assets/ (hero, logo e um card de exemplo)

spotify_update.py usa render_now_playing() para reescrever só o card de música.
"""
import math
import os
from xml.sax.saxutils import escape

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
FONT = "ui-monospace, 'SFMono-Regular', 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    'dark': dict(bg='#0b0d17', border='#1d2133', ink='#e8e4d8', dim='#737a94', faint='#3a3f55',
                 moon='#f1d79a', star='#9aa3c7', glow='#f1d79a'),
    'light': dict(bg='#f7f5ef', border='#e2ddcf', ink='#1c1e2a', dim='#6e7386', faint='#c9c3b2',
                  moon='#8a5f12', star='#9b916f', glow='#d9b25c'),
}

REDUCED_MOTION = '@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }'


def crescent(rows=22, cols=40, cw=7.8, ch=13.0):
    """Lua crescente em ASCII. Devolve (linhas, estrelas) com estrelas como (linha, coluna, char)."""
    cx, cy = cols * cw / 2, rows * ch / 2
    r = min(cx, cy) - ch * 0.6
    bx, by, br = cx + 0.62 * r, cy - 0.18 * r, 0.92 * r      # disco que "come" a lua
    ramp = '.:-=+*#%@'
    craters = [(cx - 0.62 * r, cy - 0.30 * r, 0.13 * r), (cx - 0.45 * r, cy + 0.50 * r, 0.10 * r)]
    stars = [(0, 3, '+'), (1, 33, '.'), (3, 38, '*'), (19, 37, '+'), (21, 9, '.'),
             (18, 0, '.'), (6, 0, '.'), (11, 39, '.'), (21, 28, '*')]
    lines = []
    for row in range(rows):
        line = ''
        for col in range(cols):
            px, py = (col + 0.5) * cw, (row + 0.5) * ch
            da = math.hypot(px - cx, py - cy)
            db = math.hypot(px - bx, py - by)
            if da <= r and db > br:
                lit = min(1.0, (db - br) / (0.55 * r))        # mais claro longe do terminador
                limb = 1.0 - max(0.0, (da / r) - 0.85) * 2.5   # escurece na borda
                v = max(0.0, lit * limb)
                if any(math.hypot(px - x, py - y) < cr for x, y, cr in craters):
                    v *= 0.7
                line += ramp[min(len(ramp) - 1, int(v * len(ramp)))]
            elif r - ch * 0.8 <= da <= r and db <= br and col % 2 == 0:
                line += '.'                                    # contorno da parte em sombra
            else:
                line += ' '
        lines.append(line.rstrip())
    return lines, stars


def moon_group(x, y, size=13, stagger=True):
    """<g> com a lua, linhas surgindo em sequência e estrelas piscando."""
    lines, stars = crescent(ch=size)
    cw = size * 0.6
    out = [f'<g class="moon" font-size="{size}">']
    for i, line in enumerate(lines):
        if line.strip():
            delay = f' style="animation-delay:{i * 45}ms"' if stagger else ''
            out.append(f'<text class="row" x="{x}" y="{y + (i + 1) * size}"{delay}>{escape(line)}</text>')
    for n, (row, col, ch) in enumerate(stars):
        out.append(f'<text class="star" x="{x + col * cw:.1f}" y="{y + (row + 1) * size}" '
                   f'style="animation-delay:{(n * 0.7) % 4:.1f}s">{escape(ch)}</text>')
    out.append('</g>')
    return '\n'.join(out)


def _svg(w, h, t, style, body, title, frame=True):
    rect = (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>\n'
            if frame else '')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}" font-family="{FONT}">
<title>{escape(title)}</title>
<style>
text {{ white-space: pre; }}
{style}
{REDUCED_MOTION}
</style>
{rect}{body}
</svg>
"""


def render_hero(theme):
    t = THEMES[theme]
    w, h = 1000, 330
    style = f"""
.moon .row {{ fill: {t['moon']}; animation: rise .9s cubic-bezier(.16,1,.3,1) backwards; }}
.moon .star {{ fill: {t['star']}; animation: twinkle 4s ease-in-out infinite; }}
.moon {{ filter: drop-shadow(0 0 6px {t['glow']}55); }}
.label {{ fill: {t['dim']}; font-size: 13px; letter-spacing: .14em; }}
.name {{ fill: {t['ink']}; font-size: 64px; font-weight: 700; letter-spacing: -.02em; }}
.cursor {{ fill: {t['moon']}; animation: blink 1.1s steps(1) infinite; }}
.role {{ fill: {t['ink']}; font-size: 17px; }}
.tag {{ fill: {t['moon']}; font-size: 17px; }}
.dim {{ fill: {t['dim']}; font-size: 14px; }}
.rule {{ stroke: {t['faint']}; }}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(6px); }} }}
@keyframes twinkle {{ 0%, 100% {{ opacity: .25; }} 50% {{ opacity: 1; }} }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}"""
    tx = 420
    body = f"""{moon_group(44, 18)}
<text class="label" x="{tx}" y="78">~/MXXNPY</text>
<text class="name" x="{tx - 4}" y="142">Ayu<tspan class="cursor">_</tspan></text>
<text class="role" x="{tx}" y="182">Full-stack software engineer · São Paulo, BR</text>
<line class="rule" x1="{tx}" y1="206" x2="{w - 48}" y2="206"/>
<text class="tag" x="{tx}" y="238">Software that keeps working after dark.</text>
<text class="dim" x="{tx}" y="268">Backend, interfaces, data and the infrastructure between them.</text>
<text class="label" x="{tx}" y="300">AYULE.DEV</text>"""
    return _svg(w, h, t, style, body, 'Ayu — full-stack software engineer. Crescent moon logo.')


def render_logo(theme):
    t = THEMES[theme]
    style = f""".moon .row {{ fill: {t['moon']}; }} .moon .star {{ fill: {t['star']}; animation: twinkle 4s ease-in-out infinite; }}
@keyframes twinkle {{ 0%, 100% {{ opacity: .25; }} 50% {{ opacity: 1; }} }}"""
    return _svg(360, 310, t, style, moon_group(24, 8, stagger=False), 'mxxn — crescent moon logo', frame=False)


def _fit(text, limit):
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def render_now_playing(theme, data):
    """Card de música. data: dict de spotify_tracker.format_current_playing()."""
    t = THEMES[theme]
    w, h = 1000, 120
    playing = bool(data.get('is_playing'))
    track = data.get('track') or ''
    artist = data.get('artist') or ''
    if not track or track == 'Nothing':
        label, track, artist = 'OFF AIR', 'Nothing playing right now', 'the moon is quiet tonight'
    else:
        label = 'NOW PLAYING' if playing else 'LAST PLAYED'
    anim = 'running' if playing else 'paused'
    # Parado: barras baixas e iguais, para não parecer que está tocando
    bar_rest = '' if playing else f".bar {{ animation: none; transform: scaleY(.12); opacity: .45; }}"
    style = f"""
.label {{ fill: {t['dim']}; font-size: 12px; letter-spacing: .16em; }}
.track {{ fill: {t['ink']}; font-size: 20px; font-weight: 700; }}
.artist {{ fill: {t['dim']}; font-size: 15px; }}
.disc {{ fill: none; stroke: {t['moon']}; }}
.hub {{ fill: {t['moon']}; }}
.spin {{ transform-origin: 72px 60px; animation: spin 3.2s linear infinite; animation-play-state: {anim}; }}
.bar {{ fill: {t['moon']}; transform-box: fill-box; transform-origin: bottom; animation: eq 1s ease-in-out infinite; animation-play-state: {anim}; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
@keyframes eq {{ 0%, 100% {{ transform: scaleY(.3); }} 50% {{ transform: scaleY(1); }} }}
{bar_rest}"""
    bars = '\n'.join(
        f'<rect class="bar" x="{w - 150 + i * 14}" y="40" width="8" height="40" rx="2" '
        f'style="animation-delay:-{(i * 0.37) % 1:.2f}s"/>' for i in range(7))
    body = f"""<g class="spin">
<circle class="disc" cx="72" cy="60" r="34" stroke-width="2"/>
<circle class="disc" cx="72" cy="60" r="24" stroke-width="1" opacity=".5"/>
<circle class="disc" cx="72" cy="60" r="15" stroke-width="1" opacity=".35"/>
<path class="hub" d="M72 52 a8 8 0 1 0 0 16 a6 6 0 1 1 0 -16 z"/>
</g>
<text class="label" x="134" y="40">{label}</text>
<text class="track" x="134" y="70">{escape(_fit(track, 62))}</text>
<text class="artist" x="134" y="94">{escape(_fit(artist, 78))}</text>
{bars}"""
    return _svg(w, h, t, style, body, f'{label.title()}: {track} — {artist}')


def write(name, content):
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, name)
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    if old != content:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
    return old != content


def write_now_playing(data):
    changed = False
    for theme in THEMES:
        changed |= write(f'now-playing-{theme}.svg', render_now_playing(theme, data))
    return changed


if __name__ == '__main__':
    for theme in THEMES:
        write(f'hero-{theme}.svg', render_hero(theme))
        write(f'logo-{theme}.svg', render_logo(theme))
    if not os.path.exists(os.path.join(ASSETS, 'now-playing-dark.svg')):
        write_now_playing({'track': 'Nothing'})
    print('assets ok')
