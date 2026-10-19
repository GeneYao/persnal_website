#!/usr/bin/env python3
"""Build mix detail pages (mix/<slug>/index.html) and archive/index.html from mixes.json.
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
        return ('\n  <section class="' + ('vibe has-m' if mob else 'vibe') + '">\n    <div class="vibe-grid">\n'
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
        'BACK_HREF': '../../#music' if is_latest else '../../archive/',
        'BACK_LABEL': 'GeneYao' if is_latest else 'Archive Mix',
        'EYEBROW': 'Latest Mix' if is_latest else 'Archive Mix',
        'TITLE': esc(title), 'WHEN_BLOCK': when, 'DUR_LINE': dur_line, 'DESC_BLOCK': desc,
        'CREDITS_BLOCK': credits, 'DUR': m['dur'],
        'SC_ENC': urllib.parse.quote(m['sc_url'], safe=''), 'SC_URL': m['sc_url'],
        'SPOTIFY_BTN': (yt_tpl.replace('{{YOUTUBE_URL}}', m['youtube']) if m.get('youtube') else '') + (spot_tpl.replace('{{SPOTIFY_URL}}', m['spotify']) if m.get('spotify') else ''),
        'VIDEO': video_html(m), 'TRACKLIST': tracklist, 'VIBE': vibe_html(m),
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

def build_archive():
    head = tpl[:tpl.index('<body>')]
    head = head.replace('mix/{{SLUG}}/', 'archive/').replace('photos/{{COVER}}', 'og-image.jpg')
    for k, v in {'TITLE_SHORT': 'Archive Mix', 'META_DESC': 'Archive Mix. Every DJ set by GeneYao, collected in one place.',
                 'TITLE_ATTR': 'Archive Mix', 'OG_DESC': 'Every DJ set by GeneYao, collected in one place.'}.items():
        head = head.replace('{{' + k + '}}', v)
    assert '{{' not in head
    head = head.replace('</style>', ARCHIVE_CSS + '</style>', 1)
    cards = ''
    for i, m in enumerate(mixes):
        badge = '<span class="badge">Latest</span>' if i == 0 else ''
        meta = m['dur'] + (f" · {len(m['tracks'])} TRACKS" if m['tracks'] else '')
        cards += (f'    <a class="acard" href="../mix/{m["slug"]}/">'
                  f'<div class="acover"><img src="../photos/{m["cover"]}" alt="{attr(m["title"])} artwork" loading="lazy">{badge}</div>'
                  f'<h3>{esc(m["title"])}</h3><div class="ameta">{meta}</div></a>\n')
    n = len(mixes)
    body = f'''<body>

<div class="lang-switch">
  <button type="button" class="lang-btn active" id="langZh">中</button>
  <span class="lang-sep">/</span>
  <button type="button" class="lang-btn" id="langEn">EN</button>
</div>

<div id="page" data-lang="zh">
<div class="wrap">
  <a class="back" href="../#music">
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M12 8H4M7.5 4L4 8l3.5 4"/></svg>
    <span>GeneYao</span>
  </a>

  <header class="arch-head">
    <h1>Archive Mix</h1>
  </header>

  <section class="arch-grid">
{cards}  </section>
</div>

<footer>
  <div class="wrap">
    <a class="wordmark" href="../">{re.search(r'<svg viewBox="0 0 32 32".*?</svg>', tpl, re.S).group(0)}<span>GeneYao</span></a>
    <div class="foot-icons">
      <a href="https://www.instagram.com/geneyaooo/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r="1" fill="currentColor" stroke="none"/></svg></a>
      <a href="mailto:contact@geneyao.com" aria-label="Email"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5.5" width="18" height="13" rx="3"/><path d="M4 8l8 5.5L20 8"/></svg></a>
    </div>
    <a class="fine" id="year-line" href="../">© GeneYao</a>
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
    d = os.path.join(ROOT, 'archive'); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(head + body)

for i, m in enumerate(mixes):
    build_detail(m, i)
build_archive()
print('built', len(mixes), 'mix pages + archive')
