"""Everything a project's design.py may call: `from engine.blender.api import *`."""
import math
from mathutils import Vector
from .ctx import MODE, INTERIOR, CEIL, CUT
from .materials import M, mat, srgb, BOOKC
from .geometry import box, cyl, sphere, disc, wall, window_frame, rod, floor, ceiling, rbox, link
from .fittings import curtain, blind, shell, room_floors, tread, flight
from .lights import LIGHTS, WARM, pointlight, led, ceiling_light, ceiling_fixture
from .furniture import counter_chair, chair, tower, artwork, bookcase, rnd, office_chair, bed
from .people import POSES, person, bone, figure_style
from .. import model          # model.walls(X, P), model.demolished(X, P), model.area(rooms, name)
