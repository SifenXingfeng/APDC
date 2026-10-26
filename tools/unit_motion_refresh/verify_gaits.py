"""Check actual exported foot trajectories, contact direction, pairing and ground reach."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
from gaits import *

io.create_material=lambda definition,mesh,directory: None
reports=[]
for ident in GROUND_MODELS+['APDC_ump_chibi']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rel=Path('gfx/models/units')/ident/(ident+'.mesh')
    mesh=STAGE/rel if (STAGE/rel).exists() else ROOT/rel
    io.import_meshfile(str(mesh),imp_mesh=True,imp_skel=True,imp_locs=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rest={b.name:b.head_local.copy() for b in rig.data.bones};legs=[]
    for n,h in rest.items():
        if n.endswith('_upper') and n[:-6]+'_foot' in rest:
            legs.append(dict(bones=[n,n[:-6]+'_lower',n[:-6]+'_foot'],hip=h,ankle=rest[n[:-6]+'_foot']))
    if ident=='APDC_ump_chibi':
        assert len(legs)==4
        for l in legs:l['phase']=0. if 'front' in l['bones'][0] else .5
        assert max(l['hip'].y for l in legs if l['phase']==0)<min(l['hip'].y for l in legs if l['phase']==.5)
    else:assign_alternating(legs)
    anim=STAGE/'gfx/models/units'/ident/(ident+'_move.anim')
    io.import_animfile(str(anim));scene=bpy.context.scene;cfg=settings(ident)
    assert scene.frame_end-scene.frame_start+1==cfg['frames']
    records=[];samples={l['bones'][2]:[] for l in legs};max_error=0;min_contacts=99
    for f in range(scene.frame_start,scene.frame_end+1):
        scene.frame_set(f);bpy.context.view_layer.update();t=(f-1)/(cfg['frames']-1);contacts=[]
        for l in legs:
            foot=l['bones'][2];p=rig.pose.bones[foot].matrix.translation.copy()
            dy,dz,contact=foot_path(t,l['phase'],cfg['stride'],cfg['lift'],cfg['duty'])
            expected=Vector(l['ankle'])+Vector((0,dy,dz));error=(p-expected).length
            max_error=max(max_error,error);assert error<.002,(ident,f,foot,'Target missed',error)
            samples[foot].append((t,list(p),contact))
            if contact:
                contacts.append(foot);assert abs(p.z-l['ankle'].z)<.002
        min_contacts=min(min_contacts,len(contacts));records.append({'frame':f,'ground_contacts':contacts})
    velocities=[]
    for l in legs:
        foot=l['bones'][2]
        for a,b in zip(samples[foot],samples[foot][1:]):
            phase_a=(a[0]+l['phase'])%1.;phase_b=(b[0]+l['phase'])%1.
            if a[2] and b[2] and phase_b>phase_a:
                velocity=(b[1][1]-a[1][1])/(b[0]-a[0])
                velocities.append(velocity)
                assert velocity>0,(ident,foot,'Backwards stance',velocity)
                # With body advancing -Y at the matching speed, planted feet
                # remain stationary in world space (no treadmill reversal).
                assert abs(velocity-cfg['stride']/cfg['duty'])<.003
    for a in legs:
        for b in legs:
            if a is b:continue
            paired=a['phase']==b['phase']
            if paired:
                for sa,sb in zip(samples[a['bones'][2]],samples[b['bones'][2]]):
                    da=Vector(sa[1])-Vector(a['ankle']);db=Vector(sb[1])-Vector(b['ankle'])
                    assert (da-db).length<.002
            if ident!='APDC_ump_chibi' and a.get('side')==b.get('side') and abs(a.get('longitudinal_rank',0)-b.get('longitudinal_rank',0))==1:
                assert not paired,'Same-side adjacent legs must alternate'
    if ident!='APDC_ump_chibi':assert min_contacts>=len(legs)//2
    else:
        assert min_contacts==0,'Bounding run should include short suspension'
        assert {sum('front' in n for n in r['ground_contacts']) for r in records}=={0,2}
        assert {sum('rear' in n for n in r['ground_contacts']) for r in records}=={0,2}
    result={'id':ident,'animation_sha256':sha(anim),'mesh_sha256':sha(mesh),'frames':cfg['frames'],'stance_direction':'+Y (forward body motion is -Y)','minimum_stance_velocity':min(velocities),'maximum_target_error':max_error,'minimum_ground_contacts':min_contacts,'phases':{l['bones'][2]:l['phase'] for l in legs},'contacts':records}
    reports.append(result);print('EXPORTED_GAIT_PASS',ident,'legs',len(legs),'min_contacts',min_contacts,flush=True)
save_json(WORK/'gait_revision_validation.json',{'status':'PASS','actual_exported_binaries_checked':True,'models':reports,'game_visual_acceptance':False})
