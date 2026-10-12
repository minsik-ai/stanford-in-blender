"""Stanford Gates Computer Science Building: photo-informed exterior in metres.
Reference geometry follows RAMSA's south / southeast photograph and portal closeup.
Run: Blender --background --python scripts/build_gates.py. No rendering in builder.
"""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
from math import pi, sin, cos, sqrt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from campus_common import setup_lighting, configure_viewport, import_plant
random.seed(1996)
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob,do_unlink=True)
for col in list(bpy.data.collections): bpy.data.collections.remove(col)
COLS={}
for n in ['01 · Gates architecture','02 · Rusticated limestone','03 · Industrial steel windows','04 · Terracotta roofs','05 · Entrance and identity','06 · Campus landscape','07 · Cameras and daylight']:
 c=bpy.data.collections.new(n); bpy.context.scene.collection.children.link(c); COLS[n]=c
COL=COLS['01 · Gates architecture']
def mat(name,color,rough=.7,metal=0,texture=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 nt=m.node_tree;b=nt.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
 if texture:
  t=nt.nodes.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=2.8;t.inputs['Detail'].default_value=3
  tc=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(tc.outputs['Object'],t.inputs['Vector']);r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(*[v*.86 for v in color],1);r.color_ramp.elements[1].color=(*[min(v*1.08,1) for v in color],1);nt.links.new(t.outputs['Fac'],r.inputs[0]);nt.links.new(r.outputs[0],b.inputs['Base Color'])
  fine=nt.nodes.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=52;fine.inputs['Detail'].default_value=3;nt.links.new(tc.outputs['Object'],fine.inputs['Vector']);bu=nt.nodes.new('ShaderNodeBump');bu.inputs['Strength'].default_value=.28;bu.inputs['Distance'].default_value=.035;nt.links.new(fine.outputs['Fac'],bu.inputs['Height']);nt.links.new(bu.outputs[0],b.inputs['Normal'])
 return m
CREAM=mat('Gates · warm buff limestone',(.70,.624,.482),texture=True)
TRIM=mat('Gates · pale limestone trim',(.76,.685,.546),texture=True)
MORTAR=mat('Gates · stone joint warm shadow',(.455,.391,.283),texture=True)
STONES=[mat('Gates · split-face limestone %02d'%i,(.485+i*.017,.359+i*.015,.219+i*.012),texture=True) for i in range(7)]
GREEN=mat('Gates · deep green industrial steel',(.026,.076,.066),.37,.5)
GLASSES=[mat('Gates · reflective blue glass %02d'%i,(.043+i*.007,.112+i*.009,.142+i*.01),.19,.38) for i in range(5)]
SHADOW=mat('Gates · interior shadow',(.025,.032,.030),.95)
BRONZE=mat('Gates · bronze accents',(.24,.157,.071),.44,.7)
ROOFTILES=[mat('Gates · terracotta tile %02d'%i,(.32+i*.024,.074+i*.008,.036+i*.004),.74,texture=True) for i in range(9)]
PAVE=mat('Campus · pale warm paving',(.48,.43,.35),texture=True)
GRASS=mat('Campus · lawn',(.12,.22,.067),texture=True)
MULCH=mat('Campus · garden soil',(.12,.076,.039),texture=True)
BARK=mat('Campus · bark',(.18,.11,.054),texture=True)
LEAVES=[mat('Campus · foliage %02d'%i,(.060+i*.016,.13+i*.016,.032+i*.009),texture=True) for i in range(5)]
WOOD=mat('Campus · bench cedar',(.31,.15,.054),texture=True)
WHITE=mat('Campus · opal globe glass',(.88,.88,.75),.28)
def mesh(name,verts,faces,material,collection=None,smooth=False):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);(collection or COL).objects.link(ob)
 if material:me.materials.append(material)
 for p in me.polygons:p.use_smooth=smooth
 return ob
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def boxverts(loc,size,angle=0):
 x,y,z=loc;w,d,h=size
 return [(x+u*w/2*cos(angle)-v*d/2*sin(angle),y+u*w/2*sin(angle)+v*d/2*cos(angle),z+t*h/2) for u,v,t in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
def box(name,loc,size,material,angle=0,edge=.025):
 ob=mesh(name,boxverts(loc,size,angle),FACES,material)
 if edge:
  b=ob.modifiers.new('Minute softened edges','BEVEL');b.width=edge;b.segments=2
 return ob
class Batch:
 def __init__(self,name,mats,col=None):self.name=name;self.mats=mats;self.col=col or COL;self.v=[];self.f=[];self.mi=[]
 def mesh(self,v,f,mi=0):
  k=len(self.v);self.v.extend(v);self.f.extend(tuple(k+x for x in face) for face in f);self.mi.extend([mi]*len(f))
 def box(self,p,s,mi=0,a=0):self.mesh(boxverts(p,s,a),FACES,mi)
 def done(self):
  if not self.v:return None
  ob=mesh(self.name,self.v,self.f,None,self.col)
  for m in self.mats:ob.data.materials.append(m)
  for p,i in zip(ob.data.polygons,self.mi):p.material_index=i
  return ob
BATCHES={}
def batch(key,mats,col=None):
 if key not in BATCHES:BATCHES[key]=Batch(key,mats,col)
 return BATCHES[key]
def line(name,points,radius,material,cyclic=False):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=radius;c.bevel_resolution=2;s=c.splines.new('POLY');s.points.add(len(points)-1)
 for p,v in zip(s.points,points):p.co=(*v,1)
 s.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,c);COL.objects.link(o);c.materials.append(material);return o
def sphere(name,loc,scale,material,sub=2):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale
 for c in list(o.users_collection):c.objects.unlink(o)
 COL.objects.link(o);o.data.materials.append(material)
 for p in o.data.polygons:p.use_smooth=True
 return o
# Position local facade geometry: positive Y points into the building.
def frame(origin,angle):
 ox,oy=origin;u=Vector((cos(angle),sin(angle),0));n=Vector((-sin(angle),cos(angle),0))
 def pt(x,y,z):return Vector((ox,oy,z))+u*x+n*y
 return pt
architecture=batch('Masonry · wall panels and deep reveals',[CREAM,TRIM,MORTAR],COL)
stonebatch=batch('Rusticated ashlar · individually coursed stones',STONES,COLS['02 · Rusticated limestone'])
windowbatch=batch('Steel windows · mullions transoms and spandrels',[GREEN],COLS['03 · Industrial steel windows'])
glassbatch=batch('Recessed glass · varied panes',GLASSES,COLS['03 · Industrial steel windows'])
darkbatch=batch('Dark interiors behind exterior openings',[SHADOW],COL)
def fbox(B,pt,a,x,y,z,w,d,h,mi=0):B.box(pt(x,y,z),(w,d,h),mi,a)
def rough_stone_box(p,size,a=0):
 # A softly irregular split face is modeled, with shallow fractured facets.
 # Rear and sides remain square; the front relief never overwhelms the joints.
 w,d,h=size;pt=frame((p[0],p[1]),a);z=p[2];v=[]
 nx,nz=4,3
 for iz in range(nz):
  for ix in range(nx):
   xx=-w/2+w*ix/(nx-1);zz=-h/2+h*iz/(nz-1)
   raised=random.uniform(.006,.025) if ix in [0,nx-1] or iz in [0,nz-1] else random.uniform(.035,.075)
   v.append(pt(xx,-d/2-raised,z+zz))
 v.extend([pt(-w/2,d/2,z-h/2),pt(w/2,d/2,z-h/2),pt(w/2,d/2,z+h/2),pt(-w/2,d/2,z+h/2)])
 f=[]
 for iz in range(nz-1):
  for ix in range(nx-1):
   k=iz*nx+ix;f.extend([(k,k+1,k+nx+1),(k,k+nx+1,k+nx)])
 f.extend([(12,15,14,13),(0,12,13,3),(8,11,14,15),(0,4,8,15,12),(3,13,14,11,7)])
 stonebatch.mesh(v,f,random.randrange(7))

def stone_patch(pt,a,x0,x1,z0,z1,y=-.055):
 # Lower walls have hand-sized staggered rusticated units, not a flat brick texture.
 course=.37;rows=max(1,round((z1-z0)/course));hh=(z1-z0)/rows
 for row in range(rows):
  x=x0;first=.80 if row%2 else 1.45
  while x<x1-.03:
   w=min(first if x==x0 else random.uniform(1.15,1.65),x1-x)
   if w>.035:
    p=pt(x+w/2,y-random.uniform(.004,.025),z0+(row+.5)*hh)
    rough_stone_box(p,(w-.021,.11+random.uniform(0,.03),hh-.021),a)
   x+=w

def panel(pt,a,x0,x1,z0,z1,rust=False):
 if x1<=x0 or z1<=z0:return
 fbox(architecture,pt,a,(x0+x1)/2,.31,(z0+z1)/2,x1-x0,.62,z1-z0,2 if rust else 0)
 if rust:stone_patch(pt,a,x0,x1,z0,z1)

def win(pt,a,x,z,w,h,upper=False):
 # Glazing is deeply behind the actual wall opening and surrounded by full stone reveals.
 fbox(darkbatch,pt,a,x,.59,z,w,.10,h)
 fbox(glassbatch,pt,a,x,.48,z,w-.10,.035,h-.10,random.randrange(5))
 for sx in [-1,1]:fbox(windowbatch,pt,a,x+sx*(w/2-.045),.40,z,.09,.12,h)
 for sz in [-1,1]:fbox(windowbatch,pt,a,x,.40,z+sz*(h/2-.045),w,.12,.09)
 for xx in [-w/6,w/6] if w>2.3 else [0]:fbox(windowbatch,pt,a,x+xx,.395,z,.055,.12,h)
 transoms=[-.24*h,.27*h] if upper else [.25*h]
 for dz in transoms:fbox(windowbatch,pt,a,x,.386,z+dz,w,.13,.065)
 fbox(architecture,pt,a,x,-.07,z-h/2-.045,w+.20,.30,.09,1)
 if upper:
  # Operable lower steel casement handles.
  fbox(windowbatch,pt,a,x+w/6+.13,.31,z-.17,.025,.08,.19)

def standard_bay(pt,a,x,w=4.15):
 # Four visible storeys: ground, small second-storey, two tall glazed upper levels.
 openings=[(2.36,2.46,2.67),(8.65,1.86,2.73),(14.25,3.94,3.13),(18.83,3.56,3.13)]
 for z,h,ww in openings:
  rust=z<10
  panel(pt,a,x-w/2,x-ww/2,z-h/2,z+h/2,rust)
  panel(pt,a,x+ww/2,x+w/2,z-h/2,z+h/2,rust)
  win(pt,a,x,z,ww,h,upper=z>11)
 spans=[(.42,1.13),(3.59,7.72),(9.58,12.28),(20.61,21.83)]
 for low,high in spans:panel(pt,a,x-w/2,x+w/2,low,high,high<10)
 # Recessed blind stone panel in the broad ground-floor spandrel.
 fbox(architecture,pt,a,x,-.079,5.55,w-.7,.08,1.14,1)
 for z in [4.38,6.65,9.82]:fbox(architecture,pt,a,x,-.13,z,w,.26,.14,1)
 # Stone side piers continue around the recessed green steel spandrel.
 for x0,x1 in [(x-w/2,x-3.13/2),(x+3.13/2,x+w/2)]:panel(pt,a,x0,x1,16.22,17.05)
 # Dark steel band links paired upper storeys, visible as photographs' green panels.
 fbox(windowbatch,pt,a,x,.39,16.63,3.13,.14,.81)
 fbox(windowbatch,pt,a,x,.28,16.33,3.21,.23,.09)
 fbox(windowbatch,pt,a,x,.28,16.98,3.21,.23,.09)
 for zz in [16.47,16.8]:fbox(windowbatch,pt,a,x,.26,zz,3.00,.08,.025)

# Structural floor plates follow the chamfered / rounded southeast corner.
foot=[(-35,-20),(21,-20)]+[(21+9*cos(t),-11+9*sin(t)) for t in [-pi/2+i*pi/2/18 for i in range(1,19)]]+[(30,22),(-35,22)]
def plate(name,poly,z,th,material):
 n=len(poly);v=[(x,y,zz) for zz in [z-th/2,z+th/2] for x,y in poly];f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return mesh(name,v,f,material)
plate('Gates · limestone foundation',foot,.19,.38,TRIM)
for z in [4.5,10.2,16.65,21.7]:plate('Internal floor plate %.1f'%z,[(x*.970,y*.970) for x,y in foot],z,.22,SHADOW)
# Front (south) elevation: the arch deliberately sits to the right of center.
front=frame((0,-20),0)
for x in [-32.775,-28.325,-23.875,-19.425,-14.975,-10.525]:standard_bay(front,0,x,4.45)
# Portal masonry x -8.3..7.7. Arch centre -0.3, diameter 8.4m.
AX=-.3;RI=4.60;SPRING=11.05;ARCHTOP=SPRING+RI
for x in [11.05,16.7]:standard_bay(front,0,x,5.65)
# Main entrance portal sides and real arched opening.
panel(front,0,19.525,21,.42,10.1,True);panel(front,0,19.525,21,10.1,21.83)
for x0,x1 in [(-8.3,AX-RI),(AX+RI,8.225)]:
 panel(front,0,x0,x1,.42,10.1,True);panel(front,0,x0,x1,10.1,17.55)
# Door, nameplate, and portal's lower glazed strip.
panel(front,0,AX-RI,AX-2.65,.42,4.3,True);panel(front,0,AX+2.65,AX+RI,.42,4.3,True)
panel(front,0,AX-RI,AX+RI,4.3,7.55,True)
win(front,0,AX,2.31,5.30,3.80)
for x in [AX-.72,AX+.72]:
 fbox(windowbatch,front,0,x,.26,2.28,.045,.1,3.40)
 fbox(windowbatch,front,0,x+.12,.22,2.08,.055,.12,.47)
# Lower rectangle and round head glazing.
win(front,0,AX,9.29,RI*2,3.47)
verts=[front(AX-RI,.48,SPRING),front(AX+RI,.48,SPRING)]+[front(AX+RI*cos(t),.48,SPRING+RI*sin(t)) for t in [i*pi/64 for i in range(65)]]
glassbatch.mesh(verts,[tuple(range(len(verts)))],2)
for off in [-3.2,-2.1,-1.05,0,1.05,2.1,3.2]:
 h=sqrt(RI*RI-off*off);fbox(windowbatch,front,0,AX+off,.39,SPRING+h/2,.075,.14,h)
# Arch wall spandrel, top with three deeply shadowed terrace windows.
for i in range(64):
 a=pi-pi*i/64;b=pi-pi*(i+1)/64;xa=AX+RI*cos(a);xb=AX+RI*cos(b);za=SPRING+RI*sin(a);zb=SPRING+RI*sin(b)
 v=[front(x,y,z) for y in [0,.65] for x,z in [(xa,za),(xb,zb),(xb,17.55),(xa,17.55)]];architecture.mesh(v,FACES,0)
for x in [-5.85,AX,5.25]:
 ww=3.5 if x!=AX else 5.05
 win(front,0,x,19.25,ww,2.95)
# Partition the complete opening surround into disjoint cells. Overlapping header
# and pier faces on the same plane caused black ray-intersection artifacts.
for x0,x1 in [(-8.3,-7.6),(-4.1,-2.825),(2.225,3.5),(7,8.225)]:panel(front,0,x0,x1,17.775,20.725)
panel(front,0,-8.3,8.225,17.55,17.775)
panel(front,0,-8.3,8.225,20.725,21.83)
# Two concentric rings, with real wedge-shaped split-faced voussoirs.
COL=COLS['05 · Entrance and identity']
for j in range(35):
 t0=j*pi/35+.002;t1=(j+1)*pi/35-.002
 for r0,r1,yy in [(RI,RI+1.04,-.14),(RI+1.04,RI+1.38,-.09)]:
  v=[front(AX+r*cos(t),y,SPRING+r*sin(t)) for y in [yy-.14,yy+.18] for r,t in [(r0,t0),(r1,t0),(r1,t1),(r0,t1)]]
  center=sum((Vector(q) for q in v[:4]),Vector())/4;center.y-=random.uniform(.003,.009);v.append(center)
  stonebatch.mesh(v,[(0,3,8),(3,2,8),(2,1,8),(1,0,8)]+FACES[1:],random.randrange(7))
for x0,x1 in [(AX-RI-1.04,AX-RI),(AX+RI,AX+RI+1.04)]:stone_patch(front,0,x0,x1,7.55,SPRING,-.23)
# Actual modest incised-style text at the entry, not an oversized presentation label.
box('Entrance · carved dedication tablet',(AX,-20.19,5.88),(6.3,.15,1.42),TRIM,edge=.018)
def text(name,body,loc,size,material,rotation=(pi/2,0,0)):
 c=bpy.data.curves.new(name,'FONT');c.body=body;c.align_x='CENTER';c.align_y='CENTER';c.size=size;c.extrude=.005;c.bevel_depth=.001;c.space_character=1.15;o=bpy.data.objects.new(name,c);COL.objects.link(o);o.location=loc;o.rotation_euler=rotation;c.materials.append(material);return o
text('Entry · William Gates','WILLIAM GATES',(AX,-20.279,6.12),.32,BRONZE)
text('Entry · Computer Science','COMPUTER SCIENCE',(AX,-20.279,5.62),.32,BRONZE)
for i in range(3):box('South entrance · shallow step',(AX,-20.75-i*.46,.30-i*.08),(11.2,.9,.16),TRIM,edge=.025)
# Side and rear wings keep fully modeled window reveals and frames.
COL=COLS['01 · Gates architecture']
for orig,a,length,count in [((30,5.5),pi/2,33,8),((-2.5,22),pi,65,15),((-35,1),-pi/2,42,10)]:
 pt=frame(orig,a);w=length/count
 for j in range(count):standard_bay(pt,a,-length/2+(j+.5)*w,w)
# Rounded southeast corner with two monumental bays around the quarter-circle.
# Short curved masonry strips keep the corner's silhouette smooth and the glazing planar.
center=Vector((21,-11,0));rad=9
round_arch=batch('Rounded corner · smooth limestone bands',[CREAM,TRIM,MORTAR],COL)
def curved_strip(name,z0,z1,r0,r1,t0=-pi/2,t1=0,material=CREAM):
 n=max(8,round((t1-t0)*36));v=[];f=[]
 for zz in [z0,z1]:
  for rr in [r0,r1]:
   for j in range(n+1):
    t=t0+(t1-t0)*j/n;v.append((21+rr*cos(t),-11+rr*sin(t),zz))
 L=n+1
 for j in range(n):f.extend([(j,j+1,2*L+j+1,2*L+j),(L+j,3*L+j,3*L+j+1,L+j+1),(j,L+j,L+j+1,j+1),(2*L+j,2*L+j+1,3*L+j+1,3*L+j)])
 return mesh(name,v,f,material)
for z0,z1 in [(.42,.8),(4.3,7.65),(9.65,12.25),(20.61,21.83)]:curved_strip('Rounded corner · horizontal limestone courses',z0,z1,8.35,9,material=MORTAR if z1<10 else CREAM)
for z in [4.34,6.7,9.84]:curved_strip('Rounded corner · projecting belt course',z-.07,z+.07,8.85,9.14,material=TRIM)
for t0,t1 in [(-pi/2,-1.38),(-.94,-.64),(-.20,0)]:curved_strip('Rounded corner · full-height stone pier',.42,21.83,8.3,9,t0,t1)
for t in [-1.16,-.42]:
 angle=t+pi/2;p=(21+9*cos(t),-11+9*sin(t));pt=frame(p,angle)
 for z,h,w in [(8.65,2,3.10),(14.25,3.94,3.5),(18.85,3.50,3.5)]:win(pt,angle,0,z,w,h,z>10)
 for dz in [16.30,16.62,16.99]:fbox(windowbatch,pt,angle,0,.36,dz,3.50,.20,.10 if dz!=16.62 else .7)
 # Square framed blind panel beneath the second-storey casement.
 fbox(architecture,pt,angle,0,-.015,5.65,3.75,.18,1.36,1)
# The rounded corner's open loggia reveals a second entrance behind deep masonry.
for t0,t1 in [(-pi/2,-1.38),(-.94,-.64),(-.20,0)]:
 curved_strip('Corner loggia · deep stone reveal',.42,4.3,7.2,9,t0,t1,material=STONES[3])
for t in [-1.16,-.42]:
 angle=t+pi/2;pt=frame((21+9*cos(t),-11+9*sin(t)),angle)
 fbox(darkbatch,pt,angle,0,2.00,2.37,4.05,.15,3.94)
 fbox(architecture,pt,angle,0,.85,.46,4.10,2.2,.16,1)
 fbox(architecture,pt,angle,0,.9,4.22,4.05,2.0,.16,1)
 # Rear glass doors and their green frames are visibly deeper than ordinary windows.
 dp=frame(pt(0,1.2,0)[:2],angle)
 win(dp,angle,0,2.21,3.02,3.40)
 fbox(windowbatch,dp,angle,0,.35,2.21,.065,.14,3.40)
 for xx in [-.14,.14]:fbox(windowbatch,dp,angle,xx,.21,2.03,.044,.12,.40)
 # Broad shallow stair and slim steel railings lead into the open corner loggia.
 for j in range(4):
  fbox(architecture,pt,angle,0,-.36-j*.36,.34-j*.085,4.75,.72,.17,1)
 for xx in [-2.25,2.25]:
  hand=[]
  for j in [0,3]:
   yy=-.35-j*.36;zz=1.23-j*.085
   line('Corner loggia · rail post',[pt(xx,yy,zz-.89),pt(xx,yy,zz)],.025,GREEN)
   hand.append(pt(xx,yy,zz))
  line('Corner loggia · sloping handrail',hand,.032,GREEN)
 # A continuous steel spandrel links the paired upper-storey window stack.
 curved_strip('Corner · curved green window spandrel',16.20,17.10,8.40,8.61,t-.205,t+.205,material=GREEN)
 for t0,t1 in [(t-.22,t-.205),(t+.205,t+.22)]:curved_strip('Corner · narrow spandrel reveal',16.20,17.10,8.35,9,t0,t1)
# Small stonework blocks follow the curved skin and respect glazing openings.
for row in range(26):
 z=.45+(row+.5)*.368
 for j in range(25):
  t=-pi/2+(j+.5)*pi/2/25
  in_bay=any(abs(t-a)<.22 for a in [-1.16,-.42])
  if in_bay and ((.8<z<4.3) or (7.65<z<9.65)):continue
  if not in_bay or 4.3<z<7.65:
   a=t+pi/2;rough_stone_box((21+9.04*cos(t),-11+9.04*sin(t),z),(.546,.12,.343),a)
# Deep roof overhang and dark stained timber brackets.
fascia=batch('Roof · dark soffit fascia and exposed brackets',[GREEN],COLS['04 · Terracotta roofs'])
for orig,a,length,count in [((-7,-20.05),0,56,34),((30.05,5.5),pi/2,33,21),((-2.5,22.05),pi,65,38),((-35.05,1),-pi/2,42,25)]:
 pt=frame(orig,a);fbox(fascia,pt,a,0,-.58,21.92,length+1.3,1.58,.22)
 for j in range(count):
  x=-length/2+(j+.5)*length/count
  fbox(fascia,pt,a,x,-.37,21.59,.18,1.20,.38)
curved_strip('Rounded corner · overhanging eave',21.80,22.06,8.6,10.25,material=GREEN)
# Terracotta roof: thousands of separately colored overlapping barrel tiles.
COL=COLS['04 · Terracotta roofs']
tilebatch=Batch('Roof · individually modeled overlapping clay barrel tiles',ROOFTILES,COL)
tile_count=0
def tiled_panel(name,outerA,outerB,innerB,innerA):
 global tile_count
 A,B,C,D=map(Vector,[outerA,outerB,innerB,innerA]);normal=(B-A).cross(D-A).normalized()
 if normal.z<0:normal=-normal
 mesh(name+' · roof substrate',[A,B,C,D],[(0,1,2,3)],ROOFTILES[2])
 length=((D-A).length+(C-B).length)/2;rows=max(1,round(length/.49))
 for row in range(rows):
  t0=row/rows;t1=min(1,(row+1.14)/rows)
  left=A.lerp(D,t0);right=B.lerp(C,t0);left2=A.lerp(D,t1);right2=B.lerp(C,t1)
  count=max(1,round((right-left).length/.325))
  for j in range(count):
   verts=[]
   for L,R in [(left,right),(left2,right2)]:
    for q in range(6):
     f=(j+.04+.92*q/5)/count;P=L.lerp(R,f)+normal*(.032+.082*sin(pi*q/5));verts.append(P)
   faces=[(q,q+1,6+q+1,6+q) for q in range(5)]
   tilebatch.mesh(verts,faces,random.choices(range(9),weights=[1,2,3,6,8,7,5,3,1])[0]);tile_count+=1
# The broad roof has a low unobtrusive flat well behind the visible tiled perimeter.
tiled_panel('South roof',(-36.1,-21.2,22.10),(21,-21.2,22.10),(21,-10,25.45),(-25,-10,25.45))
tiled_panel('West roof',(-36.1,23.1,22.10),(-36.1,-21.2,22.10),(-25,-10,25.45),(-25,12,25.45))
tiled_panel('North roof',(31.1,23.1,22.10),(-36.1,23.1,22.10),(-25,12,25.45),(20,12,25.45))
tiled_panel('East roof',(31.1,-11,22.10),(31.1,23.1,22.10),(20,12,25.45),(20,-10,25.45))
# Fan of tiles sweeps around the recognisable southeast corner, terminating in a glazed skylight.
for j in range(16):
 t0=-pi/2+j*pi/32;t1=t0+pi/32
 tiled_panel('Curved corner roof', (21+10.2*cos(t0),-11+10.2*sin(t0),22.1),(21+10.2*cos(t1),-11+10.2*sin(t1),22.1),(21+.9*cos(t1),-11+.9*sin(t1),25.45),(21+.9*cos(t0),-11+.9*sin(t0),25.45))
box('Roof · recessed flat central well',(-2.5,1,25.28),(45,22,.25),GREEN,edge=0)
# Raised low polygon skylight above the curved circulation corner.
verts=[(21+2.5*cos(2*pi*j/10),-11+2.5*sin(2*pi*j/10),25.5) for j in range(10)]+[(21,-11,26.4)]
mesh('Corner stair · pyramidal blue skylight',verts,[(j,(j+1)%10,10) for j in range(10)],GLASSES[2])
for j in range(10):line('Skylight · metal glazing bar',[verts[j],verts[10]],.033,GREEN)
for p1,p2 in [((-36.1,-21.2,22.2),(-25,-10,25.5)),((-36.1,23.1,22.2),(-25,12,25.5)),((31.1,23.1,22.2),(20,12,25.5))]:line('Roof · terracotta hip cap',[p1,p2],.13,ROOFTILES[5])
for a,b in [((-25,-10,25.5),(21,-10,25.5)),((-25,-10,25.5),(-25,12,25.5)),((-25,12,25.5),(20,12,25.5)),((20,12,25.5),(20,-10,25.5))]:line('Roof · terracotta upper ridge cap',[a,b],.13,ROOFTILES[6])
ob=tilebatch.done();ob['individual_tiles']=tile_count
# Downspouts use the same dark green as the window frames.
for x in [-34.6,-8.55,20.4]:line('South facade · rainwater downpipe',[(x,-20.28,21.65),(x,-20.30,1.0),(x,-20.55,.8)],.07,GREEN)
# Landscape: contained planting, campus paving, bike stands and globe lamps.
COL=COLS['06 · Campus landscape']
box('Campus · continuous ground',(0,0,-.15),(1800,1800,.18),GRASS,edge=0)
box('Campus · building plaza',(-1,-1,-.025),(91,66,.14),PAVE,edge=.05)
# Smooth circulation band in front, fine expansion joints at a credible human scale.
joints=batch('Campus · paving expansion joints',[MORTAR],COL)
for x in range(-45,46,4):joints.box((x,-28,.055),(.015,14,.007))
for y in [-22,-26,-30,-34]:joints.box((0,y,.055),(91,.018,.007))
for x in [-27,-13,13,32]:
 box('Campus · planter rim',(x,-24.7,.35),(7.0,3.3,.60),TRIM,edge=.1)
 box('Campus · planter soil',(x,-24.7,.64),(6.6,2.9,.07),MULCH,edge=.06)
 for k in range(7):sphere('Campus · low mixed shrub',(x-2.8+k*.93,-24.65,.96),(.71,.76,.51),random.choice(LEAVES),2)
# Benches, kept low so the architecture remains readable.
for x,y in [(-20,-29),(19,-29),(-41,8),(36,12)]:
 for i in range(6):box('Campus · bench seat slat',(x,y-.39+i*.155,.69),(2.5,.12,.085),WOOD,edge=.025)
 for i in range(4):box('Campus · bench back slat',(x,y+.46,1.00+i*.14),(2.5,.1,.10),WOOD,edge=.025)
 for dx in [-.94,.94]:
  box('Campus · bench iron leg',(x+dx,y,.37),(.12,.65,.62),GREEN,edge=.02)
  box('Campus · bench upright',(x+dx,y+.48,1.02),(.10,.1,.88),GREEN,edge=.02)
for x in [-35,-17,7,28]:
 for k in range(4):
  xx=x+(k-1.5)*.85
  pts=[(xx,-22.35,.20),(xx,-22.35,1.01)]+[(xx,-22.35+.38*(1-cos(pi*j/12)),1.01+.38*sin(pi*j/12)) for j in range(13)]+[(xx,-21.59,.20)]
  line('Campus · bicycle rack',pts,.035,GREEN)
for x,y in [(-37,-24),(9,-22.1),(27,-23),(34,8),(-40,16)]:
 box('Campus · lamp base',(x,y,.34),(.34,.34,.6),GREEN,edge=.04)
 line('Campus · slender globe lamp',[(x,y,.4),(x,y,3.48)],.065,GREEN)
 sphere('Campus · opal lamp globe',(x,y,3.7),(.27,.27,.29),WHITE,3)
# Trees flank the composition rather than obscuring the arched portal.
for idx,(x,y,height) in enumerate([(-43,-12,9),(39,18,10),(-39,28,10.6),(33,31,11),(-22,31,9)]):
 import_plant('broadleaf',(x,y,0),scale=height/23,collection=COL,angle=idx*1.19)
# Two discreet entry planters and basin refer to the landscaped campus forecourt.
# Landscaping is interpretive; no invented central landmark fountain is added.
for x in [-5.8,5.3]:
 box('Entrance · sandstone planter',(x,-21.5,.38),(2.15,1.45,.7),TRIM,edge=.06)
 sphere('Entrance · clipped myrtle',(x,-21.5,1.05),(1,.62,.58),LEAVES[3],2)
for b in BATCHES.values():b.done()
# Cameras and illumination match the Hoover Tower daylight series.
COL=COLS['07 · Cameras and daylight']
def camera(name,loc,target,lens):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=3000;return o
hero=camera('Camera · Gates architectural portrait',(80,-108,34),(-2,-1,11.4),48)
camera('Camera · Gates entrance craftsmanship',(19,-62,17),(-.3,-18.5,11),55)
camera('Camera · Gates campus overview',(91,-109,79),(-2,1,9),53)
scene=bpy.context.scene;scene.camera=hero;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=96;scene.cycles.use_denoising=True;scene.cycles.max_bounces=8
scene.render.resolution_x=2400;scene.render.resolution_y=1800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.filepath=str(ROOT/'renders/gates_hero.png')
setup_lighting()
configure_viewport(scene,rendered=False)
source='''GATES COMPUTER SCIENCE BUILDING · STANFORD UNIVERSITY
Photo-informed architectural reconstruction, 2026. Estimated metres; not a surveyed or construction model.
Primary visual references:
https://www.ramsa.com/expertise/project/gates-computer-science-building
https://www.ramsa.com/sites/default/files/92014-ESTO-96A16.104.psd__0.jpg
https://www.ramsa.com/sites/default/files/92014-ESTO-96A16.107.jpg
https://www.fca-arch.com/education/gates-computer-building
https://www.cs.stanford.edu/contact-us
Recognisable features: four visible storeys, asymmetrical south portal, rough lower limestone courses, smooth upper limestone, tall green industrial window bays, southeast rounded stair volume, low red clay roofs and corner skylight.
Dimensions, less-photographed rear elevations, roof well, interior slabs and grounds are approximate. Original photographs are only reference; no photo textures are embedded.
Viewing: use Rendered viewport shading for full sun shadows and scene sky, or F12 for the final camera render.
'''
t=bpy.data.texts.new('README · references and viewing');t.write(source)
scene['project']='Gates Computer Science Building · Stanford University';scene['references']='RAMSA; Fong & Chan Architects; Stanford Computer Science';scene['reconstruction_note']='Photo-informed exterior. Estimated dimensions, rear elevations and landscaping.';scene['roof_tile_count']=tile_count
for ob in bpy.context.selected_objects:ob.select_set(False)
(ROOT/'renders').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Gates_Computer_Science_Stanford.blend'))
print(json.dumps({'saved':bpy.data.filepath,'objects':len(bpy.data.objects),'vertices':sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'),'roof_tiles':tile_count}))
