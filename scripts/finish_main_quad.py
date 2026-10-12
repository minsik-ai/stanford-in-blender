import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from campus_common import configure_viewport
s=bpy.context.scene
lawn=bpy.data.materials['Quad · lawn']
for ob in s.objects:
    if ob.type=='MESH':
        for slot in ob.material_slots:
            if slot.material and slot.material.name=='Quad · surrounding ground':slot.material=lawn
configure_viewport(s,rendered=False)
s.camera=bpy.data.objects['Main Quad · Campus overview']
s.render.filepath=str(ROOT/'renders/main_quad_overview.png')
s['reconstruction_note']='Photo-informed whole Main Quad exterior; dimensions, secondary facades, minor sculpture and landscaping approximated. Memorial Church texture credited in embedded sources.'
notes=bpy.data.texts.get('Main Quad · SOURCES AND ACCURACY')
if notes and '(1902)' in notes.as_string():
    corrected=notes.as_string().replace('(1902)','(1905)');notes.clear();notes.write(corrected)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Main Quad presentation saved; outside terrain is green lawn, courtyard remains paved.')
