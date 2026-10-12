"""Shared daylight, cameras and original landscape assets for Stanford models."""
import bpy, math
from mathutils import Vector, Matrix
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
_TEMPLATES={}

def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c

def setup_lighting():
    s=bpy.context.scene; s.unit_settings.system='METRIC'; s.unit_settings.scale_length=1
    s.render.engine='CYCLES'; s.cycles.samples=128; s.cycles.use_denoising=True
    s.cycles.preview_samples=24; s.cycles.use_preview_denoising=True
    s.cycles.max_bounces=8; s.cycles.diffuse_bounces=4; s.cycles.glossy_bounces=4
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='METAL'; prefs.get_devices()
        for d in prefs.devices: d.use=d.type=='METAL'
        s.cycles.device='GPU'
    except Exception: s.cycles.device='CPU'
    world=bpy.data.worlds.new('California daylight · Stanford series'); world.use_nodes=True
    n=world.node_tree.nodes; n.clear(); l=world.node_tree.links
    out=n.new('ShaderNodeOutputWorld')
    ambient=n.new('ShaderNodeBackground'); ambient.name='Soft blue daylight'
    ambient.inputs['Color'].default_value=(.45,.58,.74,1); ambient.inputs['Strength'].default_value=.65
    background=n.new('ShaderNodeBackground'); background.name='California blue sky'; background.inputs['Strength'].default_value=.7
    tex=n.new('ShaderNodeTexCoord'); sep=n.new('ShaderNodeSeparateXYZ'); l.new(tex.outputs['Normal'],sep.inputs[0])
    mr=n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value=-.65; mr.inputs['From Max'].default_value=.04; mr.clamp=True
    l.new(sep.outputs['Z'],mr.inputs[0]); ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(.025,.115,.32,1); ramp.color_ramp.elements[1].color=(.16,.38,.65,1)
    l.new(mr.outputs[0],ramp.inputs[0]); l.new(ramp.outputs[0],background.inputs[0])
    lp=n.new('ShaderNodeLightPath'); mix=n.new('ShaderNodeMixShader')
    l.new(lp.outputs['Is Camera Ray'],mix.inputs[0]); l.new(ambient.outputs[0],mix.inputs[1]); l.new(background.outputs[0],mix.inputs[2]); l.new(mix.outputs[0],out.inputs['Surface'])
    s.world=world
    sun_data=bpy.data.lights.new('Afternoon sun','SUN'); sun_data.energy=2.8; sun_data.color=(1,.92,.78); sun_data.angle=.04
    sun=bpy.data.objects.new('Afternoon sun',sun_data); collection('90 · Cameras & lighting').objects.link(sun)
    sun.rotation_euler=(math.radians(42),math.radians(-22),math.radians(-25))
    s.view_settings.view_transform='AgX'; s.view_settings.look='AgX - Medium High Contrast'; s.view_settings.exposure=.8
    s.render.image_settings.file_format='PNG'; s.render.image_settings.color_mode='RGB'; s.render.resolution_percentage=100
    s.render.film_transparent=False
    return s

def camera(name, location, target, lens=50, collection=None):
    data=bpy.data.cameras.new(name); ob=bpy.data.objects.new(name,data)
    (collection or globals()['collection']('90 · Cameras & lighting')).objects.link(ob)
    ob.location=location; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens; data.clip_end=4000; data.clip_start=.1
    return ob

def configure_viewport(scene=None, rendered=True):
    scene=scene or bpy.context.scene
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                space=a.spaces.active; shade=space.shading
                shade.use_scene_world=True; shade.use_scene_lights=True
                shade.use_scene_world_render=True; shade.use_scene_lights_render=True
                shade.type='RENDERED' if rendered else 'MATERIAL'
                space.overlay.show_overlays=False
                space.region_3d.view_perspective='CAMERA'; space.region_3d.view_camera_zoom=0

def import_plant(kind, location, scale=1.0, collection=None, angle=0):
    """Instance editable original foliage from the Hoover model; no remote assets."""
    if kind not in ('palm','broadleaf'): raise ValueError('kind must be palm or broadleaf')
    if kind not in _TEMPLATES:
        source=ROOT/'Hoover_Tower_Stanford.blend'
        names = ['ENV_Palm_00_Curved_Trunk','ENV_Palm_00_Growth_Scars','ENV_Palm_00_Pinnate_Foliage','ENV_Palm_00_Frond_Rachis'] if kind=='palm' else ['ENV_Backdrop_00_Trunk_and_Branches','ENV_Backdrop_00_Individual_Leaves']
        with bpy.data.libraries.load(str(source),link=False) as (src,dst):
            dst.objects=[name for name in names if name in src.objects]
        _TEMPLATES[kind]=[o for o in dst.objects if o is not None]
        if not _TEMPLATES[kind]: raise RuntimeError('Missing original plant assets: '+kind)
    col=collection or globals()['collection']('80 · Landscape')
    origin=Vector((-23,-6,0) if kind=='palm' else (-35,30,0))
    rot=Matrix.Rotation(angle,4,'Z'); transform=Matrix.Translation(Vector(location))@rot@Matrix.Scale(scale,4)@Matrix.Translation(-origin)
    result=[]
    for template in _TEMPLATES[kind]:
        ob=template.copy(); ob.data=template.data; ob.name=kind.capitalize()+' · '+template.name
        ob.parent=None; ob.matrix_world=transform@template.matrix_world; col.objects.link(ob); result.append(ob)
    return result

def _material(name,color,rough=.7):
    m=bpy.data.materials.get(name)
    if m is None:
        m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
        bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=rough
    return m

def bench(name,location,angle=0,collection=None):
    col=collection or globals()['collection']('80 · Landscape')
    wood=_material('Campus · warm timber',(.295,.16,.065)); metal=_material('Campus · dark metal',(.065,.08,.073),.5)
    vs=[]; fs=[]; ids=[]
    def part(loc,size,mi):
        x,y,z=loc; a,b,c=[v*.5 for v in size]; base=len(vs)
        for dx,dy,dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
            X=x+dx*a; Y=y+dy*b; Z=z+dz*c
            vs.append((location[0]+X*math.cos(angle)-Y*math.sin(angle),location[1]+X*math.sin(angle)+Y*math.cos(angle),location[2]+Z))
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]: fs.append(tuple(base+i for i in f)); ids.append(mi)
    for x in [-.7,.7]:
        part((x,0,.26),(.06,.5,.46),1); part((x,.28,.73),(.045,.045,.56),1)
    for k in range(5): part((0,-.25+k*.125,.52),(2.1,.105,.065),0)
    for k in range(3): part((0,.29,.73+k*.115),(2.1,.055,.085),0)
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.materials.append(wood); me.materials.append(metal); me.update()
    for p,i in zip(me.polygons,ids): p.material_index=i
    ob=bpy.data.objects.new(name,me); col.objects.link(ob)
    be=ob.modifiers.new('Soft bench edges','BEVEL'); be.width=.01; be.segments=2
    return ob
