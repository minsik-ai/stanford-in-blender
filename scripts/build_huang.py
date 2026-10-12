"""Photo-informed Jen-Hsun Huang Engineering Center, Stanford University.
All geometry in estimated metres. Run in background Blender; this script never renders.
Primary sources: Stanford Engineering and architect Isaac Campbell / OFFICE 52.
"""
import bpy, sys, math, random, json
from math import pi, sin, cos, sqrt
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from campus_common import setup_lighting, camera, configure_viewport, import_plant, bench
random.seed(2010)
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
COLS={}
for name in ['01 · Huang octagonal pavilion','02 · Teaching wing and arcade','03 · Red steel and glazing','04 · Tiled solar roof and monitors','05 · Sunken terrace and landscape','06 · Furniture and identity','90 · Cameras & lighting']:
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);COLS[name]=c
COL=COLS['01 · Huang octagonal pavilion']

def mat(name,color,rough=.7,metal=0,texture=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
 if texture:
  n=m.node_tree.nodes;l=m.node_tree.links;tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.5;noise.inputs['Detail'].default_value=3;l.new(tc.outputs['Object'],noise.inputs['Vector']);r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(*[v*.94 for v in color],1);r.color_ramp.elements[1].color=(*[min(v*1.04,1) for v in color],1);l.new(noise.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],b.inputs['Base Color']);fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=95;fine.inputs['Detail'].default_value=2;l.new(tc.outputs['Object'],fine.inputs['Vector']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.014;l.new(fine.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
 return m
STONE=[mat('Huang · honed limestone %02d'%i,(.60+i*.011,.54+i*.010,.432+i*.009),texture=True) for i in range(7)]
CORE=mat('Huang · limestone joints',(.49,.454,.374),texture=True)
TRIM=mat('Huang · pale concrete coping',(.63,.63,.584),texture=True)
BASE=mat('Huang · gray concrete plinth',(.36,.375,.352),texture=True)
RED=mat('Huang · terracotta red steel',(.245,.070,.043),.42,.45)
FRAME=mat('Huang · charcoal window frame',(.037,.047,.045),.36,.58)
STEEL=mat('Huang · stainless steel rails',(.25,.28,.27),.30,.72)
GLASS=[mat('Huang · blue green glazing %02d'%i,(.047+i*.006,.101+i*.012,.132+i*.012),.20,.43) for i in range(5)]
SHADOW=mat('Huang · shaded interior',(.026,.033,.032),.94)
WOOD=mat('Huang · soffit cedar',(.265,.139,.064),texture=True)
ROOF=[mat('Huang · clay roof tile %02d'%i,(.30+i*.022,.069+i*.008,.033+i*.004),.76,texture=True) for i in range(9)]
PV=mat('Huang · photovoltaic deep blue cells',(.015,.036,.080),.20,.40)
PVCELL=mat('Huang · photovoltaic cell dividers',(.19,.235,.29),.34,.6)
PAVE=[mat('Campus · sandstone pavers %02d'%i,(.445+i*.008,.413+i*.008,.353+i*.008),texture=True) for i in range(6)]
GRASS=mat('Campus · clipped lawn',(.10,.208,.056),texture=True)
MULCH=mat('Campus · planted soil',(.105,.063,.031),texture=True)
LEAVES=[mat('Campus · small leaf %02d'%i,(.068+i*.015,.123+i*.021,.028+i*.008),texture=True) for i in range(5)]
FLOWERS=[mat('Campus · flower lavender',(.245,.148,.282)),mat('Campus · flower yellow',(.60,.42,.074)),mat('Campus · flower salmon',(.49,.19,.12))]
CANVAS=mat('Cafe · ivory umbrella cloth',(.77,.755,.685),.88)
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def mesh(name,v,f,m=None,col=None,smooth=False):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);(col or COL).objects.link(o)
 if m:me.materials.append(m)
 if smooth:
  for p in me.polygons:p.use_smooth=True
 return o

def boxverts(p,s,a=0):
 x,y,z=p;w,d,h=s
 return [(x+u*w/2*cos(a)-v*d/2*sin(a),y+u*w/2*sin(a)+v*d/2*cos(a),z+t*h/2) for u,v,t in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
def box(name,p,s,m,a=0,edge=.02):
 o=mesh(name,boxverts(p,s,a),FACES,m)
 if edge:b=o.modifiers.new('Soft edges','BEVEL');b.width=edge;b.segments=2
 return o
class Batch:
 def __init__(self,name,mats,col):self.name=name;self.mats=mats;self.col=col;self.v=[];self.f=[];self.ids=[]
 def mesh(self,v,f,mi=0):
  k=len(self.v);self.v.extend(v);self.f.extend([tuple(k+i for i in q) for q in f]);self.ids.extend([mi]*len(f))
 def box(self,p,s,a=0,mi=0):self.mesh(boxverts(p,s,a),FACES,mi)
 def finish(self):
  if not self.v:return
  o=mesh(self.name,self.v,self.f,None,self.col)
  for m in self.mats:o.data.materials.append(m)
  for p,i in zip(o.data.polygons,self.ids):p.material_index=i
  return o
B=[]
def batch(name,mats,col=None):b=Batch(name,mats,col or COL);B.append(b);return b
C=batch('Masonry · core panels',[CORE,TRIM,BASE]);S=batch('Limestone · individually coursed ashlar',STONE)
W=batch('Metal · window profiles and red steel',[FRAME,RED,STEEL],COLS['03 · Red steel and glazing'])
G=batch('Glass · separate reflective panes',GLASS,COLS['03 · Red steel and glazing'])
D=batch('Interior · shadow behind deep openings',[SHADOW]);R=batch('Roof · steel and cedar structure',[RED,WOOD,FRAME],COLS['04 · Tiled solar roof and monitors'])

def frame(p,a):
 px,py=p
 return lambda x,y,z:Vector((px+x*cos(a)-y*sin(a),py+x*sin(a)+y*cos(a),z))
def fb(b,pt,a,x,y,z,w,d,h,mi=0):b.box(pt(x,y,z),(w,d,h),a,mi)
def line(name,points,r,m,col=None,cyclic=False):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=r;c.bevel_resolution=1;sp=c.splines.new('POLY');sp.points.add(len(points)-1)
 for p,q in zip(sp.points,points):p.co=(*q,1)
 sp.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,c);(col or COL).objects.link(o);c.materials.append(m);return o

def ashlar(pt,a,x0,x1,z0,z1,y=-.042):
 if x1-x0<.015 or z1-z0<.015:return
 n=max(1,round((z1-z0)/.42));hh=(z1-z0)/n
 for k in range(n):
  xx=x0
  while xx<x1-.01:
   ww=min(.50 if xx==x0 and k%2 else random.uniform(.85,1.2),x1-xx)
   if ww>.02:fb(S,pt,a,xx+ww/2,y,z0+(k+.5)*hh,ww-.009,.068,hh-.008,random.randrange(7))
   xx+=ww

def panel(pt,a,x0,x1,z0,z1,stone=True,mi=0):
 # Disjoint patches avoid coplanar doubled headers, piers and sills.
 if x1<=x0 or z1<=z0:return
 fb(C,pt,a,(x0+x1)/2,.30,(z0+z1)/2,x1-x0,.58,z1-z0,mi)
 if stone:ashlar(pt,a,x0,x1,z0,z1)

def glazing(pt,a,x,z,w,h,depth=.32,vertical=2,horiz=2,red=True):
 # Panes sit behind the external masonry plane, with true-depth jambs.
 fb(D,pt,a,x,depth+.19,z,w,.07,h)
 for ix in range(vertical):
  for iz in range(horiz):
   ww=w/vertical;hh=h/horiz
   fb(G,pt,a,x-w/2+(ix+.5)*ww,depth+.065,z-h/2+(iz+.5)*hh,ww-.045,.028,hh-.045,random.randrange(5))
 for ix in range(vertical+1):fb(W,pt,a,x-w/2+ix*w/vertical,depth-.015,z,.065,.15,h,1 if red and ix in [0,vertical] else 0)
 for iz in range(horiz+1):fb(W,pt,a,x,depth-.03,z-h/2+iz*h/horiz,w,.15,.065,1 if red and iz in [0,horiz] else 0)

# Shallow segmental arch, characteristic of this modern Stanford building.
def arch_z(x,rise,half,spring):
 rr=(half*half+rise*rise)/(2*rise);return spring+rise-rr+sqrt(max(0,rr*rr-x*x))
def shallow_arch(pt,a,width,bottom,spring,half,rise,top,name):
 panel(pt,a,-width/2,-half,bottom,top);panel(pt,a,half,width/2,bottom,top)
 n=40;vv=[];ff=[]
 for j in range(n):
  x0=-half+j*2*half/n;x1=-half+(j+1)*2*half/n;z0=arch_z(x0,rise,half,spring);z1=arch_z(x1,rise,half,spring);start=len(vv)
  vv.extend([pt(x,y,z) for y in [.005,.60] for x,z in [(x0,z0),(x1,z1),(x1,top),(x0,top)]])
  ff.extend([tuple(start+i for i in f) for f in FACES])
 mesh(name+' · stone spandrel',vv,ff,STONE[3])
 # Unbroken gray arch band, without decorative pointed wedge relief.
 v=[];f=[]
 for j in range(n+1):
  x=-half+2*half*j/n;zz=arch_z(x,rise,half,spring)
  v.extend([pt(x,-.081,zz),pt(x,-.081,zz+.24),pt(x,.12,zz),pt(x,.12,zz+.24)])
 for j in range(n):
  k=j*4;f.extend([(k,k+4,k+5,k+1),(k,k+2,k+6,k+4),(k+1,k+5,k+7,k+3)])
 mesh(name+' · segmental concrete archivolt',v,f,TRIM)
 # Stone coursing on the arched spandrel is represented by very fine inlaid joints.
 for zz in [spring+rise+.30,spring+rise+.72,top-.14]:
  if zz<top:line(name+' · horizontal stone joint',[pt(-half,-.012,zz),pt(half,-.012,zz)],.0035,CORE)

def rail(pt,a,x0,x1,y,z,length_posts=None):
 count=max(2,round((x1-x0)/1.6)+1)
 for j in range(count):fb(W,pt,a,x0+(x1-x0)*j/(count-1),y,z+.54,.042,.046,1.08,2)
 for j in range(9):fb(W,pt,a,(x0+x1)/2,y,z+.12+j*.115,x1-x0,.027,.027,2)
 fb(W,pt,a,(x0+x1)/2,y,z+1.1,x1-x0,.060,.047,2)

def ngon_slab(name,cx,cy,ap,z,h,m):
 rr=ap/cos(pi/8);poly=[(cx+rr*cos(pi/8+j*pi/4),cy+rr*sin(pi/8+j*pi/4)) for j in range(8)];v=[(x,y,zz) for zz in [z-h/2,z+h/2] for x,y in poly];f=[tuple(range(7,-1,-1)),tuple(range(8,16))]+[(j,(j+1)%8,(j+1)%8+8,j+8) for j in range(8)];return mesh(name,v,f,m)
# OCTAGONAL PAVILION. Top is flat, as built; the red roof belongs to the wing.
CX,CY=-17,-13;AP=11.7;SIDE=2*AP*math.tan(pi/8)
ngon_slab('Rotunda · pale flat roof',CX,CY,AP,20.22,.26,TRIM)
ngon_slab('Rotunda · recessed roof membrane',CX,CY,AP-.38,20.39,.04,TRIM)
for zz in [0.22,6.5,12.87,19.87]:ngon_slab('Rotunda · internal floor',CX,CY,AP-1.0,zz,.20,SHADOW)
for k in range(8):
 a=k*pi/4;pt=frame((CX+AP*sin(a),CY-AP*cos(a)),a)
 # Terrace basement is partially exposed by the modeled sunken court.
 panel(pt,a,-SIDE/2,-3.65,-3.60,.26,False,2);panel(pt,a,3.65,SIDE/2,-3.6,.26,False,2)
 glazing(pt,a,0,-2.03,7.3,2.96,vertical=5,horiz=2)
 panel(pt,a,-3.65,3.65,-.55,.26,False,2)
 if k%2==0:
  for x0,x1 in [(-SIDE/2,-3.73),(3.73,SIDE/2)]:panel(pt,a,x0,x1,.26,12.52)
  panel(pt,a,-3.73,3.73,.26,.42)
  glazing(pt,a,0,6.44,7.46,12.04,depth=.40,vertical=5,horiz=5)
  # Terracotta fins project in front of alternating double-height panes.
  for x in [-2.24,-.75,.75,2.24]:fb(W,pt,a,x,-.11,7.75,.105,.46,9.07,1)
  for z in [3.17,6.35]:fb(W,pt,a,0,.03,z,7.46,.35,.18,1)
  if k==0:
   fb(W,pt,a,0,-.75,.37,7.65,1.80,.36,1);rail(pt,a,-3.8,3.8,-1.60,.57)
   for xx in [-3.8,3.8]:
    rpt=frame(pt(xx,-.75,0)[:2],a+pi/2);rail(rpt,a+pi/2,-.85,.85,0,.57)
 else:
  # Tall slit windows in three parts, surrounded by continuous honed ashlar.
  openings=[(-2.90,1.12),(0,1.12),(2.90,1.12)]
  for z0,z1 in [(.82,5.82),(7.13,12.13)]:
   last=-SIDE/2
   for xx,ww in openings:
    panel(pt,a,last,xx-ww/2,z0,z1);glazing(pt,a,xx,(z0+z1)/2,ww,z1-z0,vertical=1,horiz=3);last=xx+ww/2
   panel(pt,a,last,SIDE/2,z0,z1)
  for z0,z1 in [(.26,.82),(5.82,7.13),(12.13,12.52)]:panel(pt,a,-SIDE/2,SIDE/2,z0,z1)
 # Wide upper loggias: real shallow arch with deep dark space and a cable rail.
 panel(pt,a,-SIDE/2,SIDE/2,12.52,13.23)
 shallow_arch(pt,a,SIDE,13.23,17.87,3.71,.82,20.08,'Rotunda face %02d'%k)
 fb(C,pt,a,0,1.65,13.23,7.45,3.70,.15,1)
 # Deep loggia reveals and an opaque soffit produce the shaded outdoor room.
 # The rear curtain wall sits 3.4m behind the outer limestone face.
 for xx in [-3.84,3.84]:fb(C,pt,a,xx,2.06,16.08,.26,3.0,5.70)
 fb(D,pt,a,0,3.66,16.0,7.70,.18,5.75)
 glazing(pt,a,0,15.56,6.65,4.30,depth=3.42,vertical=5,horiz=3)
 rail(pt,a,-3.64,3.64,.22,13.34)
 # Smooth recessed cedar ceiling: no projecting decorative dentil ends.
 fb(R,pt,a,0,1.98,18.83,7.44,3.10,.14,1)
 fb(C,pt,a,0,-.09,13.26,7.68,.32,.14,1)
 fb(C,pt,a,0,-.018,20.30,SIDE+.04,.68,.18,1)
# Roof equipment is modest and lower than the rotunda parapet sightline.
for xx,yy in [(-20,-9),(-13,-9)]:box('Rotunda · roof service curb',(xx,yy,20.70),(1.2,1.6,.55),TRIM,edge=.04)

# MAIN TEACHING WING: three occupied levels plus the airy roof pavilion.
COL=COLS['02 · Teaching wing and arcade']
# Panels remain fully separated around openings on all four sides.
def main_bay(pt,a,x,w):
 for z0,z1,ww in [(.45,4.16,2.24),(5.75,9.20,1.52),(11.08,14.70,1.52)]:
  panel(pt,a,x-w/2,x-ww/2,z0,z1);panel(pt,a,x+ww/2,x+w/2,z0,z1);glazing(pt,a,x,(z0+z1)/2,ww,z1-z0,depth=.30,vertical=2 if ww>2 else 1,horiz=3)
 for z0,z1 in [(.10,.45),(4.16,5.75),(9.20,11.08),(14.70,16.12)]:panel(pt,a,x-w/2,x+w/2,z0,z1)
 # Cut-stone sills, lintels and tiny projected sunshade at the lower windows.
 for zz in [4.22,9.25,14.75]:fb(C,pt,a,x,-.04,zz,2.00,.30,.10,1)
 if x%8<4:fb(W,pt,a,x,-.55,9.58,w-.2,1.15,.07,2)

# Internal plates are inset beyond all glazing to avoid exposed dark slivers.
for zz in [.04,4.72,10.2,15.98]:box('Teaching wing · floor plate',(18,9.5,zz),(28.8,67.8,.22),SHADOW,edge=0)
facades=[((3,9.5),-pi/2,69,18),((33,9.5),pi/2,69,18),((18,-25),0,30,8),((18,44),pi,30,8)]
for origin,a,length,count in facades:
 pt=frame(origin,a);step=length/count
 for j in range(count):main_bay(pt,a,-length/2+(j+.5)*step,step)
 fb(C,pt,a,0,.22,16.23,length,.80,.18,1)
 # Raised roof's red steel supports and dark horizontal brise-soleil.
 for j in range(count+1):fb(R,pt,a,-length/2+j*step,.26,17.13,.25,.34,1.67,0)
 for zz in [16.65,16.92,17.19,17.46]:fb(R,pt,a,0,.88,zz,length,.07,.12,2)
 fb(R,pt,a,0,.16,17.86,length+.30,.42,.32,0)
# Quad-facing colonnade: true openings with shadowed passage 4.5m behind.
arcade=frame((-2.2,9.5),-pi/2);acount=15;astep=69/acount
for j in range(acount):
 xx=-34.5+(j+.5)*astep;apt=frame(arcade(xx,0,0)[:2],-pi/2)
 shallow_arch(apt,-pi/2,astep,.08,3.50,1.74,.58,4.80,'Quad arcade %02d'%j)
 for side in [-1,1]:fb(C,apt,-pi/2,side*(astep+3.48)/4,.29,.64,(astep-3.48)/2,.66,1.12,2)
# Colonnade return around southern end, visible beside pavilion's glass link.
pt=frame((18,-29.8),0)
for j in range(7):
 apt=frame((3+(j+.5)*30/7,-29.8),0);shallow_arch(apt,0,30/7,.08,3.5,1.58,.58,4.80,'South arcade %02d'%j)
box('Quad colonnade · deep terrace slab',(.25,9.5,4.93),(5.8,69.5,.27),TRIM,edge=.03)
box('South colonnade · terrace slab',(18,-27.4,4.93),(30.1,5.5,.27),TRIM,edge=.03)
rail(arcade,-pi/2,-34.4,34.4,-.16,5.11)
rail(frame((18,-29.8),0),0,-14.95,14.95,-.12,5.11)
# Long timber shade trellis over the terrace, respecting the glazed bridge.
for y0,y1 in [(-3,17),(22,41)]:
 for yy in [y0,y1]:
  for xx in [-1.28,1.54]:W.box((xx,yy,6.68),(.14,.14,3.02),mi=1)
 for xx in [-1.42,1.74]:R.box((xx,(y0+y1)/2,8.20),(.22,y1-y0+.65,.26),mi=0)
 for j in range(round((y1-y0)/.48)+1):R.box((.12,y0+j*.48,8.32),(4.05,.11,.16),mi=1)
# The pergola continues around the visible courtyard-facing return.
for xx in [4.0,10.8,17.6,24.4,31.2]:
 for yy in [-29.0,-25.5]:W.box((xx,yy,6.67),(.14,.14,3.02),mi=1)
for yy in [-29.10,-25.40]:R.box((17.6,yy,8.22),(28.1,.22,.28),mi=0)
for j in range(61):R.box((3.85+j*.46,-27.25,8.39),(.12,4.7,.18),mi=1)
# A red-framed, two-storey transparent link joins wing to octagonal pavilion.
link=frame((-1.13,-19.7),0)
for yy,a in [(-19.7,0),(-6.3,pi)]:
 pt=frame((-1.13,yy),a);glazing(pt,a,0,7.01,8.3,13.35,depth=.02,vertical=5,horiz=5)
 fb(R,pt,a,0,-.12,13.84,8.55,.60,.32,0)
for zz in [.15,6.52,13.66]:box('Glass link · slab',(-1.13,-13,zz),(8.3,13.4,.22),SHADOW,edge=0)
# Stair is discernible behind link glazing, adding useful depth rather than empty glass.
for j in range(20):box('Glass link · internal stair tread',(-3.5+j*.21,-13,1+j*.24),(.30,2.5,.13),TRIM,edge=.01)

# ROOF: peripheral red tiles, photovoltaic bands and sawtooth glass monitors.
COL=COLS['04 · Tiled solar roof and monitors']
T=batch('Roof · individually overlapping clay barrel tiles',ROOF)
tile_count=0
def tiled_panel(name,p0,p1,p2,p3):
 global tile_count
 A,Bb,Cc,Dd=map(Vector,[p0,p1,p2,p3]);normal=(Bb-A).cross(Dd-A).normalized()
 if normal.z<0:normal=-normal
 mesh(name+' · substrate',[A,Bb,Cc,Dd],[(0,1,2,3)],ROOF[2])
 rows=max(1,round(((Dd-A).length+(Cc-Bb).length)/2/.48))
 for row in range(rows):
  t0=row/rows;t1=min(1,(row+1.13)/rows);L=A.lerp(Dd,t0);Rt=Bb.lerp(Cc,t0);L2=A.lerp(Dd,t1);R2=Bb.lerp(Cc,t1);n=max(1,round((Rt-L).length/.32))
  for j in range(n):
   v=[]
   for ll,rr in [(L,Rt),(L2,R2)]:
    for q in range(6):v.append(ll.lerp(rr,(j+.04+.92*q/5)/n)+normal*(.027+.065*sin(pi*q/5)))
   T.mesh(v,[(q,q+1,q+7,q+6) for q in range(5)],random.choices(range(9),[1,2,4,6,8,7,4,2,1])[0]);tile_count+=1
# Lifted hip roof surrounding a recessed well, matching source aerial photography.
OX0,OX1,OY0,OY1=0,36,-28,47;IX0,IX1,IY0,IY1=9,27,-19,38;EZ,RZ=18.30,20.68
tiled_panel('West solar roof',(OX0,OY1,EZ),(OX0,OY0,EZ),(IX0,IY0,RZ),(IX0,IY1,RZ))
tiled_panel('East solar roof',(OX1,OY0,EZ),(OX1,OY1,EZ),(IX1,IY1,RZ),(IX1,IY0,RZ))
tiled_panel('South hip roof',(OX0,OY0,EZ),(OX1,OY0,EZ),(IX1,IY0,RZ),(IX0,IY0,RZ))
tiled_panel('North hip roof',(OX1,OY1,EZ),(OX0,OY1,EZ),(IX0,IY1,RZ),(IX1,IY1,RZ))
# Broad, visibly red folded-metal fascia under the tiled eaves.
for p,s in [((-.05,9.5,18.15),(.38,75.6,.38)),((36.05,9.5,18.15),(.38,75.6,.38)),((18,-28.05,18.15),(36.7,.38,.38)),((18,47.05,18.15),(36.7,.38,.38))]:R.box(p,s,mi=0)
for p,q in [((0,-28,EZ),(9,-19,RZ)),((36,-28,EZ),(27,-19,RZ)),((0,47,EZ),(9,38,RZ)),((36,47,EZ),(27,38,RZ))]:line('Roof · clay hip cap',[p,q],.12,ROOF[5])
box('Roof · well membrane',(18,9.5,20.05),(18,57,.14),BASE,edge=0)
# Solar modules mounted just above the visible west and east roof slopes.
PV_B=batch('Photovoltaic panels · cells',[PV,PVCELL,STEEL]);panel_count=0
for side in ['W','E']:
 for row in range(3):
  x0=1.65+row*2.14 if side=='W' else 34.35-row*2.14
  for j in range(43):
   yy=-16.95+j*1.24;dx=1 if side=='W' else -1
   def pp(u,v):
    xx=x0+dx*u;zz=EZ+(xx if side=='W' else 36-xx)*(RZ-EZ)/9+.14;return Vector((xx,yy+v,zz))
   corners=[pp(0,0),pp(1.99,0),pp(1.99,1.15),pp(0,1.15)]
   PV_B.mesh(corners,[(0,1,2,3)],0);panel_count+=1
   for u in [0,1.99]:
    v=[pp(u-.018,0),pp(u+.018,0),pp(u+.018,1.15),pp(u-.018,1.15)];PV_B.mesh(v,[(0,1,2,3)],2)
   for vv in [0,1.15]:PV_B.mesh([pp(0,vv-.018),pp(1.99,vv-.018),pp(1.99,vv+.018),pp(0,vv+.018)],[(0,1,2,3)],2)
   for u in [.33,.66,.995,1.33,1.66]:PV_B.mesh([pp(u-.0025,0)+Vector((0,0,.004)),pp(u+.0025,0)+Vector((0,0,.004)),pp(u+.0025,1.15)+Vector((0,0,.004)),pp(u-.0025,1.15)+Vector((0,0,.004))],[(0,1,2,3)],1)
   for vv in [.23,.46,.69,.92]:PV_B.mesh([pp(0,vv-.0025)+Vector((0,0,.005)),pp(1.99,vv-.0025)+Vector((0,0,.005)),pp(1.99,vv+.0025)+Vector((0,0,.005)),pp(0,vv+.0025)+Vector((0,0,.005))],[(0,1,2,3)],1)
# Three sawtooth light monitors with pale steel mullions and visible triangular ends.
for i,yy in enumerate([-10,9.5,29]):
 x0,x1=12.1,23.9;y0,y1=yy-4.6,yy+4.6;zlo,zhi=20.68,24.18
 mesh('Roof monitor %d · sloped glazing'%i,[(x0,y0,zhi),(x1,y0,zlo),(x1,y1,zlo),(x0,y1,zhi)],[(0,1,2,3)],GLASS[3])
 # Tall side glass with a full rectangular grid.
 pt=frame((x0,yy),-pi/2);glazing(pt,-pi/2,0,(zhi+zlo)/2,9.2,zhi-zlo,depth=.02,vertical=8,horiz=3,red=False)
 for y in [y0,y1]:
  mesh('Roof monitor · triangular end',[(x0,y,zlo),(x1,y,zlo),(x0,y,zhi)],[(0,1,2)],GLASS[2])
  for u in range(1,9):
   xx=x0+(x1-x0)*u/9;zz=zhi-(zhi-zlo)*u/9
   line('Roof monitor · end vertical mullion',[(xx,y,zlo),(xx,y,zz)],.029,TRIM)
 for j in range(9):
  yy2=y0+(y1-y0)*j/8;line('Roof monitor · sloping steel bar',[(x0,yy2,zhi+.02),(x1,yy2,zlo+.02)],.039,TRIM)
 for j in range(11):
  xx=x0+(x1-x0)*j/10;zz=zhi-(zhi-zlo)*j/10;line('Roof monitor · horizontal steel bar',[(xx,y0,zz+.025),(xx,y1,zz+.025)],.032,TRIM)
for i in range(7):box('Roof · low equipment cabinet',(29.1,-12+i*6.7,20.79),(2.5,2.2,.6),TRIM,edge=.035)

# SUNKEN COURT. The terrain has a real opening; the terrace is not drawn on a plane.
COL=COLS['05 · Sunken terrace and landscape']
box('Ground · deep continuous earth',(0,0,-4.10),(1800,1800,.20),GRASS,edge=0)
# Four soil volumes surround the sunken rectangle without covering its floor.
for p,s in [((0,455,-2),(1800,958,4)),((0,-482,-2),(1800,842,4)),((-470,-42.5,-2),(860,37,4)),((454,-42.5,-2),(892,37,4))]:
 terrain=box('Ground · grade around terrace',p,s,TRIM,edge=0)
 terrain.data.materials.append(GRASS)
 # Only the upward horizontal face is lawn; every exposed cut is retaining masonry.
 terrain.data.polygons[1].material_index=1
# Continuous pale retaining face closes the strip beneath pavilion and connector.
# Its face sits behind the existing cafe glazing, which remains fully exposed.
box('Court · continuous north retaining wall',(-16,-23.985,-1.73),(48.0,.15,3.60),TRIM,edge=.018)
box('Court · north retaining wall cap',(-16,-24.02,.09),(48.0,.26,.13),TRIM,edge=.018)
# Site paving follows the cut in the terrain.
for p,s in [((-8,9,.04),(102,66,.14)),((-49,-42.5,.04),(18,37,.14)),((23,-42.5,.04),(30,37,.14)),((-7,-65,.04),(84,8,.14))]:box('Campus · upper plaza paving',p,s,PAVE[3],edge=.02)
box('Court · sunken cafe paving',(-16,-34.25,-3.58),(48,21.5,.14),PAVE[3],edge=.03)
# Small genuine pavers across the sunken terrace, batched for close views.
PB=batch('Court · individual modular sandstone pavers',PAVE)
for ix in range(80):
 for iy in range(34):
  xx=-39.7+ix*.60;yy=-43.9+iy*.60
  PB.box((xx,yy,-3.50),(.594,.594,.024),mi=random.randrange(6))
# Retaining walls beside the lower terrace.
for xx in [-40.12,8.12]:
 box('Court · retaining wall',(xx,-34,-1.74),(.26,20,3.65),TRIM,edge=.025)
 box('Court · retaining wall coping',(xx,-34,.13),(.39,20.2,.16),TRIM,edge=.025)
 rpt=frame((xx,-34),pi/2);rail(rpt,pi/2,-9.8,9.8,0,.24)
# A broad stair splits lawns into terraces. Twenty-four rises give a 3.6m descent.
for j in range(24):
 yy=-44.30-j*.60-(j//8)*.8;top=-3.45+j*.15
 box('Court · broad stair tread %02d'%j,(-16,yy,(-3.70+top)/2),(18.0,.61,top+3.70),TRIM,edge=.012)
 if j in [7,15]:
  box('Court · stair landing',(-16,yy-.70,(-3.70+top)/2),(18,1.4,top+3.7),TRIM,edge=.012)
# Rail segments follow each straight run, with level sections at landings.
for xx in [-25.05,-16,-6.95]:
 points=[]
 for j in range(24):
  yy=-44.30-j*.60-(j//8)*.8;zz=-3.45+j*.15+.97
  points.append((xx,yy,zz))
  if j%4==0:line('Court · stair railing upright',[(xx,yy,zz-.95),(xx,yy,zz)],.028,STEEL)
 line('Court · continuous stair handrail',points,.034,STEEL)
# Terraced lawns, each bounded by pale concrete seat walls.
for xmin,xmax in [(-40,-25.35),(-6.65,8)]:
 for row in range(6):
  yfront=-44.0-row*2.4-(row//2)*.8;depth=2.4;top=-2.85+row*.60
  box('Court · lawn terrace earth',((xmin+xmax)/2,yfront-depth/2,(-3.75+top)/2),(xmax-xmin,depth,top+3.75),TRIM,edge=.02)
  box('Court · lawn terrace grass',((xmin+xmax)/2,yfront-depth/2,top+.025),(xmax-xmin-.42,depth-.24,.05),GRASS,edge=.01)
  box('Court · lawn terrace seat coping',((xmin+xmax)/2,yfront+.025,top+.07),(xmax-xmin+.02,.20,.15),TRIM,edge=.02)
# Basement cafe glazing on the court's north retaining facade adjacent to pavilion.
pt=frame((-34,-24.25),0)
for xx in [-3.6,0,3.6]:
 glazing(pt,0,xx,-1.93,3.05,3.05,depth=.06,vertical=2,horiz=3)
 panel(pt,0,xx-1.80,xx-1.525,-3.5,.08,False,2);panel(pt,0,xx+1.525,xx+1.80,-3.5,.08,False,2)
# Gardens at grade beside the octagon and colonnade, with curved stone borders.
LB=batch('Landscape · delicate shrub foliage',LEAVES);FB=batch('Landscape · lavender and yellow flowers',FLOWERS)
def garden(cx,cy,rx,ry,z=.10):
 n=64;v=[(cx,cy,z)]+[(cx+rx*cos(2*pi*j/n),cy+ry*sin(2*pi*j/n),z) for j in range(n)];mesh('Campus · curved planted bed',v,[(0,j+1,(j+1)%n+1) for j in range(n)],MULCH)
 line('Campus · curved pale planting edge',v[1:],.085,TRIM,cyclic=True)
 for j in range(round(rx*ry*20)):
  r=sqrt(random.random());a=random.uniform(0,2*pi);x=cx+rx*.96*r*cos(a);y=cy+ry*.96*r*sin(a);h=random.uniform(.12,.52)
  # Small folded leaves produce detail without spheres or huge object counts.
  for q in range(5):
   aa=a+q*2*pi/5;rr=random.uniform(.12,.21);vv=[(x,y,z+h*.4),(x+rr*cos(aa),y+rr*sin(aa),z+h),(x+.5*rr*cos(aa+.5),y+.5*rr*sin(aa+.5),z+h*.76)]
   LB.mesh(vv,[(0,1,2)],random.randrange(5))
  if j%4==0:
   rr=.045;zz=z+h+.035;FB.mesh([(x-rr,y,zz),(x,y-rr,zz),(x+rr,y,zz),(x,y+rr,zz)],[(0,1,2,3)],j%3)
for p in [(-42,-8,8,4),(-41,14,7,4),(-18,23,8,4.8),(-19,40,7,3.5),(42,27,4,7)]:garden(*p)
# Original detailed vegetation from the Stanford series is instanced and remains editable.
for i,(x,y,s) in enumerate([(-47,3,.45),(-35,23,.43),(-15,34,.46),(42,38,.53),(43,-6,.42),(-44,-54,.32),(12,-56,.34)]):import_plant('broadleaf',(x,y,0),s,COL,i*.71)
for i,(x,y,s) in enumerate([(-49,40,.67),(-44,46,.72)]):import_plant('palm',(x,y,0),s,COL,i*.5)
# Discreet planting on the open upper terrace.
for y in [-1,5,11,24,30,36]:
 box('Terrace · linear planter',(.80,y,5.34),(1.45,3.35,.46),TRIM,edge=.025)
 for j in range(9):
  xx=.8+random.uniform(-.6,.6);yy=y+random.uniform(-1.45,1.45)
  LB.box((xx,yy,5.74),(.25,.36,.38),mi=random.randrange(5))

# HUMAN-SCALE FURNITURE: café tables, woven chairs, ivory parasols and benches.
COL=COLS['06 · Furniture and identity']
FURN=batch('Cafe · steel tables and chairs',[STEEL,WOOD,CANVAS])
def disk(b,cx,cy,z,r,h,mi,n=24):
 v=[(cx+r*cos(2*pi*j/n),cy+r*sin(2*pi*j/n),zz) for zz in [z-h/2,z+h/2] for j in range(n)];f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)];b.mesh(v,f,mi)
def cafe(x,y,z,umbrella=False):
 disk(FURN,x,y,z+.76,.64,.055,0);FURN.box((x,y,z+.39),(.08,.08,.74),mi=0)
 for a in [0,pi/2]:FURN.box((x,y,z+.10),(.92,.06,.06),a,0)
 for k in range(4):
  a=k*pi/2;cx=x+1.03*cos(a);cy=y+1.03*sin(a)
  disk(FURN,cx,cy,z+.46,.245,.032,0,16)
  for t in [-1,1]:
   for u in [-1,1]:FURN.box((cx+t*.17,cy+u*.17,z+.23),(.024,.025,.46),mi=0)
  # Curved wire chair back, legible at courtyard camera scale.
  for j in range(5):
   rr=.25;aa=a-pi/2+j*pi/4
   p0=(cx+rr*cos(aa),cy+rr*sin(aa),z+.47);p1=(p0[0],p0[1],z+.91);line('Cafe · chair back wire',[p0,p1],.012,STEEL)
  pts=[(cx+.25*cos(a-pi/2+j*pi/20),cy+.25*sin(a-pi/2+j*pi/20),z+.91) for j in range(21)];line('Cafe · curved chair rim',pts,.018,STEEL)
 if umbrella:
  FURN.box((x,y,z+1.45),(.035,.035,2.9),mi=0)
  n=8;v=[(x,y,z+3.12)]+[(x+1.70*cos(2*pi*j/n),y+1.70*sin(2*pi*j/n),z+2.57) for j in range(n)];FURN.mesh(v,[(0,j+1,(j+1)%n+1) for j in range(n)],2)
  for j in range(n):line('Cafe · umbrella spoke',[(x,y,z+3.09),v[j+1]],.016,STEEL)
for x,y,z,u in [(-32,-32,-3.48,True),(-26,-35,-3.48,False),(-18,-36,-3.48,True),(-10,-33,-3.48,True),(0,-37,-3.48,False),(-35,-16,.14,True),(-36,-10,.14,True),(-25,3,.14,False),(-25,8,.14,False)]:cafe(x,y,z,u)
for i,(x,y,a) in enumerate([(-48,12,pi/2),(-34,32,0),(-19,28,0),(-8,37,pi/2),(-43,-3,pi/2)]):bench('Campus · timber bench %02d'%i,(x,y,.14),a,COL)
for x,y in [(-40,-20),(-40,7),(-23,27),(-3,39),(39,-24)]:
 line('Campus · slim path light',[(x,y,.12),(x,y,3.6)],.053,STEEL)
 disk(FURN,x,y,3.68,.30,.12,0)
# Restrained building identity, positioned above the lower-court entrance.
def text(name,body,loc,size,m,a=0):
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.space_character=1.10;cu.extrude=.003;o=bpy.data.objects.new(name,cu);COL.objects.link(o);o.location=loc;o.rotation_euler=(pi/2,0,a);cu.materials.append(m)
text('Huang · entrance name','JEN-HSUN HUANG',(-17,-24.777,-.04),.18,FRAME)
text('Huang · entrance subtitle','ENGINEERING CENTER',(-17,-24.777,-.30),.16,FRAME)
# Finalize batched geometry only after all shared architectural components exist.
for b in B:
 o=b.finish()
 if b is T:o['individual_tiles']=tile_count
# Embedding references and limitations makes this self-contained and honestly editable.
notes='''JEN-HSUN HUANG ENGINEERING CENTER · STANFORD UNIVERSITY
Photo-informed exterior reconstruction, October 2026. Dimensions estimated in metres; not a measured or construction model.
Primary reference photographs actually inspected:
https://www.office-52.com/work/jen-hsun-huang-engineering-center/
https://www.office-52.com/image/HEC_09.jpg
https://www.office-52.com/image/HEC_10.jpg
https://www.office-52.com/image/HEC_12.jpg
https://www.office-52.com/image/HEC_14.jpg
https://engineering100.stanford.edu/stories/designing-for-the-future
https://engineering.stanford.edu/about/visit/location
Stanford exterior photo by Tim Griffith / School of Engineering. Quad aerial by Todd Quam / School of Engineering.
Primary interpretation: flat octagonal limestone pavilion with shallow segmental upper loggias, tall alternating glazed and slit-window faces; glass connecting link; a long teaching wing, lower arcade, elevated red steel/tile solar roof with three sawtooth glass monitors; terraced lower cafe court.
Scale, unseen rear facades, structural interiors, relative site placement, plants and furniture are approximate. The adjacent Spilker, Y2E2 and Shriram buildings are intentionally not included. No reference photographs are embedded as textures.
Scene daylight and materials match the Hoover/Gates Stanford series. Material Preview opens with scene world and lights enabled. Use Rendered shading / F12 for final shadow quality.
'''
t=bpy.data.texts.new('README · Huang references and reconstruction notes');t.write(notes)
scene=setup_lighting();scene['project']='Jen-Hsun Huang Engineering Center · Stanford University';scene['reconstruction_note']='Photo-informed estimated exterior; unseen facades, dimensions and grounds approximated.';scene['roof_tile_count']=tile_count;scene['photovoltaic_panel_count']=panel_count
hero=camera('Huang · Architectural portrait',(-94,-135,45),(-4,1,8.0),48,COLS['90 · Cameras & lighting'])
detail=camera('Huang · Courtyard detail',(-67,-83,24),(-16,-22,7.7),57,COLS['90 · Cameras & lighting']);detail['suggested_resolution']='2000x1500'
camera('Huang · Solar roof overview',(-91,-97,79),(1,6,8),51,COLS['90 · Cameras & lighting'])
scene.camera=hero;scene.render.resolution_x=2400;scene.render.resolution_y=1800;scene.render.resolution_percentage=100;scene.render.filepath=str(ROOT/'renders/huang_hero.png')
configure_viewport(scene,rendered=False)
for ob in bpy.context.selected_objects:ob.select_set(False)
(ROOT/'renders').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Huang_Engineering_Center_Stanford.blend'))
unique={ob.data for ob in bpy.data.objects if ob.type=='MESH'}
print(json.dumps({'saved':bpy.data.filepath,'objects':len(bpy.data.objects),'unique_vertices':sum(len(me.vertices) for me in unique),'roof_tiles':tile_count,'photovoltaic_panels':panel_count}))
