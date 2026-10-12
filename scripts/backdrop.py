"""Procedural broadleaf campus trees, forming an organic backdrop to Hoover Tower."""
import bpy
import math
import random
from mathutils import Vector


def build_backdrop():
    rng = random.Random(8837)
    coll = bpy.data.collections.get('07 · Landscape')
    if coll is None:
        coll = bpy.data.collections.new('07 · Landscape')
        bpy.context.scene.collection.children.link(coll)
    for ob in list(coll.objects):
        if ob.name.startswith('ENV_Backdrop'):
            bpy.data.objects.remove(ob, do_unlink=True)

    def mat(name, color, roughness=.87):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color = (*color, 1)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1)
        p.inputs['Roughness'].default_value = roughness
        return m
    bark = mat('ENV_Backdrop_Rough_Bark', (.165, .137, .095), .94)
    nodes = bark.node_tree.nodes
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 7
    noise.inputs['Detail'].default_value = 4
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .42
    bump.inputs['Distance'].default_value = .065
    bark.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    bark.node_tree.links.new(bump.outputs['Normal'], nodes.get('Principled BSDF').inputs['Normal'])
    greens = [mat('ENV_Backdrop_Leaf_%02d'%i, c, .73) for i,c in enumerate([
        (.077,.142,.045), (.108,.187,.064), (.153,.229,.075),
        (.195,.265,.092), (.128,.201,.080), (.082,.157,.075)])]

    def make(name, verts, faces, materials, indices=None, smooth=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        for m in materials:
            me.materials.append(m)
        me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        for i,p in enumerate(me.polygons):
            p.use_smooth = smooth
            if indices:
                p.material_index = indices[i]
        return ob

    def tube(vs, fs, points, radii, sides):
        start = len(vs)
        for j,p in enumerate(points):
            p = Vector(p)
            tangent = Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])
            tangent.normalize()
            ref = Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0))
            u = tangent.cross(ref).normalized()
            w = tangent.cross(u).normalized()
            for k in range(sides):
                a = k*math.tau/sides
                q = p+(u*math.cos(a)+w*math.sin(a))*radii[j]
                vs.append(tuple(q))
            if j:
                for k in range(sides):
                    a = start+(j-1)*sides+k
                    b = start+(j-1)*sides+(k+1)%sides
                    fs.append((a,b,b+sides,a+sides))
        fs.append(tuple(start+k for k in reversed(range(sides))))
        fs.append(tuple(start+(len(points)-1)*sides+k for k in range(sides)))

    trees=[(-35,30,22,12),(-50,40,25,13),(-5,48,24,12),
           (20,45,21,11),(42,30,20,10),(55,45,26,13)]
    for treeindex,(x,y,height,width) in enumerate(trees):
        bv,bf,lv,lf,li=[],[],[],[],[]
        base=Vector((x,y,0))
        lean=Vector((rng.uniform(-.8,.8),rng.uniform(-.8,.8),0))
        trunk=[]
        for j in range(11):
            t=j/10
            trunk.append(base+lean*t*t+Vector((.11*math.sin(t*7),.09*math.sin(t*11),height*.76*t)))
        tube(bv,bf,trunk,[.56*(1-j/13)**.8 for j in range(11)],11)
        for root in range(5):
            az=root*math.tau/5
            tip=base+Vector((math.cos(az)*1.25,math.sin(az)*1.25,.04))
            tube(bv,bf,[base+Vector((0,0,.45)),tip],[.27,.035],6)
        for main in range(13):
            tier=main/12
            az=main*2.3999632+rng.uniform(-.3,.3)
            spread=width*.42*(.65+.35*math.sin(tier*math.pi))
            radial=Vector((math.cos(az),math.sin(az),0))
            start=base+lean*.5+Vector((0,0,height*(.32+.29*tier)))
            endpoint=base+lean+radial*spread+Vector((0,0,height*(.55+.30*tier)))
            points=[start.lerp(endpoint,k/4)+Vector((0,0,-.42*math.sin(math.pi*k/4))) for k in range(5)]
            tube(bv,bf,points,[.25*(1-k/5)**1.15+.017 for k in range(5)],8)
            for secondary in range(3):
                a=az+(secondary-1)*.68+rng.uniform(-.25,.25)
                d=Vector((math.cos(a),math.sin(a),0))
                se=endpoint+d*rng.uniform(.65,1.45)+Vector((0,0,rng.uniform(.45,1.6)))
                ss=points[3] if secondary==0 else endpoint
                tube(bv,bf,[ss,ss.lerp(se,.55)+Vector((0,0,-.2)),se],[.085,.053,.025],6)
                for twig in range(3):
                    a2=a+(twig-1)*.85+rng.uniform(-.4,.4)
                    td=Vector((math.cos(a2),math.sin(a2),0))
                    te=se+td*rng.uniform(.5,1.25)+Vector((0,0,rng.uniform(-.4,1.05)))
                    tube(bv,bf,[se,se.lerp(te,.58),te],[.034,.021,.009],5)
                    # Forty separate, folded, lanceolate leaves form each airy
                    # terminal cluster. No opaque sphere or cone canopy surfaces.
                    radius=rng.uniform(.57,.97)
                    for leaf in range(40):
                        theta=rng.uniform(0,math.tau)
                        zz=rng.uniform(-1,1)
                        rr=math.sqrt(max(0,1-zz*zz))*rng.random()**.25
                        c=te+Vector((rr*math.cos(theta)*radius,rr*math.sin(theta)*radius,zz*radius*.64))
                        yaw=theta+rng.uniform(-.8,.8)
                        pitch=rng.uniform(-.55,.85)
                        direction=Vector((math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)))
                        cross=Vector((-math.sin(yaw),math.cos(yaw),rng.uniform(-.2,.2))).normalized()
                        normal=direction.cross(cross).normalized()
                        length=rng.uniform(.31,.64)
                        halfwidth=length*rng.uniform(.18,.31)
                        baseleaf=c-direction*length*.46
                        tip=c+direction*length*.54-normal*length*.12
                        idx=len(lv)
                        lv.extend([tuple(baseleaf),tuple(c-cross*halfwidth),tuple(tip),
                                   tuple(c+cross*halfwidth),tuple(c+normal*length*.065)])
                        lf.extend([(idx,idx+1,idx+4),(idx+1,idx+2,idx+4),
                                   (idx+2,idx+3,idx+4),(idx+3,idx,idx+4)])
                        color=rng.choices(range(6),[3,4,3,1,3,2])[0]
                        li.extend([color]*4)
        make('ENV_Backdrop_%02d_Trunk_and_Branches'%treeindex,bv,bf,[bark],smooth=True)
        make('ENV_Backdrop_%02d_Individual_Leaves'%treeindex,lv,lf,greens,li,smooth=True)
    return coll


if __name__ == '__main__':
    build_backdrop()
