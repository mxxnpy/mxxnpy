// Card "Now playing" gerado na hora a partir da API do Spotify.
// GET /?theme=dark|light  ->  image/svg+xml
// Secrets (wrangler secret put): SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
// Cores e medidas iguais às de THEMES/W/PAD em ../brand.py, que gera os outros painéis.

const W = 900;
const PAD = 48;
const CHAR = 0.6;
const GAP = 14;
const FONT = "ui-monospace, 'SFMono-Regular', 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace";
const CACHE_SECONDS = 15; // segura rajadas de visitas sem martelar a API do Spotify

const THEMES = {
  dark: { bg: '#0b0d17', border: '#1d2133', ink: '#e8e4d8', dim: '#8a90a8', moon: '#f1d79a' },
  light: { bg: '#f7f5ef', border: '#e2ddcf', ink: '#1c1e2a', dim: '#5f6477', moon: '#a87516' },
};

let token = { value: null, expiresAt: 0 };

async function accessToken(env) {
  if (token.value && Date.now() < token.expiresAt) return token.value;
  const response = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + btoa(`${env.SPOTIFY_CLIENT_ID}:${env.SPOTIFY_CLIENT_SECRET}`),
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({ grant_type: 'refresh_token', refresh_token: env.SPOTIFY_REFRESH_TOKEN }),
  });
  if (!response.ok) throw new Error(`token ${response.status}`);
  const data = await response.json();
  token = { value: data.access_token, expiresAt: Date.now() + (data.expires_in - 60) * 1000 };
  return token.value;
}

const info = (track) => ({ track: track.name, artist: track.artists.map((a) => a.name).join(', ') });
const same = (a, b) => a.track === b.track && a.artist === b.artist;

function previous(history, shown, count = 3) {
  const out = [];
  for (const item of history) {
    if (same(item, shown) || (out.length && same(item, out[out.length - 1]))) continue;
    out.push(item);
    if (out.length === count) break;
  }
  return out;
}

async function nowPlaying(env) {
  const headers = { Authorization: `Bearer ${await accessToken(env)}` };
  const [recentRes, currentRes] = await Promise.all([
    fetch('https://api.spotify.com/v1/me/player/recently-played?limit=6', { headers }),
    fetch('https://api.spotify.com/v1/me/player/currently-playing', { headers }),
  ]);
  if (!recentRes.ok) throw new Error(`recent ${recentRes.status}`);
  const history = ((await recentRes.json()).items || []).map((item) => info(item.track));

  // 204 = nada tocando; podcasts e anúncios chegam sem 'item' de música
  if (currentRes.status === 200) {
    const data = await currentRes.json();
    if (data.is_playing && data.currently_playing_type === 'track' && data.item) {
      const now = info(data.item);
      return { isPlaying: true, ...now, recent: previous(history, now) };
    }
  }
  if (history.length) return { isPlaying: false, ...history[0], recent: previous(history.slice(1), history[0]) };
  return null;
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const fit = (s, n) => (s.length <= n ? s : s.slice(0, n - 1).trimEnd() + '…');

function label(text, y) {
  const x1 = Math.round(PAD + text.length * 15 * (CHAR + 0.18) + 16);
  return `<text class="label" x="${PAD}" y="${y}">${esc(text)}</text>\n` +
    `<line class="rule" x1="${x1}" y1="${y - 5}" x2="${W - PAD}" y2="${y - 5}"/>`;
}

function render(theme, data) {
  const t = THEMES[theme] || THEMES.dark;
  const recent = (data && data.recent) || [];
  const h = 150 + (recent.length ? 76 + 30 * recent.length : 0);
  const playing = Boolean(data && data.isPlaying);
  let state = 'NOTHING PLAYING';
  let track = 'Nothing playing right now';
  let artist = 'Spotify is quiet';
  if (data) {
    state = playing ? 'NOW PLAYING' : 'LAST PLAYED';
    ({ track, artist } = data);
  }
  const anim = playing ? 'running' : 'paused';
  const barRest = playing ? '' : '.bar { animation: none; transform: scaleY(.12); opacity: .45; }';
  const cx = PAD + 34;
  const bars = Array.from({ length: 7 }, (_, i) =>
    `<rect class="bar" x="${W - PAD - 92 + i * 14}" y="84" width="8" height="40" rx="2" style="animation-delay:-${((i * 0.37) % 1).toFixed(2)}s"/>`).join('\n');
  const rows = recent.map((r, i) =>
    `<text x="${PAD}" y="${232 + i * 30}"><tspan class="idx">${String(i + 1).padStart(2, '0')}</tspan>` +
    `<tspan class="rtrack" dx="20">${esc(fit(r.track, 34))}</tspan>` +
    `<tspan class="rartist">  ${esc(fit(r.artist, 26))}</tspan></text>`).join('\n');
  const total = h + GAP;
  const title = `${state.charAt(0)}${state.slice(1).toLowerCase()}: ${track} by ${artist}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${total}" viewBox="0 0 ${W} ${total}" role="img" aria-label="${esc(title)}" font-family="${FONT}">
<title>${esc(title)}</title>
<style>
text { white-space: pre; }
.label { fill: ${t.dim}; font-size: 15px; letter-spacing: .18em; }
.rule { stroke: ${t.border}; }
.track { fill: ${t.ink}; font-size: 24px; font-weight: 700; }
.artist { fill: ${t.dim}; font-size: 19px; }
.idx { fill: ${t.dim}; font-size: 15px; }
.rtrack { fill: ${t.ink}; font-size: 19px; }
.rartist { fill: ${t.dim}; font-size: 19px; }
.disc { fill: none; stroke: ${t.moon}; }
.spin { transform-origin: ${cx}px 104px; animation: spin 3.2s linear infinite; animation-play-state: ${anim}; }
.bar { fill: ${t.moon}; transform-box: fill-box; transform-origin: bottom; animation: eq 1s ease-in-out infinite; animation-play-state: ${anim}; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes eq { 0%, 100% { transform: scaleY(.3); } 50% { transform: scaleY(1); } }
${barRest}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style>
<rect x="0.5" y="0.5" width="${W - 1}" height="${h - 1}" rx="16" fill="${t.bg}" stroke="${t.border}"/>
${label(state, 56)}
<g class="spin">
<circle class="disc" cx="${cx}" cy="104" r="34" stroke-width="2"/>
<circle class="disc" cx="${cx}" cy="104" r="22" stroke-width="1" opacity=".5"/>
<circle class="disc" cx="${cx}" cy="104" r="6" stroke-width="1"/>
</g>
<text class="track" x="${PAD + 96}" y="100">${esc(fit(track, 40))}</text>
<text class="artist" x="${PAD + 96}" y="128">${esc(fit(artist, 52))}</text>
${bars}
${recent.length ? label('BEFORE THAT', 190) + '\n' + rows : ''}
</svg>`;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const theme = url.searchParams.get('theme') === 'light' ? 'light' : 'dark';
    const cacheKey = new Request(`${url.origin}/?theme=${theme}`);
    const cache = caches.default;
    const cached = await cache.match(cacheKey);
    if (cached) return withNoStore(cached);

    let data = null;
    try {
      data = await nowPlaying(env);
    } catch (err) {
      // Sem o Spotify, mostra o card vazio em vez de imagem quebrada no perfil
      console.error('spotify', err.message);
    }
    const response = new Response(render(theme, data), {
      headers: { 'Content-Type': 'image/svg+xml; charset=utf-8', 'Cache-Control': `public, max-age=${CACHE_SECONDS}` },
    });
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return withNoStore(response);
  },
};

// Para o GitHub (camo) e o navegador, sempre buscar de novo; o cache curto fica só na borda da Cloudflare
function withNoStore(response) {
  const out = new Response(response.body, response);
  out.headers.set('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0');
  return out;
}
