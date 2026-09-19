# 烟雨江南 / 雪月江南 — editable procedural courtyard, Blender 4.5
# Run in Blender Text Editor. Change this central parameter block and rerun.
import bpy, math, random, os, json
from mathutils import Vector
from math import sin, cos, pi

# output_dir 契约：该目录下须有 textures/ 子目录（贴图），脚本在其下写出
# Jiangnan.blend / scene_statistics.json / renders/。可用环境变量 JN_OUT 覆盖；
# 默认取当前 .blend 所在目录——仓库内 Jiangnan.blend 位于根目录，即开箱即用。
_DEFAULT_OUT = os.environ.get('JN_OUT') or (os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd())
PARAMS = dict(seed=36, weather=0, wind=0.7, blossom_density=1.3,
              rain_count=750, snow_count=480, resolution=1600, samples=96,
              art_upgrade=True, texture_strength=0.82,
              stage=5, render=False, output_dir=_DEFAULT_OUT)
# weather: 0 = mist / rain, 1 = snow; stage: 1 courtyard,2 plants,3 weather,4 sky,5 light
P=PARAMS; PREFIX='JN_'; SCENE='烟雨江南 · 雪月江南'
def enum(obj, prop, value):
    items=obj.bl_rna.properties[prop].enum_items
    if value in [i.identifier for i in items]: setattr(obj,prop,value)
def mesh(name,v,f,mat,col):
    d=bpy.data.meshes.new(PREFIX+name); d.from_pydata(v,[],f); d.update()
    o=bpy.data.objects.new(PREFIX+name,d); col.objects.link(o)
    if mat: d.materials.append(mat)
    return o
def box(name,loc,size,mat,col,bev=0):
    x,y,z=[q/2 for q in size]
    v=[(a*x+loc[0],b*y+loc[1],c*z+loc[2]) for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    o=mesh(name,v,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],mat,col)
    if bev:
        m=o.modifiers.new('柔化石缘','BEVEL'); m.width=bev; m.segments=2
    return o
def uv(name,loc,scale,mat,col,seg=16,rings=8):
    v=[]; f=[]
    for j in range(rings+1):
        a=pi*j/rings
        for i in range(seg):
            b=2*pi*i/seg; v.append((loc[0]+scale[0]*sin(a)*cos(b),loc[1]+scale[1]*sin(a)*sin(b),loc[2]+scale[2]*cos(a)))
    for j in range(rings):
        for i in range(seg):
            a=j*seg+i; b=j*seg+(i+1)%seg; f.append((a,a+seg,b+seg,b))
    o=mesh(name,v,f,mat,col)
    for p in o.data.polygons:p.use_smooth=True
    return o
def line(name,pts,radius,mat,col,radii=None):
    d=bpy.data.curves.new(PREFIX+name,'CURVE'); d.dimensions='3D'; d.resolution_u=12; d.bevel_depth=radius; d.bevel_resolution=3
    s=d.splines.new('BEZIER'); s.bezier_points.add(len(pts)-1)
    for i,(p,co) in enumerate(zip(s.bezier_points,pts)):
        p.co=co
        enum(p,'handle_left_type','AUTO'); enum(p,'handle_right_type','AUTO')
        if radii:p.radius=radii[i]
    o=bpy.data.objects.new(PREFIX+name,d);col.objects.link(o);d.materials.append(mat);return o
def material(name,color,rough=.5,noise=0,metal=0,emit=0):
    m=bpy.data.materials.new(PREFIX+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n=m.node_tree.nodes; l=m.node_tree.links; b=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*color,1); b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    if emit:b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emit
    if noise:
        t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=noise;t.inputs['Detail'].default_value=4
        tc=n.new('ShaderNodeTexCoord');l.new(tc.outputs['Object'],t.inputs['Vector'])
        r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.15;r.color_ramp.elements[0].color=tuple(c*.48 for c in color)+(1,)
        r.color_ramp.elements[1].position=.85;r.color_ramp.elements[1].color=(*color,1)
        l.new(t.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],b.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.06
        l.new(t.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    return m
def light(name,loc,color,energy,size=1,target=None,kind='AREA'):
    d=bpy.data.lights.new(PREFIX+name,kind);d.color=color;d.energy=energy
    if kind=='AREA':d.shape='DISK' if 'DISK' in [i.identifier for i in d.bl_rna.properties['shape'].enum_items] else d.shape;d.size=size
    elif kind=='POINT':d.shadow_soft_size=size
    o=bpy.data.objects.new(PREFIX+name,d);C['light'].objects.link(o);o.location=loc
    if target:o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o
def camera(name,loc,target,lens=45,ortho=0):
    d=bpy.data.cameras.new(PREFIX+name);o=bpy.data.objects.new(PREFIX+name,d);C['camera'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=250
    if ortho:d.type='ORTHO';d.ortho_scale=ortho
    return o
def start():
    global S,C,M,R,CTRL
    random.seed(P['seed']);R=random
    old=bpy.data.scenes.get(SCENE)
    if old:
        for o in list(old.objects):
            if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.scenes.remove(old)
    for c in list(bpy.data.collections):
        if c.name.startswith(PREFIX):bpy.data.collections.remove(c)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX) and m.users==0:bpy.data.materials.remove(m)
    if bpy.app.background:
        S=bpy.context.scene;S.name=SCENE
    else:
        S=bpy.data.scenes.new(SCENE);bpy.context.window.scene=S
    C={}
    for key,label in [('court','01_庭院_墙瓦月门'),('water','02_水石_汀步'),('tree','03_梅树_可动花枝'),('dew','04_露珠'),('rain','05_夜雨'),('snow','06_落雪'),('cover','07_薄雪覆盖'),('sky','08_云月远山'),('light','09_冷月暖灯'),('camera','10_验证相机'),('control','00_总控')]:
        c=bpy.data.collections.new(PREFIX+label);S.collection.children.link(c);C[key]=c
    CTRL=bpy.data.objects.new(PREFIX+'总控_天气0雨1雪_风力',None);C['control'].objects.link(CTRL);CTRL['Weather']=P['weather'];CTRL['Wind']=P['wind']
    CTRL.id_properties_ui('Weather').update(min=0,max=1,description='0 烟雨 / 1 雪夜：驱动雨、雪、积雪互斥切换')
    CTRL.id_properties_ui('Wind').update(min=0,max=2,description='梅枝摇摆强度')
    M={k:material(k,*args) for k,args in {
      'plaster':((.62,.66,.62),.82,5),'tile':((.045,.067,.075),.3,12),'edge':((.16,.20,.20),.58,14),
      'stone':((.27,.31,.29),.38,8),'darkstone':((.07,.105,.10),.52,8),'wood':((.075,.043,.025),.55,7),
      'bronze':((.28,.18,.07),.28,0,.7),'moss':((.065,.12,.064),.88,18),
      'bark':((.11,.074,.050),.82,13),'pink':((.67,.19,.25),.4,0),'ivory':((.91,.65,.62),.46,0),
      'gold':((.7,.39,.12),.45,0),'paper':((1,.42,.10),.6,0,0,2.4),'snow':((.8,.87,.91),.7,25),
      'water':((.055,.13,.145),.14,0,.35),'dew':((.66,.84,.85),.07,0),
      'rain':((.22,.34,.39),.22,0,0,.025)}.items()}
    for n in M['plaster'].node_tree.nodes:
        if n.type=='VALTORGB':n.color_ramp.elements[0].color=(.51,.55,.51,1)
        if n.type=='BUMP':n.inputs['Strength'].default_value=.12;n.inputs['Distance'].default_value=.018
    b=next(n for n in M['dew'].node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Transmission Weight'].default_value=.92;b.inputs['IOR'].default_value=1.333
    b=next(n for n in M['water'].node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Coat Weight'].default_value=.5
    S.world=bpy.data.worlds.new(PREFIX+'夜色');S.world.use_nodes=True
    bg=next(n for n in S.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.085,.13,.18,1);bg.inputs[1].default_value=.35
    try:S.render.engine='CYCLES'
    except TypeError:pass
    S.cycles.samples=P['samples'];S.cycles.use_denoising=True
    S.render.resolution_x=P['resolution'];S.render.resolution_y=int(P['resolution']*.625);S.render.resolution_percentage=100
    S.render.image_settings.file_format='PNG';S.render.fps=24;S.frame_start=1;S.frame_end=240
    S.camera=camera('三分之四',(12,-26,9),(0,2,3.5),43)
    camera('正面',(1,-26,7),(0,3,3.5),43)
    camera('顶视',(0,-.1,31),(0,0,0),45,35)
    light('施工柔光',(0,-5,13),(.68,.8,1),2200,12,(0,0,0))
def roof(name,cx,cy,z,w,d,col):
    # Curved Chinese roof, individually ridged clay tile courses, lifted corners.
    v=[];f=[]
    nx=max(12,int(w/.22));ny=max(6,int(d/.3))
    for side in [-1,1]:
        for i in range(nx):
            x0=-w/2+w*i/nx;x1=-w/2+w*(i+1)/nx
            for j in range(ny):
                t0=j/ny;t1=(j+1)/ny
                k=len(v)
                for x,t in [(x0,t0),(x1,t0),(x1,t1),(x0,t1)]:
                    zz=z+1.15*(1-t)**1.8+.24*(abs(x)/(w/2))**8*t**3
                    v.append((cx+x,cy+side*(d/2)*t,zz))
                f.append(tuple(range(k,k+4)))
        for i in range(nx+1):
            x=-w/2+w*i/nx
            pts=[(cx+x,cy+side*d/2*t,z+1.15*(1-t)**1.8+.24*(abs(x)/(w/2))**8*t**3+.025) for t in [0,.2,.4,.6,.8,1]]
            line(name+'_筒瓦',pts,.045,M['tile'],col)
    o=mesh(name+'_瓦面',v,f,M['tile'],col)
    line(name+'_正脊',[(cx-w/2-.1,cy,z+1.45),(cx-w/2+.5,cy,z+1.23),(cx,cy,z+1.22),(cx+w/2-.5,cy,z+1.23),(cx+w/2+.1,cy,z+1.45)],.11,M['edge'],col)
    for side in [-1,1]:
        line(name+'_檐口',[(cx+x,cy+side*d/2,z+.24*(abs(x)/(w/2))**8) for x in [-w/2,-w/3,0,w/3,w/2]],.075,M['edge'],col)
    return o
def lantern(x,y,h=1):
    c=C['court'];s=h
    for z,w,dz in [(.08,.85,.16),(.22,.65,.12),(.62,.25,.7),(1.02,.65,.14),(1.58,.75,.15)]:box('石灯_座',(x,y,z*s),(w*s,w*s,dz*s),M['stone'],c,.035)
    box('石灯_暖芯',(x,y,1.3*s),(.32*s,.32*s,.44*s),M['paper'],c,.02)
    for dx in [-.25,.25]:
        for dy in [-.25,.25]:box('石灯_立柱',(x+dx*s,y+dy*s,1.3*s),(.09*s,.09*s,.48*s),M['darkstone'],c,.015)
    v=[(x+a*s,y+b*s,z*s) for a,b,z in [(-.55,-.55,1.62),(.55,-.55,1.62),(.55,.55,1.62),(-.55,.55,1.62),(0,0,2.0)]]
    mesh('石灯_攒尖顶',v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],M['darkstone'],c)
    uv('石灯_宝珠',(x,y,2.03*s),(.09*s,)*3,M['stone'],c)
    light('灯火',(x,y,1.3*s),(1,.40,.12),65*s,.26,kind='POINT')
def courtyard():
    c=C['court'];w=C['water']
    box('庭基',(0,0,-.45),(23,21,.8),M['darkstone'],c,.18)
    box('庭土',(0,1,-.03),(21,18,.15),M['moss'],w,.15)
    # Pond and paved edges: a quiet, broad foreground mirror.
    box('静水',(0,-4.1,.08),(16,7,.08),M['water'],w,.1)
    for side in [-1,1]:
        for j in range(15):box('池岸石',(side*8.2,-7.5+j*.49,.13),(.55,.46,.3),M['stone'],w,.055)
    for j in range(32):box('池沿',( -7.8+j*.5,-7.75,.13),(.47,.35,.3),M['stone'],w,.04)
    for row in range(6):
        for i in range(26):
            x=-9.5+i*.76+(row%2)*.34;y=.05+row*.65
            box('庭院青石',(x,y,.09),(.73,.62,.16),M['stone'] if R.random()>.23 else M['darkstone'],w,.025)
    # Stepping stones describe a gentle S across the pond.
    for i in range(12):
        y=-7.3+i*.68;x=1.3*sin(i*.37)-.6
        o=box('曲水汀步',(x,y,.22),(1.32,.57,.25),M['stone'],w,.08)
    # Rear wall segments surround a genuine circular aperture, no boolean dependency.
    gx=1.4;gy=5.2;zc=2.25;rad=2.0;H=4.75
    box('白墙_西',(-5.3,gy,H/2),(9.4,.48,H),M['plaster'],c,.035)
    box('白墙_东',(7.3,gy,H/2),(7.8,.48,H),M['plaster'],c,.035)
    v=[];f=[]
    for i in range(96):
        a=2*pi*i/96;b=2*pi*(i+1)/96
        # radial strip to surrounding square, with front and rear faces
        inner=[(gx+rad*cos(t),zc+rad*sin(t)) for t in [a,b]]
        outer=[]
        for t in [a,b]:
            dx=cos(t);dz=sin(t);fac=min(2.01/max(abs(dx),1e-6),((H-zc) if dz>0 else zc)/max(abs(dz),1e-6))
            outer.append((gx+fac*dx,zc+fac*dz))
        k=len(v)
        for y in [gy-.24,gy+.24]:
            v.extend([(inner[0][0],y,inner[0][1]),(inner[1][0],y,inner[1][1]),(outer[1][0],y,outer[1][1]),(outer[0][0],y,outer[0][1])])
        f.extend([(k,k+1,k+2,k+3),(k+7,k+6,k+5,k+4),(k,k+4,k+5,k+1)])
    mesh('月洞门_贯通墙体',v,f,M['plaster'],c)
    for i in range(64):
        a=2*pi*i/64;b=2*pi*(i+.94)/64;v=[]
        for y in [gy-.32,gy+.32]:
            for r,t in [(rad,a),(rad,b),(rad+.19,b),(rad+.19,a)]:v.append((gx+r*cos(t),y,zc+r*sin(t)))
        mesh('月门_弧形砖券',v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7)],M['edge'],c)
    for x,width in [(-5.3,9.4),(7.3,7.8)]:
        box('墙脚勒石',(x,gy-.02,.23),(width,.57,.46),M['darkstone'],c,.03)
    roof('院墙黛瓦',.5,gy,4.77,22,1.6,c)
    # East return wall with a lattice window.
    box('东墙',(10.2,1.8,1.65),(.42,6.3,3.3),M['plaster'],c,.03)
    for y in [-.4,2.1]:
        box('漏窗暗底',(9.97,y,1.8),(.025,1.4,1.35),M['wood'],c)
        for t in [-.6,-.3,0,.3,.6]:
            box('漏窗格',(9.93,y+t,1.8),(.07,.055,1.4),M['edge'],c,.01)
            box('漏窗格',(9.93,y,1.8+t),(.07,1.4,.055),M['edge'],c,.01)
    # West tea pavilion, airy open timber bay.
    box('听雨轩台基',(-7,1.2,.18),(5.2,5.3,.36),M['stone'],c,.09)
    for x in [-9,-5]:
        for y in [-.8,3.2]:
            box('柱础',(x,y,.43),(.55,.55,.45),M['edge'],c,.06)
            line('木柱',[(x,y,.6),(x,y,3.95)],.14,M['wood'],c)
    for y in [-.8,3.2]:box('轩梁',(-7,y,3.8),(4.7,.24,.32),M['wood'],c,.035)
    for x in [-9,-5]:box('轩梁',(x,1.2,3.8),(.24,4.5,.32),M['wood'],c,.035)
    roof('听雨轩',-7,1.2,3.9,6,5.8,c)
    for i in range(15):
        x=-8.8+i*.26;box('轩后竹格',(x,3.2,2.0),(.055,.08,2.8),M['wood'],c,.012)
    box('茶案',(-7,1.5,1.05),(2.3,.85,.16),M['wood'],c,.05)
    for x in [-7.8,-6.2]:box('茶案脚',(x,1.5,.65),(.14,.65,.8),M['wood'],c,.025)
    uv('茶壶',(-7,1.5,1.25),(.16,.13,.14),M['darkstone'],c)
    for x in [-7.5,-6.5]:uv('茶盏',(x,1.45,1.19),(.075,.075,.05),M['bronze'],c)
    for x,y,s in [(-3.2,-2.2,1.0),(5.2,.3,1.15),(3.8,6.9,.85),(-8.2,-5.8,.8)]:lantern(x,y,s)
    # Borrowed scenery behind the opening and scholar stones by water.
    for i in range(7):box('门后石径',(1.4+.25*sin(i),6+i*.8,.12),(1.5,.7,.18),M['stone'],w,.05)
    for x,y,s in [(-4.2,-.4,1.0),(6.7,-1.4,1.5),(7.4,-2.0,.8),(-8.1,-3.5,.7)]:
        for j in range(3):
            o=uv('太湖叠石',(x+R.uniform(-.3,.3),y+R.uniform(-.3,.3),s*(.35+j*.42)),(s*(.65-j*.12),s*.4,s*.5),M['stone'],w,12,8)
            for vert in o.data.vertices:vert.co+=Vector((R.uniform(-.12,.12),R.uniform(-.12,.12),R.uniform(-.10,.10)))
    # Stone bench, invitation to stillness.
    box('观水石榻',(5.0,1.8,.62),(2.4,.7,.2),M['stone'],c,.07)
    for x in [4.2,5.8]:box('石榻脚',(x,1.8,.32),(.35,.55,.5),M['darkstone'],c,.03)
def driven(o,path,index,expression,prop='Wind'):
    d=o.driver_add(path,index).driver if index is not None else o.driver_add(path).driver
    d.type='SCRIPTED';v=d.variables.new();v.name='v'
    enum(v,'type','SINGLE_PROP');v.targets[0].id=CTRL;v.targets[0].data_path='["'+prop+'"]';d.expression=expression
def attach(o,parent):
    bpy.context.view_layer.update();o.parent=parent;o.matrix_parent_inverse=parent.matrix_world.inverted()
def petals(name,positions,col,parent=None):
    vv=[];ff=[];uvs=[];stamenv=[];stamenf=[]
    for pos,size in positions:
        normal=Vector((R.uniform(-.5,.5),R.uniform(-1,-.3),R.uniform(.3,1))).normalized()
        u=normal.cross(Vector((0,0,1))).normalized();v=normal.cross(u)
        angle=R.random()*6.28
        for k in range(5):
            a=angle+2*pi*k/5;axis=u*cos(a)+v*sin(a);side=-u*sin(a)+v*cos(a)
            center=Vector(pos);idx=len(vv)
            vv.append(tuple(center+normal*.009));uvs.append((.5,.16))
            for j in range(9):
                t=2*pi*j/8;p=center+axis*size*(.53+.53*cos(t))+side*size*.43*sin(t)+normal*size*.15*(1+cos(t))
                vv.append(tuple(p));uvs.append((.5+.33*sin(t),.5+.33*cos(t)))
            for j in range(8):ff.append((idx,idx+j+1,idx+j+2))
        # Raised pollen centers remain 3D instead of being painted into albedo.
        center=Vector(pos)+normal*size*.17;idx=len(stamenv);r=size*.14
        stamenv.extend([tuple(center+v*r),tuple(center-v*r),tuple(center+u*r),tuple(center-u*r),tuple(center+normal*r)])
        stamenf.extend([(idx,idx+2,idx+4),(idx+2,idx+1,idx+4),(idx+1,idx+3,idx+4),(idx+3,idx,idx+4)])
    o=mesh(name,vv,ff,M['ivory'] if R.random()<.3 else M['pink'],col)
    layer=o.data.uv_layers.new(name='花瓣UV')
    for loop in o.data.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    st=mesh(name+'_花蕊',stamenv,stamenf,M['gold'],col)
    if parent:attach(o,parent)
    if parent:attach(st,parent)
    return o
def vegetation():
    c=C['tree']
    def tree(base,scale,mirror=1):
        bx,by,bz=base
        def pt(x,y,z):return Vector((bx+x*scale*mirror,by+y*scale,bz+z*scale))
        trunk=[pt(0,0,0),pt(-.15,.05,.9),pt(.18,.12,1.8),pt(.35,0,2.6),pt(.1,.12,3.3),pt(.6,.1,4.2)]
        line('老梅_苍干',trunk,.24*scale,M['bark'],c,[1,.85,.64,.49,.28,.03])
        for k in range(7):
            a=k*2*pi/7;line('梅根',[pt(cos(a)*.7,sin(a)*.55,.07),pt(cos(a)*.35,sin(a)*.3,.2),pt(0,0,.5)],.09*scale,M['bark'],c,[.1,.7,1])
        for j in range(11):
            root=trunk[2+j%3];ang=j*2.399;length=R.uniform(1.5,2.8)*scale
            direction=Vector((cos(ang)*mirror,sin(ang)*.65,R.uniform(.25,.65)))
            end=root+direction*length
            mid=root+direction*length*.42+Vector((0,0,-.18*scale))
            branch=line('老梅_横斜枝',[root,mid,end],.085*scale,M['bark'],c,[1,.6,.06])
            pivot=bpy.data.objects.new(PREFIX+'风动枝组',None);c.objects.link(pivot);pivot.location=root
            attach(branch,pivot);driven(pivot,'rotation_euler',1,f'v*0.012*sin(frame*0.033+{j})');driven(pivot,'rotation_euler',0,f'v*0.009*sin(frame*0.024+{j*1.7})')
            blooms=[]
            for k in range(7):
                t=.25+k*.105;start=mid.lerp(end,t)
                side=Vector((-direction.y,direction.x,.5)).normalized()*(1 if k%2 else -1)
                tip=start+side*R.uniform(.35,.8)*scale+Vector((0,0,.22*scale))
                twig=line('老梅_花梢',[start,start.lerp(tip,.5)+Vector((0,0,.1)),tip],.024*scale,M['bark'],c,[1,.6,.04]);attach(twig,pivot)
                for b in range(int(R.uniform(4,8)*P['blossom_density'])):
                    p=start.lerp(tip,R.uniform(.2,1))+Vector((R.uniform(-.05,.05),R.uniform(-.05,.05),R.uniform(-.05,.05)))
                    size=R.uniform(.048,.085)*scale;blooms.append((p,size))
                    if R.random()<.15:
                        dew=uv('花尖露珠',p+Vector((0,-.02,-.045*scale)),(.012*scale,.012*scale,.019*scale),M['dew'],C['dew'],8,6);attach(dew,pivot)
            petals('五瓣梅_枝组',blooms,c,pivot)
        for j in range(8):
            a=R.random()*6.28;uv('树脚苔石',(bx+cos(a)*.6,by+sin(a)*.5,.15),(.3,.2,.15),M['moss'],C['water'],12,6)
    tree((-3.55,1.65,.18),1.25,1)
    tree((7.4,2.2,.18),1.05,-1)
    tree((3.9,8.2,.1),.8,-1)
    # Bamboo borrowed beyond the wall, arranged as sparse calligraphic strokes.
    for j in range(22):
        x=R.uniform(-8,9);y=R.uniform(7.8,10);h=R.uniform(4.4,7.4)
        line('远竹_竹竿',[(x,y,0),(x+.15,y,h*.5),(x+.35,y,h)],.035,M['moss'],c,[1,.8,.2])
        vv=[];ff=[]
        for k in range(22):
            z=R.uniform(h*.48,h);side=R.choice([-1,1]);p=Vector((x+.25,y,z));end=p+Vector((side*R.uniform(.2,.75),R.uniform(-.3,.3),R.uniform(-.1,.4)))
            q=end+Vector((side*.3,0,-.13));i=len(vv);vv.extend([p,end+Vector((0,-.065,.06)),q,end+Vector((0,.065,-.06))]);ff.append((i,i+1,i+2,i+3))
        mesh('远竹_披叶',vv,ff,M['moss'],c)
    # Grasses soften the water's hard stone edge.
    for j in range(70):
        x=R.choice([-1,1])*R.uniform(7.6,9.6);y=R.uniform(-7,3);vv=[];ff=[]
        for k in range(9):
            p=Vector((x+R.uniform(-.15,.15),y+R.uniform(-.15,.15),.05));h=R.uniform(.18,.65);i=len(vv)
            vv.extend([p+Vector((-.025,0,0)),p+Vector((.025,0,0)),p+Vector((R.uniform(-.25,.25),R.uniform(-.1,.1),h))]);ff.append((i,i+1,i+2))
        mesh('苔岸细草',vv,ff,M['moss'],c)
    petals('水上落梅',[(Vector((R.uniform(-6,6),R.uniform(-7,-1),.13)),R.uniform(.025,.05)) for i in range(95)],C['water'])
def weather_visibility(o,snow):
    expr='v < 0.5' if snow else 'v >= 0.5'
    driven(o,'hide_render',None,expr,'Weather');driven(o,'hide_viewport',None,expr,'Weather')
def weather():
    # Native drivers: no external handlers or simulation cache needed after reopening.
    for snow,count in [(False,P['rain_count']),(True,P['snow_count'])]:
        col=C['snow' if snow else 'rain'];proto=None
        for i in range(count):
            x=R.uniform(-10,10);y=R.uniform(-8,9);z=R.uniform(.3,10)
            if proto is None:
                if snow:proto=uv('雪粒',(0,0,0),(.024,.018,.024),M['snow'],col,6,4)
                else:proto=line('雨丝',[(0,0,0),(.016,.008,-.17)],.0017,M['rain'],col)
                o=proto
            else:o=bpy.data.objects.new(PREFIX+('雪粒' if snow else '雨丝'),proto.data);col.objects.link(o)
            o.location=(x,y,z);s=R.uniform(.6,1.4);o.scale=(s,s,s)
            speed=R.uniform(.032,.058) if snow else R.uniform(.22,.34)
            driven(o,'location',2,f'0.3+(({z:.5f}-frame*{speed:.5f})%9.7)')
            if snow:driven(o,'location',0,f'{x:.5f}+0.18*v*sin(frame*0.04+{i:.3f})')
            weather_visibility(o,snow)
    # Growing rain rings; omitted in the snow state.
    for i in range(38):
        x=R.uniform(-7.4,7.4);y=R.uniform(-7.2,-1.2)
        o=line('雨落涟漪',[(.25*cos(t*2*pi/32),.25*sin(t*2*pi/32),0) for t in range(33)],.0016,M['rain'],C['rain']);o.location=(x,y,.127)
        for ax in [0,1]:driven(o,'scale',ax,f'0.08+((frame+{i*7})%42)/30')
        weather_visibility(o,False)
    # Thin accumulation follows actual roof and stepping-stone surfaces.
    for o in list(C['court'].objects):
        if '瓦面' in o.name:
            cp=bpy.data.objects.new(PREFIX+'瓦上薄雪',o.data.copy());C['cover'].objects.link(cp);cp.data.materials.clear();cp.data.materials.append(M['snow']);cp.location.z=.045;weather_visibility(cp,True)
    for i in range(12):
        y=-7.3+i*.68;x=1.3*sin(i*.37)-.6
        o=box('汀步薄雪',(x,y,.355),(1.25,.51,.035),M['snow'],C['cover'],.045);weather_visibility(o,True)
    for o in list(C['water'].objects):
        if '太湖叠石' in o.name:
            coords=[v.co for v in o.data.vertices];hi=max(v.z for v in coords);center=sum(coords,Vector())/len(coords)
            cap=uv('石上残雪',(center.x,center.y,hi-.06),(.32,.24,.10),M['snow'],C['cover'],12,6);weather_visibility(cap,True)
    # Moistness changes with weather while materials remain editable.
    for key in ['stone','tile']:
        b=next(n for n in M[key].node_tree.nodes if n.type=='BSDF_PRINCIPLED');driven(b.inputs['Roughness'],'default_value',None,'.3+.32*v','Weather')
def volume_material(name,color,density):
    m=bpy.data.materials.new(PREFIX+name);m.use_nodes=True;n=m.node_tree.nodes;n.clear()
    out=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeVolumePrincipled');p.inputs['Color'].default_value=(*color,1);p.inputs['Density'].default_value=density;p.inputs['Anisotropy'].default_value=.15
    m.node_tree.links.new(p.outputs['Volume'],out.inputs['Volume']);return m
def sky():
    c=C['sky']
    moon=material('月华',(.75,.87,1),.9,4,0,1.8)
    uv('明月',(1.5,25,10.3),(1.12,1.12,1.12),moon,c,64,32)
    # Layers of distant ridges make the moon-gate opening a framed landscape.
    for layer in range(3):
        mat=material('远山'+str(layer),(.07+layer*.025,.14+layer*.023,.18+layer*.027),1)
        vv=[];ff=[];y=17+layer*7
        for i in range(81):
            x=-45+i*1.1;h=2.1+layer*.55+1.6*sin(i*.13+layer*1.7)**2+.5*sin(i*.49+layer)
            vv.extend([(x,y,-1),(x,y,h)])
            if i:ff.append((2*i-2,2*i,2*i+1,2*i-1))
        mesh('水墨远山',vv,ff,mat,c)
    cloudmat=volume_material('蓬松云体',(.62,.7,.8),.1)
    n=cloudmat.node_tree.nodes;l=cloudmat.node_tree.links;p=next(x for x in n if x.type=='PRINCIPLED_VOLUME')
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=7;tex.inputs['Detail'].default_value=6
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.42;ramp.color_ramp.elements[0].color=(0,0,0,1)
    ramp.color_ramp.elements[1].position=.72;ramp.color_ramp.elements[1].color=(.6,.6,.6,1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Density'])
    p.inputs['Emission Color'].default_value=(.12,.18,.27,1);p.inputs['Emission Strength'].default_value=.025
    for j,(cx,cy,cz) in enumerate([(-9,23,10.1),(6,29,10.7),(-1,34,12.4)]):
        for i in range(7):
            o=uv('云团',(cx+(i-3)*1.3,cy+R.uniform(-.4,.4),cz+R.uniform(-.35,.5)),(R.uniform(1.2,2.1),1.1,R.uniform(.85,1.5)),cloudmat,c,16,8)
            driven(o,'location',0,f'0.6*sin(frame*0.006+{j})')
    fog=volume_material('庭院轻岚',(.38,.49,.56),.006)
    box('轻岚',(0,5,4),(45,50,14),fog,c)
    box('院外水天',(0,25,-.6),(160,160,.1),M['water'],c)
def atmosphere():
    o=bpy.data.objects.get(PREFIX+'施工柔光')
    if o:bpy.data.objects.remove(o,do_unlink=True)
    light('月光_主塑形',(-6,9,15),(.48,.68,1),2600,8,(0,0,0))
    light('天光_暗部细节',(1,-7,13),(.48,.63,.82),1500,14,(0,2,1))
    light('月门_远景',(3,12,7),(.42,.68,.85),900,6,(1,4,1))
    light('梅花_柔暖反射',(-4,-1,5),(1,.54,.35),130,4,(-3,2,3))
    light('茶轩灯',(-7,1,2.8),(1,.49,.22),140,.5,kind='POINT')
    light('梅梢轮廓',(8,4,9),(.63,.78,1),700,5,(5,2,3))
    # Paper lantern hung under the eave, restrained warm accent.
    uv('轩内纱灯',(-7,1,3),(.22,.22,.38),M['paper'],C['court'],24,16)
    for z in [2.62,3.38]:uv('纱灯铜口',(-7,1,z),(.16,.16,.045),M['bronze'],C['court'])
    line('纱灯悬绳',[(-7,1,3.4),(-7,1,3.95)],.013,M['wood'],C['court'])
    fontpath=r'C:\Windows\Fonts\simkai.ttf'
    font=bpy.data.fonts.load(fontpath,check_existing=True) if os.path.exists(fontpath) else None
    def inscription(name,body,loc,size):
        d=bpy.data.curves.new(PREFIX+name,'FONT');d.body=body;d.size=size;d.extrude=.001
        enum(d,'align_x','CENTER')
        if font:d.font=font
        o=bpy.data.objects.new(PREFIX+name,d);C['court'].objects.link(o);o.location=loc;o.rotation_euler=(pi/2,0,0);d.materials.append(M['gold'])
    box('听雨轩匾',(-7,-.97,3.65),(1.25,.12,.43),M['wood'],C['court'],.025)
    inscription('听雨轩题字','听 雨 轩',(-7,-1.043,3.55),.25)
    for x,chars in [(-9,'致虚极'),(-5,'守静笃')]:
        for j,char in enumerate(chars):inscription('柱联',char,(x,-.952,2.65-j*.29),.20)
    bg=next(n for n in S.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.065,.11,.18,1);bg.inputs[1].default_value=.22
    S.view_settings.exposure=.1
    # Slow water movement remains native to the material node tree.
    n=M['water'].node_tree.nodes;l=M['water'].node_tree.links;b=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    t=n.new('ShaderNodeTexNoise');t.noise_dimensions='4D';t.inputs['Scale'].default_value=18;t.inputs['Detail'].default_value=2
    driven(t.inputs['W'],'default_value',None,'frame*0.008')
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.026
    l.new(t.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
def set_weather(mode):
    CTRL['Weather']=int(mode);CTRL.update_tag();S.frame_set(S.frame_current);bpy.context.view_layer.update()
def refine_clouds():
    # Radial falloff removes visible volume-container boundaries.
    for m in bpy.data.materials:
        if not m.name.startswith(PREFIX+'蓬松云体'):continue
        n=m.node_tree.nodes;l=m.node_tree.links;p=next(x for x in n if x.type=='PRINCIPLED_VOLUME')
        density_link=next((x for x in l if x.to_socket==p.inputs['Density']),None)
        if not density_link:continue
        source=density_link.from_socket;l.remove(density_link)
        tc=n.new('ShaderNodeTexCoord');dist=n.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,.5);l.new(tc.outputs['Generated'],dist.inputs[0])
        fade=n.new('ShaderNodeValToRGB');fade.color_ramp.elements[0].position=.22;fade.color_ramp.elements[0].color=(1,1,1,1);fade.color_ramp.elements[1].position=.49;fade.color_ramp.elements[1].color=(0,0,0,1);l.new(dist.outputs['Value'],fade.inputs[0])
        mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(source,mul.inputs[0]);l.new(fade.outputs[0],mul.inputs[1]);l.new(mul.outputs[0],p.inputs['Density'])
        p.inputs['Emission Strength'].default_value=0
    light('高云月照',(-3,18,18),(.6,.75,1),1900,9,(0,27,12))
def image_material(key,asset,scale,depth=.035,uv=False,tint=None):
    path=os.path.join(P['output_dir'],'textures',asset+'.png')
    if not os.path.exists(path):return
    mat=M[key];n=mat.node_tree.nodes;l=mat.node_tree.links;b=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    im=bpy.data.images.load(path,check_existing=True);im.pack()
    tex=n.new('ShaderNodeTexImage');tex.label='AI绘制 · '+asset;tex.image=im
    tc=n.new('ShaderNodeTexCoord');tc.label='真实尺度映射'
    if uv:l.new(tc.outputs['UV'],tex.inputs['Vector'])
    else:
        tex.projection='BOX';tex.projection_blend=.25
        v=n.new('ShaderNodeVectorMath');v.operation='MULTIPLY';v.inputs[1].default_value=scale
        l.new(tc.outputs['Object'],v.inputs[0]);l.new(v.outputs[0],tex.inputs['Vector'])
    color=tex.outputs['Color']
    if tint:
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*tint,1);l.new(color,mix.inputs[1]);color=mix.outputs[0]
    mix=n.new('ShaderNodeMixRGB');mix.inputs[0].default_value=P['texture_strength'];mix.inputs[1].default_value=b.inputs['Base Color'].default_value
    l.new(color,mix.inputs[2]);l.new(mix.outputs[0],b.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.label='图像灰度近似微凹凸';bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=depth
    l.new(tex.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    # Explicitly arranged nodes keep the material editable and readable.
    tc.location=(-800,0);tex.location=(-420,100);mix.location=(-120,180);bump.location=(-120,-180);b.location=(140,80)
    if key in ['pink','ivory']:
        b.inputs['Subsurface Weight'].default_value=.16;b.inputs['Subsurface Radius'].default_value=(1,.35,.2);b.inputs['Roughness'].default_value=.4
def art_upgrade():
    from mathutils import noise
    import bmesh
    def weld(o):
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    for args in [('plaster','plaster',(.32,.32,.32),.035),('stone','stone',(.7,.7,.7),.07),('edge','stone',(1,1,1),.035),('bark','bark',(1.6,1.6,.45),.10),('wood','wood',(1.1,1.1,.30),.035),('tile','clay',(.85,.85,.85),.022)]:image_material(*args)
    image_material('pink','petal',(1,1,1),.007,True,(.94,.55,.65));image_material('ivory','petal',(1,1,1),.006,True)
    # Replace piled spheres by individually sculpted, pierced scholar stones.
    for o in list(C['water'].objects):
        if o.name.startswith(PREFIX+'太湖叠石'):bpy.data.objects.remove(o,do_unlink=True)
    for o in list(C['cover'].objects):
        if o.name.startswith(PREFIX+'石上残雪'):bpy.data.objects.remove(o,do_unlink=True)
    for idx,(x,y,h,w) in enumerate([(6.8,-1.1,2.85,.95),(-4.1,-.35,1.5,.67),(-8.1,-3.5,1.2,.55)]):
        rock=uv('太湖石_瘦透漏皱',(0,0,0),(w,.48,h/2),M['stone'],C['water'],48,36)
        for v in rock.data.vertices:
            q=v.co.copy();t=q.z/(h/2)
            dis=noise.noise_vector(q*3.4+Vector((idx,0,0)))*.12
            v.co+=dis;v.co.x+=.24*sin(t*3.8)+.15*t;v.co.z+=h/2+.1
        rock.location=(x,y,0)
        weld(rock)
        for j in range(3 if idx==0 else 2):
            z=.48+j*h*.27;cx=x+(.15 if j%2 else -.12);sz=.18+j*.035
            cutter=uv('布尔孔_临时',(cx,y,z),(.30 if idx==0 else .21,1.3,sz),None,C['water'],24,16)
            weld(cutter)
            mod=rock.modifiers.new('天然穿孔','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
            bpy.context.view_layer.objects.active=rock
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter,do_unlink=True)
        for p in rock.data.polygons:p.use_smooth=True
        for j in range(12):
            a=R.uniform(0,2*pi);r=R.uniform(.3,.9)
            uv('湖石苔脚',(x+cos(a)*r,y+sin(a)*r*.55,.12),(R.uniform(.12,.28),.16,.065),M['moss'],C['water'],10,5)
        cap=uv('湖石残雪',(x+.05,y,h+.02),(.30,.21,.07),M['snow'],C['cover'],16,8);weather_visibility(cap,True)
    # Continuous site terrain prevents a floating display-plinth appearance.
    ground=material('庭外湿土',(.032,.052,.038),.93,16)
    vv=[];ff=[];nx=55;ny=42
    for j in range(ny):
        y=-28+j
        for i in range(nx):
            x=-27+i;outside=min(1,max(0,(abs(x)-10)/4,(abs(y+1)-10)/5))
            vv.append((x,y,-.085+outside*.13*sin(x*.67)*cos(y*.43)))
            if i and j:a=j*nx+i;ff.append((a,a-1,a-1-nx,a-nx))
    mesh('庭院延展地形',vv,ff,ground,C['water'])
    # A single old lateral bough, the brushstroke that draws the eye towards the gate.
    c=C['tree'];root=Vector((-3.35,1.7,3.05))
    pivot=bpy.data.objects.new(PREFIX+'主景横斜梅_风动',None);c.objects.link(pivot);pivot.location=root
    pts=[root,Vector((-2.3,1.5,3.25)),Vector((-1.05,1.1,3.95)),Vector((.4,1.15,4.45)),Vector((1.8,1.45,4.35)),Vector((2.6,1.65,4.8))]
    b=line('主景老梅_横斜',pts,.105,M['bark'],c,[1,.9,.7,.5,.25,.03]);attach(b,pivot)
    driven(pivot,'rotation_euler',1,'v*0.012*sin(frame*0.029)')
    blooms=[]
    for j in range(24):
        t=R.uniform(.15,.97);a=pts[min(int(t*5),4)].lerp(pts[min(int(t*5)+1,5)],t*5%1)
        tip=a+Vector((R.uniform(-.12,.32),R.uniform(-.32,.25),R.uniform(.15,.65)))
        twig=line('横斜细梢',[a,a.lerp(tip,.6),tip],.016,M['bark'],c,[1,.65,.02]);attach(twig,pivot)
        for j2 in range(R.randint(3,7)):blooms.append((a.lerp(tip,R.uniform(.3,1)),R.uniform(.05,.08)))
    petals('横斜梅花',blooms,c,pivot)
    # Foreground branch hangs in the upper-left margin, not over the central gate.
    pts=[(-10,-6,5.5),(-8.5,-5.8,5.9),(-6.8,-5.6,5.7),(-5.7,-5.5,6.0)]
    line('前景框枝',pts,.055,M['bark'],c,[1,.8,.4,.03]);blooms=[]
    for i in range(11):
        a=Vector(pts[1]).lerp(Vector(pts[3]),i/11);tip=a+Vector((.15,.1,-R.uniform(.25,.65)))
        line('前景梅梢',[a,tip],.013,M['bark'],c,[1,.03])
        for j in range(4):blooms.append((a.lerp(tip,R.uniform(.15,1)),R.uniform(.06,.085)))
    petals('前景点梅',blooms,c)
    # Fine roots and fallen petals break perfectly clean paving edges.
    for j in range(38):
        x=R.uniform(-9,9);y=R.uniform(-.05,3.3)
        uv('石缝湿苔',(x,y,.183),(R.uniform(.04,.12),.025,.014),M['moss'],C['water'],8,4)
    # Image-backed distant atmosphere is explicitly a background, never a substitute for 3D architecture.
    path=os.path.join(P['output_dir'],'textures','landscape.png')
    if os.path.exists(path):
        for o in list(C['sky'].objects):
            if o.name.startswith(PREFIX+'水墨远山'):bpy.data.objects.remove(o,do_unlink=True)
        m=material('生成远山_借景',(.1,.15,.2),1);n=m.node_tree.nodes;l=m.node_tree.links;b=next(x for x in n if x.type=='BSDF_PRINCIPLED')
        im=bpy.data.images.load(path,check_existing=True);im.pack();tex=n.new('ShaderNodeTexImage');tex.image=im;l.new(tex.outputs['Color'],b.inputs['Base Color']);l.new(tex.outputs['Color'],b.inputs['Emission Color']);b.inputs['Emission Strength'].default_value=.65
        v=[];f=[];uvs=[]
        for j in range(2):
            for i in range(65):
                a=-1.05+2.1*i/64;v.append((65*sin(a),65*cos(a),-10+j*43));uvs.append((i/64,j))
                if j and i:a0=i-1;f.append((a0,a0+1,a0+66,a0+65))
        o=mesh('远山环幕_生成贴图',v,f,m,C['sky']);uv_layer=o.data.uv_layers.new(name='远山全景UV')
        for loop in o.data.loops:uv_layer.data[loop.index].uv=uvs[loop.vertex_index]
    # Layered lighting: reduce frontal flattening, preserve readable penumbrae.
    bpy.data.objects[PREFIX+'天光_暗部细节'].data.energy=850
    bpy.data.objects[PREFIX+'月光_主塑形'].data.energy=2200
    bpy.data.objects[PREFIX+'梅梢轮廓'].data.energy=950
    bpy.data.objects[PREFIX+'梅花_柔暖反射'].data.energy=90
    for name,loc,target,lens in [('正面',(1,-24,5.2),(0,3,3.0),40),('三分之四',(10,-22,7.2),(0,2,2.8),40)]:
        o=bpy.data.objects[PREFIX+name];o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens
    S.view_settings.exposure=.2
def statistics():
    obs=list(S.objects);meshes=[o for o in obs if o.type=='MESH'];curves=[o for o in obs if o.type=='CURVE']
    mats=set(m for o in obs if hasattr(o.data,'materials') for m in o.data.materials if m)
    result={'scene':S.name,'objects':len(obs),'mesh_objects':len(meshes),'curve_objects':len(curves),'vertices':sum(len(o.data.vertices) for o in meshes),'polygons':sum(len(o.data.polygons) for o in meshes),'materials':len(mats),'collections':len(C),'cameras':sum(o.type=='CAMERA' for o in obs),'lights':sum(o.type=='LIGHT' for o in obs),'object_drivers':sum(len(o.animation_data.drivers) if o.animation_data else 0 for o in obs),'frames':[S.frame_start,S.frame_end],'fps':S.render.fps,'weather':CTRL['Weather']}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result
def deliver():
    os.makedirs(P['output_dir'],exist_ok=True)
    script=os.path.join(P['output_dir'],'jiangnan.py')
    if os.path.exists(script):
        t=bpy.data.texts.get('jiangnan.py') or bpy.data.texts.new('jiangnan.py');t.clear();t.write(open(script,encoding='utf-8').read())
    for f in bpy.data.fonts:
        if f.filepath and 'kai' in f.filepath.lower():
            try:f.pack()
            except Exception:pass
    with open(os.path.join(P['output_dir'],'scene_statistics.json'),'w',encoding='utf-8') as f:json.dump(statistics(),f,ensure_ascii=False,indent=2)
    # Write only this scene, preserving the unrelated open project on disk.
    bpy.data.libraries.write(os.path.join(P['output_dir'],'Jiangnan.blend'),{S,bpy.data.texts['jiangnan.py']},fake_user=True,compress=True)
def viewport():
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.camera=S.camera;a.spaces.active.use_local_camera=False
                a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False
                a.spaces.active.shading.type='MATERIAL'
                a.spaces.active.region_3d.view_camera_zoom=0
    bpy.context.view_layer.update()
def build(stage=None):
    start();courtyard()
    level=P['stage'] if stage is None else stage
    if level>=2:vegetation()
    if level>=3:weather()
    if level>=4:sky()
    if level>=5:
        atmosphere();refine_clouds()
        if P.get('art_upgrade',False):art_upgrade()
    S.frame_set(80);viewport()
    print('STAGE',level,'OBJECTS',len(S.objects))
if __name__=='__main__':
    build();deliver()
    if P['render']:
        rdir=os.path.join(P['output_dir'],'renders');os.makedirs(rdir,exist_ok=True)
        for name in ['正面','顶视','三分之四']:
            S.camera=bpy.data.objects[PREFIX+name];S.render.filepath=os.path.join(rdir,name+'.png');bpy.ops.render.render(write_still=True)
