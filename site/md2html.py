#!/usr/bin/env python3
"""Markdown -> a single self-contained HTML page.  Pure stdlib (the boxes it runs on have no pip).

    python3 md2html.py PLAYBOOK.md out/index.html ["Page title"]

Supports what the playbook actually uses: ATX headings, paragraphs, fenced code, inline code,
bold/italic, links, images, ul/ol (one level of nesting), tables, blockquotes, hr, and
`> **Trap:**` blockquotes which get a warning style.  A table of contents is built from the h2/h3.
"""
import html
import re
import sys

# ----------------------------------------------------------------- inline spans


def inline(t):
    """Inline markdown inside one already-escaped line."""
    out = []
    # code spans first, and hide them from the other rules
    parts = re.split(r'(`[^`]+`)', t)
    for p in parts:
        if p.startswith('`') and p.endswith('`') and len(p) > 1:
            out.append('<code>' + p[1:-1] + '</code>')
            continue
        p = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', r'<img src="\2" alt="\1">', p)
        p = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', p)
        p = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', p)
        p = re.sub(r'(?<![\w*])\*([^*\n]+)\*(?![\w*])', r'<em>\1</em>', p)
        p = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', p)
        # bare URLs
        p = re.sub(r'(?<!["=>])\bhttps?://[^\s<)]+', lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', p)
        out.append(p)
    return ''.join(out)


def esc(t):
    return html.escape(t, quote=False)


def slug(t):
    s = re.sub(r'<[^>]+>', '', t)
    s = re.sub(r'[^\w\s-]', '', s).strip().lower()
    return re.sub(r'[\s_]+', '-', s)


# ----------------------------------------------------------------- block parser


def convert(md):
    lines = md.split('\n')
    out, toc = [], []
    i, n = 0, len(lines)

    def close_list(stack):
        while stack:
            out.append('</%s>' % stack.pop())

    stack = []          # open list tags
    while i < n:
        ln = lines[i]

        # fenced code
        if ln.startswith('```'):
            close_list(stack)
            lang = ln[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].startswith('```'):
                buf.append(esc(lines[i]))
                i += 1
            i += 1
            cls = ' class="lang-%s"' % lang if lang else ''
            out.append('<pre><code%s>%s</code></pre>' % (cls, '\n'.join(buf)))
            continue

        # indented code block (4 spaces), only when not inside a list
        if not stack and re.match(r'^    \S', ln):
            buf = []
            while i < n and (lines[i].startswith('    ') or not lines[i].strip()):
                buf.append(esc(lines[i][4:]))
                i += 1
            while buf and not buf[-1].strip():
                buf.pop()
            out.append('<pre><code>%s</code></pre>' % '\n'.join(buf))
            continue

        # table: a header row followed by a |---|---| divider
        if ln.startswith('|') and i + 1 < n and re.match(r'^\|[\s:|-]+\|$', lines[i + 1]):
            close_list(stack)
            def cells(row):
                return [c.strip() for c in row.strip().strip('|').split('|')]
            head = cells(ln)
            aligns = []
            for spec in cells(lines[i + 1]):
                aligns.append('right' if spec.endswith(':') and not spec.startswith(':')
                              else 'center' if spec.startswith(':') and spec.endswith(':') else '')
            i += 2
            rows = []
            while i < n and lines[i].startswith('|'):
                rows.append(cells(lines[i]))
                i += 1
            def td(tag, vals):
                return ''.join('<%s%s>%s</%s>' % (tag, ' style="text-align:%s"' % aligns[k]
                                                  if k < len(aligns) and aligns[k] else '',
                                                  inline(esc(v)), tag) for k, v in enumerate(vals))
            out.append('<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                       % (td('th', head), ''.join('<tr>%s</tr>' % td('td', r) for r in rows)))
            continue

        # heading
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m:
            close_list(stack)
            lvl, txt = len(m.group(1)), inline(esc(m.group(2).strip()))
            sid = slug(txt)
            if lvl in (2, 3):
                toc.append((lvl, sid, re.sub(r'<[^>]+>', '', txt)))
                out.append('<h%d id="%s"><a class="anchor" href="#%s">%s</a></h%d>' % (lvl, sid, sid, txt, lvl))
            else:
                out.append('<h%d id="%s">%s</h%d>' % (lvl, sid, txt, lvl))
            i += 1
            continue

        # horizontal rule
        if re.match(r'^\s*(-{3,}|\*{3,})\s*$', ln):
            close_list(stack)
            out.append('<hr>')
            i += 1
            continue

        # blockquote (consumes following lines)
        if ln.startswith('>'):
            close_list(stack)
            buf = []
            while i < n and lines[i].startswith('>'):
                buf.append(lines[i].lstrip('>').strip())
                i += 1
            body = inline(esc(' '.join(x for x in buf if x)))
            warn = ' class="warn"' if re.match(r'<strong>(Trap|Warning|Careful|Never)', body) else ''
            out.append('<blockquote%s>%s</blockquote>' % (warn, body))
            continue

        # list item
        m = re.match(r'^(\s*)([-*+]|\d+[.)])\s+(.*)$', ln)
        if m:
            indent, mark, txt = len(m.group(1)), m.group(2), m.group(3)
            tag = 'ul' if mark in '-*+' else 'ol'
            depth = 1 + (indent >= 2)
            while len(stack) > depth:
                out.append('</%s>' % stack.pop())
            if len(stack) < depth:
                out.append('<%s>' % tag)
                stack.append(tag)
            elif stack[-1] != tag:
                out.append('</%s>' % stack.pop())
                out.append('<%s>' % tag)
                stack.append(tag)
            # continuation lines of the same item
            body = [txt]
            i += 1
            while i < n and lines[i].strip() and not re.match(r'^(\s*)([-*+]|\d+[.)])\s+', lines[i]) \
                    and not lines[i].startswith(('#', '|', '>', '```')):
                body.append(lines[i].strip())
                i += 1
            out.append('<li>%s</li>' % inline(esc(' '.join(body))))
            continue

        # blank line
        if not ln.strip():
            close_list(stack)
            i += 1
            continue

        # paragraph
        close_list(stack)
        buf = []
        while i < n and lines[i].strip() and not lines[i].startswith(('#', '|', '>', '```', '    ')) \
                and not re.match(r'^(\s*)([-*+]|\d+[.)])\s+', lines[i]) \
                and not re.match(r'^\s*(-{3,}|\*{3,})\s*$', lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append('<p>%s</p>' % inline(esc(' '.join(buf))))

    close_list(stack)
    return '\n'.join(out), toc


# ----------------------------------------------------------------- page shell

CSS = """
:root{
  --ground:#f4f2ee; --panel:#fbfaf7; --ink:#1f1e1b; --muted:#6b675f; --rule:#ddd8ce;
  --accent:#a8784a; --code-bg:#efece5; --warn-bg:#f8efe2; --warn-rule:#d7a45e;
  --body:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#171613; --panel:#201e1a; --ink:#ece8e1; --muted:#a39d92; --rule:#36322c;
  --accent:#d1a577; --code-bg:#252119; --warn-bg:#2b2419; --warn-rule:#8a6a34;
}}
:root[data-theme="dark"]{
  --ground:#171613; --panel:#201e1a; --ink:#ece8e1; --muted:#a39d92; --rule:#36322c;
  --accent:#d1a577; --code-bg:#252119; --warn-bg:#2b2419; --warn-rule:#8a6a34;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth; scroll-padding-top:20px}
body{margin:0; background:var(--ground); color:var(--ink); font:16px/1.65 var(--body);
     -webkit-text-size-adjust:100%}
.shell{max-width:1180px; margin:0 auto; padding:0 16px; display:grid; gap:34px;
       grid-template-columns:minmax(0,1fr); align-items:start}
@media (min-width:940px){.shell{grid-template-columns:232px minmax(0,1fr); padding:0 24px}}
header.top{grid-column:1/-1; padding:44px 0 6px; border-bottom:1px solid var(--rule)}
.eyebrow{font:500 11px/1 var(--mono); letter-spacing:.14em; text-transform:uppercase; color:var(--muted)}
header.top h1{font:600 clamp(26px,4vw,38px)/1.1 var(--body); letter-spacing:-.015em; margin:10px 0 8px}
header.top p{color:var(--muted); margin:0 0 22px; max-width:68ch}
nav.toc{position:sticky; top:16px; font-size:13.5px; line-height:1.45; padding-bottom:40px}
@media (max-width:939px){nav.toc{position:static; border-bottom:1px solid var(--rule); padding-bottom:20px}}
nav.toc .lbl{font:500 11px/1 var(--mono); letter-spacing:.12em; text-transform:uppercase;
             color:var(--muted); display:block; margin-bottom:10px}
nav.toc a{display:block; color:var(--muted); text-decoration:none; padding:3px 0}
nav.toc a.l3{padding-left:13px; font-size:12.5px}
nav.toc a:hover{color:var(--accent)}
main{min-width:0; padding-bottom:80px}
h2{font:600 23px/1.25 var(--body); letter-spacing:-.01em; margin:44px 0 12px;
   padding-top:14px; border-top:1px solid var(--rule)}
h3{font:600 17px/1.3 var(--body); margin:28px 0 8px}
h4{font:600 15px/1.3 var(--body); margin:20px 0 6px; color:var(--muted)}
h2:first-child{margin-top:8px; border-top:0}
a{color:var(--accent)}
.anchor{color:inherit; text-decoration:none}
p{margin:0 0 14px}
ul,ol{margin:0 0 14px; padding-left:22px}
li{margin:3px 0}
li>ul,li>ol{margin:3px 0}
code{font:0.87em/1.5 var(--mono); background:var(--code-bg); padding:.12em .36em; border-radius:4px;
     overflow-wrap:anywhere}
pre{background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:14px 16px;
    overflow-x:auto; margin:0 0 18px}
pre code{background:none; padding:0; font-size:13px; line-height:1.6; white-space:pre}
blockquote{margin:0 0 18px; padding:12px 16px; background:var(--panel); border-left:3px solid var(--rule);
           border-radius:0 8px 8px 0; color:var(--muted)}
blockquote.warn{background:var(--warn-bg); border-left-color:var(--warn-rule); color:var(--ink)}
.tablewrap{overflow-x:auto; margin:0 0 18px}
table{border-collapse:collapse; width:100%; font-size:14.5px; min-width:420px}
th,td{text-align:left; padding:7px 12px 7px 0; border-bottom:1px solid var(--rule); vertical-align:top}
th{font-weight:600; white-space:nowrap}
hr{border:0; border-top:1px solid var(--rule); margin:30px 0}
img{max-width:100%; height:auto; border-radius:8px}
del{color:var(--muted)}
footer{grid-column:1/-1; border-top:1px solid var(--rule); padding:16px 0 40px; color:var(--muted);
       font:12.5px/1.6 var(--mono)}
"""

PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>{css}</style>
<div class="shell">
  <header class="top">
    <span class="eyebrow">{eyebrow}</span>
    <h1>{h1}</h1>
    <p>{lede}</p>
  </header>
  <nav class="toc"><span class="lbl">On this page</span>{toc}</nav>
  <main>{body}</main>
  <footer>{footer}</footer>
</div>
"""


def render(md, title=None, eyebrow='', lede='', footer=''):
    body, toc = convert(md)
    # the first h1 becomes the page header rather than part of the body
    m = re.search(r'<h1[^>]*>(.*?)</h1>', body)
    h1 = re.sub(r'<[^>]+>', '', m.group(1)) if m else (title or 'Playbook')
    if m:
        body = body[:m.start()] + body[m.end():]
    nav = ''.join('<a class="l%d" href="#%s">%s</a>' % (lvl, sid, esc(txt)) for lvl, sid, txt in toc)
    return PAGE.format(title=esc(title or h1), css=CSS, eyebrow=esc(eyebrow), h1=esc(h1),
                       lede=inline(esc(lede)), toc=nav, body=body, footer=inline(esc(footer)))


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    ttl = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(src, encoding='utf-8').read()
    # an optional "<!-- lede: ... -->" / "<!-- eyebrow: ... -->" / "<!-- footer: ... -->" header
    meta = dict(re.findall(r'<!--\s*(eyebrow|lede|footer):\s*(.*?)\s*-->', text))
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    open(dst, 'w', encoding='utf-8').write(render(text, ttl, meta.get('eyebrow', ''),
                                                  meta.get('lede', ''), meta.get('footer', '')))
    print('wrote', dst, len(open(dst, encoding='utf-8').read()) // 1024, 'KiB')
