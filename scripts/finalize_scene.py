import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
ns={'__name__':'backdrop_module','__file__':str(ROOT/'scripts/backdrop.py')}
exec(compile((ROOT/'scripts/backdrop.py').read_text(),str(ROOT/'scripts/backdrop.py'),'exec'),ns)
ns['build_backdrop']()
s=bpy.context.scene
s.camera=bpy.data.objects['Camera · architectural portrait']
s.render.resolution_x=1920; s.render.resolution_y=2400; s.render.resolution_percentage=100
s.cycles.samples=160; s.cycles.use_denoising=True
s.render.filepath=str(ROOT/'renders/hoover_hero.png')
# Make the entire tower easy to select and transform, independent of landscape.
root=bpy.data.objects.get('Hoover Tower · complete architecture')
if not root:
    root=bpy.data.objects.new('Hoover Tower · complete architecture',None)
    s.collection.objects.link(root); root.empty_display_type='PLAIN_AXES'; root.empty_display_size=3
    for col in bpy.data.collections:
        if col.name[:2] in ['01','02','03','04','05','06']:
            for ob in col.objects: ob.parent=root
# Embed reference and project notes in the editable Blender file.
notes=bpy.data.texts.get('ABOUT · Hoover Tower') or bpy.data.texts.new('ABOUT · Hoover Tower')
notes.clear(); notes.write('''HOOVER TOWER / STANFORD UNIVERSITY
Photo-informed architectural exterior reconstruction, October 2026.

Overall height: 86.87 m (285 ft). Other dimensions are visual estimates;
this is an artistic reconstruction, not a measured architectural survey.
Landscaping is an illustrative campus setting. Lion reliefs and some
carved ornament are simplified interpretations.

DETAILS
Three recessed bays per facade; paired arched upper windows; sparse slit
windows; octagonal belfry with 8 open arches; grilles and bronze bells;
four stone corner pinnacles; 4,568 individually modeled overlapping
terracotta tiles; fluted lantern, carved cap, orb and lightning rod;
concentric entry archivolts, glazed doors, stairs and low exhibition wings.

EDITING
Collections 01-06 contain the architecture; the top-level empty
'Hoover Tower · complete architecture' transforms it as one assembly.
Collection 07 contains all landscaping. Collection 08 contains the three
named cameras and lighting. Materials are procedural and self-contained.

VIEWS
Camera · architectural portrait / 1920 x 2400
Camera · crown craftsmanship / 1800 x 2000
Camera · entrance study / 1800 x 1400
Cycles, Metal GPU, denoising. AgX color management.

REFERENCES
https://architectplanning.stanford.edu/hoover-tower
https://www.hoover.org/events/hoover-tower-80th-anniversary
https://news.stanford.edu/stories/2021/02/hoover-tower-undergoes-repair-fix-last-years-lightning-strike-damage
https://commons.wikimedia.org/wiki/File:Hoover_Tower_east_face.JPG
East-face reference photograph: BrokenSphere, CC BY-SA 3.0.
Reference photos are not used as textures in this scene.

REPRODUCE
The scripts directory contains build_hoover.py, landscape.py,
refine_scene.py, refine_details.py, backdrop.py and finalize_scene.py.
Run rebuild_hoover.py within Blender to repeat the complete build.
Original starting scene is preserved as before_hoover.blend.
''')
for ob in bpy.context.selected_objects: ob.select_set(False)
bpy.context.view_layer.objects.active=None
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.shading.type='MATERIAL'; a.spaces.active.shading.use_scene_world=True; a.spaces.active.shading.use_scene_lights=True; a.spaces.active.shading.use_scene_world_render=True; a.spaces.active.shading.use_scene_lights_render=True; a.spaces.active.overlay.show_overlays=False
            a.spaces.active.region_3d.view_perspective='CAMERA'; a.spaces.active.region_3d.view_camera_zoom=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Hoover_Tower_Stanford.blend'))
arch=[ob for col in bpy.data.collections if col.name[:2] in ['01','02','03','04','05','06'] for ob in col.objects]
zs=[(o.matrix_world@Vector(p)).z for o in arch for p in o.bound_box]
report={'height_m':round(max(zs)-min(zs),5),'objects':len(bpy.data.objects),'mesh_vertices':sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'),'roof_tiles':bpy.data.objects['Dome · overlapping scalloped clay tiles']['individual_tiles'],'materials':len(bpy.data.materials),'cameras':[o.name for o in bpy.data.objects if o.type=='CAMERA'],'missing_external_images':[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists()]}
(ROOT/'scene_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
