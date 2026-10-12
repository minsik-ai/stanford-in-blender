"""Quiet, landscaped campus context for the Hoover Tower architectural model.
All assets are original procedural geometry; units are metres.
"""
import bpy
import math
import random
from mathutils import Vector


def build_landscape():
    random.seed(641)
    name = '07 · Landscape'
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    for ob in list(coll.objects):
        if ob.name.startswith('ENV_'):
            bpy.data.objects.remove(ob, do_unlink=True)

    def material(label, color, roughness=.78, noise_scale=None, bump=.0):
        name = 'ENV_' + label
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        m.diffuse_color = (*color, 1)
        n = m.node_tree.nodes
        n.clear()
        out = n.new('ShaderNodeOutputMaterial')
        bs = n.new('ShaderNodeBsdfPrincipled')
        bs.inputs['Base Color'].default_value = (*color, 1)
        bs.inputs['Roughness'].default_value = roughness
        m.node_tree.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
        if noise_scale is not None:
            tex = n.new('ShaderNodeTexNoise')
            tex.inputs['Scale'].default_value = noise_scale
            tex.inputs['Detail'].default_value = 3
            tex.inputs['Roughness'].default_value = .7
            ramp = n.new('ShaderNodeValToRGB')
            ramp.color_ramp.elements[0].position = .12
            ramp.color_ramp.elements[0].color = (*[x * .72 for x in color], 1)
            ramp.color_ramp.elements[1].position = .89
            ramp.color_ramp.elements[1].color = (*[min(1, x * 1.18) for x in color], 1)
            m.node_tree.links.new(tex.outputs['Fac'], ramp.inputs['Fac'])
            m.node_tree.links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
            if bump:
                b = n.new('ShaderNodeBump')
                b.inputs['Strength'].default_value = .3
                b.inputs['Distance'].default_value = bump
                m.node_tree.links.new(tex.outputs['Fac'], b.inputs['Height'])
                m.node_tree.links.new(b.outputs['Normal'], bs.inputs['Normal'])
        return m

    grass = material('Irrigated_Lawn', (.145, .225, .072), .97, 38, .035)
    stone = material('Warm_Paving', (.59, .565, .48), .83, 160, .008)
    cutstone = material('Pale_Stone_Edging', (.63, .59, .48), .84, 65, .018)
    grout = material('Paving_Joints', (.345, .332, .286), .9)
    soil = material('Planting_Mulch', (.098, .068, .043), .97, 28, .04)
    bark = material('Palm_Trunk', (.33, .285, .204), .91, 44, .055)
    trunkring = material('Palm_Leaf_Scars', (.26, .232, .177), .96, 65, .012)
    wood = material('Bench_Timber', (.295, .16, .065), .7, 8, .01)
    metal = material('Graphite_Metal', (.065, .08, .073), .51)
    shrubmats = [material('Shrub_Leaf_%02d' % i, c, .82) for i, c in enumerate([
        (.085, .155, .049), (.13, .205, .065), (.188, .266, .089), (.078, .134, .047)])]
    palmmats = [material('Palm_Frond_%02d' % i, c, .68) for i, c in enumerate([
        (.12, .215, .061), (.165, .279, .079), (.217, .33, .108), (.102, .18, .044), (.265, .329, .112)])]
    cypressmats = [material('Cypress_Foliage_%02d' % i, c, .9) for i, c in enumerate([
        (.06, .117, .075), (.092, .155, .082), (.122, .189, .104)])]

    def mesh(label, verts, faces, mats, ids=None, smooth=False):
        data = bpy.data.meshes.new('ENV_' + label)
        data.from_pydata(verts, [], faces)
        data.materials.clear()
        for mat in mats:
            data.materials.append(mat)
        data.update()
        obj = bpy.data.objects.new('ENV_' + label, data)
        coll.objects.link(obj)
        for i, p in enumerate(data.polygons):
            p.use_smooth = smooth
            if ids:
                p.material_index = ids[i]
        return obj

    def box(label, center, dims, mat, bevel=0):
        x, y, z = center
        a, b, c = [v / 2 for v in dims]
        vs = [(x+dx*a, y+dy*b, z+dz*c) for dx, dy, dz in
              [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
               (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
        ob = mesh(label, vs, [(0,3,2,1), (4,5,6,7), (0,1,5,4),
                             (1,2,6,5), (2,3,7,6), (3,0,4,7)], [mat])
        if bevel:
            mod = ob.modifiers.new('Soft manufactured edges', 'BEVEL')
            mod.width = bevel
            mod.segments = 2
        return ob

    def tube_accum(vs, fs, points, radii, sides=10):
        start = len(vs)
        for j, p in enumerate(points):
            p = Vector(p)
            if j == len(points)-1:
                tangent = p-Vector(points[j-1])
            else:
                tangent = Vector(points[j+1])-p
            tangent.normalize()
            ref = Vector((0,0,1)) if abs(tangent.z) < .95 else Vector((1,0,0))
            u = tangent.cross(ref).normalized()
            w = tangent.cross(u).normalized()
            for k in range(sides):
                q = p + radii[j]*(u*math.cos(k*math.tau/sides)+w*math.sin(k*math.tau/sides))
                vs.append(tuple(q))
            if j:
                for k in range(sides):
                    a = start+(j-1)*sides+k
                    b = start+(j-1)*sides+(k+1)%sides
                    fs.append((a,b,b+sides,a+sides))
        fs.append(tuple(start+k for k in reversed(range(sides))))
        fs.append(tuple(start+(len(points)-1)*sides+k for k in range(sides)))

    def disk(label, x, y, radius, top, mat, depth=.04, sides=64):
        v, f = [], []
        tube_accum(v, f, [(x,y,top-depth), (x,y,top)], [radius,radius], sides)
        return mesh(label, v, f, [mat])

    # The plaza is an actual ground treatment, with no display plinth or raised edge.
    box('Continuous_Ground', (0,0,-.115), (600,600,.16), grass)
    for label, center, size in [
        ('Front_Plaza', (0,-22,.0), (58,14,.06)),
        ('Rear_Plaza', (0,21,.0), (58,12,.06)),
        ('West_Plaza', (-23.5,0,.0), (11,30,.06)),
        ('East_Plaza', (23.5,0,.0), (11,30,.06)),
        ('Entry_Walk', (0,-65,.0), (9,72,.06)),
        ('West_Campus_Walk', (-64,0,.0), (70,5.5,.06)),
        ('East_Campus_Walk', (64,0,.0), (70,5.5,.06)),
        ('Rear_Campus_Walk', (0,55,.0), (7,56,.06)),
    ]:
        box(label, center, size, stone)

    # Wide, finely jointed square paving catches low-angle light without visual clutter.
    v, f = [], []
    def flat_rect(x0,x1,y0,y1,z=.031):
        i=len(v)
        v.extend([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)])
        f.append((i,i+1,i+2,i+3))
    for x in range(-27, 28, 3):
        flat_rect(x-.012,x+.012,-29,-15)
        flat_rect(x-.012,x+.012,15,27)
        if abs(x)>=18:
            flat_rect(x-.012,x+.012,-15,15)
    for y in range(-27,28,3):
        if y < -15 or y>15:
            flat_rect(-29,29,y-.012,y+.012)
        elif -15<=y<=15:
            flat_rect(-29,-18,y-.012,y+.012)
            flat_rect(18,29,y-.012,y+.012)
    for y in range(-98,-28,4):
        flat_rect(-4.5,4.5,y-.014,y+.014)
    mesh('Plaza_Expansion_Joints',v,f,[grout])

    def planting_ring(label,x,y,r):
        disk(label+'_Mulch',x,y,r,.058,soil)
        vs,fs=[],[]
        # Round limestone curbing only 8cm tall.
        n=64
        for z,rad in [(.03,r),(.03,r+.14),(.105,r),(.105,r+.14)]:
            vs.extend([(x+rad*math.cos(k*math.tau/n),y+rad*math.sin(k*math.tau/n),z) for k in range(n)])
        for k in range(n):
            l=(k+1)%n
            fs.extend([(k,l,l+2*n,k+2*n),(k+n,k+3*n,l+3*n,l+n),
                       (k+2*n,l+2*n,l+3*n,k+3*n)])
        mesh(label+'_Stone_Edge',vs,fs,[cutstone])

    def palm(label,x,y,height,lean,heading):
        trunkv,trunkf=[],[]
        center=[]
        segs=64
        for j in range(segs+1):
            t=j/segs
            center.append((x+lean*math.cos(heading)*t*t,
                           y+lean*math.sin(heading)*t*t,.08+height*t))
        radii=[.38-.115*j/segs+.035*math.cos(j/segs*math.pi) for j in range(segs+1)]
        tube_accum(trunkv,trunkf,center,radii,20)
        mesh(label+'_Curved_Trunk',trunkv,trunkf,[bark],smooth=True)
        # Thin, irregular old frond scars wrap around the slender trunk.
        rv,rf=[],[]
        for j in range(2,int(height/.21)):
            t=(j*.21)/height
            z=.08+height*t
            cx=x+lean*math.cos(heading)*t*t
            cy=y+lean*math.sin(heading)*t*t
            rad=.38-.115*t+.035*math.cos(t*math.pi)
            tube_accum(rv,rf,[(cx,cy,z-.012),(cx,cy,z+.012)], [rad+.011,rad+.013],14)
        mesh(label+'_Growth_Scars',rv,rf,[trunkring],smooth=True)
        crown=Vector(center[-1])
        lv,lf,lids=[],[],[]
        sv,sf=[],[]
        for j in range(26):
            az=j*2.39996323+random.uniform(-.15,.15)
            d=Vector((math.cos(az),math.sin(az),0))
            side=Vector((-math.sin(az),math.cos(az),0))
            # Older outer leaves arch downward; younger inner fronds sweep upward.
            ring=j%3
            length=random.uniform(3.3,4.4) if ring!=2 else random.uniform(2.8,3.6)
            rise=[1.5,2.1,3.2][ring]+random.uniform(-.2,.2)
            drop=[2.7,2.1,1.0][ring]
            def spine(t):
                return crown+d*(length*t)+Vector((0,0,rise*math.sin(t*math.pi*.68)-drop*t*t))
            pts=[tuple(spine(k/20)) for k in range(21)]
            tube_accum(sv,sf,pts,[.043*(1-k/21)**.72+.006 for k in range(21)],5)
            for n in range(1,27):
                t=n/28
                mid=spine(t)
                spread=.88*(math.sin(math.pi*t)**.66)*(length/4)+.035
                for sign in [-1,1]:
                    # Every narrow leaflet has a peaked cross-section, tapered tip,
                    # swept plan, and drooping outer end rather than a flat fan.
                    n0=len(lv)
                    sweep=d*(.21+.22*t)
                    for step in range(5):
                        u=step/4
                        q=mid+side*(sign*spread*u)+sweep*u+Vector((0,0,-.37*u*u+.08*math.sin(math.pi*u)))
                        half=.052*(math.sin(math.pi*u*.96)**.62)+(.012 if step==0 else 0)
                        if step==4:
                            half=.001
                        lv.extend([tuple(q-d*half),tuple(q+Vector((0,0,.017*math.sin(math.pi*u)))),tuple(q+d*half)])
                    mi=random.choices(range(5),[3,4,2,2,1])[0]
                    for step in range(4):
                        a=n0+step*3
                        lf.extend([(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)])
                        lids.extend([mi,mi])
        mesh(label+'_Pinnate_Foliage',lv,lf,palmmats,lids,smooth=True)
        mesh(label+'_Frond_Rachis',sv,sf,[palmmats[1]],smooth=True)

    for i,(x,y,h,l,a) in enumerate([(-23,-6,17,.85,.8),(24,14,18.3,.8,2.1),(-28,22,16.3,1.15,1.4)]):
        planting_ring('Palm_%02d'%i,x,y,1.55)
        palm('Palm_%02d'%i,x,y,h,l,a)

    # Small individual leaves form irregular shrubs; no faceted sphere canopies.
    def ellipsoid_accum(vs,fs,ids,center,radii,matid,segments=8,rings=5):
        base=len(vs)
        x,y,z=center
        rx,ry,rz=radii
        for j in range(rings+1):
            lat=-math.pi/2+math.pi*j/rings
            for k in range(segments):
                az=math.tau*k/segments
                jitter=1+random.uniform(-.07,.07)
                vs.append((x+rx*math.cos(lat)*math.cos(az)*jitter,
                           y+ry*math.cos(lat)*math.sin(az)*jitter,z+rz*math.sin(lat)))
        for j in range(rings):
            for k in range(segments):
                a=base+j*segments+k
                b=base+j*segments+(k+1)%segments
                fs.append((a,b,b+segments,a+segments));ids.append(matid)

    shrubv,shrubf,shrubids=[],[],[]
    # Leave the approach and all entrances open; planting sits beyond the plaza.
    beds=[(-35,-18,5,2),(34,-15,4,2),(-36,22,5,2),(34,28,4,2),(-17,33,3,2),(16,33,3,2)]
    for bi,(bx,by,rx,ry) in enumerate(beds):
        # Low elliptical mulch surface in the lawn, tucked around clusters.
        verts=[(bx,by,.018)]+[(bx+rx*math.cos(k*math.tau/48),by+ry*math.sin(k*math.tau/48),.018) for k in range(48)]
        faces=[(0,k+1,(k+1)%48+1) for k in range(48)]
        mesh('Shrub_Bed_%02d'%bi,verts,faces,[soil])
        for j in range(14):
            u=random.random()**.5
            a=random.random()*math.tau
            cx=bx+rx*.85*u*math.cos(a);cy=by+ry*.8*u*math.sin(a)
            size=random.uniform(.45,.75)
            ellipsoid_accum(shrubv,shrubf,shrubids,(cx,cy,.36),(size,size*.82,.44),random.randrange(4))
            for k in range(20):
                angle=random.random()*math.tau
                dz=random.uniform(-.15,.32)
                rr=size*random.uniform(.62,1)
                ellipsoid_accum(shrubv,shrubf,shrubids,(cx+rr*math.cos(angle),cy+rr*math.sin(angle),.43+dz),(.11,.08,.075),random.randrange(4),5,3)
    mesh('Low_Shrub_Planting',shrubv,shrubf,shrubmats,shrubids,smooth=True)

    # A restrained backdrop of narrow Italian cypresses on the far lawn.
    cv,cf,ci=[],[],[]
    tv,tf=[],[]
    for x,y,h in [(-44,40,12),(-40,44,13.8),(40,43,13),(45,39,11.8),(-53,15,10.5),(54,24,11.5)]:
        tube_accum(tv,tf,[(x,y,.02),(x+.15,y,h*.88)],[.23,.10],10)
        for j in range(100):
            t=random.uniform(.12,.99)
            z=h*t
            r=(1.25*(math.sin(t*math.pi)**.75))
            a=random.uniform(0,math.tau)
            rr=random.uniform(.1,.7)*r
            ellipsoid_accum(cv,cf,ci,(x+rr*math.cos(a),y+rr*math.sin(a),z),
                            (r*random.uniform(.4,.7),r*random.uniform(.4,.7),random.uniform(.55,.95)),
                            random.randrange(3),7,4)
    mesh('Cypress_Trunks',tv,tf,[bark],smooth=True)
    mesh('Cypress_Crowns',cv,cf,cypressmats,ci,smooth=True)

    # Two unobtrusive campus benches face the forecourt.
    for i,(x,y) in enumerate([(-21,-25.7),(21,-25.7)]):
        for leg in [-.7,.7]:
            box('Bench_%d_Leg_%s'%(i,leg),(x+leg,y,.26),(.065,.5,.46),metal,.012)
        for k in range(5):
            box('Bench_%d_Seat_%d'%(i,k),(x,y-.25+k*.125,.52),(2.1,.105,.065),wood,.013)
        for leg in [-.7,.7]:
            box('Bench_%d_Back_Support_%s'%(i,leg),(x+leg,y+.28,.73),(.045,.045,.56),metal,.009)
        for k in range(3):
            box('Bench_%d_Back_%d'%(i,k),(x,y+.29,.73+k*.115),(2.1,.055,.085),wood,.012)
    for i,(x,y) in enumerate([(-6.2,-34),(6.2,-34),(-6.2,-51),(6.2,-51)]):
        box('Walk_Light_%02d'%i,(x,y,.43),(.16,.16,.84),metal,.022)
        box('Walk_Light_Cap_%02d'%i,(x,y,.785),(.17,.17,.035),cutstone,.01)

    # Ground plane is intentionally large: no presentation-base edges in any view.
    return coll


if __name__ == '__main__':
    build_landscape()
