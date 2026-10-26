"""Keep the vanilla joint topology but adapt leg proportions and torso motion.

Binary animation samples retain the source FPS/sample count, scale/visibility
tracks and event timing. Only penguin-owned copies are written.
"""
import copy
import json
from pathlib import Path
import re
import bpy
from mathutils import Matrix, Quaternion, Vector

PREFIX='APDC_penguin_'

def adapt(rig,backend,pdx,model,units,gfx_path):
    names=[b.name for b in rig.data.bones]
    source={b.name:b.matrix_local.copy() for b in rig.data.bones}
    moved={'Hip':1.60,'LeftUpLeg':1.45,'RightUpLeg':1.45,'LeftLeg':.98,'RightLeg':.98}
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name,z in moved.items():
        bone=rig.data.edit_bones[name];m=bone.matrix.copy();m.translation.z=z;bone.matrix=m
    # Move the complete arm branches forward together. This makes room for the
    # broad belly and beak while preserving the relative two-handed grip.
    arm_names=set()
    for root in ('LeftShoulder','RightShoulder'):
        arm_names.add(root);arm_names.update(b.name for b in rig.data.edit_bones[root].children_recursive)
    for name in arm_names:
        bone=rig.data.edit_bones[name];m=bone.matrix.copy();m.translation.y-=.70;bone.matrix=m
    bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
    target={b.name:b.matrix_local.copy() for b in rig.data.bones}
    source_local={};target_local={}
    for bone in rig.data.bones:
        a=source[bone.name];b=target[bone.name]
        if bone.parent:a=source[bone.parent.name].inverted_safe()@a;b=target[bone.parent.name].inverted_safe()@b
        source_local[bone.name]=backend.swap_coord_space(a)
        target_local[bone.name]=backend.swap_coord_space(b)
    registry=(units/'animation.asset').read_text(encoding='utf-8-sig')
    files={m[0]:m[1] for m in re.findall(r'animation\s*=\s*\{\s*name\s*=\s*"([^"]+)"\s*file\s*=\s*"([^"]+)"',registry)}
    types=set(re.findall(r'type\s*=\s*"([^"]+)"',gfx_path.read_text()))
    types={t[len(PREFIX):] if t.startswith(PREFIX) else t for t in types}
    output=model/'animations';output.mkdir(exist_ok=True)
    manifest=[]
    def transform_t(name,values):
        # Feet stay at the source rest position, with short hidden legs above.
        factor=.40 if name=='Hip' else (.35 if name in ('LeftLeg','RightLeg','LeftFoot','RightFoot') else 1)
        return list(target_local[name].translation+(Vector(values)-source_local[name].translation)*factor)
    def transform_q(name,values):
        if name not in ('head','back_mid'):return values
        rest=source_local[name].to_quaternion()
        q=Quaternion((values[3],values[0],values[1],values[2]))
        delta=rest.inverted()@q
        # A round continuous penguin neck cannot twist as far as a human neck.
        q=rest@Quaternion().slerp(delta,.40 if name=='head' else .70)
        return [q.x,q.y,q.z,q.w]
    for filename in sorted({files[t] for t in types}):
        tree=pdx.read_meshfile(str(units/filename));info=tree.find('info');samples=tree.find('samples')
        assert {b.tag for b in info}==set(names),filename
        for bone in info:
            name=bone.tag;bone.set('t',transform_t(name,bone.get('t')));bone.set('q',transform_q(name,bone.get('q')))
        ti=qi=0
        translations=list(samples.get('t',[]));rotations=list(samples.get('q',[]))
        for frame in range(info.get('sa')[0]):
            for bone in info:
                channels=bone.get('sa')[0]
                if 't' in channels:
                    translations[ti:ti+3]=transform_t(bone.tag,translations[ti:ti+3]);ti+=3
                if 'q' in channels:
                    rotations[qi:qi+4]=transform_q(bone.tag,rotations[qi:qi+4]);qi+=4
        assert ti==len(translations) and qi==len(rotations),filename
        if translations:samples.set('t',translations)
        if rotations:samples.set('q',rotations)
        path=output/('APDC_'+filename);pdx.write_animfile(str(path),tree)
        check=pdx.read_meshfile(str(path))
        assert check.find('info').attrib==info.attrib
        manifest.append({'source':filename,'output':path.name,'fps':info.get('fps')[0],'samples':info.get('sa')[0]})
    deltas={name:list(backend.swap_coord_space(Matrix.Translation(target[name].translation-source[name].translation)).translation)
            for name in names if (target[name].translation-source[name].translation).length>1e-5}
    return {'moved_joint_heights':moved,'arm_forward_offset':.70,'joint_world_deltas_game':deltas,
            'topology_preserved':True,'bones':len(names),'clips':manifest}
