#!/usr/bin/env python3
"""Build the two variants of a page that exist side by side: the live one, and a dated preview.

    site/page-variants.py live    IN.html OUT.html [--prefix ../] [--assets ../presentation/]
    site/page-variants.py preview IN.html OUT.html --prefix ../../ --assets ../../presentation/

The owner wants to see a change on a throwaway unlisted URL before it goes on the real page. Rather
than keeping two copies of a 76 KB page in step, the source carries both variants marked:

    <!-- live:start -->    …only in the live page…     <!-- live:end -->
    <!-- preview:start --> …only in the preview…       <!-- preview:end -->

`live` drops the preview blocks, `preview` drops the live ones; both then remove the markers, so
neither output keeps this scaffolding. --prefix rewrites the claude.ai Artifact links publish.sh
normally rewrites (the preview sits one directory deeper, hence ../../); which links, from the environment:
PLANNIT_ARTIFACTS="id=page/ id=page/ …" (the project's project.conf ARTIFACTS, exported by publish.sh). --assets points the page's
images at the folder that has them — except any file that sits next to OUT, which is how the preview
keeps its own copies of the sheets it is about.
"""
import datetime
import os
import re
import sys

ARTIFACTS = dict(a.split('=', 1) for a in os.environ.get('PLANNIT_ARTIFACTS', '').split())
USAGE = __doc__.strip().splitlines()[2].strip()


def drop(html, kind):
    # the markers may carry a label: <!-- preview:start engineer-contractor -->
    return re.sub(r'<!--\s*%s:start\b[^>]*-->.*?<!--\s*%s:end\b[^>]*-->' % (kind, kind), '', html, flags=re.S)


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ('live', 'preview'):
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    mode, src, out = sys.argv[1:4]
    prefix, assets = '../', ''
    rest = sys.argv[4:]
    i = 0
    while i < len(rest):
        if rest[i] == '--prefix' and i + 1 < len(rest): prefix = rest[i + 1]; i += 2
        elif rest[i] == '--assets' and i + 1 < len(rest): assets = rest[i + 1]; i += 2
        else: print(f'ignoring {rest[i]!r}', file=sys.stderr); i += 1

    html = open(src, encoding='utf-8').read()
    html = drop(html, 'preview' if mode == 'live' else 'live')
    html = re.sub(r'<!--\s*(?:preview|live):(?:start|end)\b[^>]*-->\n?', '', html)
    today = datetime.date.today().isoformat()
    html = html.replace('{{DATE}}', today)
    if mode == 'preview':                                    # a dated name, so two previews never mix
        html = re.sub(r'<title>(.*?)</title>', lambda m: f'<title>{m.group(1)} — preview {today}</title>',
                      html, count=1)
    outdir = os.path.dirname(os.path.abspath(out))
    for aid, page in ARTIFACTS.items():
        html = html.replace(f'https://claude.ai/artifact/{aid}', prefix + page)
    if assets:
        def keep_or_move(m):
            name = m.group(1)
            local = os.path.isfile(os.path.join(outdir, name))       # e.g. the preview's own sheets
            return m.group(0) if local else f'src="{assets}{name}"'
        html = re.sub(r'src="([^"/:]+\.(?:jpg|png|svg|webp))"', keep_or_move, html)
    os.makedirs(outdir, exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)
    print(f'  {mode:7s} {out} ({len(html) / 1024:.0f} KB)'
          f'{"  assets -> " + assets if assets else ""}{"  links -> " + prefix if prefix != "../" else ""}')


main()
