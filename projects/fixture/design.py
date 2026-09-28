"""FIXTURE — what is built, in order: engine calls only."""
import existing as X, proposal as PR
from engine.blender.api import *

shell(X, PR)                                              # walls, openings (with window frames and glass)
room_floors(PR.ROOMS, model.walls(X, PR), set())          # a floor per room and a threshold under the door
chair(2.0, 2.2, -1)
bed(4.60, 6.20, 1.40, 3.20, 'N', 'linen')
if INTERIOR:
    ceiling(-0.25, 7.35, -0.25, 3.45)
    floor(-200, 200, -200, 200, 'ground', -3.0)           # something for the window to look out on
    ceiling_light(1.40, 2.60, 1.50, 1.70, 45)             # one recessed light per room
    ceiling_light(5.00, 6.20, 1.50, 1.70, 45)
