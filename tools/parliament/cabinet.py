"""Migrate the old cabinet into shared member/prime/deputy appointments."""
from common import *
import re


def import_candidates():
    # IDs 1..47 remain save-compatible with the previous six-slot cabinet.
    source=read('tools/parliament/legacy/APDC_cabinet_scripted_effects.txt')
    old_triggers=read('tools/parliament/legacy/APDC_cabinet_scripted_triggers.txt')
    candidate_party={}
    for n in parse(old_triggers):
        m=re.fullmatch(r'APDC_cabinet_candidate_(\d+)_enabled',n.key)
        if m:
            p=next((c.key.removeprefix('APDC_is_').removesuffix('_in_governing_coalition') for c in n.children if c.key.startswith('APDC_is_') and c.key.endswith('_in_governing_coalition')),None)
            candidate_party[int(m[1])]=p
    result=[]
    for i in range(1,48):
        char={1:'GER_APDC_romy_riefenstahl',2:'GER_APDC_eugene_rugosa'}.get(i)
        result.append({'id':i,'character':char,'countries':['GER'],'party':candidate_party[i],
                       'name_key':char or 'APDC_CABINET_CANDIDATE_'+str(i)+'_NAME',
                       'portrait':{1:'GFX_portrait_GER_APDC_romy_riefenstahl_small',2:'GFX_portrait_GER_APDC_eugene_rugosa_small'}.get(i,'GFX_idea_unknown'),
                       'member_idea':char,'member_traits':['prince_of_terror'] if i==1 else ['compassionate_gentleman'] if i==2 else [],
                       'chief_traits':[],'chief_modifiers':{},'placeholder':char is None})
    parent={}
    for path in (ROOT/'common/ideologies').glob('*.txt'):
        for outer in parse(path.read_text('utf-8-sig')):
            if outer.key=='ideologies':
                for group in outer.children:
                    t=group.get('types')
                    if t:parent.update({n.key:group.key for n in t.children})
    characters={}
    for path in sorted((ROOT/'common/characters').glob('*.txt')):
        for outer in parse(path.read_text('utf-8-sig')):
            if outer.key=='characters':characters.update({n.key:n for n in outer.children})
    identities={c['character']:c for c in result if c['character']}
    for path in sorted((ROOT/'history/countries').glob('*.txt')):
        tag=path.name[:3];nodes=parse(path.read_text('utf-8-sig'))
        # Explicit party-head records take precedence over character defaults.
        explicit={}
        for n in nodes:
            if n.key=='promote_character' and n.val('ideology') in parent:
                explicit[n.val('character')]=parent[n.val('ideology')]
        recruits={n.value for n in nodes if n.key=='recruit_character' and n.value in characters}
        recruits.update(k for k in explicit if k in characters)
        for char in sorted(recruits):
            n=characters[char]
            party=explicit.get(char)
            roles=[c for c in n.children if c.key=='country_leader']
            if party is None:party=next((parent[r.val('ideology')] for r in roles if r.val('ideology') in parent),None)
            if party not in PARTIES:continue
            if char in identities:
                row=identities[char]
                if tag not in row['countries']:row['countries'].append(tag)
                continue
            portrait='GFX_leader_unknown'
            portraits=n.get('portraits');civilian=portraits.get('civilian') if portraits else None
            if civilian:portrait=civilian.val('large',civilian.val('small',portrait))
            advisor=next((c for c in n.children if c.key=='advisor' and c.val('slot')=='political_advisor'),None)
            member_traits=[t.key for t in advisor.get('traits').children] if advisor and advisor.get('traits') else []
            row={'id':1000+len(identities),'character':char,'countries':[tag],'party':party,
                 'name_key':n.val('name',char),'portrait':portrait,
                 'member_idea':advisor.val('idea_token',char) if advisor else None,
                 'member_traits':member_traits,'chief_traits':[],'chief_modifiers':{},'placeholder':False}
            result.append(row);identities[char]=row
    json_write('tools/parliament/data/candidates.json',{'schema_version':1,'note':'IDs 1..47 are preserved. New IDs are persistent; append rather than renumber. Empty chief definitions are deliberate authoring slots, not fabricated bonuses.','candidates':result})
    return result


def generate(loc):
    candidates=load_json('candidates.json')['candidates'];settings=load_json('settings.json')
    trait_catalog={}
    files={p.name:p for p in (GAME/'common/country_leader').glob('*.txt')}
    files.update({p.name:p for p in (ROOT/'common/country_leader').glob('*.txt')})
    for path in files.values():
        for outer in parse(path.read_text('utf-8-sig')):
            if outer.key=='leader_traits':trait_catalog.update({n.key:n for n in outer.children})
    native_keys=set(re.findall(r'^## ([A-Za-z0-9_]+)$',(GAME/'documentation/modifiers_documentation.md').read_text('utf-8'),re.M))
    native_keys.update(n.key for p in (ROOT/'common/modifier_definitions').glob('*.txt') for n in parse(p.read_text('utf-8-sig')))
    def trait_modifiers(traits,explicit):
        result={}
        for trait in traits:
            if trait not in trait_catalog:raise ValueError('Unregistered cabinet trait: '+trait)
            for n in trait_catalog[trait].children:
                if n.key in native_keys and n.value is not None:
                    try:value=float(n.value)
                    except ValueError:raise ValueError('Use explicit role modifiers for parameterized trait '+trait)
                    result[n.key]=result.get(n.key,0)+value
        result.update(explicit)
        return result
    effects='';triggers='';ideas='';defined=''
    for c in candidates:
        i=c['id'];party=c['party'];char=c['character']
        loc[P+'candidate_'+str(i)]=('$'+c['name_key']+'$') if re.fullmatch(r'[A-Za-z0-9_.-]+',c['name_key']) else c['name_key']
        loc[P+'member_traits_'+str(i)]=' / '.join('$'+t+'$' for t in c['member_traits']) or '无成员特质'
        loc[P+'chief_traits_'+str(i)]=' / '.join('$'+t+'$' for t in c['chief_traits']) or '无首席特质'
        loc[P+'candidate_tip_'+str(i)]='§Y$'+P+'candidate_'+str(i)+'$§!\n[ApdcParlCandidateTrait]\n\n[ApdcParlAppointmentCost]'
        ids=' '.join('original_tag = '+tag for tag in c['countries'])
        visible='OR = { '+ids+' }'+(' has_character = '+char if char else '')
        visible+=' has_country_flag = APDC_governing_coalition_'+party
        if c['placeholder']:visible+=' '+ck('selected_role','<',7)
        else:visible+=' OR = { '+ck('selected_role','<',7)+' '+ck('winner_'+party,'=',1)+' }'
        triggers+=block(P+'candidate_'+str(i)+'_visible',visible)
        quota='OR = { '+ck('selected_role','>',6)+' check_variable = { APDC_cabinet_used_'+party+' < APDC_cabinet_available_'+party+' } '+ck('selected_old_party','=',PARTIES.index(party)+1)+' }'
        affordable='OR = { AND = { '+ck('selected_role','=',7)+' '+ck('free_prime','=',1)+' } AND = { '+ck('selected_role','=',8)+' '+ck('free_deputy','=',1)+' } AND = { '+ck('selected_role','<',7)+' has_political_power > '+str(settings['member_cost']-1)+' } has_political_power > '+str(settings['chief_cost']-1)+' }'
        triggers+=block(P+'candidate_'+str(i)+'_enabled',P+'candidate_'+str(i)+'_visible = yes '+quota+' '+affordable)
        # A shared hidden idea stores authored chief effects, independent of
        # the member's native advisor idea and current country-leader traits.
        chief_idea=P+'chief_'+str(i)
        loc[chief_idea]='$'+P+'candidate_'+str(i)+'$的首席特质'
        loc[P+'member_'+str(i)]='$'+P+'candidate_'+str(i)+'$的成员特质'
        chief_mods=trait_modifiers(c['chief_traits'],c['chief_modifiers'])
        member_mods=trait_modifiers(c['member_traits'],c.get('member_modifiers',{}))
        ideas+=block(chief_idea,'allowed = { always = no }\nallowed_civil_war = { always = yes }\nremoval_cost = -1\n'+block('modifier','\n'.join(k+' = '+str(v) for k,v in chief_mods.items())))
        ideas+=block(P+'member_'+str(i),'allowed = { always = no }\nallowed_civil_war = { always = yes }\nremoval_cost = -1\n'+block('modifier','\n'.join(k+' = '+str(v) for k,v in member_mods.items())))
        assignment=''
        for role in range(1,9):
            # Identity check is by character token where possible, so duplicate
            # roster records can never place the same person in two offices.
            test=ck('role_'+str(role),'=',i)
            if char:
                token='APDC_prime_minister_character' if role==7 else 'APDC_deputy_prime_minister_character' if role==8 else P+'role_token_'+str(role)
                test='OR = { '+test+' check_variable = { '+token+' = token:'+char+' } }'
            assignment+=iff(test,P+'clear_role_'+str(role)+' = yes\n')
        for role in range(1,9):
            if role>6 and not char:continue
            body=P+'clear_role_'+str(role)+' = yes\n'+sv('role_'+str(role),i)
            if char:body+='set_variable = { '+P+'role_token_'+str(role)+' = token:'+char+' }\n'
            if role<7:
                body+='set_variable = { APDC_cabinet_slot_'+str(role)+' = '+str(i)+' }\nadd_political_power = -'+str(settings['member_cost'])+'\n'
                body+='add_ideas = '+(c['member_idea'] or P+'member_'+str(i))+'\n'
            else:
                office='prime' if role==7 else 'deputy'
                body+=iff(ck('free_'+office,'=',1),sv('free_'+office,0),'add_political_power = -'+str(settings['chief_cost'])+'\n')
                body+='add_ideas = '+chief_idea+'\nset_variable = { APDC_'+('prime_minister' if role==7 else 'deputy_prime_minister')+'_character = token:'+str(char)+' }\n'
            assignment+=iff(ck('selected_role','=',role),body)
        assignment+='APDC_update_cabinet_statistics = yes\napdc_parl_refresh_candidates = yes\napdc_parl_refresh = yes\n'
        effects+=effect('appoint_'+str(i),iff(P+'candidate_'+str(i)+'_enabled = yes',assignment))
    for role in range(1,9):
        clear=''
        for c in candidates:
            idea=(c['member_idea'] or P+'member_'+str(c['id'])) if role<7 else P+'chief_'+str(c['id'])
            if idea:clear+=iff(ck('role_'+str(role),'=',c['id']),'remove_ideas = '+idea+'\n')
        clear+='clear_variable = '+P+'role_'+str(role)+'\nclear_variable = '+P+'role_token_'+str(role)+'\n'
        clear+=('clear_variable = APDC_cabinet_slot_'+str(role)+'\n') if role<7 else ('clear_variable = APDC_'+('prime_minister' if role==7 else 'deputy_prime_minister')+'_character\n')
        effects+=effect('clear_role_'+str(role),clear)
    # Cabinet slots remain in the old IDs; synchronize only the new role index.
    migrate=''
    for role in range(1,7):migrate+='set_variable = { '+P+'role_'+str(role)+' = APDC_cabinet_slot_'+str(role)+' }\n'
    for c in candidates:
        if c['character']:
            for role,token in [(7,'APDC_prime_minister_character'),(8,'APDC_deputy_prime_minister_character')]:
                migrate+=iff('check_variable = { '+token+' = token:'+c['character']+' }',sv('role_'+str(role),c['id']))
    effects+=effect('migrate_role_records',migrate)
    refresh='clear_array = '+P+'candidates\n'+sv('selected_old_party',0)+sv('real_candidate_count',0)
    for j,p in enumerate(PARTIES):
        body='add_to_array = { '+P+'candidates = -'+str(j+1)+' }\n'+(('add_to_array = { '+P+'candidates = 0 }\n')*3)+sv('candidate_column',0)
        for c in candidates:
            if c['party']==p:
                body+=iff(P+'candidate_'+str(c['id'])+'_visible = yes','add_to_array = { '+P+'candidates = '+str(c['id'])+' }\n'+op('real_candidate_count','add',1)+op('candidate_column','add',1)+iff(ck('candidate_column','=',4),sv('candidate_column',0)))
        body+=iff(ck('candidate_column','>',0),block('while_loop_effect','limit = { '+ck('candidate_column','<',4)+' }\nadd_to_array = { '+P+'candidates = 0 }\n'+op('candidate_column','add',1)))
        refresh+=iff('has_country_flag = APDC_governing_coalition_'+p+' OR = { '+ck('selected_role','<',7)+' '+ck('winner_'+p,'=',1)+' }',body)
    for c in candidates:
        for role in range(1,7):refresh+=iff(ck('selected_role','=',role)+' '+ck('role_'+str(role),'=',c['id']),sv('selected_old_party',PARTIES.index(c['party'])+1))
    effects+=effect('refresh_candidates',refresh+op('dirty','add',1))
    reconcile=''
    for c in candidates:
        for role in range(1,9):
            valid=('has_country_flag = APDC_governing_coalition_'+c['party']) if role<7 else ck('winner_'+c['party'],'=',1)
            reconcile+=iff(ck('role_'+str(role),'=',c['id'])+' NOT = { '+valid+' }',P+'clear_role_'+str(role)+' = yes\n')
    effects+=effect('reconcile_cabinet',reconcile)
    effects+=effect('select_role',iff(ck('selected_role','=','$ROLE$')+' has_country_flag = '+P+'candidate_panel_open','clr_country_flag = '+P+'candidate_panel_open\n'+op('dirty','add',1),sv('selected_role','$ROLE$')+'set_variable = { APDC_cabinet_selected_slot = $ROLE$ }\nAPDC_update_cabinet_statistics = yes\napdc_parl_refresh_candidates = yes\nset_country_flag = '+P+'candidate_panel_open\n'))
    effects+=effect('appoint_selected',''.join(iff(ck('selected_candidate','=',c['id']),P+'appoint_'+str(c['id'])+' = yes\n') for c in candidates))
    effects+=effect('dismiss_selected',''.join(iff(ck('selected_role','=',r),P+'clear_role_'+str(r)+' = yes\n') for r in range(1,9))+'APDC_update_cabinet_statistics = yes\napdc_parl_refresh_candidates = yes\n')
    write('common/scripted_effects/apdc_parliament_cabinet.txt',effects)
    write('common/scripted_triggers/apdc_parliament_cabinet_triggers.txt',triggers)
    write('common/ideas/apdc_parliament_chief_traits.txt',block('ideas',block('hidden_ideas',ideas)))
    # New aliases resolve to the supplied existing portraits, preserving old
    # top-bar token-based portraits and the user's fixed character art.
    def texts(name,records,default):
        return block('defined_text','name = '+name+'\n'+''.join(block('text','trigger = { '+test+' }\nlocalization_key = '+key) for test,key in records)+block('text','localization_key = '+default))
    for r in range(1,9):
        rolevar='APDC_cabinet_slot_'+str(r) if r<7 else P+'role_'+str(r)
        fallback='GFX_apdc_parl_empty_slot'
        if r>6:
            fallback=P+'legacy_'+('prime' if r==7 else 'deputy')+'_portrait'
            loc[fallback]='[APDCPrimeMinisterPortrait]' if r==7 else '[APDCDeputyPrimeMinisterPortrait]'
        defined+=texts('ApdcParlRole'+str(r)+'Portrait',[('check_variable = { '+rolevar+' = '+str(c['id'])+' }','GFX_apdc_parl_portrait_'+str(c['id'])) for c in candidates],fallback)
    # Shared candidate row context is the numeric candidate ID.
    for name,field,default in [('Name','name_key','APDC_CABINET_EMPTY_TEXT'),('Portrait','portrait','GFX_idea_unknown')]:
        defined+=texts('ApdcParlCandidate'+name,[(ck('candidate_context','=',c['id']),P+'candidate_'+str(c['id']) if name=='Name' else 'GFX_apdc_parl_portrait_'+str(c['id'])) for c in candidates],default)
    records=[]
    for c in candidates:
        records.append((ck('candidate_context','=',c['id'])+' '+ck('selected_role','>',6),P+'chief_traits_'+str(c['id'])))
        records.append((ck('candidate_context','=',c['id']),P+'member_traits_'+str(c['id'])))
    defined+=texts('ApdcParlCandidateTrait',records,'APDC_CABINET_EMPTY_TEXT')
    defined+=texts('ApdcParlCandidateEffects',[(ck('candidate_context','=',1)+' '+ck('selected_role','<',7),'APDC_CABINET_ROMY_EFFECTS'),(ck('candidate_context','=',2)+' '+ck('selected_role','<',7),'APDC_CABINET_EUGENE_EFFECTS')],P+'empty')
    write('common/scripted_localisation/apdc_parliament_cabinet.txt',defined)
    # Preserve unknown legacy prime/deputy records, while known new selections
    # resolve the actual source name and the chief trait rather than stale data.
    original=read('tools/parliament/legacy/APDC_cabinet_scripted_localisation.txt')
    edits=[]
    for node in parse(original):
        name=node.val('name')
        mapping={
            'APDCPrimeMinisterName':(7,'name'),'APDCDeputyPrimeMinisterName':(8,'name'),
            'APDCPrimeMinisterPortrait':(7,'portrait'),'APDCDeputyPrimeMinisterPortrait':(8,'portrait'),
            'APDCPrimeMinisterTraitBlock':(7,'trait'),'APDCDeputyPrimeMinisterTraitBlock':(8,'trait')
        }
        if name not in mapping:continue
        role,kind=mapping[name];extra=''
        for c in candidates:
            if not c['character']:continue
            key=P+'candidate_'+str(c['id']) if kind=='name' else 'GFX_apdc_parl_portrait_'+str(c['id']) if kind=='portrait' else P+'chief_traits_'+str(c['id'])
            extra+=block('text','trigger = { '+ck('role_'+str(role),'=',c['id'])+' }\nlocalization_key = '+key)
        body='name = '+name+'\n'+extra+'\n'.join(original[c.start:c.end] for c in node.children if c.key!='name')
        edits.append((node.start,node.end,block('defined_text',body)))
    write('common/scripted_localisation/APDC_cabinet_scripted_localisation.txt',patches(original,edits))
    # Preserve the original six-slot quota algorithm. Extend its used counters
    # for new real candidates, and remove the retired satisfaction calculation.
    legacy=read('tools/parliament/legacy/APDC_cabinet_scripted_effects.txt')
    nodes=parse(legacy);new=''
    for n in nodes:
        if n.key=='APDC_update_cabinet_statistics':
            keep=[]
            for child in n.children:
                raw=legacy[child.start:child.end]
                if 'APDC_cabinet_base_support_' in raw or 'APDC_cabinet_support_' in raw:continue
                keep.append(raw)
            body='\n'.join(keep)
            extra=''
            for c in candidates:
                if c['id']>47:
                    extra+=iff('OR = { '+' '.join('check_variable = { APDC_cabinet_slot_'+str(r)+' = '+str(c['id'])+' }' for r in range(1,7))+' }','add_to_variable = { APDC_cabinet_used_'+c['party']+' = 1 }\n')
            marker='set_variable = { APDC_cabinet_coalition_total = 0 }'
            assert marker in body
            body=body.replace(marker,extra+marker)
            new+=block(n.key,body)
        else:new+=legacy[n.start:n.end]+'\n'
    write('common/scripted_effects/APDC_cabinet_scripted_effects.txt',new)
    # Old explicit hire entry points now use the same guards/role switch path.
    current=read('common/scripted_effects/APDC_cabinet_scripted_effects.txt')
    edits=[]
    for n in parse(current):
        m=re.fullmatch(r'APDC_cabinet_hire_candidate_(\d+)',n.key)
        if m:edits.append((n.start,n.end,block(n.key,sv('selected_role','APDC_cabinet_selected_slot')+P+'appoint_'+m[1]+' = yes\n')))
        m=re.fullmatch(r'APDC_cabinet_clear_slot_([1-6])',n.key)
        if m:edits.append((n.start,n.end,block(n.key,sv('role_'+m[1],'APDC_cabinet_slot_'+m[1])+P+'clear_role_'+m[1]+' = yes\n')))
        m=re.fullmatch(r'APDC_cabinet_remove_party_members_(.+)',n.key)
        if m:
            body=current[n.value_start+1:n.value_end-1]
            for c in candidates:
                if c['party']==m[1] and c['id']>47:
                    for r in range(1,7):
                        body+=iff('check_variable = { APDC_cabinet_slot_'+str(r)+' = '+str(c['id'])+' }',P+'clear_role_'+str(r)+' = yes\n')
            edits.append((n.start,n.end,block(n.key,body)))
    write('common/scripted_effects/APDC_cabinet_scripted_effects.txt',patches(current,edits))
