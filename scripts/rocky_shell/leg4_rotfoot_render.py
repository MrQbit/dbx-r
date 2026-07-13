import bpy, math
from mathutils import Vector
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1000; sc.render.resolution_y=1000
def imp(p):
    b=set(bpy.data.objects); bpy.ops.wm.stl_import(filepath=p)
    return list(set(bpy.data.objects)-b)[0]
def mat(name,col,rough=0.9,emis=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(*col,1); b.inputs["Roughness"].default_value=rough
    b.inputs["Emission Color"].default_value=(*col,1); b.inputs["Emission Strength"].default_value=emis
    return m
o=imp(SP+"/_leg4_footregion_rot.stl"); o.data.materials.append(mat("s",(0.62,0.60,0.56)))
# z' ticks along x=342 (just past tip): spheres at z=-10(green),-5(cyan),0(white),5(yellow),10(red)
ticks=[(-10,(0.1,0.8,0.2)),(-5,(0.2,0.8,0.9)),(0,(1,1,1)),(5,(0.95,0.85,0.1)),(10,(0.9,0.15,0.1))]
for z,c in ticks:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.4,location=(342,0,z))
    bpy.context.object.data.materials.append(mat("t%s"%z,c,0.4,emis=1.0))
# y' ticks at z=22: y=-10 green, 0 white, 10 red (for the +z' view)
for y,c in [(-10,(0.1,0.8,0.2)),(0,(1,1,1)),(10,(0.9,0.15,0.1))]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.4,location=(342,y,22))
    bpy.context.object.data.materials.append(mat("u%s"%y,c,0.4,emis=1.0))
bpy.ops.object.light_add(type='SUN',location=(300,-300,500)); bpy.context.object.data.energy=3.0
bpy.ops.object.light_add(type='SUN',location=(-200,300,-200)); bpy.context.object.data.energy=1.8
bpy.ops.object.light_add(type='SUN',location=(400,300,200)); bpy.context.object.data.energy=1.6
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
sc.world.node_tree.nodes["Background"].inputs[0].default_value=(0.05,0.06,0.08,1)
cam_d=bpy.data.cameras.new("cam"); cam=bpy.data.objects.new("cam",cam_d)
sc.collection.objects.link(cam); sc.camera=cam
cam_d.type='ORTHO'; cam_d.ortho_scale=95
C=Vector((322,0,-2))
def look(frm):
    cam.location=Vector(frm); cam.rotation_euler=(Vector(frm)-C).to_track_quat('Z','Y').to_euler()
for nm,frm in {"posYr":(322,300,-2),"negYr":(322,-300,-2),"posZr":(322,0,300),"frontr":(620,80,30)}.items():
    look(frm); sc.render.filepath=SP+f"/_rotfoot_{nm}.png"
    bpy.ops.render.render(write_still=True)
print("ROTFOOT_RENDER_DONE")
