#!/usr/bin/env python3
"""Build the weekly "Five Songs" pages, the archive page and newsletter text.

Usage (from repo root):
  python3 _build/build_songs.py                       # real data -> songs/
  python3 _build/build_songs.py --data X.json --out DIR   # preview build elsewhere

Data file: a list of weeks, newest first or any order:
  {"date": "2026-10-23", "intro_zh": "...", "intro_en": "...",
   "songs": [{"title": "...", "artist": "...", "blurb_zh": "...", "blurb_en": "...",
              "link": "https://open.spotify.com/track/...", "cover": "optional file name"}]}
Album covers are fetched from the public iTunes search and saved to photos/songs/.
"""
import argparse, datetime, html, json, os, re, subprocess, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, '_build')
ap = argparse.ArgumentParser()
ap.add_argument('--data', default=os.path.join(B, 'songs.json'))
ap.add_argument('--out', default=ROOT)
args = ap.parse_args()
OUT = args.out
weeks = json.load(open(args.data, encoding='utf-8'))
weeks.sort(key=lambda w: w['date'], reverse=True)

tpl = open(os.path.join(B, 'template.html'), encoding='utf-8').read()
HEAD = tpl[:tpl.index('<body>')]
ICON = re.search(r'<svg viewBox="0 0 32 32".*?</svg>', tpl, re.S).group(0)
esc = lambda s: html.escape(s, quote=False)
attr = lambda s: html.escape(s, quote=True)

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40] or 'song'

def fetch_cover(song):
    """Return cover file name inside photos/songs/ (downloads if missing)."""
    if song.get('cover'):
        return song['cover']
    name = slug(song['artist'] + '-' + song['title']) + '.jpg'
    dest_dir = os.path.join(OUT, 'photos', 'songs')
    dest = os.path.join(dest_dir, name)
    if os.path.exists(dest):
        return name
    os.makedirs(dest_dir, exist_ok=True)
    q = urllib.parse.urlencode({'term': f"{song['artist']} {song['title']}", 'entity': 'song', 'limit': 1})
    data = json.load(urllib.request.urlopen(f'https://itunes.apple.com/search?{q}'))
    if not data['results']:
        raise SystemExit(f"No cover found for {song['artist']} - {song['title']}; set song['cover'] manually")
    url = data['results'][0]['artworkUrl100'].replace('100x100bb', '600x600bb')
    open(dest, 'wb').write(urllib.request.urlopen(url).read())
    subprocess.run(['sips', '-Z', '600', '-s', 'formatOptions', '72', dest], capture_output=True)
    return name

def weekday(d):
    return datetime.date.fromisoformat(d).strftime('%a').upper()

def fmt(d):
    return d.replace('-', '.') + ' ' + weekday(d)

CSS = '''
  .songs-head{ padding-block: 28px 8px; }
  .songs-head h1{ font-size: clamp(38px, 6vw, 64px); line-height:1.02; }
  .songs-head .meta{ margin-top:12px; font-family:'IBM Plex Mono', monospace; font-size:13px; letter-spacing:.06em; color: var(--accent); }
  .songs-head .intro{ margin: 16px 0 0; max-width: 56ch; color: var(--ink-soft); font-size:16px; line-height:1.8; }
  .song-list{ margin: 36px 0 0; padding:0; list-style:none; border-top:1px solid var(--line); }
  .song{ display:grid; grid-template-columns: 36px 132px 1fr; gap: 20px; align-items:center; padding: 22px 0; border-bottom:1px solid var(--line); }
  .song .no{ font-family:'IBM Plex Mono', monospace; font-size:14px; color: var(--accent); }
  .song img{ width:132px; height:132px; object-fit:cover; border-radius:14px; border:1px solid var(--line); box-shadow: var(--shadow); }
  .song h3{ font-size: 26px; line-height:1.15; }
  .song .artist{ margin-top:6px; font-family:'IBM Plex Mono', monospace; font-size:12.5px; letter-spacing:.05em; color: var(--ink-soft); }
  .song .blurb{ margin: 12px 0 0; font-size:15.5px; line-height:1.8; max-width:60ch; }
  .song .go{ margin-top:12px; display:inline-flex; align-items:center; gap:6px; font-family:'IBM Plex Mono', monospace; font-size:12px; letter-spacing:.08em; text-transform:uppercase; color: var(--accent); text-decoration:none; }
  .song .go svg{ width:13px; height:13px; transition: transform .2s ease; }
  .song .go:hover svg{ transform: translate(2px,-2px); }
  .week-nav{ display:flex; justify-content:space-between; gap:16px; padding-block: 28px 80px; font-family:'IBM Plex Mono', monospace; font-size:12.5px; letter-spacing:.06em; text-transform:uppercase; }
  .week-nav a{ text-decoration:none; color: var(--ink-soft); }
  .week-nav a:hover{ color: var(--accent); }
  .week-nav a.all{ display:inline-flex; align-items:center; gap:6px; padding: 9px 16px; border:1px solid var(--line); border-radius:999px; color: var(--accent); transition: border-color .2s ease; }
  .week-nav a.all:hover{ border-color: var(--accent); }
  .week-nav a.all svg{ width:13px; height:13px; transition: transform .2s ease; }
  .week-nav a.all:hover svg{ transform: translate(2px,-2px); }
  .week-list{ margin: 32px 0 0; padding:0; list-style:none; border-top:1px solid var(--line); }
  .week-row{ display:grid; grid-template-columns: 150px 1fr; gap:20px; align-items:center; padding: 20px 0; border-bottom:1px solid var(--line); text-decoration:none; color: var(--ink); }
  .week-row:hover .wd{ color: var(--ink); }
  .week-row .wd{ font-family:'IBM Plex Mono', monospace; font-size:14px; color: var(--accent); transition: color .2s ease; }
  .week-row .strip{ display:flex; gap:8px; flex-wrap:wrap; }
  .week-row .names{ margin-top:8px; font-size:14px; color: var(--ink-soft); }
  .week-row .strip img{ width:56px; height:56px; object-fit:cover; border-radius:8px; border:1px solid var(--line); }
  @media (max-width: 640px){
    .song{ grid-template-columns: 96px 1fr; gap: 14px; align-items:start; }
    .song .no{ display:none; }
    .song img{ width:96px; height:96px; border-radius:10px; }
    .song h3{ font-size: 21px; }
    .week-row{ grid-template-columns: 1fr; gap:10px; }
  }
'''

def page_shell(title, desc, url, body_main, back_href):
    head = HEAD
    for k, v in {'TITLE_SHORT': esc(title), 'META_DESC': attr(desc), 'TITLE_ATTR': attr(title), 'OG_DESC': attr(desc)}.items():
        head = head.replace('{{' + k + '}}', v)
    head = head.replace('mix/{{SLUG}}/', url).replace('photos/{{COVER}}', 'og-image.jpg')
    assert '{{' not in head, re.findall(r'\{\{[A-Z_]+\}\}', head)
    head = head.replace('</style>', CSS + '</style>', 1)
    return head + f'''<body>

<div class="lang-switch">
  <button type="button" class="lang-btn active" id="langZh">中</button>
  <span class="lang-sep">/</span>
  <button type="button" class="lang-btn" id="langEn">EN</button>
</div>

<div id="page" data-lang="zh">
<div class="wrap">
  <a class="back" href="{back_href}">
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M12 8H4M7.5 4L4 8l3.5 4"/></svg>
    <span>GeneYao</span>
  </a>
{body_main}
</div>

<footer>
  <div class="wrap">
    <a class="wordmark" href="{back_href}">{ICON}<span>GeneYao</span></a>
    <div class="foot-icons">
      <a href="https://www.instagram.com/geneyaooo/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r="1" fill="currentColor" stroke="none"/></svg></a>
      <a href="mailto:geneyao0302@gmail.com" aria-label="Email"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5.5" width="18" height="13" rx="3"/><path d="M4 8l8 5.5L20 8"/></svg></a>
    </div>
    <a class="fine" id="year-line" href="{back_href}">© GeneYao</a>
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

ARROW = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 12L12 4M6 4h6v6"/></svg>'

def build_week(i, w):
    covers = [fetch_cover(s) for s in w['songs']]
    lis = ''
    for n, (s, c) in enumerate(zip(w['songs'], covers), 1):
        blurb = ''
        if s.get('blurb_zh'):
            blurb += f'      <p class="blurb lang-zh">{esc(s["blurb_zh"])}</p>\n'
        if s.get('blurb_en'):
            blurb += f'      <p class="blurb lang-en">{esc(s["blurb_en"])}</p>\n'
        go = (f'      <a class="go" href="{attr(s["link"])}" target="_blank" rel="noopener">'
              f'<span class="lang-zh">在 YouTube 收聽</span><span class="lang-en">Listen on YouTube</span>{ARROW}</a>\n') if s.get('link') else ''
        lis += (f'    <li class="song">\n      <div class="no">{n:02d}</div>\n'
                f'      <img src="../../photos/songs/{c}" alt="{attr(s["title"])} album cover" loading="lazy">\n'
                f'      <div>\n      <h3>{esc(s["title"])}</h3>\n      <div class="artist">{esc(s["artist"])}</div>\n{blurb}{go}      </div>\n    </li>\n')
    intro = ''
    if w.get('intro_zh'):
        intro += f'    <p class="intro lang-zh">{esc(w["intro_zh"])}</p>\n'
    if w.get('intro_en'):
        intro += f'    <p class="intro lang-en">{esc(w["intro_en"])}</p>\n'
    newer = weeks[i - 1] if i > 0 else None
    older = weeks[i + 1] if i + 1 < len(weeks) else None
    nav = '  <nav class="week-nav">\n'
    nav += (f'    <a href="../{older["date"]}/">← {older["date"].replace("-", ".")}</a>\n' if older else '    <span></span>\n')
    nav += f'    <a class="all" href="../">Archive {ARROW}</a>\n'
    nav += (f'    <a href="../{newer["date"]}/">{newer["date"].replace("-", ".")} →</a>\n' if newer else '    <span></span>\n')
    nav += '  </nav>'
    main = (f'  <header class="songs-head">\n    <p class="eyebrow">Five Songs for This Week</p>\n    <h1>{fmt(w["date"])}</h1>\n'
            f'{intro}  </header>\n'
            f'  <ol class="song-list">\n{lis}  </ol>\n{nav}')
    desc = f"Five Songs for This Week, {w['date'].replace('-', '.')}: " + ', '.join(s['title'] for s in w['songs'])
    out = page_shell(f"Five Songs for This Week {w['date'].replace('-', '.')}", desc, f"songs/{w['date']}/", main, '../../')
    d = os.path.join(OUT, 'songs', w['date']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)

    # newsletter text (markdown, paste into Buttondown)
    lines = [f"# Five Songs for This Week {w['date'].replace('-', '.')}", '']
    if w.get('intro_zh'): lines += [w['intro_zh'], '']
    if w.get('intro_en'): lines += [w['intro_en'], '']
    for n, (s, c) in enumerate(zip(w['songs'], covers), 1):
        lines += [f"## {n}. {s['title']}", f"**{s['artist']}**", '']
        lines += [f"![{s['title']}](https://geneyao.com/photos/songs/{c})", '']
        if s.get('blurb_zh'): lines += [s['blurb_zh'], '']
        if s.get('blurb_en'): lines += [s['blurb_en'], '']
        if s.get('link'): lines += [f"[在 YouTube 收聽 ↗]({s['link']})", '']
    lines += ['---', '', '<p style="text-align:center; margin:32px 0;"><a href="https://geneyao.com/songs/" style="display:inline-block; padding:12px 28px; background-color:#4F6142; border:1.5px solid #4F6142; border-radius:999px; color:#FFFFFF; font-weight:700; text-decoration:none;">查看過往推薦 ↗</a></p>', '']
    nd = os.path.join(OUT, '_build', 'newsletter'); os.makedirs(nd, exist_ok=True)
    open(os.path.join(nd, f"{w['date']}.md"), 'w', encoding='utf-8').write('\n'.join(lines))
    return covers

def build_archive(all_covers):
    rows = ''
    for w, covers in zip(weeks, all_covers):
        names = ' · '.join(esc(s['title']) for s in w['songs'])
        strip = ''.join(f'<img src="../photos/songs/{c}" alt="" loading="lazy">' for c in covers)
        rows += (f'    <li><a class="week-row" href="{w["date"]}/"><div class="wd">{fmt(w["date"])}</div>'
                 f'<div><div class="strip">{strip}</div><div class="names">{names}</div></div></a></li>\n')
    main = ('  <header class="songs-head">\n    <h1>Five Songs for This Week</h1>\n'
            '    <p class="intro lang-zh">每週一與您分享我正在聆聽的五首歌</p>\n'
            '    <p class="intro lang-en">Five songs I&#39;m listening to, shared with you every Monday.</p>\n  </header>\n'
            f'  <ul class="week-list">\n{rows}  </ul>\n  <div style="height:80px"></div>')
    out = page_shell('Five Songs for This Week', "Five songs I'm listening to, shared with you every Monday.", 'songs/', main, '../')
    d = os.path.join(OUT, 'songs'); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)

all_covers = [build_week(i, w) for i, w in enumerate(weeks)]
build_archive(all_covers)
print('built', len(weeks), 'week page(s) + archive ->', OUT)
