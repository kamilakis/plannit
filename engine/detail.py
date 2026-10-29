"""Detail sheets: several views of the model on one A3 sheet, each at its own scale — a kitchen's plan and
elevations, a schedule of windows. Laid out in paper millimetres and written as an SVG (print it with
print_pdf.py in.svg out.pdf 420 297) and a DXF (R12; paper mm × the sheet's main scale, so lengths read true in
the views drawn at that scale). The views are cut through the model's boxes (out/renders/model-dump.json, the
same file the A.2 sheet reads): what the cut plane passes through is drawn in section, what lies beyond it in
view, with hidden lines removed. Stdlib only; the project's details.py says what goes on each sheet.
Plan frame as everywhere: x, z metres, h up. A view maps model boxes to its own (u, w): u to the right, w up."""
import math
from xml.sax.saxutils import escape

LAYERS = {  # name: (ACI colour, svg colour, svg stroke mm, flags)
    'FRAME': (7, '#000', 0.35, ''), 'TITLE': (7, '#000', 0.18, ''), 'CUT': (7, '#000', 0.35, ''),
    'HATCH': (1, '#8c2d19', 0.09, ''), 'OUTLINE': (7, '#000', 0.18, ''), 'DETAIL': (8, '#444', 0.1, ''),
    'HIDDEN': (8, '#555', 0.12, 'dash'), 'GLASS': (5, '#2a6db0', 0.12, ''), 'FILL': (9, '#eee', 0.0, 'fill'),
    'DIMENSIONS': (7, '#000', 0.09, ''), 'DIM_TEXT': (7, '#000', 0.1, ''), 'TEXT': (7, '#000', 0.1, ''),
    'TAG': (1, '#b0281a', 0.18, ''), 'NOTES': (7, '#000', 0.1, '')}
FILLS = {'k_sage': '#dde3d3', 'k_oak': '#efe1c8', 'k_stone': '#f3eee6', 'k_recess': '#f3eee6', 'k_sink': '#e9dcc4',
         'steel': '#e1e4e8', 'black_glass': '#6b6f75', 'black': '#333', 'oak': '#efe1c8', 'white_matte': '#fafafa',
         'wall': '#ffffff', 'plaster': '#ffffff', 'glass': '#e3eff8', 'cut': '#d9d9d9'}


def text_w(t, h): return len(t) * 0.60 * h * 1.38 * 0.90        # paper mm, DejaVu Sans Condensed, roughly (capitals)


class Box:
    """One model box seen from a view: its rectangle (u0, u1, w0, w1), its depth beyond the cut (d0, d1), name, material."""
    __slots__ = ('u0', 'u1', 'w0', 'w1', 'd0', 'd1', 'n', 'm')
    def __init__(s, u0, u1, w0, w1, d0, d1, n, m): s.u0, s.u1, s.w0, s.w1, s.d0, s.d1, s.n, s.m = u0, u1, w0, w1, d0, d1, n, m


# how each kind of view maps a model box (x0, x1, z0, z1, h0, h1) to (u0, u1, w0, w1, d0, d1)
def looking(direction, at):
    """'+z' / '-z' / '+x' / '-x': an elevation looking that way, its cut plane at z (or x) = at; 'down': a plan,
    cut at h = at. Each keeps the viewer's right hand on +u (plan: +x right, +z down the paper)."""
    return {
        '+z': lambda x0, x1, z0, z1, h0, h1: (-x1, -x0, h0, h1, z0 - at, z1 - at),
        '-z': lambda x0, x1, z0, z1, h0, h1: (x0, x1, h0, h1, at - z1, at - z0),
        '+x': lambda x0, x1, z0, z1, h0, h1: (z0, z1, h0, h1, x0 - at, x1 - at),
        '-x': lambda x0, x1, z0, z1, h0, h1: (-z1, -z0, h0, h1, at - x1, at - x0),
        'down': lambda x0, x1, z0, z1, h0, h1: (x0, x1, -z1, -z0, at - h1, at - h0)}[direction]


class View:
    """A drawing at 1:scale, in its own metres (u right, w up), placed on the paper later (Paper.put)."""
    def __init__(s, scale, title=None):
        s.scale, s.k, s.title = scale, 1000 / scale, title
        s.fmt = lambda v: f'{round(v * 1000):d}'          # dimension figures: mm (a schedule in metres sets its own)
        s.E = []                                    # (kind, layer, ...) in view metres; text heights in paper mm
    # ---- primitives (view metres)
    def line(s, l, a, b): s.E.append(('line', l, a, b))
    def pline(s, l, pts, closed=True): s.E.append(('pline', l, list(pts), closed))
    def fill(s, colour, pts): s.E.append(('fill', 'FILL', list(pts), colour))
    def text(s, l, p, t, h, rot=0, align='c'): s.E.append(('text', l, p, t, h, rot, align))
    def rect(s, l, u0, u1, w0, w1): s.pline(l, [(u0, w0), (u1, w0), (u1, w1), (u0, w1)])
    def hatch(s, u0, u1, w0, w1, step_mm=1.6):
        """45° hatch over a rectangle, its spacing in paper mm."""
        st = step_mm / s.k; c = math.floor((u0 - w1) / st) * st
        while c < u1 - w0:
            c += st                                 # the line u - w = c
            a = (max(u0, w0 + c), max(u0, w0 + c) - c); b = (min(u1, w1 + c), min(u1, w1 + c) - c)
            if b[0] - a[0] > 1e-6: s.line('HATCH', a, b)
    def brk(s, u, w0, w1):
        """A break line across the view at u: the drawing goes on past it."""
        z = 1.2 / s.k; m = (w0 + w1) / 2
        s.pline('DETAIL', [(u, w0), (u, m - 2 * z), (u + z, m - z), (u - z, m + z), (u, m + 2 * z), (u, w1)], False)
    def tag(s, p, t, r_mm=2.3):
        """A unit number in a circle (the schedule's numbering)."""
        r = r_mm / s.k
        s.pline('TAG', [(p[0] + r * math.cos(i * math.pi / 12), p[1] + r * math.sin(i * math.pi / 12)) for i in range(24)])
        s.text('TAG', p, t, 2.0)
    def marker(s, p, letter, direction, r_mm=3.0):
        """A view marker on a plan: a circle with the view's letter and a filled point toward where it looks."""
        r = r_mm / s.k; dx, dy = {'+x': (1, 0), '-x': (-1, 0), '+z': (0, -1), '-z': (0, 1)}[direction]
        s.pline('TEXT', [(p[0] + r * math.cos(i * math.pi / 12), p[1] + r * math.sin(i * math.pi / 12)) for i in range(24)])
        tip = (p[0] + dx * r * 1.9, p[1] + dy * r * 1.9)                  # outside the circle, clear of the letter
        a = (p[0] + dx * r * 0.8 - dy * r * 0.6, p[1] + dy * r * 0.8 + dx * r * 0.6); b = (p[0] + dx * r * 0.8 + dy * r * 0.6, p[1] + dy * r * 0.8 - dx * r * 0.6)
        s.E.append(('fill', 'FILL', [a, tip, b], '#000'))
        s.text('TEXT', p, letter, 2.6)
    # ---- dimensions (view metres; figures in mm)
    def dim(s, a, b, at, horiz, ext_from=None, lift=0):
        if abs(b - a) < 0.004: return
        P = (lambda u: (u, at)) if horiz else (lambda u: (at, u))
        t = 0.9 / s.k
        s.line('DIMENSIONS', P(a), P(b))
        for u in (a, b):
            q = P(u); s.line('DIMENSIONS', (q[0] - t, q[1] - t), (q[0] + t, q[1] + t))
            if ext_from is not None:
                sg = 1 if at > ext_from else -1; g = 0.8 / s.k
                s.line('DIMENSIONS', (u, ext_from + sg * g) if horiz else (ext_from + sg * g, u),
                       (u, at + sg * g) if horiz else (at + sg * g, u))
        v = s.fmt(abs(b - a)); m = (a + b) / 2
        off = (1.3 + lift) / s.k
        if horiz: s.text('DIM_TEXT', (m, at + off), v, 1.6)
        else: s.text('DIM_TEXT', (at - off, m), v, 1.6, 90)
    def chain(s, pts, at, horiz, ext_from=None, total=True, gap_mm=5.0):
        """A dimension chain; a figure too long for its span is lifted clear of its neighbours. The overall
        dimension goes one row further out (away from ext_from)."""
        pts = sorted(set(round(p, 4) for p in pts)); lifted = False
        for a, b in zip(pts, pts[1:]):
            short = abs(b - a) * s.k < text_w(s.fmt(abs(b - a)), 1.6) + 0.8
            lifted = short and not lifted
            s.dim(a, b, at, horiz, ext_from, 2.2 if lifted else 0)
        if total and len(pts) > 2:
            out = gap_mm / s.k * (1 if ext_from is None or at > ext_from else -1)
            s.dim(pts[0], pts[-1], at + out, horiz)
    # ---- a cut through boxes: the section and what lies beyond it, hidden lines removed
    def project(s, boxes, see, far=1.5, crop=None, lines=('k_gap', 'gap', 'fridge_gap'), cut_fill=None, hatch_cut=('wall', 'plaster', 'column', 'beam', 'slab')):
        """boxes: [(name, x0, x1, z0, z1, h0, h1, material)]; see: looking(...). Boxes the plane passes through are
        drawn in section (walls hatched, joinery filled in its colour, heavy outline); boxes up to `far` beyond it
        in view, nearer ones hiding the edges of those behind; thin boxes named in `lines` become a single line.
        crop: (u0, u1, w0, w1) — nothing is drawn outside it. Returns (cut boxes, seen boxes)."""
        cut, seen = [], []
        for n, x0, x1, z0, z1, h0, h1, m in boxes:
            u0, u1, w0, w1, d0, d1 = see(x0, x1, z0, z1, h0, h1)
            if crop:
                u0, u1, w0, w1 = max(u0, crop[0]), min(u1, crop[1]), max(w0, crop[2]), min(w1, crop[3])
                if u1 - u0 < 1e-4 or w1 - w0 < 1e-4: continue
            b = Box(u0, u1, w0, w1, d0, d1, n, m)
            if d1 <= 1e-6: continue                                   # in front of the plane
            if d0 < -1e-6: cut.append(b)
            elif d0 <= far: seen.append(b)
        seen.sort(key=lambda b: -b.d0)                                # far first
        opaque = lambda b: b.m not in ('glass', 'glass_matte') and b.n not in lines
        for b in seen:
            if b.n in lines: continue
            s.fill(FILLS.get(b.m, '#fff'), [(b.u0, b.w0), (b.u1, b.w0), (b.u1, b.w1), (b.u0, b.w1)])
        for b in cut:
            s.fill(cut_fill or ('#fff' if b.n in hatch_cut else FILLS.get(b.m, '#fff')), [(b.u0, b.w0), (b.u1, b.w0), (b.u1, b.w1), (b.u0, b.w1)])
            if b.n in hatch_cut: s.hatch(b.u0, b.u1, b.w0, b.w1)
        # visible edges: each seen box's four, minus what a nearer box (or the section) covers
        def covers(o, b): return o is not b and opaque(o) and (o in cut or o.d0 < b.d0 - 0.004)
        occ = cut + seen
        for b in seen:
            hide = [o for o in occ if covers(o, b)]
            if b.n in lines:                                          # a door gap: one line down its middle
                if (b.u1 - b.u0) < (b.w1 - b.w0): s._seg('DETAIL', True, (b.u0 + b.u1) / 2, b.w0, b.w1, hide)
                else: s._seg('DETAIL', False, (b.w0 + b.w1) / 2, b.u0, b.u1, hide)
                continue
            l = 'GLASS' if b.m in ('glass', 'glass_matte') else ('DETAIL' if b.m in ('black', 'black_glass') or b.n.endswith('handle') else 'OUTLINE')
            for w in (b.w0, b.w1): s._seg(l, False, w, b.u0, b.u1, hide)
            for u in (b.u0, b.u1): s._seg(l, True, u, b.w0, b.w1, hide)
        for b in cut: s.rect('CUT', b.u0, b.u1, b.w0, b.w1)
        return cut, seen
    def _seg(s, l, vertical, c, a, b, hide, eps=1e-4):
        """The parts of an axis-aligned segment (u = c, w from a to b if vertical; else w = c, u from a to b) that
        no box in `hide` covers (a segment along a box's edge is not covered by it)."""
        iv = [(a, b)]
        for o in hide:
            lo, hi, c0, c1 = (o.w0, o.w1, o.u0, o.u1) if vertical else (o.u0, o.u1, o.w0, o.w1)
            if not (c0 + eps < c < c1 - eps): continue
            nxt = []
            for p, q in iv:
                if hi <= p or lo >= q: nxt.append((p, q)); continue
                if lo > p: nxt.append((p, lo))
                if hi < q: nxt.append((hi, q))
            iv = nxt
        for p, q in iv:
            if q - p > 0.002: s.line(l, (c, p) if vertical else (p, c), (c, q) if vertical else (q, c))
    # ---- extent on paper (mm, relative to the view's origin u = w = 0), for laying views out
    def extent(s):
        xs, ys = [], []
        for e in s.E:
            pts = [e[2], e[3]] if e[0] == 'line' else (e[2] if e[0] in ('pline', 'fill') else [e[2]])
            for p in pts: xs.append(p[0] * s.k); ys.append(-p[1] * s.k)
            if e[0] == 'text':
                w = text_w(e[3], e[4]); p = e[2]
                if abs(e[5]) < 1: xs += [p[0] * s.k - w / 2, p[0] * s.k + w / 2]
                else: ys += [-p[1] * s.k - w / 2, -p[1] * s.k + w / 2]
        return min(xs), max(xs), min(ys), max(ys)


class Paper:
    """An A3 sheet (landscape by default): views put on it, paper-mm text, a frame and a title block."""
    def __init__(s, scale, landscape=True):
        s.W, s.H = (420, 297) if landscape else (297, 420)
        s.scale = scale                              # the DXF's unit: paper mm × this
        s.E = []                                     # (kind, layer, ...) in paper mm, y down
    @staticmethod
    def title_w(view):
        """How far a view's title runs on the paper (mm), for laying views side by side."""
        if not view.title: return 0
        t, sub = view.title if isinstance(view.title, tuple) else (view.title, f'1:{view.scale}')
        return text_w(t, 2.6) * 1.12 + 3 + text_w(sub, 2.0)
    def put(s, view, x, y, anchor='tl'):
        """Place a view so its extent's top-left (or 'bl' bottom-left, 'tr', 'br', 'c') corner lands at (x, y) mm;
        its title under it. Returns its paper box (x0, x1, y0, y1)."""
        e0, e1, f0, f1 = view.extent()
        ox = {'l': x - e0, 'r': x - e1, 'c': x - (e0 + e1) / 2}[anchor[1] if len(anchor) > 1 else 'c']
        oy = {'t': y - f0, 'b': y - f1, 'c': y - (f0 + f1) / 2}[anchor[0]]
        M = lambda p: (ox + p[0] * view.k, oy - p[1] * view.k)
        for e in view.E:
            if e[0] == 'line': s.E.append(('line', e[1], M(e[2]), M(e[3])))
            elif e[0] == 'pline': s.E.append(('pline', e[1], [M(p) for p in e[2]], e[3]))
            elif e[0] == 'fill': s.E.append(('fill', e[1], [M(p) for p in e[2]], e[3]))
            elif e[0] == 'text': s.E.append(('text', e[1], M(e[2]), *e[3:]))
        box = (ox + e0, ox + e1, oy + f0, oy + f1)
        if view.title:
            t, sub = view.title if isinstance(view.title, tuple) else (view.title, f'1:{view.scale}')
            s.text('TEXT', (box[0], box[3] + 6), t, 2.6, align='l')
            s.text('TEXT', (box[0] + text_w(t, 2.6) * 1.12 + 3, box[3] + 6), sub, 2.0, align='l')
            s.line('TEXT', (box[0], box[3] + 8), (box[0] + text_w(t, 2.6), box[3] + 8))
        return box
    def line(s, l, a, b): s.E.append(('line', l, a, b))
    def pline(s, l, pts, closed=True): s.E.append(('pline', l, list(pts), closed))
    def fill(s, colour, pts): s.E.append(('fill', 'FILL', list(pts), colour))
    def text(s, l, p, t, h, rot=0, align='c'): s.E.append(('text', l, p, t, h, rot, align))
    def rect(s, l, x0, y0, x1, y1): s.pline(l, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    def notes(s, x, y, lines, width, h=1.6, lead=3.6):
        """Lines of text from (x, y), each wrapped to `width` mm (continuations indented). Returns the y after them."""
        for t in lines:
            words, cur, first = t.split(' '), '', True
            for wd in words:
                if cur and text_w(cur + ' ' + wd, h) * 0.92 > width:
                    s.text('NOTES', (x if first else x + 3, y), cur, h, align='l'); y += lead; cur, first = wd, False
                else: cur = (cur + ' ' + wd) if cur else wd
            if cur: s.text('NOTES', (x if first else x + 3, y), cur, h, align='l'); y += lead
        return y
    def table(s, x, y, cols, rows, h=1.9, rh=5.0, head=True):
        """A ruled table at (x, y) top-left: cols [(title, width mm, align)], rows [[cell text]]. Returns its bottom y."""
        X = [x]
        for _t, w, _a in cols: X.append(X[-1] + w)
        allrows = ([[c[0] for c in cols]] if head else []) + rows
        for i, r in enumerate(allrows):
            y0 = y + i * rh
            for j, (t, (_ct, w, al)) in enumerate(zip(r, cols)):
                tx = {'l': X[j] + 1.2, 'c': (X[j] + X[j + 1]) / 2, 'r': X[j + 1] - 1.2}[al]
                s.text('TITLE' if head and i == 0 else 'NOTES', (tx, y0 + rh / 2), t, h * (0.9 if head and i == 0 else 1), align=al)
            s.line('TITLE', (x, y0), (X[-1], y0))
        yb = y + len(allrows) * rh
        s.line('TITLE', (x, yb), (X[-1], yb))
        if head: s.line('FRAME', (x, y + rh), (X[-1], y + rh))
        for u in X: s.line('TITLE', (u, y), (u, yb))
        return yb
    def frame(s, rows, notes=(), notes_at=None, block_w=120):
        """The border (20 mm binding margin on the left), the title block in the bottom-right corner (rows
        [(label, value)]), and notes: lines of text from notes_at (x, y) — by default left of the title block."""
        s.rect('FRAME', 20, 10, s.W - 10, s.H - 10)
        RH = 7.2; x1 = s.W - 10; x0 = x1 - block_w; y = s.H - 10 - RH * len(rows)
        s.block = (x0, y)
        for k, v in rows:
            s.rect('TITLE', x0, y, x1, y + RH)
            s.text('TITLE', (x0 + 2, y + 2.0), k, 1.5, align='l')
            s.text('TITLE', ((x0 + x1) / 2, y + 4.9), v, 2.3 if len(v) < 44 else 1.9)
            y += RH
        if notes:
            nx, ny = notes_at
            for t in notes: s.text('NOTES', (nx, ny), t, 1.75, align='l'); ny += 3.9
    def north(s, x, y):
        """North arrow: TRUE north = plan +x (paper right on a plan drawn with +x to the right)."""
        s.pline('FRAME', [(x + 9, y), (x - 7, y - 4.5), (x - 4, y), (x - 7, y + 4.5)])
        s.fill('#000', [(x + 9, y), (x - 7, y - 4.5), (x - 4, y)]); s.text('TITLE', (x + 12, y), 'Β', 4)
    # ---- files
    def write(s, base):
        s._svg(base + '.svg'); s._dxf(base + '.dxf')
    def _svg(s, path):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.W}mm" height="{s.H}mm" viewBox="0 0 {s.W} {s.H}">',
               '<rect width="100%" height="100%" fill="#fff"/>',
               '<style>text{font-family:"DejaVu Sans Condensed","DejaVu Sans",sans-serif;dominant-baseline:central}</style>']
        P = lambda p: f'{p[0]:.2f},{p[1]:.2f}'
        for e in s.E:
            k, l = e[0], e[1]; col, sw, fl = LAYERS[l][1], LAYERS[l][2], LAYERS[l][3]
            dash = ' stroke-dasharray="1.6 0.8"' if fl == 'dash' else ''
            if k == 'line': out.append(f'<polyline points="{P(e[2])} {P(e[3])}" fill="none" stroke="{col}" stroke-width="{sw}"{dash}/>')
            elif k == 'pline':
                tg = 'polygon' if e[3] else 'polyline'
                out.append(f'<{tg} points="{" ".join(P(p) for p in e[2])}" fill="none" stroke="{col}" stroke-width="{sw}"{dash} stroke-linejoin="round"/>')
            elif k == 'fill': out.append(f'<polygon points="{" ".join(P(p) for p in e[2])}" fill="{e[3]}" stroke="none"/>')
            elif k == 'text':
                _, _, p, t, h, rot, al = e
                anc = {'l': 'start', 'c': 'middle', 'r': 'end'}[al]
                out.append(f'<text x="{p[0]:.2f}" y="{p[1]:.2f}" font-size="{h * 1.38:.2f}" text-anchor="{anc}" fill="{col}" '
                           f'transform="rotate({-rot:.2f} {p[0]:.2f} {p[1]:.2f})">{escape(t)}</text>')
        out.append('</svg>'); open(path, 'w').write('\n'.join(out))
    def _dxf(s, path):
        K = s.scale; X = lambda x: round(x * K, 1); Y = lambda y: round((s.H - y) * K, 1)
        esc = lambda t: ''.join(c if ord(c) < 128 else f'\\U+{ord(c):04X}' for c in t)
        w = []; P = lambda c, v: w.append(f'{c:>3}\n{v}')
        P(0, 'SECTION'); P(2, 'HEADER'); P(9, '$ACADVER'); P(1, 'AC1009')
        P(9, '$EXTMIN'); P(10, 0); P(20, 0); P(30, 0); P(9, '$EXTMAX'); P(10, X(s.W)); P(20, Y(0)); P(30, 0)
        P(9, '$DIMSCALE'); P(40, K); P(9, '$LTSCALE'); P(40, K)
        P(0, 'ENDSEC'); P(0, 'SECTION'); P(2, 'TABLES')
        P(0, 'TABLE'); P(2, 'LTYPE'); P(70, 2); P(0, 'LTYPE'); P(2, 'CONTINUOUS'); P(70, 0); P(3, 'Solid line'); P(72, 65); P(73, 0); P(40, 0.0)
        P(0, 'LTYPE'); P(2, 'DASHED'); P(70, 0); P(3, '__ __ __'); P(72, 65); P(73, 2); P(40, 3.0); P(49, 2.0); P(49, -1.0); P(0, 'ENDTAB')
        P(0, 'TABLE'); P(2, 'STYLE'); P(70, 1); P(0, 'STYLE'); P(2, 'STANDARD'); P(70, 0); P(40, 0); P(41, 1); P(50, 0); P(71, 0); P(42, 2.5); P(3, 'arial.ttf'); P(4, ''); P(0, 'ENDTAB')
        P(0, 'TABLE'); P(2, 'LAYER'); P(70, len(LAYERS))
        for n, (c, _, _, f) in LAYERS.items(): P(0, 'LAYER'); P(2, n); P(70, 1 if f == 'fill' else 0); P(62, c); P(6, 'DASHED' if f == 'dash' else 'CONTINUOUS')
        P(0, 'ENDTAB'); P(0, 'ENDSEC'); P(0, 'SECTION'); P(2, 'ENTITIES')
        AL = {'l': 0, 'c': 1, 'r': 2}
        for e in s.E:
            k, l = e[0], e[1]
            if k == 'line': a, b = e[2], e[3]; P(0, 'LINE'); P(8, l); P(10, X(a[0])); P(20, Y(a[1])); P(30, 0); P(11, X(b[0])); P(21, Y(b[1])); P(31, 0)
            elif k == 'pline':
                P(0, 'POLYLINE'); P(8, l); P(66, 1); P(10, 0); P(20, 0); P(30, 0); P(70, 1 if e[3] else 0)
                for p in e[2]: P(0, 'VERTEX'); P(8, l); P(10, X(p[0])); P(20, Y(p[1])); P(30, 0)
                P(0, 'SEQEND'); P(8, l)
            elif k == 'fill':                       # on the FILL layer, frozen: the colours are for the SVG
                q = e[2] + [e[2][-1]] * (4 - len(e[2])) if len(e[2]) <= 4 else None
                if q is None: continue
                a, b, c, d = q; P(0, 'SOLID'); P(8, l)
                for g, p in ((0, a), (1, b), (2, d), (3, c)): P(10 + g, X(p[0])); P(20 + g, Y(p[1])); P(30 + g, 0)
            elif k == 'text':
                _, _, p, t, h, rot, al = e; P(0, 'TEXT'); P(8, l); P(10, X(p[0])); P(20, Y(p[1])); P(30, 0); P(40, round(h * K, 1)); P(1, esc(t))
                P(50, round(rot, 2)); P(72, AL[al]); P(11, X(p[0])); P(21, Y(p[1])); P(31, 0); P(73, 2)
        P(0, 'ENDSEC'); P(0, 'EOF')
        open(path, 'w', newline='\r\n').write('\n'.join(w) + '\n')
