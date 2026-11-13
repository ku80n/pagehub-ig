"""Blender (bpy) scene of the POV Reel: a phone on a desk in the evening, its
screen plays the frames from parts.py, handheld camera with a slow push-in and
shallow depth of field. Cycles on CPU, half resolution (the sharp screen and
the captions are composited afterwards by compose.py).

  python3 scene.py WORKDIR [first last [step]]
"""
import json, math, pathlib, random, sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

work = pathlib.Path(sys.argv[1])
N = len(list((work / "screen").glob("*.jpg")))
first, last, step = (int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1) if len(sys.argv) > 3 else (1, N, 1)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end, sc.frame_step = first, last, step
sc.render.fps = 30
random.seed(4)


def mat(name, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m


def add(obj, material):
    obj.data.materials.append(material)
    return obj

# desk
bpy.ops.mesh.primitive_plane_add(size=40)
add(bpy.context.object, mat("desk", **{"Base Color": (0.05, 0.036, 0.028, 1), "Roughness": 0.28}))

# phone: body + screen, propped up a little at the far end
bpy.ops.object.empty_add(location=(0, 0, 0.0)); rig = bpy.context.object
rig.rotation_euler = (math.radians(7), 0, math.radians(-5))
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.04)); body = bpy.context.object
body.scale = (0.75, 1.30, 0.07); bpy.ops.object.transform_apply(scale=True)
bv = body.modifiers.new("b", "BEVEL"); bv.width, bv.segments = 0.03, 6
bpy.ops.object.shade_smooth()
add(body, mat("body", **{"Base Color": (0.02, 0.02, 0.025, 1), "Metallic": 0.9, "Roughness": 0.32}))
body.parent = rig
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.0762)); scr = bpy.context.object
scr.scale = (0.69, 0.69 * 16 / 9, 1); bpy.ops.object.transform_apply(scale=True)
scr.parent = rig
m = mat("screen", **{"Base Color": (0, 0, 0, 1), "Roughness": 0.06})
nt = m.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.load(str(work / "screen" / "0001.jpg")); img.source = "SEQUENCE"
tex.image = img
tex.image_user.frame_duration, tex.image_user.frame_start, tex.image_user.frame_offset = N, 1, 0
tex.image_user.use_auto_refresh = True
bsdf = nt.nodes["Principled BSDF"]
nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
bsdf.inputs["Emission Strength"].default_value = 1.5
add(scr, m)

# things on the desk, out of focus
bpy.ops.mesh.primitive_cylinder_add(radius=0.42, depth=0.9, location=(-1.25, 2.5, 0.45))
add(bpy.context.object, mat("mug", **{"Base Color": (0.75, 0.72, 0.68, 1), "Roughness": 0.35})); bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.45, 2.3, 0.06)); nb = bpy.context.object
nb.scale = (1.5, 2.0, 0.12); nb.rotation_euler[2] = 0.3
add(nb, mat("notebook", **{"Base Color": (0.03, 0.09, 0.12, 1), "Roughness": 0.5}))
for i in range(16):                                            # lights far behind: bokeh
    col = random.choice([(1, 0.62, 0.3), (0.11, 0.6, 0.76), (1, 0.85, 0.7)])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.05, 0.11), segments=12, ring_count=6,
                                         location=(random.uniform(-3.2, 3.2), random.uniform(4.2, 7.5), random.uniform(0.12, 0.9)))
    e = bpy.data.materials.new(f"e{i}"); e.use_nodes = True
    b = e.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (*col, 1); b.inputs["Emission Strength"].default_value = 60
    add(bpy.context.object, e)

for loc, size, energy, col in (((-2.6, -1.2, 3.0), 2.5, 260, (1, 0.74, 0.5)), ((2.8, 2.6, 2.2), 2.0, 220, (0.2, 0.7, 0.95))):
    bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.object
    L.data.size, L.data.energy, L.data.color = size, energy, col
    L.rotation_euler = Vector((0, 0, 0.3)) - Vector(loc); L.rotation_euler = (Vector(loc) * -1).to_track_quat("-Z", "Y").to_euler()
w = bpy.data.worlds.new("w"); w.use_nodes = True; sc.world = w
w.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.014, 0.02, 1)

# camera: handheld drift + push-in, always looking at the phone
bpy.ops.object.empty_add(location=(0, 0.02, 0.08)); target = bpy.context.object
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.lens = 38
cam.data.dof.use_dof, cam.data.dof.focus_object, cam.data.dof.aperture_fstop = True, scr, 1.6
tr = cam.constraints.new("TRACK_TO"); tr.target, tr.track_axis, tr.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
for f in range(1, N + 1):
    t = (f - 1) / 30; w_ = 2 * math.pi * (f - 1) / N
    push = min(1, t / 10.8); push = 1 - (1 - push) ** 2
    d = 2.5 - 0.4 * push
    cam.location = (0.10 + 0.14 * math.sin(w_) + 0.03 * math.sin(5 * w_ + 1),
                    -0.62 * d + 0.05 * math.sin(3 * w_),
                    0.78 * d + 0.04 * math.sin(2 * w_ + 0.5) + 0.015 * math.sin(7 * w_))
    target.location = (0.012 * math.sin(4 * w_), 0.05 + 0.012 * math.sin(3 * w_ + 2), 0.08)
    cam.keyframe_insert("location", frame=f); target.keyframe_insert("location", frame=f)

r = sc.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y, r.resolution_percentage = 540, 960, 100
c = sc.cycles
c.samples, c.use_adaptive_sampling, c.use_denoising = 10, False, True
c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 3, 1, 2, 0
c.caustics_reflective = c.caustics_refractive = False
r.use_persistent_data = True
sc.view_settings.view_transform = "Standard"
r.image_settings.file_format = "PNG"
r.filepath = str(work / "cg" / "")

corners = {}
Z = 0.0762                                                # transform_apply baked the offset into the mesh
loc = [Vector((-0.345, 0.345 * 16 / 9, Z)), Vector((0.345, 0.345 * 16 / 9, Z)), Vector((0.345, -0.345 * 16 / 9, Z)), Vector((-0.345, -0.345 * 16 / 9, Z))]
import os
name = os.environ.get("CORNERS", "corners.json")
for f in range(1, N + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ce, se = cam.evaluated_get(dg), scr.evaluated_get(dg)
    mw = rig.matrix_basis @ scr.matrix_basis                  # static; the evaluated matrix_world misses the offset
    pts = [world_to_camera_view(sc, ce, mw @ p) for p in loc]
    corners[f] = [[p.x, 1 - p.y] for p in pts]
(work / name).write_text(json.dumps(corners))
if "CORNERS" not in os.environ:
    bpy.ops.render.render(animation=True)
