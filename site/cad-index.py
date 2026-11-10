#!/usr/bin/env python3
"""Write <stage>/cad/index.html: the /cad/ folder as a page, its sheets grouped by category, each with a thumbnail
and its files (PDF, DXF, PNG, SVG) with their sizes. The groups come from the project's cad.json:

    {"title": "...", "groups": [{"title": "...", "note": "a few words", "sheets": [["file-stem", "Α.1", "label"], ...]}]}

Any sheet in the folder no group names lands in a last group, so nothing published is ever hidden.
Usage: cad-index.py <project dir> <cad dir>. Stdlib only."""
import html, json, os, sys

proj, cad = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(proj, 'cad.json')))
present = {}
for f in sorted(os.listdir(cad)):
    stem, ext = os.path.splitext(f)
    if ext.lower() in ('.pdf', '.dxf', '.png', '.svg'): present.setdefault(stem, []).append(ext[1:].lower())
groups, named = [], set()
for g in cfg['groups']:
    rows = [(s, no, label) for s, no, label in g['sheets'] if s in present]
    named.update(s for s, *_r in g['sheets'])
    if rows: groups.append((g['title'], g.get('note', ''), rows))
rest = [(s, '', s) for s in present if s not in named]
if rest: groups.append((cfg.get('other', 'Άλλα'), '', rest))

E = html.escape
def size(p):
    n = os.path.getsize(p)
    return f'{n / 1024:.0f} KB' if n < 1024 * 1024 else f'{n / 1024 / 1024:.1f} MB'
ORDER = ('pdf', 'dxf', 'png', 'svg')
HINT = {'pdf': 'για εκτύπωση', 'dxf': 'CAD', 'png': 'εικόνα', 'svg': 'διανυσματικό'}

out = []
for title, note, rows in groups:
    out.append(f'<section><h2>{E(title)}</h2>' + (f'<p class="note">{E(note)}</p>' if note else '') + '<ul>')
    for stem, no, label in rows:
        exts = present[stem]
        thumb = f'<a class="thumb" href="{E(stem)}.png" target="_blank"><img src="{E(stem)}.png" alt="" loading="lazy"></a>' if 'png' in exts else '<span class="thumb"></span>'
        links = ' '.join(f'<a class="f{" main" if x == "pdf" else ""}" href="{E(stem)}.{x}" title="{HINT[x]} · {size(os.path.join(cad, stem + "." + x))}">'
                         f'{x.upper()}<small>{size(os.path.join(cad, stem + "." + x))}</small></a>' for x in ORDER if x in exts)
        out.append(f'<li>{thumb}<div class="txt"><span class="no">{E(no)}</span><span class="label">{E(label)}</span>'
                   f'<div class="files">{links}</div></div></li>')
    out.append('</ul></section>')

page = f'''<!doctype html><html lang="el"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(cfg.get("title", "Σχέδια"))}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500&family=Hanken+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap">
<style>
:root{{--ground:#efeeea;--paper:#f8f7f4;--ink:#1f1e1b;--muted:#6b675f;--rule:#d8d4cb;--oak:#a8784a;
  --display:"Bricolage Grotesque","Helvetica Neue",Arial,sans-serif;--body:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root{{--ground:#191816;--paper:#221f1c;--ink:#ece8e1;--muted:#a39d92;--rule:#38342f;--oak:#d1a577}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font:16px/1.5 var(--body);padding:0 16px}}
main{{max-width:960px;margin:0 auto;padding:40px 0 64px}}
h1{{font:500 clamp(28px,5vw,40px)/1.1 var(--display);margin:0 0 6px}}
.lede{{color:var(--muted);margin:0 0 36px}} .lede a{{color:inherit}}
h2{{font:500 22px/1.2 var(--display);margin:0}}
section{{margin:0 0 36px}} .note{{color:var(--muted);margin:2px 0 12px;font-size:15px}}
ul{{list-style:none;margin:0;padding:0;display:grid;gap:12px}}
li{{display:grid;grid-template-columns:150px 1fr;gap:16px;align-items:center;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:12px}}
.thumb{{display:block;aspect-ratio:1.414;background:#fff;border:1px solid var(--rule);border-radius:4px;overflow:hidden}}
.thumb img{{width:100%;height:100%;object-fit:contain;display:block}}
.no{{font:500 13px var(--mono);color:var(--oak);margin-right:8px}} .label{{font-weight:600}}
.files{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
.f{{display:inline-flex;align-items:baseline;gap:6px;padding:4px 10px;border:1px solid var(--rule);border-radius:999px;color:var(--ink);text-decoration:none;font:500 13px var(--mono)}}
.f small{{color:var(--muted);font-size:11px}} .f:hover{{border-color:var(--ink)}}
.f.main{{background:var(--ink);color:var(--ground);border-color:var(--ink)}} .f.main small{{color:inherit;opacity:.7}}
@media (max-width:560px){{li{{grid-template-columns:96px 1fr;gap:12px}}}}
</style>
<main><h1>{E(cfg.get("title", "Σχέδια"))}</h1>
<p class="lede">{cfg.get("lede", "")}</p>
{"".join(out)}
</main></html>
'''
open(os.path.join(cad, 'index.html'), 'w').write(page)
print(f'   /cad/index.html: {sum(len(r) for _t, _n, r in groups)} sheets in {len(groups)} groups')
