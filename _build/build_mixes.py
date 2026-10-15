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

def vibe_html(m):
    v = m.get('vibe')
    if not v:
        return ''
    if v is True:
        return vibe
    if isinstance(v, dict):
        def col(items, cls):
            body = '\n'.join(f'        <img src="../../photos/{i["file"]}" alt="{attr(i["alt"])}" loading="lazy">' for i in items)
            return f'      <div class="{cls}">\n{body}\n      </div>'
        mid_cls = 'vcol mid' + (' mid2' if len(v['mid']) == 2 else '')
        return ('\n  <section class="vibe">\n    <div class="vibe-grid">\n'
                + col(v['left'], 'vcol') + '\n' + col(v['mid'], mid_cls) + '\n' + col(v['right'], 'vcol')
                + '\n    </div>\n  </section>\n')
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
    <div class="fine" id="year-line">© GeneYao</div>
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
