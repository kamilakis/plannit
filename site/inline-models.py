#!/usr/bin/env python3
"""Fill the 3D viewer page's two inline model blocks from the exported GLBs.

    site/inline-models.py IN.html OUT.html flat.glb flat_b.glb [flat_d.glb ...]

Each flat[_X].glb fills <script id="model-X"> (flat.glb -> model-a); every GLB given must have a block.

The viewer hands GLTFLoader.parse its models from two <script id="model-a|model-b"> blocks instead
of fetching them: claude.ai Artifacts block `data:` and `blob:` fetches, so the models have to sit
inside the page. That makes the page a build product — and for as long as the base64 lived in the
source file, nothing regenerated it. On 2026-09-19 the live viewer was found drawing a
33,298-triangle model with no curtains and no frosted shower screen, two exports behind the .glb
files sitting next to it on the same URL.

So: the source page keeps both blocks EMPTY and publish.sh calls this on every build. IN is never
modified; OUT is written to a temporary file, moved into place, then read back and compared against
the GLBs, so a mangled copy cannot be published silently. Stdlib only — debnuc has no pip.
"""
import base64, hashlib, json, os, re, struct, sys

USAGE = 'usage: site/inline-models.py IN.html OUT.html flat.glb flat_b.glb [flat_d.glb ...]'


def die(msg):
    print('inline-models: ' + msg, file=sys.stderr)
    sys.exit(1)


def block_pattern(sid):
    """The open tag, the payload, and </script> — payload captured so it can be read back."""
    return re.compile(r'(<script\b[^>]*\bid="%s"[^>]*>)(.*?)(</script>)' % re.escape(sid), re.S)


def read_glb(path):
    """Return (bytes, triangles, material count) after checking it really is a GLB."""
    if not os.path.isfile(path):
        die(f'{path}: no such file — export it first (blender -b -P scene.py -- glb and -- glb-b)')
    data = open(path, 'rb').read()
    if data[:4] != b'glTF':
        die(f'{path}: not a GLB (magic is {data[:4]!r})')
    off, js = 12, None
    while off + 8 <= len(data):
        ln, ty = struct.unpack_from('<II', data, off)
        if ty == 0x4E4F534A:                       # 'JSON'
            js = json.loads(data[off + 8:off + 8 + ln])
        off += 8 + ln + (-ln % 4)
    if js is None:
        die(f'{path}: GLB has no JSON chunk')
    tri = sum(js['accessors'][p['indices']]['count'] // 3
              for m in js.get('meshes', []) for p in m['primitives'])
    return data, tri, len(js.get('materials', []))


def main():
    if len(sys.argv) < 5:
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    src, out, glbs = sys.argv[1], sys.argv[2], sys.argv[3:]
    html = open(src, encoding='utf-8').read()
    filled = []
    def block_id(path):
        m = re.fullmatch(r'flat(?:_([a-z]))?\.glb', os.path.basename(path))
        if not m: die(f'{path}: expected flat.glb or flat_<letter>.glb')
        return 'model-' + (m.group(1) or 'a')
    for sid, path in ((block_id(g), g) for g in glbs):
        data, tri, mats = read_glb(path)
        pat = block_pattern(sid)
        if not pat.search(html):
            die(f'{src}: no <script id="{sid}"> block to fill')
        b64 = base64.b64encode(data).decode('ascii')     # atob() chokes on whitespace inside
        html = pat.sub(lambda m: m.group(1) + b64 + m.group(3), html, count=1)
        filled.append((sid, path, data))
        print(f'  {sid} <- {os.path.basename(path)}: {len(data) / 1024:.0f} KiB, '
              f'{tri} triangles, {mats} materials')

    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(html)
    os.replace(tmp, out)

    # read back: what we just handed over has to carry the exact bytes of the GLB it claims to be
    check = open(out, encoding='utf-8').read()
    for sid, path, data in filled:
        got = block_pattern(sid).search(check).group(2).strip()
        if hashlib.sha256(base64.b64decode(got)).hexdigest() != hashlib.sha256(data).hexdigest():
            die(f'{out}: {sid} did not survive the round trip — refusing to hand it over')
    print(f'  wrote {out} ({os.path.getsize(out) / 1024 / 1024:.2f} MB); models verified against the GLBs')


main()
