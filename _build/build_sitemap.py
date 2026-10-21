#!/usr/bin/env python3
"""Write sitemap.xml and robots.txt. Run from the repo root after the other build scripts:  python3 _build/build_sitemap.py"""
import os, subprocess, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://geneyao.com'

def lastmod(path):
    try:
        d = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', path], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        d = ''
    return d

pages = [('index.html', '/', '1.0'), ('archive/index.html', '/archive/', '0.8'), ('songs/index.html', '/songs/', '0.8')]
for f in sorted(glob.glob(os.path.join(ROOT, 'mix', '*', 'index.html'))):
    slug = f.split(os.sep)[-2]; pages.append((f'mix/{slug}/index.html', f'/mix/{slug}/', '0.7'))
for f in sorted(glob.glob(os.path.join(ROOT, 'songs', '*', 'index.html'))):
    d = f.split(os.sep)[-2]; pages.append((f'songs/{d}/index.html', f'/songs/{d}/', '0.6'))

for f in sorted(glob.glob(os.path.join(ROOT, 'articles', '*', '*', 'index.html'))):
    parts = f.split(os.sep); cat, slug = parts[-3], parts[-2]
    pages.append((f'articles/{cat}/{slug}/index.html', f'/articles/{cat}/{slug}/', '0.6'))
for f in sorted(glob.glob(os.path.join(ROOT, 'articles', '*', 'index.html'))):
    cat = f.split(os.sep)[-2]
    pages.insert(3, (f'articles/{cat}/index.html', f'/articles/{cat}/', '0.7'))
if os.path.exists(os.path.join(ROOT, 'articles', 'index.html')):
    pages.insert(3, ('articles/index.html', '/articles/', '0.8'))

out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path, url, prio in pages:
    lm = lastmod(path)
    out.append('  <url><loc>%s%s</loc>%s<priority>%s</priority></url>' % (BASE, url, '<lastmod>%s</lastmod>' % lm if lm else '', prio))
out.append('</urlset>')
open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % BASE)
print('sitemap:', len(pages), 'urls')
