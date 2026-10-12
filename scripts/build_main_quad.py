"""Photo-informed full Stanford Main Quadrangle exterior, metre units.
Run in Blender. Geometry estimates and primary sources are embedded in the .blend.
"""
import bpy, math, random, sys, json
from pathlib import Path
from math import sin,cos,pi,sqrt
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from campus_common import setup_lighting,camera,configure_viewport,import_plant,bench
bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(1891)
COLS={}
for name in ['01 · Inner Quad sandstone ranges','02 · Open Romanesque arcades','03 · Outer Quad academic buildings','04 · Memorial Court and gateways','05 · Memorial Church','06 · Courtyards and landscaping','90 · Cameras and lighting']:
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);COLS[name]=c
COL=COLS['01 · Inner Quad sandstone ranges']
def mat(name,c,rough=.8,metal=0,texture=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*c,1);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if texture:
  tc=n.new('ShaderNodeTexCoord');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=38;tex.inputs['Detail'].default_value=3;l.new(tc.outputs['Object'],tex.inputs[0]);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.26;b.inputs['Distance'].default_value=.04;l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
 return m
STONE=[mat('Quad · warm sandstone %02d'%i,(.49+i*.019,.367+i*.015,.221+i*.012),texture=True) for i in range(8)]
TRIM=mat('Quad · carved honey limestone',(.64,.52,.35),texture=True)
MORTAR=mat('Quad · recessed mortar',(.30,.25,.173),texture=True)
TILE=[mat('Quad · fired terracotta %02d'%i,(.28+i*.025,.064+i*.009,.031+i*.004),texture=True) for i in range(8)]
DARK=mat('Quad · deep shaded recess',(.022,.028,.025),.98)
METAL=mat('Quad · dark patinated bronze',(.035,.048,.04),.35,.6)
GLASS=[mat('Quad · blue green glass %02d'%i,(.025+i*.007,.061+i*.01,.072+i*.013),.22,.35) for i in range(4)]
WOOD=mat('Quad · aged arcade beams',(.115,.068,.032),texture=True)
PAVE=mat('Quad · warm brick paving',(.385,.295,.218),texture=True)
PAVELIGHT=mat('Quad · limestone paving',(.60,.56,.465),texture=True)
PAVEDARK=mat('Quad · arcade checker slate',(.25,.263,.249),texture=True)
SOIL=mat('Quad · earth',(.17,.115,.065),texture=True)
GRASS=mat('Quad · lawn',(.12,.218,.059),texture=True)
GROUND=mat('Quad · surrounding ground',(.27,.30,.181),texture=True)
LEAF=[mat('Quad · garden leaf %02d'%i,(.051+i*.017,.112+i*.018,.026+i*.009)) for i in range(5)]
FLOWER=mat('Quad · red flowers',(.39,.037,.032))
BRASS=mat('Quad · time capsule brass',(.32,.23,.103),.4,.55)
OPAL=mat('Quad · opal lantern',(.79,.80,.73),.3)

class Batch:
    def __init__(self,name,col):self.name=name;self.col=col;self.v=[];self.f=[];self.mi=[];self.m=[]
    def mesh(self,vs,fs,mat):
        n=len(self.v);self.v.extend(vs);self.f.extend(tuple(n+j for j in f) for f in fs)
        if mat not in self.m:self.m.append(mat)
        self.mi.extend([self.m.index(mat)]*len(fs))
    def box(self,loc,size,mat,a=0):
        x,y,z=loc;dx,dy,dz=size;c=cos(a);s=sin(a)
        vs=[(x+c*u*dx/2-s*v*dy/2,y+s*u*dx/2+c*v*dy/2,z+w*dz/2) for u,v,w in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        self.mesh(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def quad(self,vs,mat):self.mesh(vs,[(0,1,2,3)],mat)
    def finish(self):
        if not self.v:return
        me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update();ob=bpy.data.objects.new(self.name,me);self.col.objects.link(ob)
        for m in self.m:me.materials.append(m)
        for p,i in zip(me.polygons,self.mi):p.material_index=i
        return ob

def box(name,loc,size,mat,col=None,a=0):
    b=Batch(name,col or COL);b.box(loc,size,mat,a);return b.finish()

def curve(name,points,r,mat,col=None,cyclic=False):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=1
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for p,v in zip(sp.points,points):p.co=(*v,1)
    sp.use_cyclic_u=cyclic;ob=bpy.data.objects.new(name,cu);(col or COL).objects.link(ob);cu.materials.append(mat);return ob

def cylinder(batch,center,r,depth,mat,n=12):
    x,y,z=center;v=[(x+r*cos(2*pi*k/n),y+r*sin(2*pi*k/n),z+s*depth/2) for s in [-1,1] for k in range(n)]
    f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(k,(k+1)%n,(k+1)%n+n,k+n) for k in range(n)];batch.mesh(v,f,mat)

# Geometry is batched by architectural role, preserving editable collections.
BATCHES={}
def batch(name,col=None):
 if name not in BATCHES:BATCHES[name]=Batch(name,col or COL)
 return BATCHES[name]
def local_box(b,origin,t,n,u,v,z,w,d,h,material):
 b.box((origin[0]+t[0]*u+n[0]*v,origin[1]+t[1]*u+n[1]*v,z),(w,d,h),material,math.atan2(t[1],t[0]))
def local_mesh(b,origin,t,n,vs,fs,material):
 b.mesh([(origin[0]+t[0]*u+n[0]*v,origin[1]+t[1]*u+n[1]*v,z) for u,v,z in vs],fs,material)
def lathe(b,center,profile,material,sides=16):
 x,y,z=center;v=[(x+r*cos(2*pi*j/sides),y+r*sin(2*pi*j/sides),z+zz) for r,zz in profile for j in range(sides)];fs=[]
 for k in range(len(profile)-1):
  for j in range(sides):fs.append((k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j))
 fs += [tuple(reversed(range(sides))),tuple((len(profile)-1)*sides+j for j in range(sides))];b.mesh(v,fs,material)

def rolled_surface(b,A,B,C,D,spacing=.32):
 # Rolled tile courses occupy an actual sloping quad, not a colored flat slab.
 A,B,C,D=[Vector(x) for x in [A,B,C,D]];length=(B-A).length;num=max(1,math.ceil(length/spacing));tan=(B-A).normalized()
 for j in range(num):
  t=(j+.5)/num;start=A.lerp(B,t);end=C.lerp(D,t);v=[]
  for p in [start,end]:
   for k in range(5):v.append(tuple(p+tan*cos(pi*k/4)*.105+Vector((0,0,.035+sin(pi*k/4)*.065))))
  b.mesh(v,[(k,k+1,k+6,k+5) for k in range(4)],TILE[j%8])
 n=max(1,round((A-C).length/.42))
 for row in range(1,n):
  t=row/n;L=A.lerp(C,t);R=B.lerp(D,t);mid=(L+R)/2;delta=R-L;b.box(tuple(mid+Vector((0,0,.048))),(delta.length,.024,.035),TILE[1],math.atan2(delta.y,delta.x))

def hip_roof(b,cx,cy,dx,dy,z,rise=3):
 dx+=.85;dy+=.85;short=min(dx,dy);hip=short/2
 v=[(cx+sx*dx/2,cy+sy*dy/2,z) for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 if dx>=dy:
  a=(cx-dx/2+hip,cy,z+rise);c=(cx+dx/2-hip,cy,z+rise)
  b.mesh(v+[a,c],[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4)],TILE[3])
  rolled_surface(b,v[0],v[1],a,c);rolled_surface(b,v[2],v[3],c,a);rolled_surface(b,v[3],v[0],a,a);rolled_surface(b,v[1],v[2],c,c)
  b.box((cx,cy,z+rise+.05),(max(.3,dx-2*hip),.21,.17),TILE[4])
 else:
  a=(cx,cy-dy/2+hip,z+rise);c=(cx,cy+dy/2-hip,z+rise)
  b.mesh(v+[a,c],[(0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5)],TILE[3])
  rolled_surface(b,v[0],v[1],a,a);rolled_surface(b,v[1],v[2],a,c);rolled_surface(b,v[2],v[3],c,c);rolled_surface(b,v[3],v[0],c,a)
  b.box((cx,cy,z+rise+.05),(.21,max(.3,dy-2*hip),.17),TILE[4])

def stone_facade(b,origin,t,n,length,height,openings):
 # Actual window/door openings are omitted from horizontal stone courses.
 courses=max(1,round(height/.53));ch=height/courses
 for row in range(courses):
  zz=.30+(row+.5)*ch;cuts=[(-length/2,length/2)]
  for u,z,w,h in openings:
   if abs(zz-z)<h/2+ch/2:
    new=[]
    for a,c in cuts:
     if c<=u-w/2 or a>=u+w/2:new.append((a,c));continue
     if a<u-w/2:new.append((a,u-w/2))
     if c>u+w/2:new.append((u+w/2,c))
    cuts=new
  for lo,hi in cuts:
   count=max(1,math.ceil((hi-lo)/1.18));pw=(hi-lo)/count
   for j in range(count):
    u=lo+(j+.5)*pw;local_box(b,origin,t,n,u,.018,zz,pw-.017,.20,ch-.019,STONE[(row*3+j*5)%8])

def casement(b,origin,t,n,u,z,w,h,seed=0,door=False):
 local_box(b,origin,t,n,u,-.15,z,w,h*.0+.055,h,DARK)
 local_box(b,origin,t,n,u,-.11,z,w-.14,.028,h-.13,GLASS[seed%4])
 for du in [-w/2,w/2]:local_box(b,origin,t,n,u+du,-.04,z,.07,.09,h+.1,METAL)
 for dz in [-h/2,h/2]:local_box(b,origin,t,n,u,-.04,z+dz,w+.07,.09,.075,METAL)
 for du in [-w/4,0,w/4]:local_box(b,origin,t,n,u+du,-.045,z,.032,.10,h,METAL)
 for j in range(1,max(2,round(h/.53))):local_box(b,origin,t,n,u,-.05,z-h/2+h*j/max(2,round(h/.53)),w,.10,.033,METAL)
 local_box(b,origin,t,n,u,.06,z-h/2-.09,w+.28,.40,.15,TRIM)
 # Square cut stone reveals sit behind the outer rusticated face.
 for du in [-w/2-.065,w/2+.065]:local_box(b,origin,t,n,u+du,-.04,z,.13,.32,h+.25,TRIM)
 local_box(b,origin,t,n,u,.035,z+h/2+.13,w+.38,.33,.21,TRIM)
 if door:
  for du in [-.15,.15]:local_box(b,origin,t,n,u+du,.04,z-.25,.035,.13,.40,BRASS)

# Academic rooms, with repeated stone blocks and framed openings on all elevations.
def academic(name,cx,cy,dx,dy,H,col,two=False,roofrise=3):
 wall=batch(name+' · rusticated ashlar',col);gl=batch(name+' · bronze windows and doors',col);rf=batch(name+' · tiled roof',col)
 # Recessed dark core makes glazing reveal depth readable; surface masonry stays open.
 wall.box((cx,cy,H/2+.3),(dx-.7,dy-.7,H),MORTAR)
 wall.box((cx,cy,.23),(dx+.24,dy+.24,.20),TRIM)
 for nx,ny,length in [(0,-1,dx),(0,1,dx),(-1,0,dy),(1,0,dy)]:
  t=(-ny,nx);n=(nx,ny);origin=(cx+nx*dx/2,cy+ny*dy/2);bay=max(2,round(length/4.8));pitch=length/bay;openings=[]
  levels=[(3.35,3.8),(H-3.0,3.7)] if two else [(3.75,4.7)]
  for j in range(bay):
   u=-length/2+(j+.5)*pitch
   for f,(z,h) in enumerate(levels):
    w=min(1.6,pitch*.44);door=(j==bay//2 and f==0)
    if door:z=2.45;h=4.1;w=min(1.9,pitch*.52)
    openings.append((u,z,w+.1,h+.1));casement(gl,origin,t,n,u,z,w,h,j+f,door)
  stone_facade(wall,origin,t,n,length,H,openings)
  for z in ([.48,H+.22,H/2+.12] if two else [.48,H+.22]):local_box(wall,origin,t,n,0,.04,z,length+.13,.39,.17,TRIM)
  local_box(wall,origin,t,n,0,.045,H+.38,length+.25,.56,.30,WOOD)
 hip_roof(rf,cx,cy,dx,dy,H+.5,roofrise)

# A true open arcade: solid masonry surrounds the curved opening, supported by
# rounded shafts. There is no glass or hidden wall behind the opening.
ARCADE_COLUMNS=set()
def arcade(name,start,end,outward,col=None,depth=5.2,baytarget=5.5,eave=6.6,spring=3.2):
 col=col or COLS['02 · Open Romanesque arcades'];b=batch(name+' · columns and arch masonry',col);roof=batch(name+' · rolled tile canopy',col);wood=batch(name+' · timber soffit',col)
 dx=end[0]-start[0];dy=end[1]-start[1];L=math.hypot(dx,dy);t=(dx/L,dy/L);n=outward;origin=((start[0]+end[0])/2,(start[1]+end[1])/2);count=max(1,round(L/baytarget));pitch=L/count;r=pitch*.395;ro=r+.36
 for j in range(count):
  u=-L/2+(j+.5)*pitch
  # Full-depth extruded voussoirs with small mortar joints.
  for k in range(17):
   a=pi*k/17+.002;c=pi*(k+1)/17-.002;vs=[]
   for yy in [-.42,.42]:
    for rr in [r,ro]:
     for th in [a,c]:vs.append((u+rr*cos(th),yy,spring+rr*sin(th)))
   local_mesh(b,origin,t,n,vs,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],STONE[(j+k)%8])
  # Upper ashlar triangles close to the top of each arch ring.
  for k in range(18):
   a=pi-pi*k/18;c=pi-pi*(k+1)/18;u0=u+ro*cos(a);u1=u+ro*cos(c);z0=spring+ro*sin(a);z1=spring+ro*sin(c)
   vs=[(uu,vv,zz) for vv in [-.40,.40] for uu,zz in [(u0,z0),(u1,z1),(u1,eave-.14),(u0,eave-.14)]]
   local_mesh(b,origin,t,n,vs,[(0,1,2,3),(4,7,6,5),(0,4,5,1)],STONE[(j+k//4)%8])
  # Fill the narrow vertical masonry between adjacent arch crowns.
  flank=max(.03,(pitch-2*ro)/2)
  for sign in [-1,1]:local_box(b,origin,t,n,u+sign*(ro+flank/2),0,(spring+eave)/2,flank,.8,eave-spring,STONE[j%8])
 for j in range(count+1):
  u=-L/2+j*pitch;x=origin[0]+t[0]*u;y=origin[1]+t[1]*u
  key=(round(x,3),round(y,3))
  if key in ARCADE_COLUMNS:continue
  ARCADE_COLUMNS.add(key)
  lathe(b,(x,y,.30),[(.59,0),(.62,.13),(.53,.24),(.43,.37),(.43,2.12),(.50,2.28),(.57,2.40),(.58,2.54)],TRIM,16)
  local_box(b,origin,t,n,u,0,3.015,1.18,1.13,.37,TRIM)
  # Restrained carved scroll medallions on the capital faces.
  for v in [-.575,.575]:
   for off in [-.35,0,.35]:
    pts=[(origin[0]+t[0]*(u+off+.10*cos(2*pi*q/12))+n[0]*v,origin[1]+t[1]*(u+off+.10*cos(2*pi*q/12))+n[1]*v,2.97+.10*sin(2*pi*q/12)) for q in range(12)]
    b.mesh(pts,[tuple(range(12))],STONE[6])
 local_box(b,origin,t,n,0,0,eave-.10,L+.08,1.0,.20,TRIM)
 # Sloping roof and shadow-producing timber canopy.
 vs=[(-L/2-.24,-.6,eave), (L/2+.24,-.6,eave),(-L/2-.24,depth+.12,eave+1.9),(L/2+.24,depth+.12,eave+1.9)]
 world=[(origin[0]+t[0]*u+n[0]*v,origin[1]+t[1]*u+n[1]*v,z) for u,v,z in vs]
 roof.mesh(world,[(0,1,3,2)],TILE[3]);rolled_surface(roof,*world)
 wood.mesh([(x,y,z-.14) for x,y,z in world],[(0,2,3,1)],WOOD)
 for j in range(count*3+1):
  u=-L/2+j*L/(count*3)
  # Exposed rafters follow the roof slope using a narrow quad extrusion.
  a=Vector((origin[0]+t[0]*u+n[0]*(-.58),origin[1]+t[1]*u+n[1]*(-.58),eave-.22));c=Vector((origin[0]+t[0]*u+n[0]*(depth+.12),origin[1]+t[1]*u+n[1]*(depth+.12),eave+1.66));v=Vector((t[0]*.065,t[1]*.065,0));wood.mesh([tuple(a-v),tuple(a+v),tuple(c+v),tuple(c-v)],[(0,1,2,3)],WOOD)
 # Continuous raised floor makes door and column thresholds meet.
 local_box(b,origin,t,n,0,depth/2,.19,L,depth+.6,.22,PAVELIGHT)
 # Alternating real floor inlays, clear of duplicated faces at tile borders.
 for j in range(int(L/1.5)):
  u=-L/2+(j+.5)*1.5
  for q in range(3):
   if (j+q)%2==0:local_box(b,origin,t,n,u,.75+q*1.5,.309,1.47,1.47,.012,PAVEDARK)

# Inner ring: twelve low teaching ranges enclosing the ceremonial paved court.
# The 586 × 246 ft historical court dimension gives the presentation scale.
X=89.3;Y=37.5
inner=COLS['01 · Inner Quad sandstone ranges']
# 100/110 and 1/10 across the entrance side; split by Memorial Court gateway.
for num,cx,w in [('100',-70,38),('110',-33.5,35),('1',33.5,35),('10',70,38)]:academic('Inner '+num,cx,-50.3,w,14.5,7.8,inner,roofrise=3.25)
# East/west ranges divided by the axial covered portals.
for side,nums in [(-1,['90','80']),(1,['20','30'])]:
 for num,cy in zip(nums,[-21.5,21.5]):academic('Inner '+num,side*101.8,cy,14.5,30.5,8.0,inner,roofrise=3.2)
for num,cx,w in [('70',-73.5,31.6),('60',-41.8,31.4),('50',41.8,31.4),('40',73.5,31.6)]:academic('Inner '+num,cx,50.3,w,14.5,7.8,inner,roofrise=3.25)
# Main court arcades are uninterrupted except church and the three gateway bays.
arcade('Inner north west',(-X,-Y),(-15,-Y),(0,-1))
arcade('Inner north east',(15,-Y),(X,-Y),(0,-1))
arcade('Inner south west',(-X,Y),(-13.65,Y),(0,1))
arcade('Inner south east',(13.65,Y),(X,Y),(0,1))
for side in [-1,1]:
 arcade('Inner side %s front'%side,(side*X,-Y),(side*X,-7),(side,0))
 arcade('Inner side %s rear'%side,(side*X,7),(side*X,Y),(side,0))

# Gabled Romanesque gateways with concentric archivolts and real through-openings.
def gateway(name,origin,t,n,width=30,depth=8,H=7.3,peak=11.8,openings=None):
 col=COLS['04 · Memorial Court and gateways'];b=batch(name+' · masonry',col);r=batch(name+' · roof tiles',col)
 if openings is None:openings=[(-9.5,2.5,3.0),(0,3.45,3.0),(9.5,2.5,3.0)]
 # Segment the wall around actual arches. The center arch is the principal axis.
 for face in [0,depth]:
  last=-width/2
  for u,rad,spring in openings:
   if u-rad>last:local_box(b,origin,t,n,(last+u-rad)/2,face,H/2+.3,u-rad-last,.9,H,STONE[3])
   for j in range(24):
    a=pi-pi*j/24;c=pi-pi*(j+1)/24;xa=u+rad*cos(a);xb=u+rad*cos(c);za=.3+spring+rad*sin(a);zb=.3+spring+rad*sin(c)
    local_mesh(b,origin,t,n,[(x,y,z) for y in [face-.45,face+.45] for x,z in [(xa,za),(xb,zb),(xb,H+.3),(xa,H+.3)]],[(0,1,2,3),(4,7,6,5),(0,4,5,1)],STONE[j%8])
   for rr in [rad+.08,rad+.34]:
    for j in range(20):
     a=pi*j/20+.004;c=pi*(j+1)/20-.004;vs=[(u+q*cos(th),face+(-.52 if face==0 else .52),.3+spring+q*sin(th)) for q in [rr,rr+.18] for th in [a,c]];local_mesh(b,origin,t,n,vs,[(0,1,3,2)],TRIM)
   last=u+rad
  if last<width/2:local_box(b,origin,t,n,(last+width/2)/2,face,H/2+.3,width/2-last,.9,H,STONE[3])
  local_mesh(b,origin,t,n,[(-width/2,face-.01,H+.3),(width/2,face-.01,H+.3),(0,face-.01,peak)],[(0,1,2)],STONE[4])
 # Three discrete arch bays connect front to back via side jamb walls.
 for u,rad,spring in openings:
  for sign in [-1,1]:local_box(b,origin,t,n,u+sign*(rad+.35),depth/2,1.8,.65,depth,3.0,STONE[4])
 # Pitched gable roof, with tile geometry on both slopes.
 for sign in [-1,1]:
  vs=[(sign*(width/2+.35),-.65,H+.6),(sign*(width/2+.35),depth+.65,H+.6),(0,-.65,peak+.2),(0,depth+.65,peak+.2)]
  world=[(origin[0]+t[0]*u+n[0]*v,origin[1]+t[1]*u+n[1]*v,z) for u,v,z in vs];r.mesh(world,[(0,1,3,2)],TILE[3]);rolled_surface(r,*world)
 local_box(b,origin,t,n,0,depth/2,.19,width,depth+.9,.22,PAVELIGHT)
 # Incised decorative roundels above smaller arches.
 for u,rad,spring in openings:
  if u:
   pts=[(u+.56*cos(2*pi*j/16),-.51,H+.30+.56*sin(2*pi*j/16)) for j in range(16)];local_mesh(b,origin,t,n,pts,[tuple(range(16))],TRIM)

gateway('Memorial Court triple portal',(0,-Y),(1,0),(0,-1),30,10,7.4,11.5)
for side in [-1,1]:gateway('Quad side gate %s'%side,(side*X,0),(0,1),(side,0),14,20,9.0,13.2,[(0,3.0,3.5)])

# Outer Quad massings follow the 2026 Stanford tree map; sizes/heights inferred.
outer=COLS['03 · Outer Quad academic buildings']
OUTER=[
 ('380 Sloan Math corner',-124,-88,24,63,14.8),
 ('420',-85,-108,54,24,15.3),('420 south return',-83,-85,21,22,15.3),
 ('460 Margaret Jacks',-42,-103,36,34,13.4),('460 south return',-38,-80,22,15,13.4),
 ('120 McClatchy',42,-103,36,34,13.4),('120 south return',35,-82,21,18,13.4),
 ('160 Wallenberg',83,-108,48,24,15.7),('170',81,-84,23,24,15.7),
 ('200 Lane History',124,-88,24,63,15.2),
 ('370',-128,-21,17,29,9.6),('360',-128,22,17,29,9.6),
 ('240',128,-21,17,29,9.6),('250',128,22,17,29,9.6),
 ('320 Braun Geology',-123,78,26,76,15.5),('320 south wing',-104,103,16,26,15.5),('310',-81,103,26,26,13.0),
 ('260 Pigott Language',123,78,26,76,15.5),('260 south wing',104,103,16,26,15.5),('300',81,103,26,26,13.0)]
for name,cx,cy,dx,dy,H in OUTER:academic('Outer '+name,cx,cy,dx,dy,H,outer,two=H>11,roofrise=4.0 if H>11 else 3)
# Outer continuous low cloisters unify academic blocks and minor courtyard gardens.
for side in [-1,1]:
 arcade('Outer street %s front'%side,(side*142,-126),(side*142,-8),(-side,0),depth=5.4)
 arcade('Outer street %s rear'%side,(side*142,8),(side*142,116),(-side,0),depth=5.4)
 arcade('Outer front %s'%side,(side*17,-126),(side*142,-126),(0,1),depth=6)
 # Walkways along side portal courtyards, leaving the central passage free.
 for yy in [-7,7]:arcade('Side passage %s %s'%(side,yy),(side*110,yy),(side*141,yy),(0,-1 if yy<0 else 1),depth=3.5,baytarget=5.1)
 # Memorial Court's two long colonnades.
 arcade('Memorial Court side %s'%side,(side*21,-116),(side*21,-48),(side,0),COLS['04 · Memorial Court and gateways'],depth=4.0,baytarget=5.6)
 # Two short courtyard loggias face the rear gardens.
 arcade('Rear court cloister %s'%side,(side*32,63),(side*101,63),(0,-1),depth=5.4)
# Broad gateway piers that terminate the opening toward Jane Stanford Way.
entry=batch('Memorial Court · entry piers and balustrade',COLS['04 · Memorial Court and gateways'])
for x in [-18,18]:
 entry.box((x,-126,4.0),(3.3,4.6,7.4),STONE[5]);entry.box((x,-126,7.8),(3.7,4.9,.24),TRIM)
# Broad shallow front steps link lawn/approach to the raised court level.
for j in range(4):entry.box((0,-128.2-j*.6,.15-j*.045),(33+2*j,1.1,.18),PAVELIGHT)
for side in [-1,1]:
 for k in range(21):
  x=side*(24+k*5.4);entry.box((x,-137,1.0),(.38,.60,1.65),TRIM)
 entry.box((side*80,-137,1.77),(116,.74,.24),TRIM);entry.box((side*80,-137,.23),(116,.74,.24),TRIM)

# Court floor uses closely spaced warm brick joints, eight planted circular islands,
# and a central medallion; it is intentionally not a lawn.
COL=COLS['06 · Courtyards and landscaping']
garden=batch('Quad · pavements paths and eight circle planters',COL)
garden.box((0,0,-.13),(5000,5000,.15),GRASS)
garden.box((0,-4,.08),(304,250,.18),PAVELIGHT)
garden.box((0,0,.195),(2*X,2*Y,.20),PAVE)
# Shader brick scale provides actual brick-size joints without millions of objects.
p=PAVE.node_tree.nodes.get('Principled BSDF');n=PAVE.node_tree.nodes;l=PAVE.node_tree.links
tex=n.new('ShaderNodeTexBrick');tex.inputs['Color1'].default_value=(.385,.286,.198,1);tex.inputs['Color2'].default_value=(.445,.334,.239,1);tex.inputs['Mortar'].default_value=(.235,.207,.164,1);tex.inputs['Scale'].default_value=1;tex.inputs['Mortar Size'].default_value=.008;tex.inputs['Brick Width'].default_value=.22;tex.inputs['Row Height'].default_value=.105
coord=n.new('ShaderNodeTexCoord');l.new(coord.outputs['Object'],tex.inputs['Vector']);l.new(tex.outputs['Color'],p.inputs['Base Color']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.008;l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
# Limestone circular curb, soil, and horticultural islands are genuinely round.
islands=[(x,y) for y in [-18,18] for x in [-66,-22,22,66]]
for i,(x,y) in enumerate(islands):
 lathe(garden,(x,y,.29),[(9.30,0),(9.30,.32),(9.11,.40),(8.88,.40),(8.88,.08)],TRIM,72)
 cylinder(garden,(x,y,.40),8.91,.15,SOIL,72)
# Central stone class medallion in the axial crossing.
cylinder(garden,(0,0,.305),4.3,.022,PAVELIGHT,72)
for r in [3.8,4.18]:
 pts=[(r*cos(2*pi*i/90),r*sin(2*pi*i/90),.322) for i in range(90)];curve('Quad · medallion ring',pts,.022,BRASS,COL,True)
# Memorial Court has an X-path garden layout, different from the paved Inner Quad.
garden.box((0,-83,.23),(40,66,.12),GRASS)
for row,yy in enumerate([-101,-67]):
 for direction in [-1,1]:
  # Slightly separated finishes prevent coplanar crossing artifacts.
  zz=.315+row*.004+(direction+1)*.001
  a=Vector((-19,yy-direction*15,zz));c=Vector((19,yy+direction*15,zz));d=c-a;garden.box(tuple((a+c)/2),(d.length,2.2,.10),PAVELIGHT,math.atan2(d.y,d.x))
garden.box((0,-83,.336),(3.1,68,.1),PAVELIGHT);garden.box((0,-84,.342),(40,2.2,.1),PAVELIGHT)
# Side and rear secondary courtyard landscapes.
for x,y,w,d in [(-80,-74,51,24),(80,-74,51,24),(-72,81,56,31),(72,81,56,31),(-116,0,38,12),(116,0,38,12)]:
 garden.box((x,y,.21),(w,d,.15),GRASS)
 garden.box((x,y,.30),(w,2,.08),PAVELIGHT);garden.box((x,y,.305),(2,d,.08),PAVELIGHT)
 for sx,sy in [(-1,-1),(1,1)]:garden.box((x+sx*w*.29,y+sy*d*.27,.34),(w*.22,d*.24,.08),SOIL)
# Continuous perimeter lawns support the whole architectural ensemble.
for x in [-165,165]:garden.box((x,0,.01),(30,261,.12),GRASS)
garden.box((0,-158,.01),(333,31,.12),GRASS);garden.box((0,137,.01),(300,19,.12),GRASS)
garden.box((0,-155,.13),(15,36,.13),PAVELIGHT)
# Geological / language garden curved walks use pale ribbons.
for x in [-60,60]:
 pts=[(x+24*cos(pi*j/36),83+15*sin(pi*j/36),.37) for j in range(37)];curve('Quad · rear garden curved path',pts,1.05,PAVELIGHT,COL)
# Brass class plaques run in the arcade floor, starting near the church.
for j in range(82):garden.box((-85.6,-33+j*.8,.323),(.42,.27,.014),BRASS)

# The module owns the church body, detailed mosaics and deep entrance portals.
from memorial_church import build_memorial_church
build_memorial_church(origin=(0,37.5,.30),collection=COLS['05 · Memorial Church'])
# Extend a continuous stone landing under the church threshold, no terrain gap.
garden.box((0,38.6,.20),(34,4.3,.22),PAVELIGHT)

# Palm and broadleaf specimens share the detailed Hoover series assets.
for i,(x,y) in enumerate(islands):
 import_plant('palm',(x-2.0,y-1.5,.55),scale=.70+(i%3)*.17,collection=COL,angle=i*.71)
 if i not in [1,2]:import_plant('broadleaf',(x+2.3,y+2.0,.5),scale=.37+(i%3)*.07,collection=COL,angle=i*.9)
 # Additional short palms/yucca-like rosettes make the circles botanical gardens.
 import_plant('palm',(x+3.4,y-3,.5),scale=.17+(i%2)*.07,collection=COL,angle=i+1.4)
for i,(x,y) in enumerate([(-84,-66),(-64,-72),(65,-69),(96,-66),(-71,83),(-86,72),(72,82),(87,73),(-165,-81),(167,-92),(-165,-2),(163,16),(-160,89),(162,104),(-60,139),(60,139),(-104,-157),(100,-155)]):
 import_plant('broadleaf',(x,y,.15),scale=.50+(i%4)*.065,collection=COL,angle=i*.56)
for x in [-14,14]:
 for yy in [-151,-166]:import_plant('palm',(x,yy,.15),scale=.82,collection=COL,angle=yy)
# Soft botanical leaves are curved and small; foliage shares one batched mesh.
fol=batch('Quad · low botanical planting and red flower borders',COL)
def shrub(cx,cy,rad,height,variant):
 # A small smooth leaf-covered mound supports dozens of individual folded leaves.
 v=[];sides=9;rings=5
 for row in range(rings+1):
  theta=pi/2*row/rings;rr=rad*cos(theta);zz=.48+height*sin(theta)
  for k in range(sides):
   angle=2*pi*k/sides;v.append((cx+rr*cos(angle),cy+rr*sin(angle),zz))
 fs=[(row*sides+k,row*sides+(k+1)%sides,(row+1)*sides+(k+1)%sides,(row+1)*sides+k) for row in range(rings) for k in range(sides)]
 fol.mesh(v,fs,LEAF[variant%5])
 for j in range(36):
  a=random.random()*2*pi;rr=rad*sqrt(random.random());x=cx+rr*cos(a);y=cy+rr*sin(a);z=.49+height*sqrt(max(0,1-(rr/rad)**2));ori=random.random()*2*pi;ln=random.uniform(.08,.16);wd=ln*.38
  u=Vector((cos(ori),sin(ori),.24));v=Vector((-sin(ori),cos(ori),0));c=Vector((x,y,z))
  pts=[tuple(c-u*ln),tuple(c+v*wd),tuple(c+u*ln),tuple(c-v*wd),tuple(c+Vector((0,0,.035)))]
  fol.mesh(pts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],LEAF[(variant+j)%5])
def rosette(cx,cy,scale,variant):
 for leaf in range(16):
  a=2*pi*leaf/16+random.uniform(-.15,.15);length=scale*random.uniform(.48,.85);height=scale*random.uniform(.28,.54);width=scale*random.uniform(.035,.075);v=[]
  for k in range(7):
   t=k/6;rr=length*t;z=.50+height*sin(pi*t*.9);w=width*max(0,sin(pi*t))**.72
   for side in [-1,0,1]:v.append((cx+rr*cos(a)-side*w*sin(a),cy+rr*sin(a)+side*w*cos(a),z+(0.013 if side==0 else 0)))
  fol.mesh(v,[(k*3+j,k*3+j+1,(k+1)*3+j+1,(k+1)*3+j) for k in range(6) for j in range(2)],LEAF[(variant+leaf)%5])
for i,(x,y) in enumerate(islands):
 for k in range(32):
  a=random.uniform(0,2*pi);r=random.uniform(1.2,7.9);shrub(x+r*cos(a),y+r*sin(a),random.uniform(.28,.62),random.uniform(.30,.65),i+k)
 for k in range(10):
  a=2*pi*k/10+i*.17;rosette(x+7.6*cos(a),y+7.6*sin(a),random.uniform(.65,1.05),i+k)
for yy in [-102,-66]:
 for side in [-1,1]:
  for j in range(30):
   x=side*(4+random.random()*12);y=yy+random.uniform(-3,3);cylinder(fol,(x,y,.51),.18,.22,FLOWER,6)
# Quiet campus furniture is kept to garden edges, out of central circulation.
for i,(x,y,a) in enumerate([(-78,0,pi/2),(78,0,-pi/2),(-38,31,0),(38,31,0),(-70,73,0),(70,73,0),(-75,-75,0),(76,-77,0)]):bench('Quad garden bench '+str(i),(x,y,.34),angle=a,collection=COL)
lanterns=batch('Quad · globe lanterns',COL)
for x,y in [(-40,-20),(40,-20),(-40,20),(40,20),(-84,0),(84,0),(-14,-84),(14,-84),(-155,-53),(155,-53)]:
 cylinder(lanterns,(x,y,1.9),.06,3.3,METAL,12);lathe(lanterns,(x,y,3.55),[(.06,0),(.2,.06),(.27,.24),(.20,.42),(.06,.49)],OPAL,16)
# Burghers of Calais: restrained abstract bronze silhouettes on a low stone pad.
# They are decorative stand-ins, explicitly not claimed as sculptural replicas.
sculpt=batch('Memorial Court · abstract Rodin group placeholders',COL)
sculpt.box((8,-63,.65),(4.5,3.5,.6),TRIM)
for j in range(6):
 x=8+(j%3-1)*1.05;y=-63+(j//3-.5)*1.05
 lathe(sculpt,(x,y,.95),[(.30,0),(.34,.3),(.25,1.25),(.27,1.5),(.18,1.62),(.2,1.86),(.10,1.96)],METAL,9)

for b in BATCHES.values():
 ob=b.finish()
 if ob and 'botanical planting' in ob.name:
  for poly in ob.data.polygons:poly.use_smooth=True
sc=setup_lighting();sc.name='Main Quad · Stanford historic campus';sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
lightcol=COLS['90 · Cameras and lighting']
overview=camera('Main Quad · Campus overview',(-320,-455,124),(0,-5,12),lens=44,collection=lightcol)
camera('Main Quad · High aerial survey',(-285,-385,265),(0,-3,4),lens=46,collection=lightcol)
camera('Main Quad · Memorial Church detail',(12,-27,16),(0,38,15.5),lens=42,collection=lightcol)
camera('Main Quad · Courtyard portrait',(-11,-31,4.0),(0,38,12.0),lens=25,collection=lightcol)
camera('Main Quad · Through the arcade',(-56,-41,2.0),(0,38,12),lens=34,collection=lightcol)
camera('Main Quad · Memorial Court approach',(0,-144,3.3),(0,-44,10),lens=35,collection=lightcol)
sc.camera=overview;sc.render.resolution_x=2400;sc.render.resolution_y=1600;sc.render.resolution_percentage=100;sc.cycles.samples=128;sc.render.filepath=str(ROOT/'renders/main_quad_overview.png')
configure_viewport(sc,rendered=False)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.clip_end=4000
sources='''STANFORD MAIN QUAD — SOURCES AND ACCURACY
Photo-informed exterior reconstruction, 7 October 2026. Same material, daylight and landscape presentation family as Hoover Tower, Gates and Huang.
PRIMARY PLAN REFERENCES
Stanford Transportation Main Quad bike-rack map:
https://transportation.stanford.edu/getting-stanford/bike/engineering/bike-routes-and-maps
Stanford Outer Quad Tree Map, Sairus Patel, draft30Jan2026; Stanford Inner Quad Tree Map17Oct2025:
https://trees.stanford.edu/treewalks/treemaps.htm
The maps establish12inner teaching ranges, outer building numbers and massings, secondary gardens and8circular planted islands. Reference maps are available at the linked sources; they are not bundled.
PRIMARY PHOTO AND HISTORICAL REFERENCES
https://osep.stanford.edu/policies/policy-regarding-use-main-quadrangle-memorial-court
https://quake06.stanford.edu/5-evolution-engineering-methods
https://community.stanford.edu/regional-engagement/supporting-community
https://visit.stanford.edu/explore-campus
The historic586×246ft opencourt dimension, reported in A Visit to Stanford University (1905), gives a nominal metre scale. Individual building dimensions, bay counts, roof profiles, window placement and ornament are inferred, not measured or survey-grade. The model's axes follow the formal campus axes; front entrance is−Y and church is+Y, not geographic north.
Inner court is brick paving with eight raised botanical islands. MemorialCourt is a separate lawn-and-X-path garden. Open arcades, timber canopies, columns, capitals, voussoirs, windows and rolled roof tiles are geometric. Simplified secondary building forms retain plan topology and do not include room interiors. Garden species and exact planting positions are illustrative. The bronze figures are abstract placeholders for the Burghers of Calais, not detailed sculpture replicas. MemorialChurch has its own embedded source note from the module builder. Source photographs are reference-only and not bundled, except the explicitly credited church mosaic texture.
'''
t=bpy.data.texts.new('Main Quad · SOURCES AND ACCURACY');t.write(sources)
sc['model_scope']='Whole Main Quad:12inner teaching ranges,outer academic wings,MemorialCourt,eight circular gardens,open arcades and MemorialChurch;photo-informed exterior;estimated dimensions.'
sc['courtyard_nominal_metres']='178.6 ×75.0'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Main_Quad_Stanford.blend'))
meshes={o.data for o in sc.objects if o.type=='MESH'}
print(json.dumps({'file':str(ROOT/'Main_Quad_Stanford.blend'),'objects':len(sc.objects),'unique_vertices':sum(len(m.vertices) for m in meshes),'cameras':[o.name for o in sc.objects if o.type=='CAMERA']}))
