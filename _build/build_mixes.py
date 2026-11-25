#!/usr/bin/env python3
"""Build mix pages (mix/<slug>/), playlist pages (playlists/<slug>/) and archive/ from mixes.json and playlists.json.
Run from the repo root:  python3 _build/build_mixes.py
"""
import json, re, html, os, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, '_build')
mixes = json.load(open(os.path.join(B, 'mixes.json'), encoding='utf-8'))
tpl = open(os.path.join(B, 'template.html'), encoding='utf-8').read()
vibe = open(os.path.join(B, 'vibe_section.html'), encoding='utf-8').read()
spot_tpl = open(os.path.join(B, 'spotify_btn.html'), encoding='utf-8').read()
yt_tpl = open(os.path.join(B, 'youtube_btn.html'), encoding='utf-8').read()

playlists = json.load(open(os.path.join(B, 'playlists.json'), encoding='utf-8'))

esc = lambda s: html.escape(s, quote=False)
attr = lambda s: html.escape(s, quote=True)

def strip_tags(s): return re.sub(r'<[^>]+>', ' ', s).replace('  ', ' ').strip()

def _ratio(f):
    # width / height of a photo, read from the file header so the layout can balance column heights
    import struct
    with open(os.path.join(ROOT, 'photos', f), 'rb') as fh:
        d = fh.read(2)
        fh.seek(0); b = fh.read()
    i = 2
    while i < len(b):
        if b[i] != 0xFF: i += 1; continue
        mk = b[i + 1]
        if 0xC0 <= mk <= 0xCF and mk not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack('>HH', b[i + 5:i + 9]); return w / h
        i += 2 + struct.unpack('>H', b[i + 2:i + 4])[0]
    return 1.0

def mobile_html(items):
    """Phone layout: two columns of similar height; landscape or leftover photos become full-width rows."""
    import itertools
    n = len(items)
    if n < 2:
        return ''
    ar = [_ratio(it['file']) for it in items]
    gap = 0.06
    forced = [i for i, it in enumerate(items) if it.get('wide')]
    cands = list(range(n))
    best = None
    for k in range(len(forced), min(2, len(cands)) + 1):
        for bands in itertools.combinations(cands, k):
            if any(f not in bands for f in forced):
                continue
            rest = [i for i in range(n) if i not in bands]
            if len(rest) < 2:
                continue
            for mask in range(1, 2 ** len(rest) - 1):
                if not (mask & 1):
                    continue
                a = [rest[j] for j in range(len(rest)) if mask >> j & 1]
                b = [rest[j] for j in range(len(rest)) if not mask >> j & 1]
                ha = sum(1 / ar[i] for i in a) + gap * (len(a) - 1)
                hb = sum(1 / ar[i] for i in b) + gap * (len(b) - 1)
                cost = (abs(ha - hb) / max(ha, hb) + sum(0.10 if ar[i] >= 1.3 or i in forced else 0.16 for i in bands)
                        + 0.01 * abs(len(a) - len(b)))
                if best is None or cost < best[0] - 1e-9:
                    best = (cost, bands, a, b)
    if best is None:
        return ''
    _, bands, a, b = best
    img = lambda i, cls='': (f'<img src="../../photos/{items[i]["file"]}" alt="{attr(items[i]["alt"])}"'
                              + (f' class="{cls}"' if cls else '') + ' loading="lazy">')
    col = lambda ids: '        <div class="vm-col">\n' + '\n'.join('          ' + img(i) for i in ids) + '\n        </div>'
    out = '    <div class="vibe-m">\n      <div class="vm-cols">\n' + col(a) + '\n' + col(b) + '\n      </div>\n'
    for i in bands:
        out += '      ' + img(i, 'vm-band' if ar[i] >= 1.3 else 'vm-band vm-tall') + '\n'
    return out + '    </div>\n'

def vibe_html(m):
    v = m.get('vibe')
    if not v:
        return ''
    if v is True:
        out = vibe
        items = [{'file': f, 'alt': a} for f, a in re.findall(r'src="\.\./\.\./photos/([^"]+)" alt="([^"]*)"', vibe)]
        order = [0, 1, 3, 4, 2]  # keep the story order of the desktop columns
        items = [items[i] for i in order if i < len(items)] if len(items) == 5 else items
        mob = '' if m.get('mobile_legacy') else mobile_html(items)
        return out.replace('<section class="vibe">', '<section class="vibe has-m">', 1).replace('  </section>', mob + '  </section>', 1) if mob else out
    if isinstance(v, dict) and 'trio' in v:
        imgs = '\n'.join(f'      <img src="../../photos/{i["file"]}" alt="{attr(i["alt"])}" loading="lazy">' for i in v['trio'])
        mob = '' if m.get('mobile_legacy') else mobile_html(v['trio'])
        cls = 'vibe has-m' if mob else 'vibe'
        return f'\n  <section class="{cls}">\n    <div class="vibe-trio">\n{imgs}\n    </div>\n{mob}  </section>\n'
    if isinstance(v, dict):
        def col(items, cls):
            body = '\n'.join(f'        <img src="../../photos/{i["file"]}" alt="{attr(i["alt"])}"' + (' class="wide"' if i.get('wide') else '') + ' loading="lazy">' for i in items)
            return f'      <div class="{cls}">\n{body}\n      </div>'
        mid_cls = 'vcol mid' + (' mid2' if len(v['mid']) == 2 else (' midg' if len(v['mid']) >= 3 else ''))
        ordered = []
        for j in range(max(len(v['left']), len(v['mid']), len(v['right']))):
            for key in ('left', 'mid', 'right'):
                if j < len(v[key]):
                    ordered.append(v[key][j])
        mob = '' if m.get('mobile_legacy') else mobile_html(ordered)
        fr = f' style="grid-template-columns: 1fr {v["mid_fr"]}fr 1fr"' if v.get('mid_fr') else ''
        return ('\n  <section class="' + ('vibe has-m' if mob else 'vibe') + '">\n    <div class="vibe-grid"' + fr + '>\n'
                + col(v['left'], 'vcol') + '\n' + col(v['mid'], mid_cls) + '\n' + col(v['right'], 'vcol')
                + '\n    </div>\n' + mob + '  </section>\n')
    imgs = '\n'.join(f'      <img src="../../photos/{i["file"]}" alt="{attr(i["alt"])}" loading="lazy">' for i in v)
    return f'\n  <section class="vibe">\n    <div class="vibe-masonry">\n{imgs}\n    </div>\n  </section>\n'

def video_html(m):
    vid = m.get('youtube_embed')
    if not vid:
        return ''
    return ('  <section class="video-embed">\n    <div class="frame">\n'
            f'      <iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{attr(m["title"])} (YouTube)" loading="lazy" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>\n'
            '    </div>\n  </section>\n')

CURATION_CSS = '''  <style>
  .curation{ padding-block: 0 56px; }
  .curation h2{ font-size: 32px; margin-bottom: 24px; }
  .tracklist#sets{ padding-bottom: 56px; }
  .mix-hero .action-row{ margin-top: 22px; display:flex; flex-wrap:wrap; gap:10px; }
  .mix-hero .action-row .btn .arrow{ width:13px; height:13px; }
  .cur-grid{ list-style:none; margin: 0; padding:0; display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
  .cur-grid a{ display:flex; flex-direction:column; height:100%; padding:10px 10px 14px; background: var(--surface); border:1px solid var(--line); border-radius:18px; text-decoration:none; color: var(--ink); transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
  .cur-grid a:hover{ transform: translateY(-4px); border-color: var(--accent); box-shadow: var(--shadow); }
  .cur-grid li.dj a{ border-color: var(--accent); }
  .cur-grid img{ width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:10px; display:block; }
  .cur-grid .tm{ margin-top:12px; font-family:'IBM Plex Mono', monospace; font-size:12px; letter-spacing:.04em; color: var(--ink-soft); }
  .cur-grid h3{ margin-top:4px; font-size:21px; line-height:1.25; }
  .cur-grid .go{ margin-top:auto; padding-top:10px; display:flex; align-items:center; gap:6px; font-family:'IBM Plex Mono', monospace; font-size:11.5px; letter-spacing:.04em; color: var(--ink-soft); white-space:nowrap; }
  .cur-grid .go svg{ width:18px; height:18px; flex:none; }
  @media (max-width: 720px){ .cur-grid{ grid-template-columns: 1fr 1fr; gap: 12px; } .cur-grid h3{ font-size:18px; } }
  </style>
'''
SPOTIFY_DOT = '<svg viewBox="0 0 24 24" fill="#1DB954" aria-hidden="true"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>'

def both(zh, en):
    return f'<span class="lang-zh">{esc(zh)}</span><span class="lang-en">{esc(en)}</span>'

HEADPHONES = ('<svg viewBox="8 11 28 25" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true" style="color:var(--accent)">'
              '<path d="M12.5 25v-3a9.5 9.5 0 0 1 19 0v3"/><rect x="9.5" y="24" width="6.5" height="10" rx="3"/><rect x="28" y="24" width="6.5" height="10" rx="3"/></svg>')

def cards_html(items, mix=None):
    lis = ''
    for it in items:
        n = it['count']
        dj = ' class="dj"' if it.get('dj') else ''
        if it.get('dj') and mix:   # the DJ set slot opens the set page on this site
            link = f'href="../../mix/{mix}/"'
            go = f'{HEADPHONES}{both("DJ set 頁面", "DJ set page")} ↗'
        else:
            link = f'href="{attr(it["url"])}" target="_blank" rel="noopener"'
            go = f'{SPOTIFY_DOT}{both(f"{n} 首", f"{n} tracks")} ↗'
        lis += (f'      <li{dj}><a {link}>'
                f'<img src="../../photos/{it["cover"]}" alt="{attr(it["zh"])}歌單封面" loading="lazy">'
                f'<span class="tm">{it["time"]}</span><h3>{both(it["zh"], it["en"])}</h3>'
                f'<span class="go">{go}</span></a></li>\n')
    return f'    <ul class="cur-grid">\n{lis}    </ul>\n'

LINK_CSS = '''  <style>
  .tracklist{ padding-bottom: 48px; }
  .pl-block{ padding-bottom: 80px; }
  .pl-block h2{ font-size: 32px; margin-bottom: 24px; }
  .pl-intro{ margin: -10px 0 18px; max-width: 56ch; font-size:15px; line-height:1.8; color: var(--ink-soft); }
  .pl-link{ display:flex; align-items:center; gap:18px; margin: 0; padding:14px 18px 14px 14px; background: var(--surface); border:1px solid var(--line); border-radius:22px; text-decoration:none; color: var(--ink); transition: border-color .2s ease, transform .2s ease; }
  .pl-link:hover{ border-color: var(--accent); transform: translateY(-2px); }
  .pl-link .pl-thumb{ flex:0 0 auto; width:104px; height:104px; object-fit:cover; border-radius:12px; display:block; }
  .pl-link .head{ display:flex; flex-direction:column; gap:6px; flex:1; min-width:0; }
  .pl-link .title{ font-size:17px; line-height:1.45; }
  .pl-link .arrow{ flex:0 0 auto; width:15px; height:15px; color: var(--accent); }
  @media (max-width: 480px){ .pl-link{ gap:14px; padding-right:14px; } .pl-link .pl-thumb{ width:92px; height:92px; } .pl-link .title{ font-size:15.5px; } }
  </style>
'''
ARROW_SVG = '<svg class="arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 12L12 4M6 4h6v6"/></svg>'

def playlist_link_html(m):
    slug = m.get('playlist_page')
    if not slug:
        return ''
    p = next(x for x in playlists if x['slug'] == slug)
    intro = (f'  <p class="pl-intro">{both(p["segments_intro"]["zh"], p["segments_intro"]["en"])}</p>\n'
             if p.get('segments_intro') else '')
    return (LINK_CSS + '  <section class="pl-block">\n  <h2><span class="lang-zh">歌單策劃</span><span class="lang-en">Playlist Curation</span></h2>\n' + intro + f'  <a class="pl-link" href="../../playlists/{slug}/">\n'
            f'    <img class="pl-thumb" src="../../photos/{p["cover"]}" alt="" loading="lazy">\n'
            f'    <span class="head"><span class="title">{title_lines(p["title"])}</span></span>\n'
            f'    {ARROW_SVG}\n  </a>\n  </section>\n')

def track_lis(tracks, times=None):
    times = times or [''] * len(tracks)
    return '\n'.join(f'        <li><span class="no">{i}.</span><span class="tx">{esc(t)}</span>' + (f'<span class="tm">{tm}</span>' if tm else '') + '</li>'
                     for i, (t, tm) in enumerate(zip(tracks, times), 1))

SETS_CSS = '''  <style>
  .tl-tabs{ display:grid; grid-template-columns: repeat(4, 1fr); margin-top: 22px; border-bottom:1px solid var(--line); }
  .tl-tabs button{ display:flex; flex-direction:column; align-items:center; gap:3px; margin:0 0 -1px; padding:8px 4px 12px; border:0; border-bottom:2px solid transparent; border-radius:0; background:transparent; color: var(--ink-soft); font-family:inherit; cursor:pointer; transition: color .2s ease, border-color .2s ease; }
  .tl-tabs button:hover{ color: var(--ink); }
  .tl-tabs .n{ font-size:15.5px; white-space:nowrap; }
  .tl-tabs .t{ font-family:'IBM Plex Mono', monospace; font-size:11px; letter-spacing:.04em; color: var(--ink-soft); }
  .tl-tabs button[aria-selected="true"]{ color: var(--ink); border-bottom-color: var(--accent); }
  .tl-tabs button[aria-selected="true"] .n{ font-weight:700; }
  .tl-tabs button[aria-selected="true"] .t{ color: var(--accent); }
  .tl-info{ display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px 16px; margin: 18px 0 0; font-family:'IBM Plex Mono', monospace; font-size:12.5px; letter-spacing:.04em; color: var(--ink-soft); }
  .tl-info a{ color: var(--accent); text-decoration:none; }
  .tracklist .tl-panel ol{ margin-top: 14px; }
  .tl-panel[hidden]{ display:none; }
  </style>
'''
SETS_JS = '''    <script>
    (function(){
      var box = document.getElementById('sets');
      var tabs = box.querySelectorAll('.tl-tabs button');
      tabs.forEach(function(b){ b.addEventListener('click', function(){
        tabs.forEach(function(t){ var on = t === b; t.setAttribute('aria-selected', on); document.getElementById(t.getAttribute('aria-controls')).hidden = !on; });
      }); });
    })();
    </script>
'''

def sets_html(p):
    """Playlist page tracklist with one tab per time slot (first slot selected). The DJ set slot uses the mix's own tracks."""
    tabs = panels = ''
    for i, it in enumerate(p['items']):
        on = i == 0
        dj = bool(it.get('dj'))
        tracks = next(x for x in mixes if x['slug'] == p['mix'])['tracks'] if dj else it['tracks']
        n = len(tracks)
        start = it['time'].split('–')[0]
        kind = ' · DJ SET' if dj else ''
        tabs += (f'      <button type="button" role="tab" id="tab-{i}" aria-controls="set-{i}" aria-selected="{str(on).lower()}">'
                 f'<span class="n">{both(it["zh"], "Fire" if dj else it["en"])}</span><span class="t">{start}</span></button>\n')
        panels += (f'    <div class="tl-panel" role="tabpanel" id="set-{i}" aria-labelledby="tab-{i}"{"" if on else " hidden"}>\n'
                   f'      <p class="tl-info"><span>{it["time"]} · {both(f"{n} 首", f"{n} tracks")}{kind}</span>'
                   f'<a href="{attr(it["url"])}" target="_blank" rel="noopener">{both("在 Spotify 收聽", "Listen on Spotify")} ↗</a></p>\n'
                   f'      <ol>\n{track_lis(tracks)}\n      </ol>\n    </div>\n')
    return (SETS_CSS + '  <section class="tracklist" id="sets">\n'
            '    <h2><span class="lang-zh">曲目清單</span><span class="lang-en">Tracklist</span></h2>\n'
            f'    <div class="tl-tabs" role="tablist">\n{tabs}    </div>\n{panels}{SETS_JS}  </section>\n')

def build_detail(m, idx):
    title = m['title']
    short = title.split(' | ')[0]
    first_en = strip_tags(m['desc_en'][0]) if m['desc_en'] else ''
    og_desc = (first_en[:180] + '…') if len(first_en) > 180 else (first_en or 'A DJ set by GeneYao.')
    meta_desc = f"{title}. {og_desc}"
    is_latest = idx == 0
    when = ''
    if m.get('when'):
        when = ('      <div class="meta when">\n'
                f'        <span class="lang-zh">{esc(m["when"]["zh"])}</span>\n'
                f'        <span class="lang-en">{esc(m["when"]["en"])}</span>\n'
                '      </div>\n')
    dur_line = m['dur'] + (f" · {len(m['tracks'])} TRACKS" if m['tracks'] else '')
    desc = ''
    for z, e in zip(m['desc_zh'] + [''] * 9, m['desc_en']):
        desc += f'      <p class="desc lang-zh">{z or e}</p>\n      <p class="desc lang-en">{e}</p>\n'
    credits = ''.join(
        f'      <p class="credit lang-zh">{esc(c["zh"])}</p>\n      <p class="credit lang-en">{esc(c["en"])}</p>\n'
        for c in m['credits'])
    if m['tracks']:
        times = m.get('times') or [''] * len(m['tracks'])
        lis = '\n'.join(f'        <li><span class="no">{i}.</span><span class="tx">{esc(t)}</span>' + (f'<span class="tm">{tm}</span>' if tm else '') + '</li>'
                        for i, (t, tm) in enumerate(zip(m['tracks'], times), 1))
        tracklist = ('  <section class="tracklist">\n'
                     '    <h2><span class="lang-zh">曲目清單</span><span class="lang-en">Tracklist</span></h2>\n'
                     f'    <ol>\n{lis}\n    </ol>\n  </section>\n')
    else:
        tracklist = ''
    out = tpl
    sub = {
        'TITLE_SHORT': esc(short), 'META_DESC': attr(meta_desc), 'TITLE_ATTR': attr(title), 'OG_DESC': attr(og_desc),
        'SLUG': m['slug'], 'COVER': m['cover'],
        'BACK_HREF': '../../archive/',
        'BACK_LABEL': 'Archive Mixes',
        'EYEBROW': 'Latest Mix' if is_latest else 'Archive Mix',
        'TITLE': esc(title), 'WHEN_BLOCK': when, 'DUR_LINE': dur_line, 'DESC_BLOCK': desc,
        'CREDITS_BLOCK': credits, 'DUR': m['dur'],
        'SC_ENC': urllib.parse.quote(m['sc_url'], safe=''), 'SC_URL': m['sc_url'],
        'SPOTIFY_BTN': (yt_tpl.replace('{{YOUTUBE_URL}}', m['youtube']) if m.get('youtube') else '') + (spot_tpl.replace('{{SPOTIFY_URL}}', m['spotify']) if m.get('spotify') else ''),
        'VIDEO': video_html(m), 'TRACKLIST': tracklist + playlist_link_html(m), 'VIBE': vibe_html(m),
        'WAVE': json.dumps(m['wave']),
    }
    for k, v in sub.items():
        out = out.replace('{{' + k + '}}', v)
    assert '{{' not in out, re.findall(r'\{\{[A-Z_]+\}\}', out)
    d = os.path.join(ROOT, 'mix', m['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)

ARCHIVE_CSS = '''
  .arch-head{ padding-block: 28px 8px; }
  .arch-head h1{ font-size: clamp(38px, 6vw, 64px); line-height:1.02; }
  .arch-head p{ margin: 14px 0 0; color: var(--ink-soft); max-width: 52ch; }
  .arch-tabs{ display:flex; gap:10px; margin-top: 22px; }
  .arch-tabs button{ padding:10px 18px; border-radius:999px; border:1px solid var(--line); background:transparent; color: var(--ink-soft); font-family:'IBM Plex Mono', monospace; font-size:12.5px; letter-spacing:.08em; text-transform:uppercase; cursor:pointer; }
  .arch-tabs button i{ font-style:normal; opacity:.6; margin-left:4px; }
  .arch-tabs button[aria-selected="true"]{ background: var(--accent); border-color: var(--accent); color: var(--bg); }
  .arch-grid[hidden]{ display:none; }
  .arch-grid{ display:grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 26px 20px; padding-block: 36px 88px; }
  .acard{ display:block; text-decoration:none; color: var(--ink); }
  .acard .acover{ position:relative; aspect-ratio:1/1; border-radius:20px; overflow:hidden; border:1px solid var(--line); box-shadow: var(--shadow); transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
  .acard img{ width:100%; height:100%; object-fit:cover; }
  .acard:hover .acover{ transform: translateY(-4px); border-color: var(--accent); }
  .acard h3{ font-size: 21px; line-height:1.15; margin-top: 14px; }
  .acard:hover h3{ color: var(--accent); }
  .acard .ameta{ margin-top: 6px; font-family:'IBM Plex Mono', monospace; font-size:12px; letter-spacing:.05em; color: var(--ink-soft); }
  .acard .badge{ position:absolute; left:10px; top:10px; padding:4px 10px; border-radius:999px; background: var(--bg); color: var(--accent); font-family:'IBM Plex Mono', monospace; font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; }
  @media (max-width: 560px){ .arch-grid{ grid-template-columns: 1fr 1fr; gap: 20px 12px; } .acard h3{ font-size:17px; } .acard .acover{ border-radius:14px; } }
'''

def write_page(rel, title, desc, og_image, back_href, back_label, main, tail='</div>\n'):
    """A listing-style page: shared head, back link, content, footer and language switch."""
    up = '../' * rel.count('/')
    head = tpl[:tpl.index('<body>')]
    head = head.replace('mix/{{SLUG}}/', rel).replace('photos/{{COVER}}', og_image)
    for k, v in {'TITLE_SHORT': esc(title), 'META_DESC': attr(desc), 'TITLE_ATTR': attr(title), 'OG_DESC': attr(desc)}.items():
        head = head.replace('{{' + k + '}}', v)
    assert '{{' not in head
    head = head.replace('</style>', ARCHIVE_CSS + '</style>', 1)
    body = f'''<body>

<div class="lang-switch">
  <button type="button" class="lang-btn active" id="langZh">中</button>
  <span class="lang-sep">/</span>
  <button type="button" class="lang-btn" id="langEn">EN</button>
</div>

<div id="page" data-lang="zh">
<div class="wrap">
  <a class="back" href="{back_href}">
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M12 8H4M7.5 4L4 8l3.5 4"/></svg>
    {re.search(r'<svg viewBox="0 0 32 32".*?</svg>', tpl, re.S).group(0).replace('<svg ', '<svg class="logo" aria-hidden="true" ', 1)}
    <span>{back_label}</span>
  </a>

{main}{tail}
<footer>
  <div class="wrap">
    <a class="wordmark" href="{up}">{re.search(r'<svg viewBox="0 0 32 32".*?</svg>', tpl, re.S).group(0)}<span>GeneYao</span></a>
    <div class="foot-icons">
      <a href="https://www.instagram.com/geneyaooo/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r="1" fill="currentColor" stroke="none"/></svg></a>
      <a href="mailto:contact@geneyao.com" aria-label="Email"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5.5" width="18" height="13" rx="3"/><path d="M4 8l8 5.5L20 8"/></svg></a>
    </div>
    <a class="fine" id="year-line" href="{up}">© GeneYao</a>
  </div>
</footer>
</div>

<script>
  try{{ document.getElementById('year-line').textContent = '© ' + new Date().getFullYear() + ' GeneYao'; }}catch(e){{}}
  try{{
    const page = document.getElementById('page');
    const btnZh = document.getElementById('langZh');
    const btnEn = document.getElementById('langEn');
    function setLang(lang){{
      page.dataset.lang = lang;
      document.documentElement.lang = lang === 'en' ? 'en' : 'zh-Hant';
      btnZh.classList.toggle('active', lang === 'zh');
      btnEn.classList.toggle('active', lang === 'en');
      try{{ localStorage.setItem('geneyao-lang', lang); }}catch(e){{}}
    }}
    btnZh.addEventListener('click', ()=> setLang('zh'));
    btnEn.addEventListener('click', ()=> setLang('en'));
    try{{ if(localStorage.getItem('geneyao-lang') === 'en') setLang('en'); }}catch(e){{}}
  }}catch(e){{}}
</script>
</body>
</html>
'''
    d = os.path.join(ROOT, rel); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(head + body)

TABS_JS = '''  <script>
  (function(){
    var tabs = document.querySelectorAll('.arch-tabs button');
    function show(name){
      tabs.forEach(function(t){ var on = t.dataset.tab === name; t.setAttribute('aria-selected', on); document.getElementById(t.dataset.tab).hidden = !on; });
    }
    tabs.forEach(function(t){ t.addEventListener('click', function(){ show(t.dataset.tab); try{ history.replaceState(null, '', t.dataset.tab === 'playlists' ? '#playlists' : location.pathname); }catch(e){} }); });
    window.addEventListener('hashchange', function(){ show(location.hash === '#playlists' ? 'playlists' : 'mixes'); });
    show(location.hash === '#playlists' ? 'playlists' : 'mixes');
  })();
  </script>
'''

def build_archive():
    cards = ''
    for i, m in enumerate(mixes):
        badge = '<span class="badge">Latest</span>' if i == 0 else ''
        meta = m['dur'] + (f" · {len(m['tracks'])} TRACKS" if m['tracks'] else '')
        cards += (f'    <a class="acard" href="../mix/{m["slug"]}/">'
                  f'<div class="acover"><img src="../photos/{m["cover"]}" alt="{attr(m["title"])} artwork" loading="lazy">{badge}</div>'
                  f'<h3>{esc(m["title"])}</h3><div class="ameta">{meta}</div></a>\n')
    pcards = ''
    for p in playlists:
        n = sum(it['count'] for it in p['items'])
        pcards += (f'    <a class="acard" href="../playlists/{p["slug"]}/">'
                   f'<div class="acover"><img src="../photos/{p["cover"]}" alt="{attr(p["title"]["zh"])} 封面" loading="lazy"></div>'
                   f'<h3>{title_lines(p["title"])}</h3>'
                   f'<div class="ameta">{len(p["items"])} PLAYLISTS · {n} TRACKS</div></a>\n')
    main = ('  <header class="arch-head">\n    <h1>Archive Mixes/<wbr>Playlists</h1>\n  </header>\n\n'
            '  <div class="arch-tabs" role="tablist">\n'
            f'    <button type="button" role="tab" data-tab="mixes" aria-selected="true">Mixes <i>{len(mixes)}</i></button>\n'
            f'    <button type="button" role="tab" data-tab="playlists" aria-selected="false">Playlists <i>{len(playlists)}</i></button>\n'
            '  </div>\n\n'
            f'  <section class="arch-grid" id="mixes">\n{cards}  </section>\n'
            f'  <section class="arch-grid" id="playlists" hidden>\n{pcards}  </section>\n' + TABS_JS)
    write_page('archive/', 'Archive Mixes/Playlists', 'Every DJ set and curated playlist by GeneYao, collected in one place.',
               'og-image.jpg', '../#music', 'GeneYao', main)

def title_lines(t):
    zh = '<br>'.join(esc(x) for x in t['zh'].split('｜'))
    return f'<span class="lang-zh">{zh}</span><span class="lang-en">{esc(t["en"])}</span>'

def mix_tail():
    """Same closing blocks as a DJ set page: more mixes button, newsletter card, contact (closes the .wrap div)."""
    return tpl[tpl.index('  <section class="more">'):tpl.index('<footer>')]

def build_playlist(p):
    """Header laid out like a DJ set page (cover left, details right), then the slot cards and tracklists."""
    n = sum(it['count'] for it in p['items'])
    btns = ''
    if p.get('full'):
        icon = re.search(r'<svg.*?</svg>', spot_tpl, re.S).group(0)
        btns += f'        <a class="btn solid" href="{attr(p["full"]["url"])}" target="_blank" rel="noopener">{icon}{both("全天歌單", "Full day playlist")}</a>\n'
    if p.get('mix'):
        btns += f'        <a class="btn" href="../../mix/{p["mix"]}/">{both("聽當天的 DJ set 錄音", "Listen to the DJ set recording")} {ARROW_SVG}</a>\n'
    actions = f'      <div class="action-row">\n{btns}      </div>\n' if btns else ''
    main = (CURATION_CSS + '  <section class="mix-hero">\n'
            f'    <div class="cover"><img src="../../photos/{p["cover"]}" alt="{attr(p["title"]["zh"])} 封面"></div>\n'
            '    <div>\n      <p class="eyebrow">Playlist Curation</p>\n'
            f'      <h1>{title_lines(p["title"])}</h1>\n'
            f'      <div class="meta when">{both(p["when"]["zh"], p["when"]["en"])}</div>\n'
            f'      <div class="meta dur">{len(p["items"])} PLAYLISTS · {n} TRACKS</div>\n'
            f'      <p class="desc">{both(p["intro"]["zh"], p["intro"]["en"])}</p>\n'
            '      <p class="credit">Presented by GeneYao</p>\n'
            + actions + '    </div>\n  </section>\n'
            '  <section class="curation">\n    <h2><span class="lang-zh">分段歌單</span><span class="lang-en">Playlists by Time Slot</span></h2>\n'
            + cards_html(p['items'], p.get('mix')) + '  </section>\n' + sets_html(p) + vibe_html(p))
    write_page(f'playlists/{p["slug"]}/', p['title']['zh'], p['intro']['zh'], 'photos/' + p['cover'],
               '../../archive/#playlists', 'Playlists', main, mix_tail())

for i, m in enumerate(mixes):
    build_detail(m, i)
for p in playlists:
    build_playlist(p)
build_archive()
print('built', len(mixes), 'mix pages +', len(playlists), 'playlist pages + archive')
