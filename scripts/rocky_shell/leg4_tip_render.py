import bpy, math
from mathutils import Vector
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=900; sc.render.resolution_y=900
def imp(p):
    b=set(bpy.data.objects); bpy.ops.wm.stl_import(filepath=p)
    return list(set(bpy.data.objects)-b)[0]
def mat(name,col,rough=0.9):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(*col,1); b.inputs["Roughness"].default_value=rough
    return m
stone=mat("stone",(0.62,0.60,0.56))
objs={}
for tag,f in [("L2",SP+"/leg2_aligned_2B.stl"),("L4",SP+"/leg4_aligned_4B.stl")]:
    o=imp(f); o.data.materials.append(stone); o.hide_render=True; objs[tag]=o
# axis markers: +y = red cone, +z = blue cone at the tip region
def cone(loc,rot,col):
    bpy.ops.mesh.primitive_cone_add(radius1=2.5,depth=8,location=loc,rotation=rot)
    o=bpy.context.object; o.data.materials.append(mat("c"+str(col),col,0.4)); return o
marks=[cone((330,26,0),(-math.pi/2,0,0),(0.95,0.15,0.1)),   # +y red
       cone((330,0,26),(0,0,0),(0.15,0.3,0.95))]            # +z blue
bpy.ops.object.light_add(type='SUN',location=(300,-300,500)); bpy.context.object.data.energy=3.0
bpy.ops.object.light_add(type='SUN',location=(-200,300,-200)); bpy.context.object.data.energy=1.6
bpy.ops.object.light_add(type='SUN',location=(400,200,100)); bpy.context.object.data.energy=1.2
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
sc.world.node_tree.nodes["Background"].inputs[0].default_value=(0.05,0.06,0.08,1)
cam_d=bpy.data.cameras.new("cam"); cam=bpy.data.objects.new("cam",cam_d)
sc.collection.objects.link(cam); sc.camera=cam
cam_d.type='ORTHO'; cam_d.ortho_scale=110
C=Vector((320,0,0))
def look(frm):
    cam.location=Vector(frm); cam.rotation_euler=(Vector(frm)-C).to_track_quat('Z','Y').to_euler()
views={"posY":(320,300,0),"negY":(320,-300,0),"posZ":(320,0,300),"negZ":(320,0,-300),"front":(620,60,40)}
for tag,o in objs.items():
    for t2,o2 in objs.items(): o2.hide_render=(o2 is not o)
    for nm,frm in views.items():
        look(frm); sc.render.filepath=SP+f"/_tip_{tag}_{nm}.png"
        bpy.ops.render.render(write_still=True)
print("TIP_RENDER_DONE")
