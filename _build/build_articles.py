#!/usr/bin/env python3
"""Build the "Albums & Mixes I Listened Through" article pages from Obsidian notes.

Usage (from the repo root):
  python3 _build/build_articles.py                    # published notes only
  python3 _build/build_articles.py --include-drafts   # also build notes from 10 Drafts (preview)
  python3 _build/build_articles.py --vault PATH --out DIR

Reads  <vault>/20 Published/*.md  (and <vault>/10 Drafts/*.md with --include-drafts)
whose front matter has  series: Albums & Mixes I Listened Through.
Writes albums/index.html, albums/<slug>/index.html and photos/albums/<cover>.
"""
import argparse, glob, html, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, '_build')
sys.path.insert(0, B)
from shell import page_shell as _shell, esc, attr, ARROW

ap = argparse.ArgumentParser()
ap.add_argument('--vault', default=os.path.expanduser('~/GeneYao'))
ap.add_argument('--out', default=ROOT)
ap.add_argument('--include-drafts', action='store_true')
args = ap.parse_args()
OUT, VAULT = args.out, args.vault
SERIES = 'Albums & Mixes I Listened Through'
CAT = 'albums'   # URL folder for this series: /articles/albums/<slug>/

SUBSCRIBE = ''
_m = re.search(r'  <div class="sub-divider".*?</section>\n', open(os.path.join(B, 'template.html'), encoding='utf-8').read(), re.S)
if _m:
    SUBSCRIBE = _m.group(0)

ICONS = {   # official brand icons in their original colors (simple-icons, CC0)
    'Spotify': '<svg viewBox="0 0 24 24" fill="#1DB954" aria-hidden="true"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>',
    'YouTube': '<svg viewBox="0 0 24 24" fill="#FF0000" aria-hidden="true"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
    'Discogs': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M1.7422 11.982c0-5.6682 4.61-10.2782 10.2758-10.2782 1.8238 0 3.5372.48 5.0251 1.3175l.8135-1.4879C16.1768.588 14.2474.036 12.1908.0024h-.1944C5.4091.0144.072 5.3107 0 11.886v.1152c.0072 3.4389 1.4567 6.5345 3.7748 8.7207l1.1855-1.2814c-1.9798-1.8743-3.218-4.526-3.218-7.4585zM20.362 3.4053l-1.1543 1.2406c1.903 1.867 3.0885 4.4636 3.0885 7.3361 0 5.6658-4.61 10.2758-10.2758 10.2758-1.783 0-3.4605-.456-4.922-1.2575l-.8542 1.5214c1.7086.9384 3.6692 1.4735 5.7546 1.4759C18.6245 23.9976 24 18.6246 24 11.9988c-.0048-3.3717-1.399-6.4146-3.638-8.5935zM1.963 11.982c0 2.8701 1.2119 5.4619 3.146 7.2953l1.1808-1.2767c-1.591-1.5166-2.587-3.6524-2.587-6.0186 0-4.586 3.7293-8.3152 8.3152-8.3152 1.483 0 2.875.3912 4.082 1.0751l.8351-1.5262C15.481 2.395 13.8034 1.927 12.018 1.927 6.4746 1.9246 1.963 6.4362 1.963 11.982zm18.3702 0c0 4.586-3.7293 8.3152-8.3152 8.3152-1.4327 0-2.7837-.3648-3.962-1.0055l-.852 1.5166c1.4303.7823 3.0718 1.2287 4.814 1.2287 5.5434 0 10.055-4.5116 10.055-10.055 0-2.8077-1.1567-5.3467-3.0165-7.1729l-1.183 1.2743c1.519 1.507 2.4597 3.5924 2.4597 5.8986zm-1.9486 0c0 3.5109-2.8558 6.3642-6.3642 6.3642a6.3286 6.3286 0 01-3.0069-.756l-.8471 1.507c1.147.624 2.4597.9768 3.854.9768 4.4636 0 8.0944-3.6308 8.0944-8.0944 0-2.239-.9143-4.2692-2.3902-5.7378l-1.1783 1.267c1.1351 1.152 1.8383 2.731 1.8383 4.4732zm-14.4586 0c0 2.3014.9671 4.382 2.515 5.8578l1.1734-1.2695c-1.207-1.159-1.9606-2.786-1.9606-4.5883 0-3.5108 2.8557-6.3642 6.3642-6.3642 1.1423 0 2.215.3048 3.1437.8352l.8303-1.5167c-1.1759-.6647-2.5317-1.0487-3.974-1.0487-4.4612 0-8.092 3.6308-8.092 8.0944zm12.5292 0c0 2.4502-1.987 4.4372-4.4372 4.4372a4.4192 4.4192 0 01-2.0614-.5088l-.8351 1.4879a6.1135 6.1135 0 002.8965.727c3.3885 0 6.1434-2.7548 6.1434-6.1433 0-1.6774-.6767-3.1989-1.7686-4.3076l-1.1615 1.2503c.7559.7967 1.2239 1.8718 1.2239 3.0573zm-10.5806 0c0 1.7374.7247 3.3069 1.8886 4.4252L8.92 15.1569l.0144.0144c-.8351-.8063-1.3559-1.9366-1.3559-3.1869 0-2.4502 1.9846-4.4372 4.4372-4.4372.8087 0 1.5646.2184 2.2174.5976l.8207-1.4975a6.097 6.097 0 00-3.0381-.8063c-3.3837-.0048-6.141 2.7525-6.141 6.141zm6.681 0c0 .2952-.2424.5351-.5376.5351-.2952 0-.5375-.24-.5375-.5351 0-.2976.24-.5375.5375-.5375.2952 0 .5375.24.5375.5375zm-3.9405 0c0-1.879 1.5239-3.4029 3.4005-3.4029 1.879 0 3.4005 1.5215 3.4005 3.4029 0 1.879-1.5239 3.4005-3.4005 3.4005S8.6151 13.861 8.6151 11.982zm.1488 0c.0048 1.7974 1.4567 3.2493 3.2517 3.2517 1.795 0 3.254-1.4567 3.254-3.2517-.0023-1.7974-1.4566-3.2517-3.254-3.254-1.795 0-3.2517 1.4566-3.2517 3.254Z"/></svg>',
    'Bandcamp': '<svg viewBox="0 0 24 24" fill="#1DA0C3" aria-hidden="true"><path d="M0 18.75l7.437-13.5H24l-7.438 13.5H0z"/></svg>',
}

CSS = '''
  .art-head{ padding-block: 28px 8px; text-align:center; }
  .art-head .eyebrow{ margin-bottom: 24px; font-size: clamp(18px, 4.8vw, 30px); letter-spacing:.12em; line-height:1.5; color: var(--ink); }
  .art-cover{ width: min(420px, 100%); aspect-ratio: 1/1; object-fit: cover; border-radius: 20px; border:1px solid var(--line); box-shadow: var(--shadow); margin: 0 auto; display:block; }
  .art-head h1{ margin-top: 28px; font-size: clamp(36px, 6vw, 60px); line-height:1.05; }
  .art-artist{ margin-top: 10px; font-size: 20px; }
  .art-sub{ margin-top: 6px; font-family:'IBM Plex Mono', monospace; font-size:12.5px; letter-spacing:.06em; color: var(--ink-soft); }
  .art-links{ margin-top: 18px; display:flex; justify-content:center; gap:12px; }
  .art-links a{ display:inline-flex; align-items:center; gap:6px; padding:11px 16px; border:1px solid var(--line); border-radius:999px; color: var(--ink-soft); text-decoration:none; font-family:'IBM Plex Mono', monospace; font-size:12px; letter-spacing:.06em; transition: color .2s ease, border-color .2s ease; }
  .art-links a:hover{ color: var(--accent); border-color: var(--accent); }
  .art-links svg{ width:24px; height:24px; }
  .art-links .go{ width:11px; height:11px; }
  .chips{ margin-top: 18px; display:flex; justify-content:center; flex-wrap:wrap; gap:8px; }
  .chip{ padding:3px 11px; font-size:11px; letter-spacing:.06em; text-transform:uppercase; color: var(--accent); border:1px solid var(--line); border-radius:999px; font-family:'IBM Plex Mono', monospace; }
  .art-body{ max-width: 680px; margin: 40px auto 0; padding-top: 32px; border-top:1px solid var(--line); }
  .art-body h2{ margin-top: 40px; font-size: 28px; }
  .art-body p{ margin: 14px 0 0; font-size: 16.5px; line-height: 1.95; }
  .art-body a{ color: var(--accent); text-underline-offset: 3px; }
  .art-body ol, .art-body ul{ margin: 14px 0 0; padding-left: 1.4em; line-height: 2; font-size:16.5px; }
  .art-body .star{ color: var(--accent); margin-left: 6px; }
  .art-body + .more{ padding-top: 40px; }
  .art-when{ font-size:15px; color: var(--ink-soft); }
  .art-list{ margin: 32px 0 0; padding:0; list-style:none; display:flex; flex-direction:column; gap:14px; }
  .art-row{ position:relative; display:grid; grid-template-columns: 148px 1fr 44px; gap:24px; align-items:center; padding: 20px 24px; background: var(--surface); border:1px solid var(--line); border-radius:20px; text-decoration:none; color: var(--ink); transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
  .art-row:hover{ transform: translateY(-3px); border-color: var(--accent); box-shadow: var(--shadow); }
  .art-row img{ width:148px; height:148px; object-fit:cover; border-radius:12px; border:1px solid var(--line); }
  .art-row h3{ font-size:22px; line-height:1.3; }
  .art-row .who{ margin-top:8px; font-family:'IBM Plex Mono', monospace; font-size:12.5px; letter-spacing:.05em; color: var(--ink-soft); }
  .art-row .ex{ margin:10px 0 0; font-size:14.5px; line-height:1.75; color: var(--ink-soft); display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
  .art-row .chips{ justify-content:flex-start; margin-top:12px; }
  .art-row .go{ width:44px; height:44px; border-radius:50%; border:1px solid var(--line); display:flex; align-items:center; justify-content:center; color: var(--accent); transition: background .2s ease, color .2s ease, border-color .2s ease; }
  .art-row .go svg{ width:16px; height:16px; transition: transform .2s ease; }
  .art-row:hover .go{ background: var(--accent); color: var(--bg); border-color: var(--accent); }
  .art-row:hover .go svg{ transform: translate(2px,-2px); }
  .art-top{ padding-block: 28px 8px; }
  .art-top h1{ font-size: clamp(34px, 5.5vw, 56px); line-height:1.05; }
  .art-top p{ margin: 14px 0 0; max-width: 56ch; color: var(--ink-soft); line-height:1.8; }
  @media (max-width: 640px){
    .art-row h3{ font-size:20px; }
    .art-row{ grid-template-columns: 92px 1fr; gap:14px; padding:14px; align-items:start; }
    .art-row img{ width:92px; height:92px; }
    .art-row .go{ display:none; }
    .art-row h3{ font-size:18px; }
    .art-row .ex{ -webkit-line-clamp:4; }
    .art-body p, .art-body ol, .art-body ul{ font-size:16px; }
  }
'''

def shell(title, desc, url, main, back, og=None, top_href=None, top_label='GeneYao', contact=False):
    out = _shell(title, desc, url, main, back, CSS, top_href, top_label, contact)
    # Article pages are Chinese only: no language switch, no English variants, ignore a saved English choice
    out = re.sub(r'<div class="lang-switch">.*?</div>\s*', '', out, count=1, flags=re.S)
    out = re.sub(r'<(p|h1|h2|div|span)[^>]*class="[^"]*lang-en[^"]*"[^>]*>.*?</\1>\s*', '', out, flags=re.S)
    out = out.replace("try{ if(localStorage.getItem('geneyao-lang') === 'en') setLang('en'); }catch(e){}", '')
    if og:
        out = out.replace('https://geneyao.com/og-image.jpg', og)
    return out

def parse(path):
    raw = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---\n(.*)', raw, re.S)
    meta, body = {}, raw
    if m:
        body = m.group(2)
        key = None
        for line in m.group(1).split('\n'):
            if re.match(r'^\s+-\s', line) and key:
                meta.setdefault(key, []).append(line.split('-', 1)[1].strip().strip('"'))
            elif ':' in line:
                key, val = line.split(':', 1); key = key.strip(); val = val.strip().strip('"')
                meta[key] = val if val else []
    return meta, body

def inline(t):
    t = esc(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', lambda m: f'<a href="{attr(m.group(2).replace("&amp;", "&"))}" target="_blank" rel="noopener">{m.group(1)}</a>', t)
    t = t.replace('⭐', '<span class="star">★</span>')
    return t

def md_to_html(md):
    out, para, items, kind = [], [], [], None
    def flush_p():
        nonlocal para
        if para: out.append('<p>' + '<br>'.join(inline(x) for x in para) + '</p>'); para = []
    def flush_l():
        nonlocal items, kind
        if items: out.append(f'<{kind}>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + f'</{kind}>'); items, kind = [], None
    for line in md.split('\n'):
        s = line.rstrip()
        mo, mu = re.match(r'^\d+\.\s+(.*)', s), re.match(r'^[-*]\s+(.*)', s)
        if s.startswith('## '):
            flush_p(); flush_l(); out.append(f'<h2>{inline(s[3:])}</h2>')
        elif mo or mu:
            flush_p(); k = 'ol' if mo else 'ul'
            if kind and kind != k: flush_l()
            kind = k; items.append((mo or mu).group(1))
        elif not s.strip():
            flush_p(); flush_l()
        elif s.strip() == '---':
            flush_p(); flush_l()
        else:
            flush_l(); para.append(s)
    flush_p(); flush_l()
    return '\n'.join(out)

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'article'

def copy_image(name):
    src = os.path.join(VAULT, 'Attachments', name)
    if not os.path.exists(src):
        raise SystemExit(f'Image not found in Attachments: {name}')
    dest_dir = os.path.join(OUT, 'photos', 'albums'); os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name)
    subprocess.run(['sips', '-Z', '900', '-s', 'format', 'jpeg', '-s', 'formatOptions', '80', src, '--out', dest], capture_output=True)
    return name

def collect():
    folders = ['20 Published'] + (['10 Drafts'] if args.include_drafts else [])
    arts = []
    for fol in folders:
        for p in sorted(glob.glob(os.path.join(VAULT, fol, '*.md'))):
            meta, body = parse(p)
            if meta.get('series') != SERIES: continue
            if fol == '20 Published' and meta.get('status') == 'draft': continue
            body = re.sub(r'%%.*?%%', '', body, flags=re.S)
            img = re.search(r'!\[\[([^\]]+)\]\]', body)
            if not img:
                img = re.search(r'!\[[^\]]*\]\(https://geneyao\.com/photos/albums/([^)\s]+)\)', body)
            if not img:
                img = re.search(r'!\[[^\]]*\]\((?:\.\./)?Attachments/([^)\s]+)\)', body)
            links = {}
            for href, alt in re.findall(r'<a href="([^"]+)"[^>]*><img[^>]*alt="([^"]+)"', body):
                if href.startswith('http'): links[alt] = href
            parts = re.split(r'\n---\s*\n', body, maxsplit=1)
            hm = re.search(r'<p style="font-size:0\.9em; opacity:0\.6; margin:0;">(.*?)</p>', parts[0], re.S)
            header_sub = html.unescape(hm.group(1).strip()) if hm else ''
            content = parts[1] if len(parts) > 1 else body
            content = '\n'.join(l for l in content.split('\n') if not l.lstrip().startswith('<'))
            tags = meta.get('tags', []) if isinstance(meta.get('tags'), list) else []
            genres = [t.split('/', 1)[1] for t in tags if t.startswith('曲風/')]
            region = [t.split('/', 1)[1].replace('-', ' ') for t in tags if t.startswith('地區/')]
            arts.append(dict(header_sub=header_sub, meta=meta, img=img.group(1) if img else None, links=links, content=content,
                             genres=genres, region=region, slug=meta.get('slug') or slugify(meta.get('album', os.path.basename(p)))))
    arts.sort(key=lambda a: a['meta'].get('date', ''), reverse=True)
    return arts

def excerpt(a, n=96):
    """Short preview text: front matter `excerpt`, else the first paragraph of the first section."""
    if a['meta'].get('excerpt'):
        return a['meta']['excerpt']
    for para in re.split(r'\n\s*\n', a['content']):
        t = para.strip()
        if not t or t.startswith(('#', '-', '*', '1.', '<', '!', '>')) and not t.startswith('**'):
            continue
        if t.startswith('**'):        # skip label lines such as "**我的服用時機：** ..."
            continue
        t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
        t = re.sub(r'[*_`]', '', t).replace('\n', ' ')
        return t[:n].rstrip('，。、, ') + ('…' if len(t) > n else '')
    return ''

def fmtdate(d):
    return d.replace('-', '.')

def build_article(a):
    m = a['meta']
    cover = copy_image(a['img']) if a['img'] else None
    chips = ''.join(f'<span class="chip">{esc(x)}</span>' for x in a['genres'])
    go_icon = ARROW.replace('<svg ', '<svg class="go" ')
    links = ''.join(f'<a href="{attr(a["links"][k])}" target="_blank" rel="noopener" aria-label="{k}" title="{k}">{ICONS[k]}{go_icon}</a>'
                    for k in ('Spotify', 'YouTube', 'Bandcamp', 'Discogs') if k in a['links'])
    label = (m.get('label', '').replace('（', ' (').replace('）', ')').replace('再版', 'reissue').replace('  ', ' ').strip())
    sub = a.get('header_sub') or ' · '.join(x for x in [label, m.get('year', '')] if x)
    head = ('  <header class="art-head">\n'
            f'    <p class="eyebrow">{"<br>".join(esc(x) for x in SERIES.split(" I ", 1)[0:1])}<br>I {esc(SERIES.split(" I ", 1)[1])}</p>\n'
            + (f'    <img class="art-cover" src="../../../photos/albums/{cover}" alt="{attr(m.get("album", ""))} album cover">\n' if cover else '')
            + f'    <h1>{esc(m.get("album", ""))}</h1>\n'
            f'    <div class="art-artist">{esc(m.get("artist", ""))}</div>\n'
            + (f'    <div class="art-sub">{esc(sub)}</div>\n' if sub else '')
            + (f'    <div class="art-links">{links}</div>\n' if links else '')
            + (f'    <div class="chips">{chips}</div>\n' if chips else '')
            + '  </header>\n')
    body = f'  <article class="art-body">\n{md_to_html(a["content"])}\n    <p class="art-when">{fmtdate(m.get("date", ""))}</p>\n  </article>\n  <section class="more">\n    <a class="btn solid" href="../../">\n      <span class="lang-zh">看其他文章</span>\n      <svg class="arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 8h10M9 4l4 4-4 4"/></svg>\n    </a>\n  </section>\n{SUBSCRIBE}'
    title = m.get('title') or f'{m.get("album", "")} · {m.get("artist", "")}'
    desc = f'{m.get("artist", "")} - {m.get("album", "")}: ' + re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', md_to_html(a['content']).split('</p>')[0]))[:120]
    og = f'https://geneyao.com/photos/albums/{cover}' if cover else None
    out = shell(title, desc, f'articles/{CAT}/{a["slug"]}/', head + body, '../../../', og, top_href='../../', top_label='Articles', contact=True)
    d = os.path.join(OUT, 'articles', CAT, a['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
    return cover

def rows_html(arts, covers, link_prefix, img_prefix):
    rows = ''
    for a, cover in zip(arts, covers):
        m = a['meta']
        chips = ''.join(f'<span class="chip">{esc(x)}</span>' for x in a['genres'])
        card_title = '<br>'.join(esc(x) for x in (m.get('title') or m.get('album', '')).split(' | '))
        rows += (f'    <li><a class="art-row" href="{link_prefix}{a["slug"]}/">'
                 + (f'<img src="{img_prefix}photos/albums/{cover}" alt="" loading="lazy">' if cover else '<span></span>')
                 + f'<div class="txt"><h3>{card_title}</h3><div class="who">{fmtdate(m.get("date", ""))}</div>'
                 + (f'<p class="ex">{esc(excerpt(a))}</p>' if excerpt(a) else '')
                 + (f'<div class="chips">{chips}</div>' if chips else '')
                 + f'</div><span class="go" aria-hidden="true">{ARROW}</span></a></li>\n')
    return rows

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)

def redirect_page(target):
    return ('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<title>Redirecting…</title><meta name="robots" content="noindex">'
            f'<link rel="canonical" href="https://geneyao.com{target}">'
            f'<meta http-equiv="refresh" content="0; url={target}">'
            f'<script>location.replace("{target}");</script></head>'
            f'<body><a href="{target}">{target}</a></body></html>\n')

def build_index(arts, covers):
    # /articles/  : latest articles of every series
    main = ('  <header class="art-top">\n    <h1>最新文章</h1>\n  </header>\n'
            f'  <ul class="art-list">\n{rows_html(arts, covers, CAT + "/", "../")}  </ul>\n  <div style="height:80px"></div>')
    write(os.path.join(OUT, 'articles', 'index.html'),
          shell('最新文章', 'GeneYao 的文章：聽過的專輯與 Mix，以及怎麼遇見它們。', 'articles/', main, '../'))
    # /articles/albums/ : this series only
    main = ('  <header class="art-top">\n    <h1>Albums &amp; Mixes I Listened Through</h1>\n  </header>\n'
            f'  <ul class="art-list">\n{rows_html(arts, covers, "", "../../")}  </ul>\n  <div style="height:80px"></div>')
    write(os.path.join(OUT, 'articles', CAT, 'index.html'),
          shell(SERIES, 'GeneYao 聽過的專輯與 Mix，以及怎麼遇見它們。', f'articles/{CAT}/', main, '../../', top_href='../', top_label='Articles'))
    # the first addresses (/albums/...) now forward to the new ones
    write(os.path.join(OUT, 'albums', 'index.html'), redirect_page('/articles/'))
    for a in arts:
        write(os.path.join(OUT, 'albums', a['slug'], 'index.html'), redirect_page(f'/articles/{CAT}/{a["slug"]}/'))

arts = collect()
if not arts:
    raise SystemExit('No articles found.')
covers = [build_article(a) for a in arts]
build_index(arts, covers)
print('built', len(arts), 'article(s):', ', '.join(a['slug'] for a in arts))
