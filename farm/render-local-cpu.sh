#!/bin/bash
# Final renders: interiors 1200x750, 16 spp + OpenImageDenoise. Living-room views first.
# Run in a job directory made by farm/pack.sh (it has the scene.py entry).
B=~/.cache/blender/blender-4.5.14-linux-x64/blender
$B -b -P scene.py -- interior tv,sofa,kitchen,kitchen2,study 75 16 && \
$B -b -P scene.py -- plan all 100 16 && $B -b -P scene.py -- cutaway all 80 16 && \
$B -b -P scene.py -- interior entrance,bathroom,bedroom1,bedroom2 75 16
