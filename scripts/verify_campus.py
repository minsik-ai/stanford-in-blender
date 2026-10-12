"""Read-only structural checks for saved architectural scenes."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
s=bpy.context.scene
meshes=[o for o in s.objects if o.type=='MESH']
unique={o.data.name:o.data for o in meshes}
missing=[]
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists():
        missing.append(im.filepath)
assert not missing, missing
assert s.camera and s.camera.type=='CAMERA'
assert s.world and s.world.use_nodes
assert s.render.engine=='CYCLES'
assert any(o.type=='LIGHT' and o.data.energy>0 for o in s.objects)
assert all(math.isfinite(v) for me in unique.values() for vert in me.vertices for v in vert.co)
viewports=[a.spaces.active.shading for screen in bpy.data.screens for a in screen.areas if a.type=='VIEW_3D']
assert viewports and all(v.type=='MATERIAL' and v.use_scene_world and v.use_scene_lights and v.use_scene_world_render and v.use_scene_lights_render for v in viewports)
report={'file':bpy.data.filepath,'scene_objects':len(s.objects),'mesh_objects':len(meshes),'unique_mesh_vertices':sum(len(me.vertices) for me in unique.values()),'instanced_mesh_vertices':sum(len(o.data.vertices) for o in meshes),'cameras':[o.name for o in s.objects if o.type=='CAMERA'],'materials':len(bpy.data.materials),'missing_external_images':missing,'saved_viewport_mode':'MATERIAL','viewport_scene_lights_and_world_enabled':True,'finite_vertex_coordinates':True,'reference_note':s.get('reconstruction_note',s.get('accuracy_note','Photo-informed reconstruction with estimated dimensions.'))}
output=Path(bpy.data.filepath).with_suffix('.verification.json'); output.write_text(json.dumps(report,indent=2))
print('VERIFIED',json.dumps(report))
