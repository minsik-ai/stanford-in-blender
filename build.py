"""Build the Stanford models without rendering, using the current Blender executable.

Examples (run from any working directory, with a path to this file):
    blender --background --factory-startup --python-exit-code 1 --python build.py -- gates
    blender --background --factory-startup --python-exit-code 1 --python build.py -- all --verify

Selectors: hoover, gates, huang, quad, all.
The .blend files are written to the repository root. Existing outputs are replaced.
Hoover is built first whenever its .blend is missing: the other models reuse its
original procedural foliage. Quad also requires the included, credited image at
references/memorial_church/front_king_of_hearts.jpg. No other images are required.

Each model runs in a fresh background Blender process so library caches and
scene data cannot leak between builds. --verify additionally runs the structural
checks in scripts/verify_campus.py and writes a .verification.json beside each
model. No package installation or third-party Python dependencies are needed.
"""
import argparse
from pathlib import Path
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parent
JOBS = {
    'hoover': ('rebuild_hoover.py',),
    'gates': ('build_gates.py',),
    'huang': ('build_huang.py',),
    'quad': ('build_main_quad.py', 'finish_main_quad.py'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('selector', choices=[*JOBS, 'all'])
    parser.add_argument('--verify', action='store_true',
                        help='Run structural checks on each generated scene.')
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = parser.parse_args(arguments)
    selected = list(JOBS) if args.selector == 'all' else [args.selector]
    if selected[0] != 'hoover' and not (ROOT / 'Hoover_Tower_Stanford.blend').exists():
        selected.insert(0, 'hoover')
    if 'quad' in selected:
        texture = ROOT / 'references/memorial_church/front_king_of_hearts.jpg'
        if not texture.is_file():
            raise FileNotFoundError(f'The credited church texture is missing: {texture}')
    (ROOT / 'renders').mkdir(exist_ok=True)
    for model in selected:
        command = [bpy.app.binary_path, '--background', '--factory-startup',
                   '--python-exit-code', '1']
        for script in JOBS[model]:
            command.extend(['--python', str(ROOT / 'scripts' / script)])
        if args.verify:
            command.extend(['--python', str(ROOT / 'scripts/verify_campus.py')])
        print(f'BUILD_START {model}', flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
        print(f'BUILD_COMPLETE {model}', flush=True)


if __name__ == '__main__':
    main()
