"""World, sun and render settings; cameras; the export modes (glb, and svg = the model dump); the render loop with
per-image fingerprints (render only what changed)."""
import bpy, math, os, time
from mathutils import Vector
from . import ctx
from .ctx import MODE, PALETTE, SUFFIX, CAMS, PCT, SAMPLES, OUT, CUT, PROJECT, SHAPES, WALLS, OPENINGS
from .materials import M, PLANK_TONES, srgb
from .geometry import COL, link
S = bpy.context.scene


def world(sky_p, sun_p):
    """Nishita sky + a sun. sky_p: elevation, rotation (deg), altitude, air, dust, strength, night (RGB);
    sun_p: azimuth (compass deg), elevation (deg), energy, angle (deg), color. Compass -> Blender:
    true north = +X, true east = -Y (plan +z)."""
    w = bpy.data.worlds.new('w'); S.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'NISHITA'
    sky.sun_disc = False; sky.sun_elevation = math.radians(sky_p['elevation']); sky.sun_rotation = math.radians(sky_p['rotation'])
    sky.altitude = sky_p['altitude']; sky.air_density = sky_p['air']; sky.dust_density = sky_p['dust']
    nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = sky_p['strength']
    if MODE == 'night':
        nt.links.remove(bg.inputs[0].links[0]); bg.inputs[0].default_value = (*sky_p['night'], 1); bg.inputs[1].default_value = 1.0

    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 0.0 if MODE == 'night' else sun_p['energy']; sun.angle = math.radians(sun_p['angle']); sun.color = sun_p['color']
    so = link(bpy.data.objects.new('sun', sun))
    az, el = math.radians(sun_p['azimuth']), math.radians(sun_p['elevation'])
    to_sun = Vector((math.cos(az) * math.cos(el), -math.sin(az) * math.cos(el), math.sin(el)))
    sky.sun_rotation = math.atan2(to_sun.x, to_sun.y)
    so.rotation_euler = to_sun.to_track_quat('Z', 'Y').to_euler()


def settings():
    S.render.engine = 'CYCLES'; cy = S.cycles
    cy.device = 'CPU'; cy.samples = SAMPLES
    DEVICE = os.environ.get('RENDER_DEVICE', 'CPU').upper()          # CPU | OPTIX | CUDA
    if DEVICE != 'CPU':
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = DEVICE; prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == DEVICE]
        if not gpus: raise SystemExit(f'no {DEVICE} device found — check the NVIDIA driver (RTX 50xx needs >= 570)')
        for d in prefs.devices: d.use = d.type == DEVICE
        cy.device = 'GPU'; cy.denoising_use_gpu = True
        print('GPU:', ', '.join(d.name for d in gpus), flush=True); cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.03
    cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
    cy.max_bounces = 8; cy.diffuse_bounces = 4; cy.glossy_bounces = 3; cy.transmission_bounces = 6; cy.transparent_max_bounces = 8
    cy.sample_clamp_indirect = 4.0; cy.caustics_reflective = False; cy.caustics_refractive = False
    S.render.resolution_x, S.render.resolution_y = 1600, 1000
    S.render.resolution_percentage = PCT; S.render.use_persistent_data = True
    S.view_settings.view_transform = 'AgX'; S.view_settings.look = 'AgX - Medium High Contrast'
    S.render.image_settings.file_format = 'JPEG'; S.render.image_settings.quality = 92
    return cy


def camera(name, pos, tgt, lens=20, exposure=0.0, ortho=None, res=None, topdown=False):
    """topdown: looks straight down, unrotated (a plan view), instead of aiming at tgt."""
    c = bpy.data.cameras.new(name); c.lens = lens; c.clip_start = 0.05
    if ortho: c.type = 'ORTHO'; c.ortho_scale = ortho
    o = link(bpy.data.objects.new(name, c))
    p = Vector((pos[0], -pos[1], pos[2])); t = Vector((tgt[0], -tgt[1], tgt[2]))
    o.location = p; o.rotation_euler = (0, 0, 0) if topdown else (t - p).to_track_quat('-Z', 'Y').to_euler()
    return (o, exposure, res)


def export_glb():
        out = os.path.join(OUT, 'flat' + SUFFIX + '.glb')
        os.makedirs(OUT, exist_ok=True)

        # Three materials are node networks rather than Principled BSDFs — planks() (the floor and the
        # island/headboard slats) and glass() (a transparent+glossy mix). glTF cannot carry either, and
        # the exporter drops them *silently*: the floor, the slats and every window came out plain white
        # in the web viewer, in both palettes. Rebuild those three flat, for the export only — the renders
        # keep the procedural planks and the mixed glass.
        def flatten(name, colour, rough, alpha=None):
            m = M.get(name)
            if not m: return
            nt = m.node_tree; nt.nodes.clear()
            b = nt.nodes.new('ShaderNodeBsdfPrincipled')
            b.inputs['Base Color'].default_value = (*srgb(colour), 1)
            b.inputs['Roughness'].default_value = rough
            b.inputs['Metallic'].default_value = 0.0
            if alpha is not None:
                b.inputs['Alpha'].default_value = alpha
                if hasattr(m, 'blend_method'): m.blend_method = 'BLEND'
            nt.links.new(b.outputs['BSDF'], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
            print(f'   flattened {name} for glTF -> {colour} (node network would export as white)', flush=True)
        tone = lambda n, fallback: '#' + ''.join(
            f'{(int(PLANK_TONES[n][0][i:i+2], 16) + int(PLANK_TONES[n][1][i:i+2], 16)) // 2:02x}' for i in (1, 3, 5)) \
            if n in PLANK_TONES else fallback
        flatten('floor_oak', tone('floor_oak', '#c9a47a'), 0.4)
        flatten('slats', tone('slats', '#b98c5f'), 0.4)
        flatten('glass', '#cfe3e8', 0.08, alpha=0.32)     # pale blue-green, translucent

        bpy.ops.object.select_all(action='DESELECT')
        for o in list(COL.objects):
            if o.type == 'LIGHT': bpy.data.objects.remove(o, do_unlink=True)
        # merge everything per material: ~480 objects -> one mesh per material, so the web viewer draws
        # a few dozen batches instead of hundreds (the model was slow on a phone otherwise)
        meshes = [o for o in COL.objects if o.type == 'MESH']
        bpy.context.view_layer.objects.active = meshes[0]
        for o in meshes: o.select_set(True)
        bpy.ops.object.convert(target='MESH')                      # bakes bevel/weighted-normal modifiers
        groups = {}
        for o in [x for x in COL.objects if x.type == 'MESH']:
            groups.setdefault(o.data.materials[0].name if o.data.materials else '_none', []).append(o)
        for name, objs in groups.items():
            bpy.ops.object.select_all(action='DESELECT')
            for o in objs: o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            if len(objs) > 1: bpy.ops.object.join()
            bpy.context.active_object.name = 'merged_' + name
        print('merged into', len(groups), 'meshes', flush=True)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_apply=True, export_cameras=False,
                                  export_lights=False, export_yup=True)
        # artifacts serve .json but not .glb: repack the GLB as a .gltf JSON with the buffer as a data URI
        import json as _json, base64, struct as _st
        d = open(out, 'rb').read(); off, js, bin_ = 12, None, b''
        while off < len(d):
            ln, ty = _st.unpack_from('<II', d, off); chunk = d[off + 8:off + 8 + ln]; off += 8 + ln + (-ln % 4)
            if ty == 0x4E4F534A: js = _json.loads(chunk.decode('utf-8'))
            elif ty == 0x004E4942: bin_ = chunk
        js['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(bin_).decode()
        js['buffers'][0]['byteLength'] = len(bin_)
        jout = out[:-4] + '.json'; open(jout, 'w').write(_json.dumps(js, separators=(',', ':')))
        print('WROTE', out, os.path.getsize(out) // 1024, 'KiB +', jout, os.path.getsize(jout) // 1024, 'KiB', flush=True)
        # the render farm's watcher counts lines starting with RENDERED to tell a pass succeeded (it greps
        # the log before/after each device attempt); glb/glb-b never printed one, so every queued glb job
        # was silently marked "rendered nothing" and retried device-by-device even when the export was fine.
        print('RENDERED', 'glb' + SUFFIX.replace('_', '-'), flush=True)
        os._exit(0)


def model_dump():
    """The svg mode: the model's bookkeeping (WALLS, OPENINGS, SHAPES) as out/renders/model-dump.json — read by the
    proposal sheets for the fittings they draw, and diffable to prove a change moved nothing. (Until 27 Sep this
    mode also ran plan2d.py, the old check / engineer / contractor drawings, now sheets A.2 and A.3.)"""
    import json
    os.makedirs(OUT, exist_ok=True)
    json.dump({'walls': WALLS, 'openings': OPENINGS, 'shapes': SHAPES}, open(os.path.join(OUT, 'model-dump.json'), 'w'))
    print('RENDERED svg', flush=True)       # the farm counts ^RENDERED lines to tell a pass worked
    os._exit(0)


def run(views):
    """Everything after the model is built: world, settings, then the mode — an export, or the renders."""
    world(views.SKY, views.SUN)
    cy = settings()
    if MODE == 'glb': export_glb()
    if MODE == 'svg': model_dump()
    CAMERAS = {k: {n: camera(n, **v) for n, v in vs.items()} for k, vs in views.CAMERAS.items()}['interior' if MODE == 'night' else MODE]
    NIGHT_EV = float(os.environ.get('NIGHT_EV', getattr(views, 'NIGHT_EV', -1.0)))   # env, else the project's views, else -1
    os.makedirs(OUT, exist_ok=True)
    # ---- render only what changed (2026-09-25). Each image gets a fingerprint of everything that can show
    # up in it: the objects in (or just around) that camera's view — geometry, placement, materials — plus
    # everything that lights the whole flat (lamps, emissive surfaces, sun, world) and the render settings.
    # render-hashes.json (next to this script, merged by publish.sh --collect) remembers the fingerprint of
    # each image in renders-final; an image whose fingerprint is unchanged is not rendered again.
    # Limits, on purpose conservative: an object is "seen" if its bounding box falls in a view widened by 20 %
    # or lies within 2 m of the camera (mirrors and bounce light come from close by). Force a full pass with
    # a file named FORCE next to scene.py, or RENDER_FORCE=1.
    import json, hashlib
    from bpy_extras.object_utils import world_to_camera_view
    _HERE = PROJECT                                # FORCE / HASHDEBUG control files live in the project folder
    _MANIFEST = os.path.join(PROJECT, 'out', 'render-hashes.json')
    _FORCE = os.path.exists(os.path.join(_HERE, 'FORCE')) or os.environ.get('RENDER_FORCE') == '1'
    try: _OLD = json.load(open(_MANIFEST))
    except Exception: _OLD = {}
    _NEW = {}
    def _h(*parts): return hashlib.sha1('|'.join(map(str, parts)).encode()).hexdigest()[:16]
    def _val(v):                 # plain values only: str() of a Blender object carries a memory address
        if isinstance(v, (bool, int, float)): return round(float(v), 4)
        if isinstance(v, str): return v
        try: return tuple(round(float(x), 4) for x in v)
        except Exception: return type(v).__name__
    _MS, _EMIT = {}, set()
    def _mat(m):
        if m is None: return 'none'
        if m.name not in _MS:
            parts = [m.name]
            if m.use_nodes and m.node_tree:
                for n in sorted(m.node_tree.nodes, key=lambda n: n.name):
                    parts.append(n.bl_idname)
                    for i in n.inputs:
                        if hasattr(i, 'default_value'):
                            parts.append((i.name, _val(i.default_value)))
                            if i.name == 'Emission Strength' and float(i.default_value) > 0: _EMIT.add(m.name)
                    if getattr(n, 'image', None): parts.append(n.image.filepath)
                parts += sorted(f'{l.from_node.name}.{l.from_socket.name}>{l.to_node.name}.{l.to_socket.name}' for l in m.node_tree.links)
            _MS[m.name] = _h(*parts)
        return _MS[m.name]
    bpy.context.view_layer.update()   # objects/cameras made this run have no matrix_world until the depsgraph runs:
                                      # without this, fingerprints taken before the first render saw them at the origin
    _OBJ = []                                      # (signature, world bbox corners, centre)
    _GLOBAL = [MODE, PALETTE, SAMPLES, PCT, CUT, NIGHT_EV, S.world.name if S.world else '']
    _GLOBAL += [S.view_settings.view_transform, S.view_settings.look, cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces,
                cy.transmission_bounces, cy.use_denoising, cy.denoiser, getattr(cy, 'adaptive_threshold', 0), S.render.resolution_percentage]
    if S.world and S.world.node_tree:
        _GLOBAL += [(n.bl_idname, [_val(i.default_value) for i in n.inputs if hasattr(i, 'default_value')]) for n in S.world.node_tree.nodes]
    for o in S.objects:
        mw = o.matrix_world
        if o.type == 'LIGHT':
            L = o.data; _GLOBAL.append((L.type, L.energy, _val(L.color), _val(mw.translation), _val(o.rotation_euler),
                                        getattr(L, 'size', 0), getattr(L, 'size_y', 0), getattr(L, 'angle', 0))); continue
        if o.type != 'MESH': continue
        mats = tuple(_mat(s.material) for s in o.material_slots)
        vs = o.data.vertices; acc = 0
        for v in vs:
            c = mw @ v.co; acc = (acc * 1000003 + round(c.x * 1000) * 7 + round(c.y * 1000) * 13 + round(c.z * 1000)) & 0xFFFFFFFFFFFF
        sig = _h(len(vs), acc, mats, o.visible_camera, o.hide_render)
        if any(s.material and s.material.name in _EMIT for s in o.material_slots): _GLOBAL.append(sig)   # it lights others
        corners = [mw @ Vector(c) for c in o.bound_box]
        _OBJ.append((sig, corners, sum(corners, Vector()) / 8, o))
    _GSIG = _h(*_GLOBAL)
    _DG = bpy.context.evaluated_depsgraph_get()
    _SEETHRU = {'glass', 'glass_matte', 'curtain_light'}        # rays carry on through these
    def _unblocked(origin, target, obj):
        """True if a ray from origin reaches target (or first hits obj) — through glass, not through walls."""
        d = target - origin; dist = d.length
        if dist < 1e-4: return True
        d.normalize(); o = origin.copy()
        for _ in range(6):
            hit, loc, _n, _i, hobj, _m = S.ray_cast(_DG, o, d, distance=dist - (o - origin).length)
            if not hit: return True
            if hobj.original == obj: return True
            mats = {sl.material.name for sl in hobj.original.material_slots if sl.material}
            if not (mats & _SEETHRU): return False
            o = loc + d * 0.002
        return False
    def _sees(cam, corners, centre, obj):
        pts = [world_to_camera_view(S, cam, c) for c in corners]
        front = [p.z > 0 for p in pts]
        near = (centre - cam.location).length < 2.0
        if not any(front): return near
        if all(front):
            xs = [p.x for p in pts]; ys = [p.y for p in pts]
            if not (max(xs) > -0.2 and min(xs) < 1.2 and max(ys) > -0.2 and min(ys) < 1.2): return False
        if near: return True
        # occlusion (25/26 Sep): without it, a change behind two walls re-rendered most of the flat's views.
        # Seen if a ray from the camera reaches its centre or any corner (pulled 3 cm inward) unobstructed.
        cl = cam.matrix_world.translation
        return any(_unblocked(cl, c + (centre - c) * min(1.0, 0.03 / max((centre - c).length, 1e-6)), obj) for c in [centre] + corners)
    for name, (cam, expo, res) in CAMERAS.items():
        if CAMS != 'all' and name not in CAMS.split(','): continue
        S.camera = cam; S.view_settings.exposure = expo + (NIGHT_EV if MODE == 'night' else 0.0)
        if res: S.render.resolution_x, S.render.resolution_y = res
        else: S.render.resolution_x, S.render.resolution_y = 1600, 1000
        img = name + SUFFIX + ('_night' if MODE == 'night' else '') + '.jpg'
        S.render.filepath = os.path.join(OUT, img)
        cd = cam.data
        _vis = sorted(sig for sig, cs, c, ob in _OBJ if _sees(cam, cs, c, ob))
        fp = _h(_GSIG, _val(cam.matrix_world), cd.type, cd.lens, cd.ortho_scale, S.view_settings.exposure,
                S.render.resolution_x, S.render.resolution_y, _vis)
        _NEW[img] = fp
        if os.path.exists(os.path.join(_HERE, 'HASHDEBUG')): json.dump([_GSIG] + _vis, open(os.path.join(OUT, img + '.sigs.json'), 'w'))
        if os.environ.get('RENDER_HASHONLY') == '1':   # fingerprints only, no render: proves a refactor changed nothing
            print('HASH', img, fp, flush=True); continue
        if not _FORCE and _OLD.get(img) == fp:
            print('RENDERED', name, 'unchanged — skipped', flush=True)   # still '^RENDERED': the watcher counts these
            continue
        _t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print('RENDERED', name, f'{time.time() - _t0:.1f}s', flush=True)   # the watcher counts '^RENDERED'
        # recorded per image as it lands, so a job that dies half way still leaves a usable manifest
        _done = os.path.join(OUT, 'render-hashes.json')
        try: _m = json.load(open(_done))
        except Exception: _m = {}
        _m[img] = fp; json.dump(_m, open(_done, 'w'), indent=0, sort_keys=True)
