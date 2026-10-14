#!/usr/bin/env python3
"""site/history/build.py — the render history page: every version of every render the project ever committed.

    build.py <project> <out-dir> [site name]

Reads the project's git history of content/presentation/*.jpg. Each commit that changed a render is one step;
each render's versions are its distinct blobs in commit order. Writes <out-dir>/index.html (the page, data
inlined) and <out-dir>/img/<blob>.jpg + <out-dir>/t/<blob>.jpg (a 1600 px copy and a 400 px thumbnail).
The resized copies are cached in <project>/out/.cache/history/ by blob id, so a rebuild only converts what is new.

Labels: commit subjects are working notes and stay private. A commit is labelled from <project>/history-labels.json
({"<commit prefix>": {"el": "...", "en": "..."}}); without an entry it shows its date only.
Titles come from the presentation page's own captions (data-base -> figcaption .where); a view with none (or one
since dropped from the page) takes its title from the same file's "_views": {"<base>": {"el": ..., "en": ...}}.
"""
import html, json, os, re, subprocess, sys
from html.parser import HTMLParser
from PIL import Image

FULL_W, THUMB_W = 1600, 400
REL = 'content/presentation'


def git(proj, *a, binary=False):
    out = subprocess.run(['git', '-C', proj, *a], check=True, capture_output=True).stdout
    return out if binary else out.decode()


def variant(stem):
    """file stem -> (base, palette a|b|d, night, empty)"""
    if stem.endswith('_empty'):
        return stem[:-6], 'd', False, True
    m = re.match(r'(.+?)(?:_([bd]))?(_night)?$', stem)
    return m.group(1), m.group(2) or 'a', bool(m.group(3)), False


class Captions(HTMLParser):
    """data-base -> (en, el) from the presentation page: the first .where span after each data-base image"""
    def __init__(self):
        super().__init__(); self.titles = {}; self.base = None; self.where = None; self.buf = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img' and a.get('data-base'):
            self.base = a['data-base']
        elif tag == 'span' and 'where' in (a.get('class') or '').split() and self.base:
            self.where = a.get('data-el', ''); self.buf = ''
    def handle_data(self, d):
        if self.where is not None: self.buf += d
    def handle_endtag(self, tag):
        if tag == 'span' and self.where is not None:
            self.titles.setdefault(self.base, (self.buf.strip(), self.where.strip()))
            self.where = None; self.base = None


def resize(proj, cache, blob, out_full, out_thumb):
    cf, ct = os.path.join(cache, blob + '.jpg'), os.path.join(cache, blob + '.t.jpg')
    if not (os.path.exists(cf) and os.path.exists(ct)):
        import io
        im = Image.open(io.BytesIO(git(proj, 'cat-file', 'blob', blob, binary=True))).convert('RGB')
        for path, w, q in ((cf, FULL_W, 80), (ct, THUMB_W, 72)):
            k = im if im.width <= w else im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            k.save(path + '.tmp', 'JPEG', quality=q, optimize=True, progressive=True); os.replace(path + '.tmp', path)
    for src, dst in ((cf, out_full), (ct, out_thumb)):
        if not os.path.exists(dst):
            try: os.link(src, dst)
            except OSError:
                import shutil; shutil.copyfile(src, dst)
    with Image.open(cf) as im:
        return im.size


def main():
    proj, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    name = sys.argv[3] if len(sys.argv) > 3 else ''
    cache = os.path.join(proj, 'out', '.cache', 'history')   # .cache: skipped by the backups; regenerable
    for d in (cache, os.path.join(out, 'img'), os.path.join(out, 't')):
        os.makedirs(d, exist_ok=True)
    labels = {}
    lf = os.path.join(proj, 'history-labels.json')
    if os.path.exists(lf):
        labels = json.load(open(lf))
    log = git(proj, 'log', '--reverse', '--format=%H%x09%aI', '--', f'{REL}/*.jpg').split('\n')
    commits, files, last = [], {}, {}
    for line in filter(None, log):
        sha, date = line.split('\t')
        tree = {}
        for row in git(proj, 'ls-tree', sha, f'{REL}/').splitlines():
            meta, path = row.split('\t')
            if path.endswith('.jpg'):
                tree[os.path.basename(path)[:-4]] = meta.split()[2]
        changed = [s for s, b in sorted(tree.items()) if last.get(s) != b]
        if not changed:
            continue
        ci = len(commits)
        lab = next((v for k, v in labels.items() if not k.startswith('_') and sha.startswith(k)), {})
        commits.append({'id': sha[:7], 'date': date, 'el': lab.get('el', ''), 'en': lab.get('en', ''), 'n': changed})
        for s in changed:
            b = tree[s]
            w, h = resize(proj, cache, b, os.path.join(out, 'img', b[:16] + '.jpg'), os.path.join(out, 't', b[:16] + '.jpg'))
            files.setdefault(s, []).append([ci, b[:16], w, h])
            last[s] = b
        for s in list(last):                    # a render deleted from the page stops there
            if s not in tree: del last[s]
    cap = Captions()
    cap.feed(open(os.path.join(proj, REL, 'index.html'), encoding='utf-8').read())
    views = {}
    for s in files:
        base, pal, night, empty = variant(s)
        en, el = cap.titles.get(base) or tuple(labels.get('_views', {}).get(base, {}).get(k, base) for k in ('en', 'el'))
        views.setdefault(base, {'en': en, 'el': el, 'files': {}})['files'][s] = [pal, night, empty]
    order = list(dict.fromkeys(b for b in re.findall(r'data-base="([^"]+)"', open(os.path.join(proj, REL, 'index.html'), encoding='utf-8').read())))
    order += sorted(b for b in views if b not in order)
    data = {'name': name, 'commits': commits, 'files': files,
            'views': [dict(base=b, **views[b]) for b in order if b in views]}
    page = open(os.path.join(os.path.dirname(__file__), 'index.html'), encoding='utf-8').read()
    page = page.replace('__NAME__', html.escape(name)).replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(page)
    keep = {f'{v[1]}.jpg' for vs in files.values() for v in vs}
    for d in ('img', 't'):
        for f in os.listdir(os.path.join(out, d)):
            if f not in keep: os.remove(os.path.join(out, d, f))
    print(f'   {len(commits)} steps, {len(files)} renders, {sum(len(v) for v in files.values())} versions')


if __name__ == '__main__':
    main()
