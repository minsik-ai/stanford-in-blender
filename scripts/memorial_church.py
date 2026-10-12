"""Editable current Stanford Memorial Church, for integration in the Main Quad.

Front is local -Y, facade at y=0, long axis +Y.  Units are metres.
The module has no scene-reset, lighting, camera, save or render side effects.
Photo-derived dimensions are approximate; see the packed source/credit text.
"""
from pathlib import Path
import bpy
import math
import random

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'references' / 'memorial_church'
PI = math.pi


class _Batch:
    def __init__(self, name, materials, collection, root):
        self.name, self.materials = name, materials
        self.collection, self.root = collection, root
        self.v, self.f, self.mi = [], [], []

    def mesh(self, vertices, faces, material=0):
        off = len(self.v)
        self.v.extend(vertices)
        self.f.extend(tuple(off + i for i in face) for face in faces)
        self.mi.extend([material] * len(faces))

    def box(self, center, dimensions, material=0, angle=0):
        x, y, z = center
        sx, sy, sz = (d / 2 for d in dimensions)
        co, si = math.cos(angle), math.sin(angle)
        v = []
        for a, b, c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                        (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
            X, Y = a*sx, b*sy
            v.append((x+X*co-Y*si, y+X*si+Y*co, z+c*sz))
        self.mesh(v, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),
                      (2,3,7,6),(3,0,4,7)], material)

    def beam(self, a, b, width, depth=None, material=0):
        # General 3D square beam, used for roof verge stones and glazing bars.
        dx,dy,dz = [b[i]-a[i] for i in range(3)]
        L = math.sqrt(dx*dx+dy*dy+dz*dz)
        if L < 1e-8:
            return
        u = (dx/L,dy/L,dz/L)
        ref = (0,0,1) if abs(u[2]) < .95 else (0,1,0)
        s = (u[1]*ref[2]-u[2]*ref[1],u[2]*ref[0]-u[0]*ref[2],u[0]*ref[1]-u[1]*ref[0])
        sl = math.sqrt(sum(t*t for t in s)); s = tuple(t/sl for t in s)
        t = (u[1]*s[2]-u[2]*s[1],u[2]*s[0]-u[0]*s[2],u[0]*s[1]-u[1]*s[0])
        d = depth if depth is not None else width
        v=[]
        for p in (a,b):
            for j,k in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                v.append(tuple(p[q]+s[q]*j*width/2+t[q]*k*d/2 for q in range(3)))
        self.mesh(v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material)

    def cylinder(self, center, radius, height, material=0, segments=40, radius_top=None):
        x,y,z=center; rt=radius if radius_top is None else radius_top
        v=[(x+r*math.cos(2*PI*i/segments), y+r*math.sin(2*PI*i/segments), z+dz)
           for r,dz in [(radius,-height/2),(rt,height/2)] for i in range(segments)]
        f=[tuple(reversed(range(segments))),tuple(range(segments,2*segments))]
        f += [(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
        self.mesh(v,f,material)

    def arch(self, center, rx, rz, spring, outer_rx, outer_rz, depth, material=0, angle=0, segments=40):
        """Solid elliptical voussoir ring, local face looks -Y."""
        cx,cy,cz=center; co,si=math.cos(angle),math.sin(angle)
        v=[]
        for yy in [-depth/2,depth/2]:
            for a,b in [(rx,rz),(outer_rx,outer_rz)]:
                for k in range(segments+1):
                    t=PI*k/segments; X=a*math.cos(t); Z=spring+b*math.sin(t)
                    v.append((cx+X*co-yy*si,cy+X*si+yy*co,cz+Z))
        n=segments+1; f=[]
        for k in range(segments):
            f += [(k,k+1,n+k+1,n+k),
                  (2*n+k,3*n+k,3*n+k+1,2*n+k+1),
                  (k,2*n+k,2*n+k+1,k+1),
                  (n+k,n+k+1,3*n+k+1,3*n+k)]
        f += [(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)]
        self.mesh(v,[tuple(reversed(face)) for face in f],material)

    def arch_fill(self, center, rx, rz, bottom, spring, material=0, angle=0, segments=40):
        cx,cy,cz=center; co,si=math.cos(angle),math.sin(angle)
        contour=[(-rx,bottom),(rx,bottom)]
        contour += [(rx*math.cos(PI*k/segments), spring+rz*math.sin(PI*k/segments)) for k in range(segments+1)]
        v=[(cx+x*co,cy+x*si,cz+z) for x,z in contour]
        self.mesh(v,[tuple(range(len(v)))],material)

    def finish(self, bevel=0, uv_photo=False):
        if not self.v:
            return None
        me=bpy.data.meshes.new(self.name)
        me.from_pydata(self.v, [], self.f); me.update()
        for m in self.materials:
            me.materials.append(m)
        for p,mi in zip(me.polygons,self.mi):
            p.material_index=mi
        if uv_photo:
            uv=me.uv_layers.new(name='Original photograph · facade coordinates')
            for p in me.polygons:
                for li in p.loop_indices:
                    v=me.vertices[me.loops[li].vertex_index].co
                    # Source image: King of Hearts 2011, 4368x2912.
                    # Coordinates below use its exactly proportional 1920x1280 preview.
                    uv.data[li].uv=((968+v.x*26.0)/1920, 1-(919-v.z*25.65)/1280)
        ob=bpy.data.objects.new(self.name,me); self.collection.objects.link(ob)
        ob.parent=self.root
        if bevel:
            mod=ob.modifiers.new('Soft worn edges','BEVEL'); mod.width=bevel; mod.segments=2
        return ob


def _material(name,color,rough=.75,noise=False,metallic=0):
    mat=bpy.data.materials.get(name)
    if mat:
        return mat
    mat=bpy.data.materials.new(name); mat.use_nodes=True; mat.diffuse_color=(*color,1)
    nodes=mat.node_tree.nodes; links=mat.node_tree.links
    bs=nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metallic
    if noise:
        tc=nodes.new('ShaderNodeTexCoord'); tex=nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value=4.5; tex.inputs['Detail'].default_value=3
        links.new(tc.outputs['Object'],tex.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(*(c*.76 for c in color),1)
        ramp.color_ramp.elements[1].color=(*(min(c*1.13,1) for c in color),1)
        links.new(tex.outputs['Fac'],ramp.inputs[0]); links.new(ramp.outputs[0],bs.inputs['Base Color'])
        fine=nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=115
        links.new(tc.outputs['Object'],fine.inputs['Vector'])
        bump=nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.22; bump.inputs['Distance'].default_value=.024
        links.new(fine.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs[0],bs.inputs['Normal'])
    return mat


def _photo_material():
    path=REF/'front_king_of_hearts.jpg'
    if not path.is_file():
        raise FileNotFoundError('Church mosaic source missing: '+str(path))
    mat=bpy.data.materials.new('MemChu · original mosaic and carved decorative panels · CC BY-SA 3.0')
    mat.use_nodes=True
    image=bpy.data.images.load(str(path),check_existing=True); image.pack()
    image['Credit']='King of Hearts, Stanford Memorial Church May 2011 002.jpg, CC BY-SA 3.0'
    image['Source']='https://commons.wikimedia.org/wiki/File:Stanford_Memorial_Church_May_2011_002.jpg'
    bs=mat.node_tree.nodes.get('Principled BSDF')
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image; tex.interpolation='Linear'
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value=.68
    # Photo texture is used only for actual 2D mosaic/artwork and carved-face color.
    # Lighting, portals, glazing, stone moldings and building masses are 3D.
    bs.inputs['Emission Color'].default_value=(0,0,0,1)
    return mat


def build_memorial_church(origin=(0,0,0), collection=None):
    """Build the current church and return root plus local/world bounds and counts."""
    if collection is None:
        collection=bpy.data.collections.new('Memorial Church · Romanesque centerpiece')
        bpy.context.scene.collection.children.link(collection)
    root=bpy.data.objects.new('Memorial Church · complete editable building',None)
    collection.objects.link(root); root.location=origin
    root['description']='Current post-1906 Memorial Church, Stanford. North/front faces local -Y.'
    root['dimensions_note']='Footprint approximately 58m long x46m wide; photo-based exterior, not survey data.'
    root['mosaic_credit']='King of Hearts / Wikimedia Commons / CC BY-SA 3.0; packed original photograph, UV selected.'
    stone=_material('MemChu · warm golden sandstone',(.59,.425,.255),noise=True)
    ashlar=[_material('MemChu · ashlar variation %02d'%i,(.54+.016*i,.375+.014*i,.214+.01*i),noise=True) for i in range(7)]
    trim=_material('MemChu · carved cream sandstone',(.66,.493,.302),noise=True)
    edge=_material('MemChu · pale sandstone arris',(.72,.55,.345),noise=True)
    dark=_material('MemChu · deep entrance shadow',(.024,.031,.032),.88)
    wood=_material('MemChu · dark oak doors',(.062,.049,.033),.58)
    glass=_material('MemChu · blue leaded stained glass',(.075,.17,.255),.22,metallic=.28)
    lead=_material('MemChu · dark bronze leadwork',(.078,.081,.068),.42,metallic=.55)
    gold=_material('MemChu · mosaic gold',(.61,.39,.11),.47,metallic=.13)
    roofmats=[_material('MemChu · terracotta tile %02d'%i,(.30+.032*i,.076+.015*i,.031+.009*i),noise=True) for i in range(6)]
    photomat=_photo_material()
    structure=_Batch('MemChu | load-bearing stone and apses',[stone,trim,edge],collection,root)
    masonry=_Batch('MemChu | individual sandstone courses',ashlar,collection,root)
    molding=_Batch('MemChu | layered carved surrounds',[trim,edge,gold],collection,root)
    recess=_Batch('MemChu | shadowed openings and doors',[dark,wood],collection,root)
    glazing=_Batch('MemChu | blue stained-glass windows',[glass],collection,root)
    metal=_Batch('MemChu | window tracery and bronze details',[lead],collection,root)
    art=_Batch('MemChu | packed mosaic artwork and ornamental facade',[photomat],collection,root)
    roof=_Batch('MemChu | tile roof foundations',roofmats,collection,root)
    tiles=_Batch('MemChu | individual overlapping barrel tiles',roofmats,collection,root)
    rng=random.Random(507)

    # Mapped facade proportion: 27.4m wide, current central arched window.
    W=13.70; floor=.32; cornice=9.42; eave=18.15; peak=28.0
    structure.box((0,1.25,.18),(28.2,5.5,.36),1)
    # Three broad stone entrance steps, shallow enough to meet the Quad paving.
    for j in range(3):
        structure.box((0,-.65-j*.52,.10+j*.075),(28.7-j*.5,2.4-j*.55,.20+j*.15),1)
    # Above-portal facade wall; lower wall is assembled around genuine openings.
    structure.box((0,.85,(cornice+eave)/2),(2*W,1.7,eave-cornice),0)
    structure.mesh([(-W,0,eave),(W,0,eave),(0,0,peak),(-W,1.7,eave),(W,1.7,eave),(0,1.7,peak)],
                   [(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],0)
    art.mesh([(-W,-.025,cornice),(W,-.025,cornice),(W,-.025,eave),(0,-.025,peak),(-W,-.025,eave)],[(0,1,2,3,4)])
    centers=[-7.16,0,7.16]
    inner_rx,inner_rz,spring=2.18,2.75,3.30
    # Front wall piers with UV-selected gold vines, plus solid side returns.
    intervals=[(-W,centers[0]-inner_rx)]
    intervals += [(centers[i]+inner_rx,centers[i+1]-inner_rx) for i in range(2)]
    intervals += [(centers[-1]+inner_rx,W)]
    for lo,hi in intervals:
        structure.box(((lo+hi)/2,.9,cornice/2),(hi-lo,1.8,cornice),0)
        art.mesh([(lo,-.032,.33),(hi,-.032,.33),(hi,-.032,cornice),(lo,-.032,cornice)],[(0,1,2,3)])
    for cx in centers:
        n=48
        # Spandrel of each opening, a wall running up to the continuous cornice.
        for k in range(n):
            t0=PI*k/n;t1=PI*(k+1)/n
            x0=cx+inner_rx*math.cos(t0); x1=cx+inner_rx*math.cos(t1)
            z0=spring+inner_rz*math.sin(t0); z1=spring+inner_rz*math.sin(t1)
            art.mesh([(x0,-.035,z0),(x1,-.035,z1),(x1,-.035,cornice),(x0,-.035,cornice)],[(0,1,2,3)])
            structure.mesh([(x0,0,z0),(x1,0,z1),(x1,0,cornice),(x0,0,cornice),
                            (x0,1.8,z0),(x1,1.8,z1),(x1,1.8,cornice),(x0,1.8,cornice)],
                           [(0,1,2,3),(7,6,5,4),(0,4,5,1),(2,6,7,3)],0)
        # Deep intrados and recessed door, actual geometry rather than black printed holes.
        molding.arch((cx,.65,0),inner_rx,inner_rz,spring,inner_rx+.14,inner_rz+.15,1.65,0,segments=48)
        for side in [-1,1]:
            molding.box((cx+side*(inner_rx+.12),.75,1.88),(.25,1.75,3.05),0)
        recess.arch_fill((cx,1.98,0),inner_rx-.05,inner_rz-.08,.28,spring,0)
        recess.box((cx,1.82,1.93),(3.22,.18,3.28),1)
        for side in [-1,1]:
            for z in [1.03,2.34]:
                molding.box((cx+side*.83,1.70,z),(1.27,.07,.86),0)
                recess.box((cx+side*.83,1.635,z),(1.13,.035,.73),1)
            metal.box((cx+side*.16,1.61,1.67),(.045,.09,.29))
        # Recessed arch moldings: stepped inward rings around a textured wide band.
        for rx,rz,thick,y in [(2.22,2.80,.12,-.20),(2.38,2.97,.15,-.33),
                               (2.61,3.24,.12,-.25),(3.22,3.95,.10,-.16),
                               (3.43,4.22,.10,-.16)]:
            molding.arch((cx,y,0),rx,rz,spring,rx+thick,rz+thick,.24,0,segments=48)
        art.arch((cx,-.19,0),2.74,3.38,spring,3.37,4.16,.03,0,segments=56)
        # Carved bundled jamb columns and block capitals.
        for side in [-1,1]:
            for off in [2.41,2.63,2.88,3.12]:
                xx=cx+side*off
                molding.cylinder((xx,-.30,1.72),.105,2.38,0,16)
                molding.cylinder((xx,-.30,.56),.15,.22,1,16)
                molding.cylinder((xx,-.30,2.99),.17,.30,0,16)
                molding.box((xx,-.30,3.17),(.39,.38,.16),0)
                # Fine fluting/twist relief, as a geometric approximation of carving.
                for f in range(3):
                    a=2*PI*f/3
                    molding.beam((xx+.09*math.cos(a),-.30+.09*math.sin(a),.63),
                                 (xx+.09*math.cos(a+.7),-.30+.09*math.sin(a+.7),2.82),.025,material=1)
            molding.box((cx+side*2.8,-.25,.44),(1.05,.65,.19),0)
            molding.box((cx+side*2.8,-.27,3.30),(1.26,.73,.26),1)
    # Continuous dentil/frieze break between the vine mosaic and upper scene.
    molding.box((0,-.15,9.42),(27.8,.58,.27),0)
    molding.box((0,-.20,9.59),(27.65,.70,.13),1)
    for k in range(41):
        x=-13.15+k*.6575
        molding.arch((x,-.26,0),.195,.23,8.98,.30,.34,.22,0,segments=12)
    # Seven window ensemble. Main glass keeps the original artwork via UV mapping.
    def facade_window(cx,rx,rz,bottom,springz,outer_width,large=False):
        glazing.arch_fill((cx,-.115,0),rx,rz,bottom,springz)
        art.arch_fill((cx,-.14,0),rx-.025,rz-.02,bottom+.02,springz)
        molding.arch((cx,-.22,0),rx,rz,springz,rx+.18,rz+.18,.32,1)
        molding.arch((cx,-.10,0),rx+.22,rz+.22,springz,rx+outer_width,rz+outer_width,.25,0)
        art.arch((cx,-.241,0),rx+.25,rz+.25,springz,rx+outer_width-.04,rz+outer_width-.04,.022)
        for side in [-1,1]:
            molding.box((cx+side*(rx+.13),-.21,(bottom+springz)/2),(.24,.35,springz-bottom),1)
            for offset in [.35,.52] if large else [.27]:
                molding.cylinder((cx+side*(rx+offset),-.22,(bottom+springz)/2),.10,springz-bottom,0,14)
            molding.box((cx+side*(rx+.35),-.24,springz),(.64,.40,.18),1)
        molding.box((cx,-.20,bottom),(2*rx+.45,.54,.15),1)
        # Glass lead lines visible with reflected sun and darker internal glass.
        for dx in ([-1.45,-.73,0,.73,1.45] if large else [0]):
            high=springz+rz*math.sqrt(max(0,1-(dx/rx)**2))
            metal.box((cx+dx,-.195,(bottom+high)/2),(.028,.048,high-bottom))
        for z in ([12.5,13.55,14.58,15.40] if large else [12.6,13.5,14.4]):
            if z < springz:
                metal.box((cx,-.20,z),(2*rx,.05,.035))
        if large:
            metal.arch((cx,-.203,0),rx*.70,rz*.70,springz,rx*.70+.032,rz*.70+.032,.06,0,segments=36)
    facade_window(0,2.64,2.75,11.80,14.66,1.50,True)
    for cx in [-8.74,-7.05,-5.37,5.37,7.05,8.74]:
        facade_window(cx,.48,.63,11.76,14.80,.46)
    # Balustrade-like stone panels underneath windows.
    for x in [-9.2,-7.45,-5.7,5.7,7.45,9.2]:
        molding.box((x,-.15,10.78),(1.54,.19,1.30),0)
        molding.box((x,-.28,10.92),(.89,.08,.59),1)
        art.mesh([(x-.40,-.327,10.68),(x+.40,-.327,10.68),(x+.40,-.327,11.17),(x-.40,-.327,11.17)],[(0,1,2,3)])
    molding.box((0,-.16,10.36),(4.88,.25,.15),1)
    molding.box((0,-.16,11.70),(4.88,.25,.15),1)
    # Gable verge follows the large mosaic field and has carved repeating rosettes.
    for side in [-1,1]:
        a=(side*13.66,-.15,18.20); b=(0,-.15,28.10)
        molding.beam(a,b,.28,.40,0)
        for k in range(34):
            t=(k+.5)/34
            x=a[0]*(1-t)+b[0]*t; z=a[2]*(1-t)+b[2]*t
            # A repeating recessed diamond bead, restrained at campus-view distance.
            molding.beam((x-.06,-.39,z-.065),(x+.06,-.39,z+.065),.11,.055,1)
    # Stone crest and a trefoil-ended cross, not a bell tower.
    molding.box((0,.3,28.05),(.63,.80,.45),0)
    molding.arch((0,-.02,0),.36,.40,28.25,.55,.60,.34,0,segments=28)
    molding.box((0,.02,29.91),(.24,.36,2.12),1)
    molding.box((0,.02,30.15),(1.65,.36,.24),1)
    for x,z in [(0,31.03),(-.85,30.15),(.85,30.15)]:
        for dx,dz in [(-.10,0),(.10,0),(0,.12)]:
            molding.box((x+dx,.02,z+dz),(.17,.38,.18),1)
    # Dedication plaque: short contemporary small plaque, not the old giant legend.
    structure.box((-11.83,-.11,1.70),(2.76,.23,1.65),1)
    plaque=bpy.data.curves.new('MemChu dedication plaque','FONT')
    plaque.body='MEMORIAL CHURCH\nERECTED BY\nJANE LATHROP STANFORD\nTO THE GLORY OF GOD\nAND IN MEMORY OF HER HUSBAND\nLELAND STANFORD'
    plaque.size=.123; plaque.space_line=1.22; plaque.align_x='CENTER'; plaque.extrude=.0008
    plaqueob=bpy.data.objects.new('MemChu | dedication inscription',plaque); collection.objects.link(plaqueob)
    plaqueob.parent=root; plaqueob.location=(-11.83,-.245,2.19); plaqueob.rotation_euler=(PI/2,0,0); plaque.materials.append(stone)

    # Cruciform body, rounded apses and a low square crossing roof rebuilt after 1906.
    structure.box((0,19.55,8.65),(24.8,29.1,17.3),0)
    structure.box((0,37.2,12.40),(21.6,19.8,24.8),0)
    structure.box((0,37.8,8.0),(31.0,16.0,16.0),0)
    for side in [-1,1]:
        structure.cylinder((side*15.35,37.8,8.0),7.65,16.0,0,64)
    structure.box((0,47.2,8.1),(16.5,7.3,16.2),0)
    structure.cylinder((0,50.0,8.1),8.0,16.2,0,64)
    # Low side aisles lead toward the more elevated transept blocks.
    for side in [-1,1]:
        structure.box((side*13.60,18.3,4.80),(4.5,26.0,9.6),0)
    # Front round stair turrets visible beyond the shoulders of the mosaic facade.
    for side in [-1,1]:
        structure.cylinder((side*12.2,6.7,6.88),2.50,13.75,0,48)
        structure.cylinder((side*12.2,6.7,13.75),2.62,.29,1,48)
        # Round red-tile caps above the stair towers.
        roof.cylinder((side*12.2,6.7,15.64),2.88,3.62,3,64,radius_top=.03)

    def gable_roof(name,cx,cy,width,length,zedge,zridge):
        h=width/2
        roof.mesh([(cx-h,cy-length/2,zedge),(cx+h,cy-length/2,zedge),(cx,cy-length/2,zridge),
                   (cx-h,cy+length/2,zedge),(cx+h,cy+length/2,zedge),(cx,cy+length/2,zridge)],
                  [(2,5,3,0),(1,4,5,2),(0,2,1),(3,4,5)],2)
        for side in [-1,1]:
            # Tile overlaps are distinct curved meshes merged into one editable batch.
            rows=max(1,math.ceil(h/.57)); columns=max(1,math.ceil(length/.44))
            for i in range(rows):
                x0=h*i/rows; x1=min(h,h*(i+1)/rows+.065)
                for j in range(columns):
                    y0=cy-length/2+j*length/columns
                    tile_patch((cx+side*x0,y0,zridge-(zridge-zedge)*x0/h),
                               (cx+side*x1,y0,zridge-(zridge-zedge)*x1/h),
                               (0,length/columns*.96,0),rng.randrange(len(roofmats)))
        molding.beam((cx-h,cy-length/2,zedge-.05),(cx,cy-length/2,zridge-.05),.17,.20,0)
        molding.beam((cx,cy-length/2,zridge-.05),(cx+h,cy-length/2,zedge-.05),.17,.20,0)

    def tile_patch(a,b,across,mi):
        # Half-round barrel profile perpendicular to slope; 10 vertices per tile.
        v=[]; sections=4
        dx,dy,dz=[b[k]-a[k] for k in range(3)]
        length=math.sqrt(dx*dx+dy*dy+dz*dz)
        ax,ay,az=across; aw=math.sqrt(ax*ax+ay*ay+az*az)
        if length < .001 or aw < .001: return
        # Surface outward normal, orient upward for both roof slopes.
        nx=dy*az-dz*ay;ny=dz*ax-dx*az;nz=dx*ay-dy*ax
        nl=math.sqrt(nx*nx+ny*ny+nz*nz)
        reverse_faces = nz > 0
        if nz<0: nx,ny,nz=-nx,-ny,-nz
        nx,ny,nz=nx/nl,ny/nl,nz/nl
        for p in (a,b):
            for k in range(sections+1):
                t=k/sections; bulge=.083*math.sin(PI*t)+.02
                v.append((p[0]+ax*t+nx*bulge,p[1]+ay*t+ny*bulge,p[2]+az*t+nz*bulge))
        n=sections+1
        faces=[(k,k+1,n+k+1,n+k) for k in range(sections)]
        if reverse_faces: faces=[tuple(reversed(face)) for face in faces]
        tiles.mesh(v,faces,mi)

    def cone_roof(cx,cy,r,z0,z1,semicircle=None):
        # All radial roofs are full solids; their inner halves intersect the body.
        roof.cylinder((cx,cy,(z0+z1)/2),r,z1-z0,2,64,radius_top=.035)
        courses=math.ceil(r/.58)
        for row in range(courses):
            rr0=max(.19,r*row/courses); rr1=min(r,r*(row+1)/courses+.07)
            if rr1 <= rr0: continue
            N=max(8,round(2*PI*(rr0+rr1)/2/.45))
            for j in range(N):
                a=2*PI*j/N; a1=2*PI*(j+.97)/N
                mi=rng.randrange(6)
                v=[]
                for rr in [rr0,rr1]:
                    z=z1-(z1-z0)*rr/r
                    for k in range(5):
                        t=k/4; th=a+(a1-a)*t
                        v.append((cx+rr*math.cos(th),cy+rr*math.sin(th),z+.025+.074*math.sin(PI*t)))
                tiles.mesh(v,[(5+k,6+k,k+1,k) for k in range(4)],mi)

    # Main nave. Its roof starts behind the mosaic pediment and meets the crossing.
    gable_roof('Nave',0,17.0,26.0,31.1,17.60,27.30)
    for side in [-1,1]:
        # Low side aisle lean-to roofs.
        roof.mesh([(side*11.8,5.3,13.1),(side*16.3,5.3,9.7),(side*16.3,31.6,9.7),(side*11.8,31.6,13.1)],[(0,1,2,3) if side>0 else (3,2,1,0)],3)
        for row in range(9):
            t0=row/9;t1=min(1,(row+1)/9+.018)
            for j in range(57):
                yy=5.3+j*26.3/57
                tile_patch((side*(11.8+4.5*t0),yy,13.1-3.4*t0),
                           (side*(11.8+4.5*t1),yy,13.1-3.4*t1),(0,26.3/57*.97,0),rng.randrange(6))
        cone_roof(side*15.35,37.8,8.20,16.45,24.15)
        cone_roof(side*12.2,6.7,2.90,13.85,17.52)
    cone_roof(0,50.0,8.55,16.55,24.55)
    # Square crossing upper walls: crown sits above three rounded arms.
    for side in [-1,1]:
        molding.box((side*10.85,37.3,24.85),(.36,20.5,.30),0)
        molding.box((0,37.3+side*10.0,24.85),(22.0,.36,.30),0)
    # Truncated hipped roof leaves a small square copper-and-glass lantern.
    outer=11.80; inner=3.65; cz=37.3; z0=25.05; z1=29.10
    for k in range(4):
        a=k*PI/2
        co,si=math.cos(a),math.sin(a)
        def tr(x,y,z): return (x*co-y*si,cz+x*si+y*co,z)
        roof.mesh([tr(-outer,outer,z0),tr(outer,outer,z0),tr(inner,inner,z1),tr(-inner,inner,z1)],[(3,2,1,0)],3)
        rows=17
        for row in range(rows):
            t0=row/rows;t1=min(1,(row+1)/rows+.006)
            yy0=outer+(inner-outer)*t0; yy1=outer+(inner-outer)*t1
            half0=yy0;half1=yy1
            N=max(10,math.ceil(2*half0/.47))
            for j in range(N):
                x0=-half0+j*2*half0/N; x1=-half1+j*2*half1/N
                aa=tr(x0,yy0,z0+(z1-z0)*t0);bb=tr(x1,yy1,z0+(z1-z0)*t1)
                across=(co*(2*half0/N*.94),si*(2*half0/N*.94),0)
                tile_patch(aa,bb,across,rng.randrange(6))
    structure.box((0,cz,29.13),(7.25,7.25,.36),1)
    # Very low glazed pyramid, visible in contemporary aerial views.
    glazing.mesh([(-3.55,cz-3.55,29.35),(3.55,cz-3.55,29.35),(3.55,cz+3.55,29.35),(-3.55,cz+3.55,29.35),(0,cz,31.0)],
                 [(0,1,4),(1,2,4),(2,3,4),(3,0,4)])
    for x,y in [(-3.55,cz-3.55),(3.55,cz-3.55),(3.55,cz+3.55),(-3.55,cz+3.55)]:
        metal.beam((x,y,29.4),(0,cz,31.05),.09)
    metal.cylinder((0,cz,31.12),.08,.26,0,16)

    # Ashlar courses are real shallow stone blocks, batched for easy navigation.
    def coursed_wall(x0,x1,y,z0,z1,rotation=0):
        h=.56; rows=int((z1-z0)/h)
        co,si=math.cos(rotation),math.sin(rotation)
        for row in range(rows):
            x=x0-(.64 if row%2 else 0)
            while x<x1:
                width=rng.uniform(.91,1.54);lo=max(x0,x);hi=min(x1,x+width)
                if hi-lo>.08:
                    xx=(lo+hi)/2
                    masonry.box((xx*co-y*si,xx*si+y*co,z0+(row+.5)*h),(hi-lo-.025,.09,h-.026),rng.randrange(7),rotation)
                x+=width
    # Exposed nave clerestory and aisle side walls.
    for side in [-1,1]:
        # Rotate the side wall so local X runs along Y.
        coursed_wall(6.0,29.5,-side*12.43,10.2,17.15,PI/2)
        coursed_wall(7.0,29.7,-side*15.90,.45,9.30,PI/2)
        # High crossing masonry above the radial roofs.
        coursed_wall(27.5,47.2,-side*10.86,20.1,24.65,PI/2)
    coursed_wall(-10.5,10.5,47.22,20.1,24.65)

    def side_window(center,angle,width=1.18,bottom=12.9,springz=15.02,rz=.59):
        cx,cy=center; rx=width/2
        co,si=math.cos(angle),math.sin(angle)
        glazing.arch_fill((cx,cy,0),rx,rz,bottom,springz,0,angle,24)
        molding.arch((cx,cy,0),rx,rz,springz,rx+.17,rz+.17,.18,0,angle,24)
        # Border jambs and multiple lead bars.
        for xx in [-rx-.095,rx+.095]:
            molding.box((cx+xx*co,cy+xx*si,(bottom+springz)/2),(.19,.23,springz-bottom),0,angle)
        for xx in [-rx*.4,rx*.4]:
            metal.box((cx+xx*co-.08*si,cy+xx*si+.08*co,(bottom+springz)/2),(.027,.04,springz-bottom),0,angle)
        for z in [bottom+.60,bottom+1.2,bottom+1.8]:
            if z<springz: metal.box((cx-.09*si,cy+.09*co,z),(width,.045,.035),0,angle)
        molding.box((cx,cy,bottom),(width+.48,.36,.16),0,angle)
    for side in [-1,1]:
        for yy in [9.0,11.1,15.7,17.8,22.4,24.5,28.0]:
            side_window((side*12.49,yy),side*PI/2)
        for yy in [11.0,17.0,23.0,28.0]:
            side_window((side*15.98,yy),side*PI/2,1.46,4.4,7.50,.73)
    # Semicircular transept apses and rear chancel have tall round-headed windows.
    for cx,cy,base_angle in [(-15.35,37.8,PI),(15.35,37.8,0),(0,50.0,PI/2)]:
        radius=7.72 if cx else 8.07
        for k in range(7):
            theta=base_angle-PI/2+(k+.5)*PI/7
            x=cx+radius*math.cos(theta);y=cy+radius*math.sin(theta)
            # Window local -Y normal matches outward radial direction.
            side_window((x,y),theta+PI/2,1.38,8.9,12.40,.70)
        # Projecting horizontal courses around the curved exterior.
        for z in [.65,7.7,15.3]:
            molding.cylinder((cx,cy,z),radius+.08,.15,0,64)
    # Narrow turret windows; only outward/front-facing ones are exposed.
    for side in [-1,1]:
        for theta in [-PI/2,0 if side>0 else PI]:
            x=side*12.2+2.54*math.cos(theta);y=6.7+2.54*math.sin(theta)
            side_window((x,y),theta+PI/2,.54,10.9,12.1,.27)
    # Cornice shadows, nave downpipes and transept buttress piers.
    for side in [-1,1]:
        molding.box((side*12.55,18.0,17.32),(.38,28.6,.29),0)
        for yy in [7.3,14.3,21.3,28.3]:
            structure.box((side*16.07,yy,4.1),(.59,.71,8.2),0)
            structure.box((side*16.07,yy,8.22),(.80,.94,.30),1)
        metal.box((side*12.50,27.2,11.4),(.09,.12,11.3))
    # A simple interior roof shadow backs the true entrance arcade.
    recess.box((0,4.1,6.10),(23.6,5.0,.16))

    finished=[]
    for batch,bevel,uv in [(structure,.028,False),(masonry,.012,False),
                            (molding,.015,False),(recess,.01,False),(glazing,0,False),
                            (metal,.007,False),(art,0,True),(roof,0,False),(tiles,0,False)]:
        ob=batch.finish(bevel,uv)
        if ob: finished.append(ob)
    txt=bpy.data.texts.get('Memorial Church · sources and texture license') or bpy.data.texts.new('Memorial Church · sources and texture license')
    txt.clear(); txt.write(SOURCE_NOTES)
    root['mesh_vertices']=sum(len(o.data.vertices) for o in finished)
    root['mesh_objects']=len(finished)
    root['tile_note']='Thousands of individually shaped overlapping barrel tiles are joined into one editable roof-tile mesh.'
    # Bounds include front steps, crest and rounded arms.
    bounds=((-23.55,-2.4,0),(23.55,58.60,31.35))
    return {'root':root,'collection':collection,'bounds_local':bounds,
            'bounds_world':tuple(tuple(p[i]+origin[i] for i in range(3)) for p in bounds),
            'mesh_vertices':root['mesh_vertices'],'mesh_objects':len(finished),
            'note':'Photographic reconstruction; no tall pre-1906 clock tower. Current front arched stained-glass window.'}


SOURCE_NOTES = '''STANFORD MEMORIAL CHURCH - MODEL NOTES AND ATTRIBUTION

Created as an editable photo-based exterior model for the Stanford Main Quad scene.
Current post-1906 building: the old clock tower/80ft spire is deliberately absent.
The modern facade has a large arched stained-glass window and six slender side
windows; the original circular rose window was lost in 1906.

DIMENSIONS
Stanford ORSL describes the cruciform plan as 190ft long and 150ft wide, and the
facade mosaic as 84ft wide and 30ft high. Those are used as approximate scale
anchors. Other dimensions, roof levels, masonry and small ornament are estimates
from photographs, not surveyed architectural documentation. Local front faces -Y.
Approximate length58m; transept width46m; tallest crest/skylight31.3m.

ARCHITECTURAL SOURCES
Stanford Office for Religious & Spiritual Life, Memorial Church History:
https://orsl.stanford.edu/memorial-church-history
Stanford Office for Religious & Spiritual Life, Memorial Church Layout:
https://orsl.stanford.edu/memorial-church-layout
Stanford University and the 1906 Earthquake, Repair of Monuments:
https://quake06.stanford.edu/4-repair-monuments
Stanford faculty Robert Siegel, aerial/current roof photographs (reference only,
not embedded or redistributed as textures):
https://web.stanford.edu/~siegelr/stanford/memchu.html

PACKED PHOTOGRAPHIC MOSAIC / FACADE DECORATION TEXTURE
King of Hearts, Stanford Memorial Church May 2011 002.jpg, photographed2011-05-07.
https://commons.wikimedia.org/wiki/File:Stanford_Memorial_Church_May_2011_002.jpg
License: Creative Commons Attribution-ShareAlike3.0 Unported.
https://creativecommons.org/licenses/by-sa/3.0/
The original photograph is packed, unaltered, into the blend file. UV coordinates
select the mosaic fields, stained-glass artwork and shallow carved-face detail.
The UV-mapped artwork adaptation is offered under the same CC BY-SA3.0 license.
No endorsement by the photographer or Stanford is implied.
The portrayed historic Salviati artwork dates to the1903/1917 installations.

ADDITIONAL PHOTOGRAPHIC REFERENCES (NOT USED AS TEXTURES)
GualdimG, Exterior of Stanford Memorial Church, Stanford, California02.jpg,
2025-04-08, CC BY-SA4.0:
https://commons.wikimedia.org/wiki/File:Exterior_of_Stanford_Memorial_Church,_Stanford,_California_02.jpg
Ed Bierman, Exterior mosaic2.jpg,2008-12-25, CC BY-SA2.0:
https://commons.wikimedia.org/wiki/File:Exterior_mosaic2.jpg

GEOMETRY
Real three-dimensional portal depth, stepped moldings, bundled jamb shafts,
modern arched window group, gable crest, curved turrets, nave clerestory, rounded
transept and chancel apses, low crossing roof and small glazed pyramidal skylight.
Individual barrel tiles are batched for performance. Carved details are a mixture
of shallow geometric detail and licensed photograph mapping. Interior not modeled.
'''
