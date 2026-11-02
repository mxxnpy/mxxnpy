"""
Painéis SVG do perfil (light/dark). O texto de cada painel fica em CONTENT.

    python brand.py            # regenera assets/

O card de música é gerado ao vivo pelo Worker em worker/ (mesmo visual).
"""
import math
import os
from xml.sax.saxutils import escape

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
FONT = "ui-monospace, 'SFMono-Regular', 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
W = 900          # largura de todos os painéis
PAD = 48
CHAR = 0.6       # largura de um caractere monoespaçado em em

THEMES = {
    'dark': dict(bg='#0b0d17', border='#1d2133', ink='#e8e4d8', dim='#8a90a8', faint='#3a3f55',
                 moon='#f1d79a', shadow='#262b40', star='#9aa3c7'),
    'light': dict(bg='#f7f5ef', border='#e2ddcf', ink='#1c1e2a', dim='#5f6477', faint='#cfc9b8',
                  moon='#a87516', shadow='#e3ddcd', star='#b3a77f'),
}

CONTENT = {
    'name': 'Ayu',
    'role': 'Full-stack engineer, São Paulo',
    'line': 'I build backend systems and the interfaces on top of them.',
    'about': [
        'I work mostly on the backend: APIs, databases, message queues, and the deploy and '
        'monitoring setup around them. I also do frontend work, mainly in Angular and React.',
        'Almost all of my work lives in private company repos, so what you see here are side '
        'projects. I\'m moving them to ayule.dev.',
        'Outside of work I play drums and guitar.',
    ],
    'stack': [
        ('Backend', 'C# / .NET, ASP.NET Core, Node.js, Python'),
        ('Frontend', 'TypeScript, Angular, React'),
        ('Data', 'PostgreSQL, SQL Server, RabbitMQ, Redis'),
        ('Infra', 'Docker, Kubernetes, AWS, GitHub Actions, Grafana'),
    ],
    'projects': [
        ('Conclave', 'One workspace for coding with several AI agents and for several clients at once.'),
        ('Marquee', 'Every show in your city from every ticket site, with a heads-up when your bands come.'),
        ('Adopt-A-Cat', 'Cat adoption, and the care that comes after it.'),
        ('Lumen', 'Research reports where every claim stays tied to its source.'),
        ('Doll Maker', 'Scripts and campaigns, built at AyuLab. Powered by Pulso.'),
    ],
    'buttons': [('ayule.dev', 'https://ayule.dev'),
                ('LinkedIn', 'https://www.linkedin.com/in/mxxnlea/'),
                ('Email', 'mailto:ayu.leandro@ayule.dev')],
}

REDUCED_MOTION = '@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }'


def wrap(text, size, width):
    """Quebra texto para caber em 'width' px numa fonte monoespaçada de 'size' px."""
    limit = int(width / (size * CHAR))
    lines, line = [], ''
    for word in text.split():
        if line and len(line) + 1 + len(word) > limit:
            lines.append(line)
            line = word
        else:
            line = f'{line} {word}'.strip()
    return lines + [line] if line else lines


GAP = 14         # respiro transparente abaixo de cada painel (o GitHub empilha as imagens coladas)


def svg(w, h, t, style, body, title, frame=True):
    rect = (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}"/>\n'
            if frame else '')
    total = h + (GAP if frame else 0)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{total}" viewBox="0 0 {w} {total}" role="img" aria-label="{escape(title)}" font-family="{FONT}">
<title>{escape(title)}</title>
<style>
text {{ white-space: pre; }}
.label {{ fill: {t['dim']}; font-size: 15px; letter-spacing: .18em; }}
.rule {{ stroke: {t['border']}; }}
{style}
{REDUCED_MOTION}
</style>
{rect}{body}
</svg>
"""


def label(text, y, w=W):
    return (f'<text class="label" x="{PAD}" y="{y}">{escape(text)}</text>\n'
            f'<line class="rule" x1="{PAD + len(text) * 15 * (CHAR + .18) + 16:.0f}" y1="{y - 5}" x2="{w - PAD}" y2="{y - 5}"/>')


# ---------- lua (provisória: retícula de pontos, até a logo nova) ----------
def moon_dots(cx, cy, r, t):
    bx, by, br = cx + 0.42 * r, cy - 0.16 * r, 0.88 * r
    step = r / 10
    out = []
    n = int(r / step) + 1
    for j in range(-n, n + 1):
        for i in range(-n, n + 1):
            x = cx + i * step + (step / 2 if j % 2 else 0)
            y = cy + j * step * 0.87
            if math.hypot(x - cx, y - cy) > r - step * 0.3:
                continue
            db = math.hypot(x - bx, y - by)
            if db > br + step * 0.25:
                v = min(1.0, (db - br) / (0.45 * r))
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{step * 0.46 * (0.4 + 0.6 * v):.2f}" fill="{t["moon"]}"/>')
    for k, (dx, dy, s) in enumerate([(1.15, -0.85, 2.2), (1.45, 0.25, 1.6), (0.75, 1.15, 1.4), (-1.2, -1.0, 1.4)]):
        out.append(f'<circle class="star" cx="{cx + dx * r:.1f}" cy="{cy + dy * r:.1f}" r="{s}" fill="{t["star"]}" '
                   f'style="animation-delay:{k * 0.9:.1f}s"/>')
    return '\n'.join(out)


# ---------- painéis ----------
def render_hero(theme):
    t = THEMES[theme]
    h = 300
    style = f"""
.name {{ fill: {t['ink']}; font-size: 76px; font-weight: 700; letter-spacing: -.02em; }}
.role {{ fill: {t['ink']}; font-size: 24px; }}
.line {{ fill: {t['dim']}; font-size: 20px; }}
.star {{ animation: twinkle 4s ease-in-out infinite; }}
@keyframes twinkle {{ 0%, 100% {{ opacity: .3; }} 50% {{ opacity: 1; }} }}"""
    tx = 330
    line = wrap(CONTENT['line'], 20, W - tx - PAD)
    body = f"""{moon_dots(165, 150, 92, t)}
<text class="name" x="{tx - 4}" y="138">{escape(CONTENT['name'])}</text>
<text class="role" x="{tx}" y="182">{escape(CONTENT['role'])}</text>
""" + '\n'.join(f'<text class="line" x="{tx}" y="{222 + i * 30}">{escape(l)}</text>' for i, l in enumerate(line))
    alt = f"{CONTENT['name']}. {CONTENT['role']}. {CONTENT['line']}"
    return svg(W, h, t, style, body, alt)


def render_about(theme):
    t = THEMES[theme]
    size, lh = 21, 34
    y = 84
    rows = []
    for para in CONTENT['about']:
        for l in wrap(para, size, W - 2 * PAD):
            rows.append(f'<text class="body" x="{PAD}" y="{y}">{escape(l)}</text>')
            y += lh
        y += 18
    style = f".body {{ fill: {t['ink']}; font-size: {size}px; }}"
    return svg(W, y + 20, t, style, label('ABOUT', 56) + '\n' + '\n'.join(rows), ' '.join(CONTENT['about']))


def render_stack(theme):
    t = THEMES[theme]
    col = PAD + 170
    y, rows = 100, []
    for i, (area, tools) in enumerate(CONTENT['stack']):
        if i:
            rows.append(f'<line class="rule" x1="{PAD}" y1="{y - 32}" x2="{W - PAD}" y2="{y - 32}"/>')
        rows.append(f'<text class="area" x="{PAD}" y="{y}">{escape(area)}</text>'
                    f'<text class="tools" x="{col}" y="{y}">{escape(tools)}</text>')
        y += 52
    style = f".area {{ fill: {t['dim']}; font-size: 19px; }} .tools {{ fill: {t['ink']}; font-size: 21px; }}"
    alt = 'Stack. ' + ' '.join(f'{a}: {b}.' for a, b in CONTENT['stack'])
    return svg(W, y - 4, t, style, label('STACK', 56) + '\n' + '\n'.join(rows), alt)


def render_projects(theme):
    t = THEMES[theme]
    col = PAD + 300
    y, rows = 100, []
    for i, (name, desc) in enumerate(CONTENT['projects']):
        if i:
            rows.append(f'<line class="rule" x1="{PAD}" y1="{y - 32}" x2="{W - PAD}" y2="{y - 32}"/>')
        name_lines = wrap(name, 21, 280)
        desc_lines = wrap(desc, 19, W - col - PAD)
        for k, l in enumerate(name_lines):
            rows.append(f'<text class="pname" x="{PAD}" y="{y + k * 28}">{escape(l)}</text>')
        for k, l in enumerate(desc_lines):
            rows.append(f'<text class="pdesc" x="{col}" y="{y + k * 28}">{escape(l)}</text>')
        y += 52 + 28 * (max(len(name_lines), len(desc_lines)) - 1)
    style = f".pname {{ fill: {t['ink']}; font-size: 21px; font-weight: 700; }} .pdesc {{ fill: {t['dim']}; font-size: 19px; }}"
    alt = 'Working on. ' + ' '.join(f'{n}: {d}' for n, d in CONTENT['projects'])
    return svg(W, y - 4, t, style, label('WORKING ON', 56) + '\n' + '\n'.join(rows), alt)


def button_width(text):
    return 40 + int(len(text) * 20 * CHAR) + 40


def render_button(theme, text):
    t = THEMES[theme]
    w, h = button_width(text), 56
    style = f".btn {{ fill: {t['ink']}; font-size: 20px; }} .arrow {{ fill: {t['moon']}; font-size: 20px; }}"
    body = (f'<text class="btn" x="22" y="35">{escape(text)}</text>'
            f'<text class="arrow" x="{w - 36}" y="35">↗</text>')
    return svg(w, h, t, style, body, text)


def render_footer(theme):
    t = THEMES[theme]
    style = '.star { animation: twinkle 4s ease-in-out infinite; } @keyframes twinkle { 0%, 100% { opacity: .3; } 50% { opacity: 1; } }'
    return svg(160, 140, t, style, moon_dots(80, 70, 44, t), 'Crescent moon logo', frame=False)


def write(name, content):
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, name)
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    if old != content:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
    return old != content


# Card ao vivo servido pelo Worker (worker/), mesmo visual dos painéis
NOW_PLAYING_URL = 'https://ayu-now-playing.ayule.workers.dev/?theme={theme}'


def _pic(src, alt, width='100%'):
    """<picture> com a variante escura e a clara; src recebe {theme}."""
    return (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{src.format(theme="dark")}">\n'
            f'  <img alt="{escape(alt, {chr(34): "&quot;"})}" src="{src.format(theme="light")}" width="{width}">\n</picture>')


def write_readme():
    c = CONTENT
    btns = '\n'.join(
        f'<a href="{url}">{_pic(f"assets/btn-{text.lower().replace(".", "")}-{{theme}}.svg", text, width=f"{button_width(text) / W * 100:.0f}%")}</a>'
        for text, url in c['buttons'])
    md = f"""{_pic('assets/hero-{theme}.svg', f"{c['name']}. {c['role']}. {c['line']}")}

{_pic('assets/about-{theme}.svg', ' '.join(c['about']))}

{_pic('assets/stack-{theme}.svg', 'Stack. ' + ' '.join(f'{a}: {b}.' for a, b in c['stack']))}

{_pic('assets/projects-{theme}.svg', 'Working on. ' + ' '.join(f'{n}: {d}' for n, d in c['projects']))}

{_pic(NOW_PLAYING_URL, 'What I am listening to on Spotify, and the three songs before it.')}

<p>
{btns}
</p>

<p align="center">
{_pic('assets/footer-{theme}.svg', 'Crescent moon logo', width='120')}
</p>
"""
    with open(os.path.join(os.path.dirname(ASSETS), 'README.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(md)


if __name__ == '__main__':
    for theme in THEMES:
        write(f'hero-{theme}.svg', render_hero(theme))
        write(f'about-{theme}.svg', render_about(theme))
        write(f'stack-{theme}.svg', render_stack(theme))
        write(f'projects-{theme}.svg', render_projects(theme))
        write(f'footer-{theme}.svg', render_footer(theme))
        for text, _ in CONTENT['buttons']:
            write(f'btn-{text.lower().replace(".", "")}-{theme}.svg', render_button(theme, text))
    write_readme()
    print('assets ok')
