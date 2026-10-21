"""Shared page shell (head, language switch, footer, scripts) for the generated pages."""
import html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, '_build')
tpl = open(os.path.join(B, 'template.html'), encoding='utf-8').read()
HEAD = tpl[:tpl.index('<body>')]
ICON = re.search(r'<svg viewBox="0 0 32 32".*?</svg>', tpl, re.S).group(0)
ARROW = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 12L12 4M6 4h6v6"/></svg>'
esc = lambda s: html.escape(s, quote=False)
attr = lambda s: html.escape(s, quote=True)


def page_shell(title, desc, url, body_main, back_href, CSS=''):
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
      <a href="mailto:contact@geneyao.com" aria-label="Email"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5.5" width="18" height="13" rx="3"/><path d="M4 8l8 5.5L20 8"/></svg></a>
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
