"""Render one named camera from a saved campus scene, leaving the file unchanged."""
import bpy, sys, argparse
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--camera',required=True); p.add_argument('--output',required=True)
p.add_argument('--size',type=int,nargs=2,default=[1800,1400]); p.add_argument('--samples',type=int,default=128)
p.add_argument('--cpu',action='store_true')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
s=bpy.context.scene
s.camera=bpy.data.objects[args.camera]
s.render.resolution_x,s.render.resolution_y=args.size; s.render.resolution_percentage=100
s.cycles.samples=args.samples; s.cycles.use_denoising=True
if args.cpu:
    s.cycles.device='CPU'
else:
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='METAL'; prefs.get_devices()
        for d in prefs.devices: d.use=d.type=='METAL'
        s.cycles.device='GPU'
    except Exception: s.cycles.device='CPU'
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
Path(args.output).parent.mkdir(parents=True,exist_ok=True);s.render.filepath=args.output
print('RENDER_START',s.camera.name,args.size,args.samples,flush=True)
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',args.output,flush=True)
