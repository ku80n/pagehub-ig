"""Blender (bpy) scene of the POV Reel, real-world scale: a phone on a wooden
desk in the evening (laptop, mug, notebook and pen out of focus, warm lamp, cool
window, small lights far behind), handheld camera with a slow push-in.
The phone's screen lights the scene with the frames from parts.py but shows only
its glass reflections to the camera: compose.py puts the sharp screen under them.
Cycles on CPU, rendered every STEP-th frame at 60% size.

  python3 scene.py WORKDIR [first last [step]]      CORNERS=1: only write corners.json
"""
import json, math, os, pathlib, random, sys
import bpy, bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector, Matrix

work = pathlib.Path(sys.argv[1])
N = len(list((work / "screen").glob("*.jpg")))
first, last, step = (int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1) if len(sys.argv) > 3 else (1, N, 4)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end, sc.frame_step = first, last, step
sc.render.fps = 30
random.seed(7)
mm = 0.001


def material(name, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m


def obj(name, mesh, *mats, loc=(0, 0, 0), rot=(0, 0, 0), smooth=False):
    o = bpy.data.objects.new(name, mesh); sc.collection.objects.link(o)
    o.location, o.rotation_euler = loc, rot
    for m in mats:
        mesh.materials.append(m)
    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True
    return o


def rounded_rect(name, w, h, r, z=0.0, seg=10, uv=False):
    bm = bmesh.new()
    vs = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            vs.append(bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)))
    f = bm.faces.new(vs)
    if uv:
        layer = bm.loops.layers.uv.new("UVMap")
        for l in f.loops:
            l[layer].uv = (l.vert.co.x / w + 0.5, l.vert.co.y / h + 0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me


def prim(op, mats, smooth=True, **kw):
    getattr(bpy.ops.mesh, op)(**kw)
    o = bpy.context.object
    for m in mats:
        o.data.materials.append(m)
    if smooth:
        bpy.ops.object.shade_smooth()
    return o

# ---- desk: wood grain from stretched noise
wood = material("wood", **{"Roughness": 0.30, "Coat Weight": 0.6, "Coat Roughness": 0.12})
nt = wood.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (260, 9, 1); mp.inputs["Rotation"].default_value = (0, 0, 0.12)
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 9; n1.inputs["Detail"].default_value = 9; n1.inputs["Distortion"].default_value = 0.6
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.30, (0.016, 0.009, 0.005, 1)
ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.75, (0.085, 0.043, 0.021, 1)
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12; bump.inputs["Distance"].default_value = 0.0004
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
nt.links.new(n1.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
prim("primitive_plane_add", [wood], smooth=False, size=4)

# ---- phone
PW, PH, PT = 71.5 * mm, 153 * mm, 8.2 * mm
SWm, SHm = 67 * mm, 67 * mm * 780 / 360
glass = material("glass", **{"Base Color": (0.004, 0.004, 0.005, 1), "Roughness": 0.03, "Coat Weight": 1.0, "Coat Roughness": 0.02})
frame = material("frame", **{"Base Color": (0.25, 0.26, 0.28, 1), "Metallic": 1.0, "Roughness": 0.28})
phone_rot = (0, 0, math.radians(-8))
body = obj("phone", rounded_rect("phone", PW, PH, 10.5 * mm), glass, frame, rot=phone_rot)
so = body.modifiers.new("s", "SOLIDIFY"); so.thickness, so.offset, so.material_offset_rim = PT, 1, 1
bv = body.modifiers.new("b", "BEVEL"); bv.width, bv.segments, bv.limit_method, bv.angle_limit = 1.3 * mm, 4, "ANGLE", math.radians(40)
body.location.z = 0.0
for p in body.data.polygons:
    p.use_smooth = True
for y, ln in ((30 * mm, 16 * mm), (8 * mm, 9 * mm)):                # side buttons
    bt = prim("primitive_cube_add", [frame], smooth=False, size=1)
    bt.scale = (1.2 * mm, ln, 2.4 * mm); bt.parent = body; bt.location = (PW / 2 + 0.2 * mm, y, PT / 2)
ZS = PT + 0.03 * mm
scr = obj("screen", rounded_rect("screen", SWm, SHm, 8.5 * mm, uv=True), rot=phone_rot, loc=(0, 0, ZS))
m = bpy.data.materials.new("screen"); m.use_nodes = True; scr.data.materials.append(m)
nt = m.node_tree; b = nt.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0, 0, 0, 1)
smu = nt.nodes.new("ShaderNodeTexNoise"); smu.inputs["Scale"].default_value = 55; smu.inputs["Detail"].default_value = 5
sr = nt.nodes.new("ShaderNodeMapRange"); sr.inputs["From Min"].default_value = 0.45; sr.inputs["From Max"].default_value = 0.75
sr.inputs["To Min"].default_value = 0.02; sr.inputs["To Max"].default_value = 0.07
nt.links.new(smu.outputs["Fac"], sr.inputs["Value"]); nt.links.new(sr.outputs["Result"], b.inputs["Roughness"])   # smudges
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.load(str(work / "screen" / "0001.jpg")); img.source = "SEQUENCE"; tex.image = img
tex.image_user.frame_duration, tex.image_user.frame_start, tex.image_user.frame_offset, tex.image_user.use_auto_refresh = N, 1, 0, True
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 2.2
nt.links.new(tex.outputs["Color"], em.inputs["Color"])
lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(b.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])

# ---- things on the desk
alu = material("alu", **{"Base Color": (0.55, 0.56, 0.58, 1), "Metallic": 1.0, "Roughness": 0.35})
lap = prim("primitive_cube_add", [alu], smooth=False, size=1, location=(-0.15, 0.27, 0.008)); lap.scale = (0.31, 0.215, 0.016); lap.rotation_euler[2] = 0.18
bl = lap.modifiers.new("b", "BEVEL"); bl.width, bl.segments = 0.004, 4
cer = material("ceramic", **{"Base Color": (0.82, 0.80, 0.76, 1), "Roughness": 0.22, "Coat Weight": 0.6})
mug = prim("primitive_cylinder_add", [cer], radius=0.041, depth=0.092, vertices=64, location=(0.105, 0.2, 0.046))
bm_ = mug.modifiers.new("b", "BEVEL"); bm_.width, bm_.segments, bm_.limit_method = 0.004, 4, "ANGLE"
prim("primitive_cylinder_add", [material("coffee", **{"Base Color": (0.035, 0.016, 0.008, 1), "Roughness": 0.08})], radius=0.037, depth=0.002, vertices=48, location=(0.105, 0.2, 0.0925))
h = prim("primitive_torus_add", [cer], major_radius=0.026, minor_radius=0.006, location=(0.150, 0.2, 0.046)); h.rotation_euler = (math.pi / 2, 0, 0)
nb = prim("primitive_cube_add", [material("cover", **{"Base Color": (0.02, 0.07, 0.10, 1), "Roughness": 0.55})], smooth=False, size=1, location=(0.175, 0.0, 0.007))
nb.scale = (0.15, 0.21, 0.014); nb.rotation_euler[2] = -0.22
bn = nb.modifiers.new("b", "BEVEL"); bn.width, bn.segments = 0.002, 3
pen = prim("primitive_cylinder_add", [material("pen", **{"Base Color": (0.6, 0.45, 0.2, 1), "Metallic": 1.0, "Roughness": 0.25})], radius=0.0045, depth=0.14, location=(0.16, -0.01, 0.0185))
pen.rotation_euler = (math.pi / 2, 0, -0.5)
for i in range(22):                                              # small lights far behind
    col = random.choice([(1, 0.6, 0.28), (1, 0.75, 0.45), (0.2, 0.62, 0.8)])
    e = bpy.data.materials.new(f"e{i}"); e.use_nodes = True
    eb = e.node_tree.nodes["Principled BSDF"]; eb.inputs["Emission Color"].default_value = (*col, 1); eb.inputs["Emission Strength"].default_value = 400
    prim("primitive_uv_sphere_add", [e], radius=random.uniform(0.004, 0.008), segments=10, ring_count=5,
         location=(random.uniform(-1.0, 1.0), random.uniform(1.2, 2.4), random.uniform(0.35, 1.5)))

# ---- light: warm lamp from the left, cool window from behind-right, dim room
for loc, size, power, col in (((-0.42, 0.22, 0.38), 0.18, 4.5, (1.0, 0.68, 0.40)),
                              ((0.28, 0.8, 0.7), 0.6, 5, (0.55, 0.75, 1.0)),
                              ((0.2, -0.5, 0.6), 0.8, 0.5, (0.8, 0.85, 1.0))):
    bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.object
    L.data.shape, L.data.size, L.data.energy, L.data.color = "DISK", size, power, col
    L.rotation_euler = (Vector((0, 0, 0.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if size < 0.3:
        L.visible_glossy = False                                   # no lamp hotspot in the middle of the screen
w = bpy.data.worlds.new("w"); w.use_nodes = True; sc.world = w
w.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.016, 0.024, 1)

# ---- camera: handheld, slow push-in, looking at the phone
bpy.ops.object.empty_add(location=(0, 0, 0)); target = bpy.context.object
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.lens, cam.data.clip_start = 50, 0.02
bpy.ops.object.empty_add(location=(0, 0.01, PT)); focus = bpy.context.object
cam.data.dof.use_dof, cam.data.dof.focus_object, cam.data.dof.aperture_fstop = True, focus, 11
tr = cam.constraints.new("TRACK_TO"); tr.target, tr.track_axis, tr.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
for f in range(1, N + 1):
    t = (f - 1) / 30; a = 2 * math.pi * (f - 1) / N
    push = min(1, t / 10.8); push = push * push * (3 - 2 * push)
    d = 0.345 - 0.05 * push
    cam.location = (0.022 + 0.016 * math.sin(a) + 0.003 * math.sin(5 * a + 1),
                    -0.72 * d + 0.006 * math.sin(3 * a),
                    0.69 * d + 0.005 * math.sin(2 * a + 0.5) + 0.002 * math.sin(7 * a))
    target.location = (0.0015 * math.sin(4 * a), 0.02 + 0.0015 * math.sin(3 * a + 2), 0)
    cam.keyframe_insert("location", frame=f); target.keyframe_insert("location", frame=f)

r = sc.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y, r.resolution_percentage = 648, 1152, 100
c = sc.cycles
c.samples, c.use_adaptive_sampling, c.use_denoising = int(os.environ.get("SAMPLES", 12)), False, True
c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 4, 2, 3, 0
c.caustics_reflective = c.caustics_refractive = False
r.use_persistent_data = True
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass
r.image_settings.file_format = "PNG"
r.filepath = str(work / "cg")

corners = {}
loc = [Vector((-SWm / 2, SHm / 2, 0)), Vector((SWm / 2, SHm / 2, 0)), Vector((SWm / 2, -SHm / 2, 0)), Vector((-SWm / 2, -SHm / 2, 0))]
mw = Matrix.Translation((0, 0, ZS)) @ Matrix.Rotation(phone_rot[2], 4, "Z")
for f in range(1, N + 1):
    sc.frame_set(f)
    ce = cam.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pts = [world_to_camera_view(sc, ce, mw @ p) for p in loc]
    corners[f] = [[p.x, 1 - p.y] for p in pts]
(work / "corners.json").write_text(json.dumps(corners))
if "CORNERS" not in os.environ:
    bpy.ops.render.render(animation=True)
