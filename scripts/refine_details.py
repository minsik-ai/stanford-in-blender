import bpy, math, random
from pathlib import Path
from mathutils import Vector
from math import sin,cos,pi
ROOT=Path(__file__).resolve().parents[1]
s=bpy.context.scene
s.view_settings.exposure=.8
s.world.node_tree.nodes['Soft blue daylight'].inputs['Strength'].default_value=.65
ramp=next(n for n in s.world.node_tree.nodes if n.type=='VALTORGB')
ramp.color_ramp.elements[0].color=(.025,.115,.32,1)
ramp.color_ramp.elements[1].color=(.16,.38,.65,1)
mr=next(n for n in s.world.node_tree.nodes if n.type=='MAP_RANGE')
mr.inputs['From Min'].default_value=-.65; mr.inputs['From Max'].default_value=.04
bpy.data.objects['Afternoon sun'].data.energy=2.8
cam=bpy.data.objects['Camera · architectural portrait']; cam.location=(111,-176,17); cam.rotation_euler=(Vector((0,0,42.5))-cam.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects['Camera · crown craftsmanship']; cam.location=(35,-53,55); cam.rotation_euler=(Vector((0,0,75.6))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=86
# Repair the tiled dome: each tile tips up at its lower rounded lip.
# Constant offsets made overlapping courses coplanar; this gives true overlaps.
DR=7.37; DZ=76.30; DH=5.92; rows=41
verts=[]; faces=[]; mids=[]; random.seed(41)
for row in range(rows):
    theta=.015+row*(1.355/rows); radius=DR*cos(theta); count=max(20,round(2*pi*radius/.30)); step=2*pi/count
    for j in range(count):
        phi=(j+(row%2)*.5)*step
        outline=[(-.5,.65),(.5,.65),(.5,-.08)]+[(.5*cos(i*pi/8),-.08-.45*sin(i*pi/8)) for i in range(1,9)]
        N=len(outline); st=len(verts)
        for layer in [0,.027]:
            for u,v in outline:
                t=theta+v*.054; az=phi+u*step*.966
                off=.015+(.65-v)/1.18*.073+layer
                verts.append(((DR+off)*cos(t)*cos(az),(DR+off)*cos(t)*sin(az),DZ+(DH+off)*sin(t)))
        fs=[tuple(st+i for i in reversed(range(N))),tuple(st+N+i for i in range(N))]+[(st+i,st+(i+1)%N,st+(i+1)%N+N,st+i+N) for i in range(N)]
        faces.extend(fs); mids.extend([random.choices(range(9),weights=[1,2,3,6,8,7,5,3,1])[0]]*len(fs))
ob=bpy.data.objects['Dome · overlapping scalloped clay tiles']; old=ob.data
me=bpy.data.meshes.new('Scalloped clay roof · lifted overlapping lips'); me.from_pydata(verts,[],faces); me.update()
for m in old.materials: me.materials.append(m)
for p,mi in zip(me.polygons,mids): p.material_index=mi
ob.data=me; bpy.data.meshes.remove(old)
# Fill quarter-metre recesses and union overlapping corner masonry.
if not s.get('shaft_union_done'):
    core=bpy.data.objects['Main structural shaft']
    for v in core.data.vertices:
        v.co.x *= 8.40/8.16; v.co.y *= 8.40/8.16
    # Reposition all fixtures on the shallower recessed surfaces.
    prefixes=('Paired arched window','Paired window central stone column','Window stone sill','Sparse shaft slit')
    for ob in bpy.data.collections['02 · Tower shaft'].objects:
        if ob.name.startswith(prefixes):
            center=sum((Vector(p) for p in ob.bound_box),Vector())/8
            axis=0 if abs(center.x)>abs(center.y) else 1
            ob.location[axis] += .24*(1 if center[axis]>0 else -1)
    tmp=bpy.data.collections.new('Temporary masonry union'); s.collection.children.link(tmp)
    parts=[o for o in bpy.data.objects if o.name.startswith('Continuous facade pier')]
    for p in parts:
        for mod in list(p.modifiers): p.modifiers.remove(mod)
        tmp.objects.link(p)
    for mod in list(core.modifiers): core.modifiers.remove(mod)
    bpy.context.view_layer.objects.active=core
    mod=core.modifiers.new('Continuous shaft masonry','BOOLEAN'); mod.operation='UNION'; mod.operand_type='COLLECTION'; mod.collection=tmp; mod.solver='EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in parts: bpy.data.objects.remove(p,do_unlink=True)
    bpy.data.collections.remove(tmp)
    edge=core.modifiers.new('Stone corner easing','BEVEL'); edge.width=.025; edge.segments=3
    s['shaft_union_done']=True
# Narrower mane and longer faces read as lion heads at architectural scale.
for ob in bpy.data.collections['03 · Observation crown'].objects:
    if ob.name.startswith(('Lion head carved face','Lion muzzle','Lion nose','Lion brow','Lion mane curl')):
        # Scale around each relief's own center, leaving placement fixed.
        pts=[v.co for v in ob.data.vertices]; center=sum(pts,Vector())/len(pts)
        for v in ob.data.vertices:
            d=v.co-center; d.z*=1.16 if 'face' in ob.name else 1.04
            v.co=center+d
s.camera=bpy.data.objects['Camera · architectural portrait']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Hoover_Tower_Stanford.blend'))
print('Tile overlap, shaft continuity, and daylight refined.')
