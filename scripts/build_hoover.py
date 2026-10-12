"""Photo-informed Hoover Tower reconstruction. Units are metres.
Known overall height: 86.87m. Other dimensions are estimated from photographs.
Run within Blender, directly or through the repository build.py entry point.
"""
import bpy, math, random, json, os
from mathutils import Vector
from pathlib import Path
from math import sin, cos, pi, sqrt
ROOT = Path(__file__).resolve().parents[1]
random.seed(41)
bpy.context.scene.pop('shaft_union_done', None)

# Preserve the user's starting scene before constructing the project.
if not (ROOT / 'before_hoover.blend').exists():
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'before_hoover.blend'), copy=True)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)

COLS = {}
for name in ['01 · Foundation & entry', '02 · Tower shaft', '03 · Observation crown',
             '04 · Terracotta dome', '05 · Lantern & pinnacles', '06 · Metalwork & details',
             '08 · Cameras & lighting']:
    col = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col); COLS[name] = col
COL = COLS['02 · Tower shaft']

def mat(name, color, rough=.7, metal=0, texture=False):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    nt=m.node_tree; bs=nt.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    if texture:
        tex=nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=3.2; tex.inputs['Detail'].default_value=3
        tc=nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Generated'],tex.inputs['Vector'])
        ramp=nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.16; ramp.color_ramp.elements[0].color=(*[x*.82 for x in color],1)
        ramp.color_ramp.elements[1].position=.86; ramp.color_ramp.elements[1].color=(*[min(x*1.08,1) for x in color],1)
        nt.links.new(tex.outputs['Fac'],ramp.inputs[0]); nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
        fine=nt.nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=95; fine.inputs['Detail'].default_value=2
        nt.links.new(tc.outputs['Object'],fine.inputs['Vector'])
        bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.2; bump.inputs['Distance'].default_value=.025
        nt.links.new(fine.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m
STUCCO=mat('Warm sandstone · fine cement stucco',(.64,.565,.43),texture=True)
TRIM=mat('Carved limestone · warm ivory',(.73,.66,.52),texture=True)
RECESS=mat('Stucco · shaded recess',(.59,.515,.39),texture=True)
STONE=mat('Portal · honey limestone',(.57,.45,.29),texture=True)
DARK=mat('Interior · shadow',(.035,.043,.042),.95)
IRON=mat('Graphite bronze · metalwork',(.035,.045,.046),.36,.7)
GLASS=mat('Window glass · cool smoked blue',(.042,.105,.13),.2,.32)
COPPER=mat('Lightning protection · aged copper',(.22,.115,.055),.4,.75)
TILES=[mat('Terracotta · shade %02d'%i,(.32+i*.024,.074+i*.008,.036+i*.004),.74,texture=True) for i in range(9)]

def mesh(name, verts, faces, material, smooth=False, collection=None):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); (collection or COL).objects.link(ob)
    if material: me.materials.append(material)
    if smooth:
        for p in me.polygons: p.use_smooth=True
    return ob

def bevel(ob, width=.03, segments=2):
    mod=ob.modifiers.new('Soft masonry edges','BEVEL'); mod.width=width; mod.segments=segments
    return ob

def tr(p, angle=0):
    x,y,z=p; return (x*cos(angle)-y*sin(angle),x*sin(angle)+y*cos(angle),z)

def box(name, loc, size, material, angle=0, edge=.02):
    x,y,z=size; verts=[tr((loc[0]+sx*x/2,loc[1]+sy*y/2,loc[2]+sz*z/2),angle) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    ob=mesh(name,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material)
    if edge: bevel(ob,edge)
    return ob

def prism(name, poly, y0, y1, material, angle=0):
    n=len(poly); vs=[tr((x,y,z),angle) for y in (y0,y1) for x,z in poly]
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,vs,fs,material)

def lathe(name, profile, material, sides=64, center=(0,0,0), smooth=True, phase=0):
    vs=[(center[0]+r*cos(phase+2*pi*j/sides),center[1]+r*sin(phase+2*pi*j/sides),center[2]+z) for r,z in profile for j in range(sides)]
    fs=[]
    for k in range(len(profile)-1):
        for j in range(sides): fs.append((k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j))
    fs+=[tuple(reversed(range(sides))),tuple((len(profile)-1)*sides+j for j in range(sides))]
    return mesh(name,vs,fs,material,smooth)

def line(name, pts, radius, material, cyclic=False):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=1; cu.bevel_depth=radius; cu.bevel_resolution=2
    sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts): p.co=(*co,1)
    sp.use_cyclic_u=cyclic; ob=bpy.data.objects.new(name,cu); COL.objects.link(ob); cu.materials.append(material); return ob

def ring(name, radius, z, material, sides=64, thick=.065):
    return line(name,[(radius*cos(2*pi*j/sides),radius*sin(2*pi*j/sides),z) for j in range(sides)],thick,material,True)

def arch_ring(name,x,y,zspring,ri,ro,bottom,material,angle=0,depth=.12):
    n=40; vs=[]; fs=[]
    for yy in (y-depth/2,y+depth/2):
        for r in (ri,ro):
            for j in range(n+1):
                t=pi*j/n; vs.append(tr((x+r*cos(t),yy,zspring+r*sin(t)),angle))
    L=n+1
    for j in range(n):
        fs.extend([(j,j+1,L+j+1,L+j),(2*L+j,3*L+j,3*L+j+1,2*L+j+1),
                   (j,2*L+j,2*L+j+1,j+1),(L+j,L+j+1,3*L+j+1,3*L+j)])
    ob=mesh(name,vs,fs,material)
    for s in [-1,1]: box(name+' jamb',(x+s*(ri+ro)/2,y,(bottom+zspring)/2),(ro-ri,depth,zspring-bottom),material,angle,.012)
    return ob

def arch_fill(name,x,y,bottom,spring,r,material,angle=0):
    poly=[(x-r,bottom),(x+r,bottom)]+[(x+r*cos(pi*j/32),spring+r*sin(pi*j/32)) for j in range(33)]
    return prism(name,poly,y-.012,y+.035,material,angle)

def wall_arch(name,x,y,width,bottom,top,opening_bottom,spring,r,depth,material,angle=0):
    # Real, open arch assembled from planar masonry patches, with deep reveals.
    left=x-width/2; right=x+width/2
    for side,a,b in [('L',left,x-r),('R',x+r,right)]:
        if b>a: box(name+side,((a+b)/2,y,(bottom+top)/2),(b-a,depth,top-bottom),material,angle,.012)
    if opening_bottom>bottom: box(name+' sill',(x,y,(bottom+opening_bottom)/2),(r*2,depth,opening_bottom-bottom),material,angle,.015)
    n=32; vs=[]; fs=[]
    for i in range(n):
        t0=pi-i*pi/n; t1=pi-(i+1)*pi/n
        xa=x+r*cos(t0); xb=x+r*cos(t1); za=spring+r*sin(t0); zb=spring+r*sin(t1)
        poly=[(xa,za),(xb,zb),(xb,top),(xa,top)]; start=len(vs)
        vs.extend(tr((u,yy,v),angle) for yy in (y-depth/2,y+depth/2) for u,v in poly)
        fs.extend(tuple(start+j for j in f) for f in [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(3,2,6,7)])
    return mesh(name+' arched spandrel',vs,fs,material)

def window(name,x,y,bottom,spring,r,angle):
    arch_fill(name+' dark glazing',x,y+.055,bottom,spring,r,GLASS,angle)
    arch_ring(name+' steel frame',x,y-.006,spring,r-.035,r+.028,bottom,IRON,angle,.065)
    for off in [-.45,0,.45]:
        u=r*off; top=spring+sqrt(max(0,r*r-u*u))-.04
        box(name+' mullion',(x+u,y-.037,(bottom+top)/2),(.024,.065,top-bottom),IRON,angle,0)
    z=bottom+.38
    while z<spring+r-.12:
        rw=r if z<=spring else sqrt(max(0,r*r-(z-spring)**2))
        box(name+' transom',(x,y-.047,z),(2*rw,.065,.025),IRON,angle,0); z+=.42

def rectangular_window(name,x,y,z,w,h,angle):
    box(name+' deep reveal',(x,y+.045,z),(w,.12,h),DARK,angle,.01)
    box(name+' glass',(x,y-.03,z),(w-.14,.045,h-.16),GLASS,angle,.008)
    for s in [-1,1]:
        box(name+' jamb',(x+s*(w/2+.06),y-.07,z),(.12,.23,h+.24),TRIM,angle,.015)
        box(name+' sill/lintel',(x,y-.07,z+s*(h/2+.06)),(w+.24,.23,.12),TRIM,angle,.015)
    box(name+' mullion',(x,y-.075,z),(.04,.06,h),IRON,angle,0)
    box(name+' crossbar',(x,y-.078,z),(w,.06,.035),IRON,angle,0)

# Tall square shaft: three shallow recessed arched bays per facade.
A=8.6; BACK=8.16; TOP=65.3
box('Main structural shaft',(0,0,TOP/2),(2*BACK,2*BACK,TOP),STUCCO,edge=.025)
for k in range(4):
    angle=k*pi/2
    # Outer panels between long recessed channels.
    bay_centers=[-5.05,0,5.05]; r=1.48; spring=60.0
    edges=[-A]+[v for c in bay_centers for v in (c-r,c+r)]+[A]
    for j in range(0,len(edges)-1,2):
        lo,hi=edges[j],edges[j+1]
        box('Continuous facade pier %s.%s'%(k,j),((lo+hi)/2,-(A+BACK)/2,TOP/2),(hi-lo,A-BACK,TOP),STUCCO,angle,.025)
    for b,x in enumerate(bay_centers):
        wall_arch('Shallow long recess %s.%s'%(k,b),x,-(A+BACK)/2,2*r,0,TOP,8.8,spring,r,A-BACK,STUCCO,angle)
        # Two smaller arches occupy the very top of each channel.
        for sx in [-.74,.74]:
            window('Paired arched window %s.%s'%(k,b),x+sx,-BACK-.06,57.35,59.36,.57,angle)
        # Engaged slender column and capital between the paired windows.
        p=tr((x,-BACK-.16,57.28),angle)
        lathe('Paired window central stone column',[(.14,0),(.19,.09),(.13,.16),(.115,2.05),(.19,2.13),(.23,2.25)],TRIM,24,p)
        box('Window stone sill',(x,-BACK-.13,57.29),(2.85,.28,.13),TRIM,angle,.025)
    # Fine horizontal frieze intersects the spring of the three big recesses.
    for lo,hi in [(-A,-6.53),(-3.57,-1.48),(1.48,3.57),(6.53,A)]:
        box('Upper shaft frieze',((lo+hi)/2,-A-.023,60.02),(hi-lo,.095,.18),TRIM,angle,.015)
    for xx in [-.58,.58]: rectangular_window('Shoulder paired small window',xx,-A-.02,63.28,.60,1.25,angle)
    levels=[54.9] if k==0 else [17.8,30.1,42.4,54.9]
    for z in levels: rectangular_window('Sparse shaft slit',0,-BACK-.035,z,.68,1.56,angle)
    box('Shaft shoulder coping',(0,-A-.05,65.32),(17.45,.36,.18),TRIM,angle,.025)

# Podium, low wings, and deeply modeled entrance.
COL=COLS['01 · Foundation & entry']
box('Square tower lower plinth',(0,0,.36),(18.2,18.2,.72),STONE,edge=.08)
for x in [-12.45,12.45]:
    box('Low exhibition wing',(x,0,3.3),(7.7,17.8,6.6),STUCCO,edge=.035)
    box('Wing coping',(x,0,6.67),(8.0,18.1,.25),TRIM,edge=.04)
    box('Wing upper setback',(x,.4,7.22),(7.4,15.8,.85),STUCCO,edge=.03)
    box('Wing top coping',(x,.4,7.68),(7.7,16.1,.17),TRIM,edge=.04)
    for xx in [x-2.35,x,x+2.35]:
        rectangular_window('Wing front high window',xx,-9.0,5.55,1.25,1.26,0)
    for xx in [x-1.8,x+1.8]:
        rectangular_window('Wing front gallery window',xx,-9.0,2.8,1.1,2.8,0)
# Entry portal projects forward and conceals the tiny hipped roof at shaft foot.
wall_arch('Monumental entrance',0,-10.0,12.8,.8,11.6,.8,5.9,2.1,3.1,STUCCO)
box('Entry parapet cap',(0,-10.0,11.64),(13.08,3.35,.18),TRIM,edge=.035)
arch_fill('Portal shadow',0,-8.37,.84,5.9,2.1,DARK)
for ri,ro,yy in [(2.12,2.3,-11.6),(2.36,2.54,-11.63),(2.57,3.55,-11.59)]:
    arch_ring('Concentric carved archivolt',0,yy,5.9,ri,ro,1.03,STONE,depth=.2)
# Individual radial stone joints on the wide archivolt.
for i in range(25):
    a=pi*i/24
    line('Portal radial stone joint',[(r*cos(a),-11.706,5.9+r*sin(a)) for r in [2.60,3.53]],.009,RECESS)
for r in [2.3,3.6]:
    line('Carved portal bead',[(r*cos(pi*j/120),-11.72,5.9+r*sin(pi*j/120)) for j in range(121)],.043,TRIM)
for s in [-1,1]:
    box('Entry flanking stone pedestal',(s*2.96,-11.72,1.46),(1.3,.52,.75),STONE,edge=.04)
    lathe('Portal engaged column',[(.16,0),(.19,.12),(.145,.24),(.145,4.1),(.22,4.2),(.25,4.3)],TRIM,24,(s*2.29,-11.64,1.62))
# Door with individual rails and panes under an arched transom.
arch_fill('Entrance iron and glass',0,-9.18,1.05,5.84,1.86,GLASS)
for x in [-1.82,-.91,0,.91,1.82]: box('Entry dark door stile',(x,-9.24,3.62),(.08,.13,5.12),IRON,edge=.007)
for z in [1.12,2.0,4.85,5.85]: box('Entry dark door rail',(0,-9.25,z),(3.7,.13,.10),IRON,edge=.007)
for x in [-.18,.18]: box('Brass door pull',(x,-9.36,2.8),(.05,.08,.42),COPPER,edge=.022)
for j in range(8):
    box('Broad shallow entry step',(0,-12.6-j*.42,.12*(8-j)),(13.7+j*.20,1.05,.24),STONE,edge=.027)
# Small red tiled hip roof at the shaft foot.
rv=[(-3.3,-8.85,11.85),(3.3,-8.85,11.85),(3.3,-5.4,11.85),(-3.3,-5.4,11.85),(0,-7.1,13.0)]
mesh('Entry roof · hip backing',rv,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],TILES[3])
for i in range(33):
    x=-3.2+i*.2; z=11.88+(1-abs(x)/3.3)*1.04
    line('Entry roof tile roll',[(x,-8.85,11.88),(x*.03,-7.1,z)],.055,TILES[i%9])
# Modest brass nameplate next to entrance.
box('Entrance brass plaque',(4.8,-11.61,3.5),(1.1,.09,.76),COPPER,edge=.04)

# Octagonal crown. The walls have eight genuine open archways.
COL=COLS['03 · Observation crown']
AP=7.05; RAD=AP/cos(pi/8); SIDE=2*AP*math.tan(pi/8)
lathe('Octagonal observation floor',[(RAD+.12,65.42),(RAD+.12,65.68),(RAD,65.78),(RAD,66.36)],TRIM,8,phase=pi/8,smooth=False)
lathe('Observation interior floor',[(6.6,66.31),(6.6,66.40)],STONE,64)
lathe('Carillon upper floor',[(6.5,74.85),(6.5,75.13)],DARK,64)
for k in range(8):
    a=k*pi/4
    wall_arch('Belfry arch %02d'%k,0,-AP+.20,SIDE,66.4,76.15,67.35,72.40,1.22,.62,STUCCO,a)
    arch_ring('Belfry carved inner reveal',0,-AP-.13,72.40,1.23,1.31,67.35,TRIM,a,.095)
    box('Belfry sill',(0,-AP-.15,67.28),(2.60,.52,.20),TRIM,a,.024)
    # Pronounced fluted stone piers on both margins; surfaces follow each octagon face.
    for x in [-(SIDE/2-.52),(SIDE/2-.52)]:
        box('Fluted belfry pier',(x,-AP-.135,71.16),(1.0,.34,8.84),TRIM,a,.018)
        for i in range(6):
            xx=x-.42+i*.168
            line('Pier fine raised flute',[tr((xx,-AP-.337,67.1),a),tr((xx,-AP-.337,75.48),a)],.052,TRIM)
        for z,w,d,h in [(66.65,1.10,.42,.4),(67.02,1.15,.44,.11),(75.63,1.08,.42,.16)]:
            box('Pier capital or base',(x,-AP-.17,z),(w,d,h),TRIM,a,.012)
    # Wire grille: subtly bows out from the arch, with horizontal rings.
    for i in range(13):
        x=-1.12+i*2.24/12; top=72.4+sqrt(max(0,1.16**2-x*x))
        pts=[]
        for j in range(9):
            z=67.45+(top-67.45)*j/8; bow=.16*sin(pi*j/8)
            pts.append(tr((x,-AP-.12-bow,z),a))
        line('Belfry vertical grille',pts,.015,IRON)
    for z in [67.75,69.1,70.55,72.0]:
        pts=[tr((-1.13+i*2.26/24,-AP-.27,z),a) for i in range(25)]
        line('Belfry horizontal grille',pts,.021,IRON)
        for i in range(9):
            x=-1.0+i*.25
            line('Belfry ornamental grille ring',[tr((x+.10*cos(2*pi*j/16),-AP-.28,z+.10*sin(2*pi*j/16)),a) for j in range(16)],.010,IRON,True)
    # Lion-head relief with a sculpted mane, muzzle, ears, and nose.
    center=Vector(tr((0,-AP-.30,74.55),a))
    def relief_ellipsoid(name, local, scale):
        p=Vector(tr(local,a))
        prof=[(sin(pi*j/12),cos(pi*j/12)) for j in range(13)]
        ob=lathe(name,prof,TRIM,24,smooth=True)
        for v in ob.data.vertices:
            q=Vector((v.co.x*scale[0],v.co.y*scale[1],v.co.z*scale[2])); v.co=Vector(tr(q,a))+p
        return ob
    relief_ellipsoid('Lion head carved face',(0,-AP-.31,74.55),(.25,.16,.31))
    for j in range(13):
        t=2*pi*j/13
        relief_ellipsoid('Lion mane curl',(.26*cos(t),-AP-.26,74.55+.33*sin(t)),(.093,.11,.13))
    for s in [-1,1]:
        relief_ellipsoid('Lion muzzle',(s*.095,-AP-.455,74.47),(.095,.083,.083))
        relief_ellipsoid('Lion brow',(s*.105,-AP-.448,74.64),(.077,.048,.028))
    relief_ellipsoid('Lion nose',(0,-AP-.515,74.52),(.071,.050,.055))
    box('Lion relief stone backing',(0,-AP-.12,74.54),(.58,.10,.7),TRIM,a,.06)
# Upper octagonal fascia and lead coping.
lathe('Octagonal crown cornice',[(RAD,75.91),(RAD+.08,76.12),(RAD+.07,76.30),(RAD-.05,76.36)],TRIM,8,phase=pi/8,smooth=False)

# A modeled carillon visible behind the grille; bronze bells with flared lips.
COL=COLS['06 · Metalwork & details']
BELL=mat('Carillon bronze · aged patina',(.24,.18,.086),.5,.64)
for zz in [69.0,71.4]:
    for yy in [-2.1,2.1]: box('Carillon steel support',(0,yy,zz+.72),(8.6,.13,.18),IRON,edge=.015)
    for i in range(7):
        rr=.31+(6-i)*.025
        lathe('Carillon bell',[(rr,0),(rr,.09),(rr*.9,.16),(rr*.55,.44),(rr*.44,.75),(rr*.2,.83)],BELL,40,(-3.5+i*1.15,(-1 if i%2 else 1)*2.1,zz))
# Crown undersill ornamental dentils.
for k in range(8):
    a=k*pi/4
    for j in range(21):
        x=-SIDE/2+(j+.5)*SIDE/21
        box('Fine crown frieze dentil',(x,-AP-.09,66.23),(.12,.12,.10),TRIM,a,.005)

# Dome substrate + individually modeled overlapping fish-scale terracotta tiles.
COL=COLS['04 · Terracotta dome']
DR=7.37; DZ=76.30; DH=5.92
profile=[(DR*cos(t),DZ+DH*sin(t)) for t in [i*(pi/2)/80 for i in range(81)]]
lathe('Dome · clay substrate',profile,TILES[1],128)
verts=[]; faces=[]; mids=[]
rows=41
for row in range(rows):
    theta=.015+row*(1.355/rows)
    radius=DR*cos(theta)
    count=max(20,round(2*pi*radius/.30))
    step=2*pi/count
    dt=.054 # generous overlap along meridian
    for j in range(count):
        phi=(j+(row%2)*.5)*step
        # Rounded bottom edge, square concealed upper edge. Shell follows ellipsoid.
        outline=[(-.50,.65),(.50,.65),(.50,-.08)]
        outline += [(.50*cos(t),-.08-.45*sin(t)) for t in [i*pi/8 for i in range(1,9)]]
        n=len(outline); st=len(verts)
        for layer in [0,.034]:
            for u,v in outline:
                t=theta+v*dt; az=phi+u*step*.965; off=.028+layer
                verts.append(((DR+off)*cos(t)*cos(az),(DR+off)*cos(t)*sin(az),DZ+(DH+off)*sin(t)))
        fs=[tuple(st+i for i in reversed(range(n))),tuple(st+n+i for i in range(n))]
        fs += [(st+i,st+(i+1)%n,st+(i+1)%n+n,st+i+n) for i in range(n)]
        faces.extend(fs); mids.extend([random.choices(range(9),weights=[1,2,3,6,8,7,5,3,1])[0]]*len(fs))
ob=mesh('Dome · overlapping scalloped clay tiles',verts,faces,None)
for m in TILES: ob.data.materials.append(m)
for f,mi in zip(ob.data.polygons,mids): f.material_index=mi
ob['individual_tiles']=sum(max(20,round(2*pi*DR*cos(.015+row*(1.355/rows))/.30)) for row in range(rows))

# Four square decorative corner pinnacles.
COL=COLS['05 · Lantern & pinnacles']
for sx in [-1,1]:
    for sy in [-1,1]:
        cx,cy=sx*7.70,sy*7.70; z0=65.50
        box('Corner pinnacle base',(cx,cy,z0+.16),(1.95,1.95,.32),TRIM,edge=.028)
        for ax in [-1,1]:
            for ay in [-1,1]: box('Pinnacle slit lantern pier',(cx+ax*.59,cy+ay*.59,z0+1.62),(.59,.59,2.60),TRIM,edge=.018)
        for a in [0,pi/2,pi,3*pi/2]:
            for u in [-.62,-.48,.48,.62]:
                pos=Vector(tr((u,-.91,0),a))+Vector((cx,cy,z0))
                line('Pinnacle flute',[tuple(pos+Vector((0,0,.44))),tuple(pos+Vector((0,0,2.87)))],.035,TRIM)
        box('Pinnacle capital',(cx,cy,z0+2.99),(1.95,1.95,.20),TRIM,edge=.018)
        # Steep, stepped pyramid and scalloped relief across its four sides.
        for row in range(8):
            r1=.98*(1-row/9); r2=.98*(1-(row+1)/9); zz=z0+3.12+row*.28
            vs=[(cx+s*r,cy+t*r,z) for r,z in [(r1,zz),(r2,zz+.28)] for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
            mesh('Pinnacle stepped cap course',vs,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],TRIM)
            for a in [0,pi/2,pi,3*pi/2]:
                for q in range(max(1,5-row//2)):
                    n=max(1,5-row//2); u=-r1+(q+.5)*2*r1/n
                    pts=[]
                    for j in range(13):
                        t=pi*j/12; p=Vector(tr((u+.10*cos(t),-r1-.012,zz+.07+.15*sin(t)),a))+Vector((cx,cy,0)); pts.append(tuple(p))
                    line('Pinnacle scallop relief',pts,.018,TRIM)
        box('Pinnacle square finial',(cx,cy,z0+5.54),(.33,.33,.41),TRIM,edge=.023)
# Main lantern: circular molded collar, octagonal open body, fluted piers.
LZ=81.87
lathe('Lantern molded circular base',[(1.39,LZ),(1.46,LZ+.12),(1.46,LZ+.23),(1.30,LZ+.33),(1.28,LZ+.46)],TRIM,96)
lathe('Lantern octagonal sill',[(1.19,LZ+.42),(1.19,LZ+.77)],TRIM,8,phase=pi/8,smooth=False)
for k in range(8):
    a=k*pi/4
    box('Lantern fluted upright',(0,-1.01,LZ+1.61),(.43,.38,1.92),TRIM,a,.018)
    for xx in [-.15,-.05,.05,.15]: line('Lantern fine fluting',[tr((xx,-1.225,LZ+.79),a),tr((xx,-1.225,LZ+2.51),a)],.025,TRIM)
lathe('Lantern lintel',[(1.22,LZ+2.52),(1.22,LZ+2.83)],TRIM,8,phase=pi/8,smooth=False)
cap=[(1.11*cos(i*pi/2/32),LZ+2.79+1.50*sin(i*pi/2/32)) for i in range(33)]
lathe('Lantern carved stone cap',cap,TRIM,64)
for row in range(7):
    t=.06+row*.19; r=1.13*cos(t); z=LZ+2.8+1.50*sin(t); n=max(6,int(2*pi*r/.34))
    for j in range(n):
        ph=(j+(row%2)*.5)*2*pi/n
        pts=[]
        for q in range(17):
            a=pi*q/16; tt=t-.085*sin(a); pp=ph+.14*cos(a)/max(r,.2)
            pts.append((1.126*cos(tt)*cos(pp),1.126*cos(tt)*sin(pp),LZ+2.8+1.513*sin(tt)))
        line('Lantern cap scallop',pts,.017,TRIM)
lathe('Finial collar',[(.19,86.04),(.22,86.11),(.22,86.18)],TRIM,40)
lathe('Crowning stone orb',[(.27*sin(pi*j/32),86.43+.27*cos(pi*j/32)) for j in range(33)],TRIM,48)
lathe('Copper lightning rod',[(.017,86.62),(.017,86.87)],COPPER,16)

# Context is a separate, editable collection.
if (ROOT/'scripts/landscape.py').exists():
    landscape_scope={'__name__':'landscape_module','__file__':str(ROOT/'scripts/landscape.py')}
    exec(compile((ROOT/'scripts/landscape.py').read_text(),str(ROOT/'scripts/landscape.py'),'exec'),landscape_scope)
    landscape_scope['build_landscape']()

COL=COLS['08 · Cameras & lighting']
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'; scene.cycles.samples=96; scene.cycles.use_denoising=True
scene.cycles.max_bounces=8; scene.cycles.diffuse_bounces=4; scene.cycles.glossy_bounces=4
try:
    cp=bpy.context.preferences.addons['cycles'].preferences; cp.compute_device_type='METAL'; cp.get_devices()
    for d in cp.devices: d.use=(d.type=='METAL')
    scene.cycles.device='GPU'
except Exception: scene.cycles.device='CPU'
world=bpy.data.worlds.new('California afternoon sky'); world.use_nodes=True
wn=world.node_tree.nodes; wn.clear(); sky=wn.new('ShaderNodeTexSky'); sky.sky_type='MULTIPLE_SCATTERING'; sky.sun_elevation=math.radians(34); sky.sun_rotation=math.radians(225); sky.sun_disc=True; sky.sun_size=.012; sky.sun_intensity=1; sky.altitude=.05; sky.air_density=1.0; sky.aerosol_density=.65; sky.ozone_density=1.2
bg=wn.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value=.35; out=wn.new('ShaderNodeOutputWorld'); world.node_tree.links.new(sky.outputs[0],bg.inputs[0]); world.node_tree.links.new(bg.outputs[0],out.inputs[0]); scene.world=world
ld=bpy.data.lights.new('Afternoon sun','SUN'); ld.energy=2.3; ld.angle=.055
sun=bpy.data.objects.new('Afternoon sun',ld); COL.objects.link(sun); sun.rotation_euler=(math.radians(31),math.radians(-28),math.radians(-28))

def camera(name,loc,target,lens):
    data=bpy.data.cameras.new(name); ob=bpy.data.objects.new(name,data); COL.objects.link(ob); ob.location=loc; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler(); data.lens=lens; data.clip_end=2500; return ob
hero=camera('Camera · architectural portrait',(108,-159,89),(0,0,42),83)
camera('Camera · crown craftsmanship',(37,-52,85),(0,0,74.2),100)
camera('Camera · entrance study',(23,-42,17),(0,-7,6.2),58)
scene.camera=hero; scene.render.resolution_x=1600; scene.render.resolution_y=2000; scene.render.resolution_percentage=60
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
scene.render.filepath=str(ROOT/'renders/hoover_preview.png')
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=.4
# Useful saved viewport with materials, clean overlays, and the tower selected.
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.shading.type='MATERIAL'; area.spaces.active.overlay.show_overlays=False
        area.spaces.active.region_3d.view_perspective='CAMERA'
for ob in bpy.context.selected_objects: ob.select_set(False)
scene['project']='Hoover Tower · Stanford University'; scene['reference_height_metres']=86.87
scene['reconstruction_note']='Photo-informed exterior reconstruction; overall height sourced, other dimensions estimated. Landscape is illustrative.'
scene['references']='Stanford University Architect; Hoover Institution 80th anniversary; Wikimedia east face (BrokenSphere).'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Hoover_Tower_Stanford.blend'))
print(json.dumps({'saved':bpy.data.filepath,'objects':len(bpy.data.objects),'mesh_vertices':sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'),'tiles':bpy.data.objects['Dome · overlapping scalloped clay tiles']['individual_tiles']}))
