"""FIXTURE — the renovation: the door between the rooms widened to 0.90. Data only (engine/model.py makes the walls)."""
from existing import ROOMS as _R
OPENING_CHANGES = {'D1': (1.10, 2.00, 0.00, 2.10, 'door')}   # widened 0.80 -> 0.90, cut into the partition
ROOMS = dict(_R)
