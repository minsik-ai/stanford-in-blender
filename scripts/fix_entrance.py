import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
name='Entry · continuous stone landing and foundation'
if name not in bpy.data.objects:
    # Top elevation matches the upper stair and the recessed door threshold.
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,-10.235,.54))
    ob=bpy.context.object; ob.name=name; ob.dimensions=(12.8,3.83,1.08)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(ob.users_collection): c.objects.unlink(ob)
    bpy.data.collections['01 · Foundation & entry'].objects.link(ob)
    ob.data.materials.append(bpy.data.materials['Portal · honey limestone'])
    b=ob.modifiers.new('Eased stone edge','BEVEL'); b.width=.02; b.segments=3
    ob.parent=bpy.data.objects.get('Hoover Tower · complete architecture')
    ob.select_set(False)
bpy.context.view_layer.objects.active=None
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Hoover_Tower_Stanford.blend'))
report_path=ROOT/'scene_verification.json'
if report_path.exists():
    report=json.loads(report_path.read_text()); report['objects']=len(bpy.data.objects)
    report['mesh_vertices']=sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH')
    report['entrance_landing_top_m']=1.08; report_path.write_text(json.dumps(report,indent=2))
print('Stone landing now joins the stair to the recessed entry threshold.')
