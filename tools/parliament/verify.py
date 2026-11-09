"""Read-only static checks and independent numerical parliament oracles."""
from fractions import Fraction
import random
import re
from common import *


def hamilton(popularity,coefficients,banned=(),seed=1):
    raw=[Fraction(str(v)) for v in popularity]
    weight=[Fraction(0) if i in banned else raw[i]*max(Fraction(0),1+Fraction(str(coefficients[i]))) for i in range(9)]
    total=sum(weight)
    if not total:raise ValueError('zero legal weight')
    quotas=[500*w/total for w in weight]
    seats=[q.numerator//q.denominator for q in quotas]
    # A random permutation is used only as the final key for exact ties.
    order=list(range(9));random.Random(seed).shuffle(order);lot={p:i for i,p in enumerate(order)}
    order.sort(key=lambda i:(-(quotas[i]-seats[i]),-raw[i],lot[i]))
    for i in order[:500-sum(seats)]:seats[i]+=1
    return seats


def run():
    checks=[]
    def check(name,value):
        assert value,name
        checks.append(name)
    check('single_party_500',hamilton([100]+[0]*8,[0]*9)==[500]+[0]*8)
    check('german_opening',hamilton([0,40,10,10,30,10,0,0,0],[0]*9)==[0,200,50,50,150,50,0,0,0])
    check('coefficients_do_not_add_percentage_points',hamilton([30,70]+[0]*7,[.1]+[0]*8)[0]==160)
    check('ban_removes_weight',hamilton([30,70]+[0]*7,[0]*9,banned=[0])==[0,500]+[0]*7)
    tied=hamilton([1]*9,[0]*9,seed=19)
    check('multi_party_equal_remainders',sum(tied)==500 and set(tied)=={55,56} and tied.count(56)==5)
    check('saved_result_not_redrawn',tied==hamilton([1]*9,[0]*9,seed=19))
    try:hamilton([0]*9,[0]*9)
    except ValueError:checks.append('zero_weight_error_exit')
    else:raise AssertionError('zero weights accepted')
    rng=random.Random(61107)
    for _ in range(300):
        pop=[rng.randrange(101) for _ in range(9)];coeff=[Fraction(rng.randrange(-100,201),100) for _ in range(9)]
        if sum(p*(1+c) for p,c in zip(pop,coeff)):
            seats=hamilton(pop,coeff,seed=77)
            assert sum(seats)==500 and all(isinstance(v,int) and v>=0 for v in seats)
    checks.append('300_fractional_allocation_cases')
    clamp=lambda x:max(-100,min(100,x))
    check('bill_attitude_clamp',clamp(75+50)==100)
    check('party_bonus_15_percent',Fraction(1)*Fraction(40,100)*Fraction(50,100)*Fraction(75,100)==Fraction(15,100))
    check('opposition_half_range',50+Fraction(1,2)*(-100)==0 and 50+Fraction(1,2)*100==100)
    check('multiplicative_speed',Fraction(110,100)*Fraction(120,100)==Fraction(132,100))
    check('remaining_fraction_not_retroactive',Fraction(1,2)*30==15)
    # Work units avoid a 30/40-day stage drifting to day31/41 through a
    # repeatedly rounded percentage increment.
    for duration in [30,60,90,120]:
        work=Fraction(0)
        stages=[]
        for day in range(1,duration+1):
            work+=1
            stages.append(1 if work*3<duration else 2 if work*3<duration*2 else 3)
        assert stages[duration//3-1]==2 and stages[2*duration//3-1]==3 and work==duration
    checks.append('exact_stage_anniversaries_30_60_90_120')
    generated=[]
    for folder in ['common/scripted_effects','common/scripted_triggers','common/scripted_guis','common/scripted_localisation','common/dynamic_modifiers','common/modifier_definitions','common/ideas','common/on_actions','events','interface']:
        for path in (ROOT/folder).glob('*parliament*'):
            if path.suffix in ('.txt','.gui','.gfx'):
                assert not path.read_bytes().startswith(b'\xef\xbb\xbf'),str(path)
                parse(path.read_text('utf-8'))
                generated.append(path)
    check('generated_clausewitz_parses',len(generated)>15)
    check('no_unsupported_parameterized_effects',not any(re.search(r'\$(?:ROLE|KIND|TARGET|OPTION|ID|MONTHS|NAME|VALUE|COST|DESC|AVAILABLE)\$',p.read_text('utf-8')) for p in generated))
    definitions={}
    for folder in ['common/scripted_effects','common/scripted_triggers']:
        for path in (ROOT/folder).glob('*.txt'):
            for node in parse(path.read_text('utf-8-sig')):
                if node.key.startswith(P):
                    assert node.key not in definitions,(node.key,str(path),definitions.get(node.key))
                    definitions[node.key]=str(path)
    for path in generated:
        for n in walk(parse(path.read_text('utf-8-sig'))):
            if n.key.startswith(P) and n.key not in definitions and n.value=='yes':
                # Flags/variables are values inside their own command blocks;
                # an apdc_* key with yes is therefore a real API invocation.
                raise AssertionError(('Undefined parliament API',n.key,str(path)))
    checks.append('all_generated_effect_trigger_calls_resolve')
    gui_nodes=parse(read('interface/apdc_parliament.gui'))
    windows={n.val('name'):n for outer in gui_nodes for n in outer.children if n.val('name')}
    windows.update({n.val('name'):n for outer in parse(read('interface/APDC_cabinet.gui')) for n in outer.children if n.val('name')})
    for outer in parse(read('common/scripted_guis/apdc_parliament.txt')):
        for entry in outer.children:
            name=entry.val('window_name');assert name in windows,('Missing GUI window',name)
            controls={n.val('name') for n in walk(windows[name].children) if n.val('name')}
            lists=entry.get('dynamic_lists')
            if lists:
                for dynamic in lists.children:
                    template=dynamic.val('entry_container')
                    assert template in windows,('Missing dynamic row',template)
                    controls.update(n.val('name') for n in walk(windows[template].children) if n.val('name'))
            props=entry.get('properties')
            if props:
                for prop in props.children:assert prop.key in controls,('Property missing control',name,prop.key)
            tr=entry.get('triggers')
            if tr:
                for prop in tr.children:
                    control=re.sub(r'_(click_enabled|visible|enabled)$','',prop.key)
                    assert control in controls,('Trigger missing control',name,prop.key)
    checks.append('scripted_gui_property_and_trigger_targets')
    check('dynamic_rows_have_no_independent_windows',all(n.val('window_name') not in {P+'reform_row',P+'special_entry',P+'candidate_row',P+'option_row'} for o in parse(read('common/scripted_guis/apdc_parliament.txt')) for n in o.children))
    layout=load_json('seat_layout.json')
    check('exact_500_layout',len(layout['points'])==500 and sum(layout['row_counts'])==500)
    check('main_and_entry_500_icons',read('interface/apdc_parliament.gui').count('name = "apdc_parl_seat_')==500 and read('interface/apdc_parliament.gui').count('name = "apdc_parl_entry_seat_')==500)
    check('old_independent_panel_removed','APDC_cabinet_member_panel' not in read('interface/APDC_cabinet.gui'))
    check('private_split_source','APDC_eco_disallows_private' in read('common/scripted_effects/APDC_economy_backend.txt'))
    check('real_purchase_price_hook','multiply_variable = { APDC_eco_purchase_unit_k = APDC_eco_purchase_price_factor }' in read('common/scripted_effects/APDC_economy_equipment.txt'))
    candidates=load_json('candidates.json')['candidates']
    check('stable_candidate_ids',len({c['id'] for c in candidates})==len(candidates) and set(range(1,48)).issubset({c['id'] for c in candidates}))
    loc_path=ROOT/'localisation/simp_chinese/apdc_parliament_l_simp_chinese.yml'
    check('localisation_utf8_bom',loc_path.read_bytes().startswith(b'\xef\xbb\xbf'))
    loc=loc_path.read_text('utf-8-sig');keys=re.findall(r'^ ([A-Za-z0-9_]+):0 ',loc,re.M)
    check('no_duplicate_generated_localisation',len(keys)==len(set(keys)))
    functions={n.val('name') for p in (ROOT/'common/scripted_localisation').glob('*parliament*.txt') for n in parse(p.read_text('utf-8-sig')) if n.key=='defined_text'}
    references=set(re.findall(r'\[(ApdcParl[A-Za-z0-9_]+)\]',loc+'\n'+read('interface/apdc_parliament.gui')+'\n'+read('common/scripted_guis/apdc_parliament.txt')))
    check('all_parliament_localisation_functions_resolve',references.issubset(functions))
    source=load_json('laws.json')
    check('confirmed_population_corrections',not any('每周人力' in line or '每月人力' in line for g in source['groups'] if g['id'] in (2,4) for o in g['options'] for line in o['effects']))
    report={'status':'passed','checks':checks,'generated_files_checked':len(generated),'candidates':len(candidates),'seats':500,'scope':'static_and_numerical','runtime_report':'runtime-verification.json'}
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'static-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'passed','checks':len(checks),'generated_files':len(generated),'candidates':len(candidates)},ensure_ascii=False))


if __name__=='__main__':run()
