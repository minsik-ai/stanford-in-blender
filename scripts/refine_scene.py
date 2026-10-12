import bpy, math
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=bpy.context.scene
# Calibrated studio-like daylight: soft environment illumination, blue photographic sky.
w=s.world; n=w.node_tree.nodes; n.clear(); l=w.node_tree.links
out=n.new('ShaderNodeOutputWorld')
ambient=n.new('ShaderNodeBackground'); ambient.name='Soft blue daylight'; ambient.inputs['Color'].default_value=(.45,.58,.74,1); ambient.inputs['Strength'].default_value=.42
camera_bg=n.new('ShaderNodeBackground'); camera_bg.name='California blue sky'; camera_bg.inputs['Strength'].default_value=.7
tex=n.new('ShaderNodeTexCoord'); sep=n.new('ShaderNodeSeparateXYZ'); l.new(tex.outputs['Normal'],sep.inputs[0])
mapping=n.new('ShaderNodeMapRange'); mapping.inputs['From Min'].default_value=-.05; mapping.inputs['From Max'].default_value=.7; mapping.clamp=True; l.new(sep.outputs['Z'],mapping.inputs[0])
ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color=(.28,.48,.66,1); ramp.color_ramp.elements[1].color=(.055,.19,.39,1); l.new(mapping.outputs[0],ramp.inputs[0]); l.new(ramp.outputs[0],camera_bg.inputs[0])
lp=n.new('ShaderNodeLightPath'); mix=n.new('ShaderNodeMixShader'); l.new(lp.outputs['Is Camera Ray'],mix.inputs[0]); l.new(ambient.outputs[0],mix.inputs[1]); l.new(camera_bg.outputs[0],mix.inputs[2]); l.new(mix.outputs[0],out.inputs['Surface'])
sun=bpy.data.objects['Afternoon sun']; sun.data.energy=2.5; sun.data.color=(1,.92,.78); sun.data.angle=.04
sun.rotation_euler=(math.radians(42),math.radians(-22),math.radians(-25))
s.view_settings.exposure=-.15; s.view_settings.look='AgX - Medium High Contrast'
cam=bpy.data.objects['Camera · architectural portrait']; cam.location=(111,-176,31); cam.rotation_euler=(Vector((0,0,42.5))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=69
cam=bpy.data.objects['Camera · crown craftsmanship']; cam.location=(35,-53,81); cam.rotation_euler=(Vector((0,0,75.9))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=92
# Dark interior walls preserve the shadow behind the open observation arches.
col=bpy.data.collections['03 · Observation crown']
for name,loc,dim in [('Carillon internal core',(0,0,70.4),(4.0,4.0,8.5))]:
    if name not in bpy.data.objects:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc); ob=bpy.context.object; ob.name=name; ob.dimensions=dim
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        for c in list(ob.users_collection): c.objects.unlink(ob)
        col.objects.link(ob); ob.data.materials.append(bpy.data.materials['Interior · shadow'])
# A ground large enough to meet the horizon rather than end behind the tower.
ground=bpy.data.objects['ENV_Continuous_Ground']; ground.scale.x=20; ground.scale.y=20
s.camera=bpy.data.objects['Camera · architectural portrait']; s.render.resolution_percentage=100; s.render.resolution_x=1600; s.render.resolution_y=2000
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.shading.type='MATERIAL'; a.spaces.active.overlay.show_overlays=False; a.spaces.active.region_3d.view_perspective='CAMERA'
s.render.filepath=str(ROOT/'renders/hoover_hero.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Hoover_Tower_Stanford.blend'))
print('Lighting and framing refinement saved')
