"""FIXTURE — how it is looked at: one palette (the library's own), section heights, sky, sun, two cameras."""
PALETTES = {}
CUTS = {'plan': 1.45, 'cutaway': 1.15, 'glb': 1.15}
SKY = dict(elevation=35, rotation=180, altitude=30, air=1.0, dust=1.0, strength=0.35, night=(0.004, 0.006, 0.014))
SUN = dict(azimuth=180, elevation=35, energy=3.5, angle=1.5, color=(1.0, 0.92, 0.82))   # from the south, through the window
CAMERAS = {
    'interior': {'room': dict(pos=(6.60, 2.80, 1.55), tgt=(1.2, 1.0, 1.0), lens=24, exposure=0.8)},   # from room B, through the door
    'cutaway':  {},
    'plan':     {'plan': dict(pos=(3.55, 1.60, 20.0), tgt=(3.55, 1.6001, 0.0), lens=50, exposure=0.3, ortho=9.0,
                          res=(1400, 1000), topdown=True)},
}
