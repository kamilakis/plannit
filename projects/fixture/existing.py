"""FIXTURE — the smallest flat that exercises the whole pipeline: two rooms, one door, one window.
Not a real place. Plan frame: x, z metres (x east, z south), room faces at the numbers below."""
CEIL = 2.70
EXT = 0.25
# id: (x0, x1, z0, z1, kind, src, note)
WALLS = {
    'n': (-0.25, 7.35, -0.25, 0.00, 'ext', 'a', 'north wall'),
    's': (-0.25, 7.35,  3.20, 3.45, 'ext', 'a', 'south wall, with the window'),
    'w': (-0.25, 0.00,  0.00, 3.20, 'ext', 'a', 'west wall'),
    'e': ( 7.10, 7.35,  0.00, 3.20, 'ext', 'a', 'east wall'),
    'p': ( 4.00, 4.10,  0.00, 3.20, 'int', 'a', 'partition, with the door'),
}
# id: (wall, a, b, kind, sill, head, src width/·/height, note) — a, b along the wall's long axis
OPENINGS = {
    'D1': ('p', 1.20, 2.00, 'door',   0.00, 2.10, 'mmm', 'door between the rooms'),
    'W1': ('s', 1.40, 2.60, 'window', 0.90, 2.20, 'mmm', 'window of room A'),
}
ROOMS = {'ΔΩΜΑΤΙΟ Α': ([(0.00, 4.00, 0.00, 3.20)], (2.0, 1.2)),
         'ΔΩΜΑΤΙΟ Β': ([(4.10, 7.10, 0.00, 3.20)], (5.6, 1.2))}
