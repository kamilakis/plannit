"""FIXTURE — the sheets' words: labels, dimensions, title blocks. Engine calls only."""
import existing as X
from sheet import gr

CIRCULATION = set()
LABELS = {}
FIXTURES, FURNITURE = ('bed_frame',), ()


def _dims(sh):
    total = sh.room_labels()
    sh.chain([-0.25, 7.35], -0.95, True, -0.25)                        # overall length, above the plan
    for h, at, u in [(True, 0.6, 2.0), (True, 0.6, 5.6), (False, 0.8, 1.6), (False, 5.6, 1.6)]:
        sh.room_dim(h, at, u)
    return total


def _finish(no, title, total):
    return dict(rows=[('PROJECT', 'FIXTURE — two rooms'), ('SHEET', f'{title} · 1:50 (A3) · {no}'), ('DATE', '27/09/2026')],
                legend=[('hatch', 'Masonry kept'), ('new', 'New masonry'), ('demolished', 'Demolition'), ('fraction', '')],
                notes=['A test project: not a real place.', f'Total clear floor area {gr(total)} m².'])


def asbuilt(sh):
    return 'fixture-asbuilt', _finish('F.1', 'AS BUILT', _dims(sh))


def proposal(sh):
    return 'fixture-proposal', _finish('F.2', 'PROPOSAL', _dims(sh))


PROPOSAL_SHEETS = (proposal,)
