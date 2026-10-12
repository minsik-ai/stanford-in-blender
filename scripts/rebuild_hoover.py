"""Rebuild the photo-informed Hoover Tower scene inside Blender."""
from pathlib import Path
root=Path(__file__).resolve().parent
for stage in ['build_hoover.py','refine_scene.py','refine_details.py','fix_entrance.py','finalize_scene.py']:
    path=root/stage
    exec(compile(path.read_text(),str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
