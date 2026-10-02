"""Materials: the named library every model builds from, palettes applied by name (ctx.PAL).
mat() makes a Principled material; glass(), glass_matte() and planks() are node networks."""
import bpy
from .ctx import PAL, PAL_PLANKS, MODE, NIGHT_LIGHTS

M = {}
PLANK_TONES = {}     # name -> the two sRGB tones a planks() material is built from (see the glb mode)
def mat(name, color, rough=0.6, metal=0.0, sheen=0.0, coat=0.0, emit=None, estr=0.0):
    if name in PAL: color = srgb(PAL[name])
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = estr
    M[name] = m; return m

def image_mat(name, path, strength=1.0):
    """A self-lit picture: an image file (relative to the project folder, e.g. 'assets/tv/show.png') through an
    Emission shader. For TV screens and the like — it shows its picture instead of reflecting the room, and a
    lit screen costs the renderer less than a glossy black one. Pair it with geometry.image_panel()."""
    import os
    from . import ctx
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission'); t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(os.path.join(ctx.PROJECT, path), check_existing=True)
    nt.links.new(t.outputs['Color'], e.inputs['Color']); e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    M[name] = m; return m

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

BOOKC = ['#6d4c3d', '#2f3e46', '#c8b89a', '#8c8c7e', '#a4523a', '#e8e1d4', '#3d5a4c', '#b08d57', '#555049', '#d6cbb8']

def glass():
    m = bpy.data.materials.new('glass'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); mix = nt.nodes.new('ShaderNodeMixShader')
    t = nt.nodes.new('ShaderNodeBsdfTransparent'); g = nt.nodes.new('ShaderNodeBsdfGlossy')
    g.inputs['Roughness'].default_value = 0.0
    mix.inputs['Fac'].default_value = 0.1
    nt.links.new(t.outputs[0], mix.inputs[1]); nt.links.new(g.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], o.inputs[0]); M['glass'] = m

def glass_matte(name='glass_matte', color='#e9eeee', rough=0.42):
    """Frosted screen: still transmits daylight, but rough enough to scatter it, so what is behind
    reads as a blur. Its own material on purpose — 'glass' is shared with every window in the flat.
    Another name/colour makes a variant, e.g. a dark smoked privacy screen."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.45
    M[name] = m; return m

def planks(name, c1, c2, width=1.9, row=0.19, rough=0.4):
    if name in PAL_PLANKS: c1, c2 = PAL_PLANKS[name]
    PLANK_TONES[name] = (c1, c2)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    tc = nt.nodes.new('ShaderNodeTexCoord')
    br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.37; br.offset_frequency = 1
    br.inputs['Color1'].default_value = (*srgb(c1), 1); br.inputs['Color2'].default_value = (*srgb(c2), 1)
    br.inputs['Mortar'].default_value = (*srgb('#6e5238'), 1)
    br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.0015
    br.inputs['Brick Width'].default_value = width; br.inputs['Row Height'].default_value = row
    br.inputs['Bias'].default_value = 0.0
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.25, 9.0, 1.0)
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6.0; nz.inputs['Detail'].default_value = 8
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs['Factor'].default_value = 0.35
    ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.3; ramp.inputs['From Max'].default_value = 0.7
    ramp.inputs['To Min'].default_value = 0.75; ramp.inputs['To Max'].default_value = 1.1
    nt.links.new(tc.outputs['Object'], br.inputs['Vector'])
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Value'])
    nt.links.new(br.outputs['Color'], mx.inputs['A'])
    comb = nt.nodes.new('ShaderNodeCombineColor')
    for k in ('Red', 'Green', 'Blue'): nt.links.new(ramp.outputs[0], comb.inputs[k])
    nt.links.new(comb.outputs[0], mx.inputs['B'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
    M[name] = m


def library():
    """The shared material library, in a fixed order (the render fingerprints hash every material)."""
    mat('wall', srgb('#eeebe5'), 0.92)
    mat('ceiling', srgb('#f3f1ec'), 0.95)
    mat('plaster', srgb('#e6e0d6'), 0.95)
    mat('oak', srgb('#c49a6c'), 0.45)
    mat('oak_dark', srgb('#8a6444'), 0.5)
    mat('white_matte', srgb('#ecebe7'), 0.55)
    mat('greige', srgb('#c9c2b6'), 0.6)
    mat('quartz', srgb('#f2f0eb'), 0.25, coat=0.3)
    mat('black', srgb('#1c1c1c'), 0.45, metal=0.6)
    mat('black_glass', srgb('#0d0d0d'), 0.08, coat=1.0)
    mat('boucle', srgb('#d9d3c8'), 1.0, sheen=0.6)
    mat('linen', srgb('#ece6dc'), 0.95, sheen=0.4)
    mat('linen_sage', srgb('#9aa58f'), 0.95, sheen=0.4)
    mat('curtain_light', srgb('#f1e9da'), 0.9, sheen=0.4)      # sheer layer: lets daylight through, softens it
    M['curtain_light'].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.55  # actually see-through
    mat('curtain_dark', srgb('#3a342c'), 0.95, sheen=0.15)     # blackout layer: for fully blocking outside light
    mat('rug', srgb('#d8ccb9'), 1.0, sheen=0.3)
    mat('terracotta', srgb('#b86d4b'), 0.8)
    mat('leaf', srgb('#4e6b3a'), 0.7)
    mat('stone', srgb('#d7cfc2'), 0.7)
    mat('microcement', srgb('#cfc8bd'), 0.55)
    mat('ceramic', srgb('#f6f6f4'), 0.12, coat=0.5)
    mat('mirror', (0.9, 0.9, 0.9), 0.02, metal=1.0)
    mat('frame', srgb('#2b2b2b'), 0.4, metal=0.3)
    mat('ground', srgb('#6f7466'), 1.0)
    mat('bulb', (1, 1, 1), 0.5, emit=(1.0, 0.82, 0.62), estr=25)
    mat('flame', (0, 0, 0), 1.0, emit=(1.0, 0.45, 0.12), estr=8)
    mat('downlight', (1, 1, 1), 0.5, emit=(1.0, 0.9, 0.78), estr=6)
    mat('led_soft', (1, 1, 1), 0.5, emit=(1.0, 0.78, 0.55), estr=1.2)
    mat('led_warm', (1, 1, 1), 0.5, emit=(1.0, 0.78, 0.55), estr=1.0)
    mat('led_dim', (1, 1, 1), 0.5, emit=(1.0, 0.78, 0.55), estr=0.35)
    mat('art1', srgb('#c9b79c'), 0.9)
    mat('art2', srgb('#3f4a3c'), 0.9)
    for i, c in enumerate(BOOKC): mat(f'book{i}', srgb(c), 0.8)
    glass()
    glass_matte()
    planks('floor_oak', '#c9a47a', '#bf9a6f')
    planks('slats', '#b98c5f', '#b3875a', width=4.0, row=0.06)
    if MODE == 'night' and NIGHT_LIGHTS == 'tagged':      # a sleeping flat: the luminaires' own glow goes out too
        for n in ('downlight', 'led_soft', 'led_warm', 'led_dim', 'bulb'):
            if n in M: M[n].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0
