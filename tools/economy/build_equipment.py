"""Private equipment presets, parallel production, stock and immediate purchases."""
from collections import defaultdict
import hashlib,json,re
from common import *
from build_backend import effect, var, mod, add, lim, P

def catalogue():
 raw={}; technologies=defaultdict(list); module_techs=defaultdict(list)
 for p in effective_files('common/units/equipment'):
  for n in parse(p.read_text('utf-8-sig')):
   if n.key=='equipments': raw.update({x.key:x for x in n.children if x.value is None})
 for p in effective_files('common/technologies'):
  for top in parse(p.read_text('utf-8-sig')):
   if top.key!='technologies':continue
   for t in top.children:
    if t.value is not None:continue
    for n in walk(t.children):
     target=technologies if n.key=='enable_equipments' else module_techs if n.key=='enable_equipment_modules' else None
     if target is not None:
      for x in n.children: target[x.key].append(t.key)
 modules={}
 idea_ids=set()
 for p in effective_files('common/ideas'):
  # Some inherited idea files contain engine extensions outside the small
  # maintenance parser's grammar. Declaration keys remain unambiguous here.
  idea_ids.update(re.findall(r'\b([A-Za-z0-9_]+)\s*=\s*\{',p.read_text('utf-8-sig')))
 for p in effective_files('common/units/equipment/modules'):
  for n in parse(p.read_text('utf-8-sig')):
   if n.key=='equipment_modules':modules.update({x.key:x for x in n.children if x.value is None})
 def inherit(key,visited=None):
  visited=set(visited or ())
  if key in visited or key not in raw:return {}
  visited.add(key); n=raw[key]; d={}
  for parent in [n.val('archetype'),n.val('parent')]:
   if parent:d.update(inherit(parent,visited))
  d.update({x.key:x for x in n.children});return d
 result=[]
 for key,n in raw.items():
  if n.val('is_archetype')=='yes' or n.val('is_buildable')=='no':continue
  d=inherit(key); category=d.get('interface_category'); cat=category.value if category else ''
  if 'naval' in str(cat) or any(s in key for s in ['ship_hull','convoy','submarine','battleship','battle_cruiser','destroyer','carrier','cruiser']):continue
  if 'build_cost_ic' not in d:continue
  if not technologies[key] and (d.get('active') is None or d['active'].value!='yes'):continue
  try:cost=float(d['build_cost_ic'].value)
  except (ValueError,TypeError):continue
  if cost<=0:continue
  selected={}; module_cost=0; cost_factor=1
  # Classic pre-designer equipment inherits its archetype's slot metadata but
  # retains its own complete cost and stats. Only actual chassis need modules.
  slots=d.get('module_slots') if any(t in key for t in ['chassis','airframe']) else None
  if slots:
   for slot in slots.children:
    if slot.val('required')!='yes':continue
    allowed=slot.get('allowed_module_categories')
    categories={x.key for x in allowed.children} if allowed else set()
    candidates=[(mid,m) for mid,m in modules.items() if m.val('category') in categories]
    if not candidates:continue
    # Ordinary complete designs, never country-exclusive or special-project
    # modules that happen to have no entry in enable_equipment_modules.
    def module_price(item):
     st=item[1].get('add_stats');x=st.val('build_cost_ic','0') if st else '0'
     try:return float(x)
     except ValueError:return 0
    preferred=['tank_modern_tank_turret','tank_super_heavy_three_man_tank_turret','tank_heavy_three_man_tank_turret','tank_medium_three_man_tank_turret','tank_light_two_man_tank_turret',
     'tank_super_heavy_cannon','tank_heavy_cannon','tank_medium_cannon','tank_small_cannon','tank_heavy_machine_gun',
     'tank_bogie_suspension','tank_riveted_armor','tank_gasoline_engine',
     'light_mg_2x','medium_bomb_bay','large_bomb_bay','small_bomb_bay','bomb_locks','torpedo_mounting',
     'engine_1_1x','engine_1_2x','engine_1_3x','engine_1_4x','engine_1_6x',
     'jet_engine_1x','jet_engine_2x','jet_engine_3x','jet_engine_4x','jet_engine_6x','rocket_engine_1']
    preferred_candidates=[x for x in candidates if x[0] in preferred]
    if preferred_candidates:candidates=preferred_candidates
    else:candidates=[x for x in candidates if not x[0].startswith(('NOR_','GER_','JAP_','SOV_')) and module_techs[x[0]]]
    if not candidates:raise ValueError('No ordinary module for '+key+':'+slot.key)
    candidates.sort(key=lambda x:(preferred.index(x[0]) if x[0] in preferred else len(preferred),module_price(x),x[0]))
    mid,m=candidates[0];selected[slot.key]=mid
    module_cost+=module_price((mid,m))
    mult=m.get('multiply_stats')
    if mult:
     try:cost_factor+=float(mult.val('build_cost_ic','0'))
     except ValueError:pass
  cost=(cost+module_cost)*cost_factor
  archetype=n.val('archetype',key)
  can_produce=d.get('can_be_produced')
  def render_nodes(nodes):
   # A native restriction referencing an idea removed by APDC cannot apply;
   # avoid repeatedly evaluating an invalid database token at runtime.
   return ' '.join(('always = no' if x.key=='has_idea' and x.value.strip('"') not in idea_ids else x.key+(' '+x.op+' ' if x.op else ' ')+(x.value if x.value is not None else '{ '+render_nodes(x.children)+' }')) for x in nodes)
  result.append({'id':key,'family':archetype,'cost':round(cost,4),
   'priority':float(n.val('priority','0')),'year':float(n.val('year',d.get('year').value if d.get('year') else '0')),
   'techs':technologies[key],'modules':selected,'module_techs':sorted({t for m in selected.values() for t in module_techs[m]}),
   'picture':d.get('picture').value if d.get('picture') else '',
   'module_unlocks':[module_techs[m] for m in selected.values() if module_techs[m]],
   'can_produce':render_nodes(can_produce.children) if can_produce else ''})
 result.sort(key=lambda e:(e['family'],e['priority'],e['year'],e['id']))
 # Stock, production progress and unlock flags are saved under numeric IDs.
 # Keep removed entries reserved so pruning old equipment never reassigns a
 # country's existing stock to a different equipment type.
 registry_path=Path(__file__).with_name('equipment_ids.json')
 registry=json.loads(registry_path.read_text('utf-8'))
 assert len(set(registry.values()))==len(registry)
 assert all(isinstance(i,int) and i>0 for i in registry.values())
 next_index=max(registry.values(),default=0)+1
 changed=False
 for e in result:
  if e['id'] not in registry:
   registry[e['id']]=next_index;next_index+=1;changed=True
  e['index']=registry[e['id']]
 if changed:registry_path.write_text(json.dumps(registry,indent=2,sort_keys=True)+'\n','utf-8')
 (WORK/'equipment_catalogue.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return result

def build():
 items=catalogue();families=defaultdict(list)
 for e in items:families[e['family']].append(e)
 registry=json.loads(Path(__file__).with_name('equipment_ids.json').read_text('utf-8'))
 size=max(registry.values())+1
 signature=hashlib.sha256(json.dumps([(e['index'],e['cost']) for e in items]).encode()).hexdigest()[:12]
 schema_flag='APDC_eco_equipment_constants_'+signature
 constants='clear_array = global.APDC_eco_equipment_costs\nresize_array = { array = global.APDC_eco_equipment_costs size = '+str(size)+' value = 0 }\n'
 constants+=''.join('set_variable = { global.APDC_eco_equipment_costs^'+str(e['index'])+' = '+str(e['cost'])+' }\n' for e in items)
 constants+='set_global_flag = '+schema_flag+'\n'
 s=effect('initialize_equipment_constants',cond('NOT = { has_global_flag = '+schema_flag+' }',constants))
 migration=''
 for array in ['stocks','production_progress']:
  migration+='resize_array = { array = APDC_eco_'+array+' size = '+str(size)+' value = 0 }\n'
 for i in sorted(registry.values()):
  migration+=f'set_variable = {{ APDC_eco_stocks^{i} = APDC_eco_stock_{i} }}\nset_variable = {{ APDC_eco_production_progress^{i} = APDC_eco_eq_progress_{i} }}\n'
 migration+='set_country_flag = APDC_eco_array_stocks_v1\nset_country_flag = APDC_eco_private_stock_dirty\n'
 # Retain all old scalar values as a recovery record, including reserved IDs.
 grow=''.join(cond('check_variable = { APDC_eco_'+array+'^num < '+str(size)+' }','resize_array = { array = APDC_eco_'+array+' size = '+str(size)+' value = 0 }\n') for array in ['stocks','production_progress'])
 s+=effect('initialize_stock_arrays',cond('NOT = { has_country_flag = APDC_eco_array_stocks_v1 }',migration)+grow)
 s+=effect('equipment_unlocked','set_country_flag = APDC_eco_equipment_dirty\nclr_country_flag = APDC_eco_research_counted_today\n')
 refresh='APDC_eco_initialize_equipment_constants = yes\nAPDC_eco_initialize_stock_arrays = yes\nclear_array = APDC_eco_equipment_rows\nclear_array = APDC_eco_equipment_active\n'
 for fam,entries in families.items():
  refresh+='set_temp_variable = { APDC_eco_family_selected = 0 }\n'
  for e in reversed(entries):
   i=e['index']; eid=e['id']; un='OR = { '+' '.join('has_tech = '+t for t in e['techs'])+' }' if e['techs'] else 'always = yes'
   if 'chassis' in eid:un+=' has_dlc = "No Step Back"'
   if 'airframe' in eid:un+=' has_dlc = "By Blood Alone"'
   un+=' '+e['can_produce']
   for techs in e['module_unlocks']:un+=' OR = { '+' '.join('has_tech = '+t for t in techs)+' }'
   create=''
   if e['modules']:
    create='create_equipment_variant = { name = "APDC '+eid+'" type = '+eid+' modules = { '+ ' '.join(k+' = '+v for k,v in e['modules'].items())+' } }\n'
   first=create+'set_country_flag = APDC_eco_eq_'+str(i)+'\n'
   refresh+=cond(un,cond('NOT = { has_country_flag = APDC_eco_eq_'+str(i)+' }',first)+
    cond('check_variable = { APDC_eco_family_selected = 0 }','add_to_array = { array = APDC_eco_equipment_active value = '+str(i)+' }\nset_temp_variable = { APDC_eco_family_selected = 1 }\n'))
 for e in items:
  i=e['index'];refresh+=cond('has_country_flag = APDC_eco_eq_'+str(i),'add_to_array = { array = APDC_eco_equipment_rows value = '+str(i)+' }\n')
 refresh+='clr_country_flag = APDC_eco_equipment_dirty\n'
 s+=effect('refresh_equipment',refresh)
 s+=effect('ensure_equipment',cond('OR = { has_country_flag = APDC_eco_equipment_dirty NOT = { has_country_flag = APDC_eco_array_stocks_v1 } NOT = { has_global_flag = '+schema_flag+' } }','APDC_eco_refresh_equipment = yes\n'))
 production='APDC_eco_ensure_equipment = yes\n'+calc('private_efficiency','modifier@production_factory_max_efficiency_factor',('add',.5),('max',0))
 production+=calc('private_ic',var('private_mil'),('multiply',3.5),('multiply','{ value = modifier@industrial_capacity_factory add = 1 max = 0 }'),('multiply',var('private_efficiency')))
 production+=cond('check_variable = { APDC_eco_equipment_active^num > 0 }',calc('ic_per_type',var('private_ic'),('divide','APDC_eco_equipment_active^num')))
 produce='for_each_loop = { array = APDC_eco_equipment_active\nset_temp_variable = { APDC_eco_production_id = v }\n'
 produce+='set_variable = { global.APDC_eco_equipment_lookup_id = APDC_eco_production_id }\n'
 produce+=setv('production_cost','global.APDC_eco_equipment_costs^global.APDC_eco_equipment_lookup_id')
 produce+=cond(check('production_cost','>',0),
  'add_to_variable = { APDC_eco_production_progress^APDC_eco_production_id = APDC_eco_ic_per_type }\n'+
  calc('eq_complete','APDC_eco_production_progress^APDC_eco_production_id',('divide',var('production_cost')),('round','down'))+
  'add_to_variable = { APDC_eco_stocks^APDC_eco_production_id = APDC_eco_eq_complete }\n'+
  calc('production_remainder',var('eq_complete'),('multiply',var('production_cost')),('multiply',-1),('add','APDC_eco_production_progress^APDC_eco_production_id'))+
  'set_variable = { APDC_eco_production_progress^APDC_eco_production_id = APDC_eco_production_remainder }\n'+
  cond(check('eq_complete','>',0),'set_country_flag = APDC_eco_private_stock_dirty\n'))+'}\n'
 production+=cond(check('private_ic','>',0),produce)
 s+=effect('produce_equipment',production)
 # A purchase uses a two-part cash balance, retaining single-ruble precision.
 prepare=''
 buy=''
 nationalize=''
 for e in items:
  i=e['index'];stock='APDC_eco_stocks^'+str(i);eid=e['id']; variant=' variant_name = "APDC '+eid+'"' if e['modules'] else ''
  prepare+=cond(check('purchase_id','=',i),setv('purchase_stock',stock)+setv('purchase_unit_k',e['cost']*.2))
  deliver='add_equipment_to_stockpile = { type = '+eid+' amount = APDC_eco_purchase_quantity producer = THIS'+variant+' }\n'
  buy+=cond(check('purchase_id','=',i),
   'subtract_from_variable = { '+stock+' = APDC_eco_purchase_quantity }\n'+deliver)
  nationalize+=cond('check_variable = { '+stock+' > 0 }',
   setv('purchase_quantity',stock)+deliver+'set_variable = { '+stock+' = 0 }\n')
 s+=effect('prepare_purchase','APDC_eco_ensure_equipment = yes\n'+prepare+'clamp_variable = { var = APDC_eco_purchase_quantity min = 0 max = APDC_eco_purchase_stock }\n'+
  calc('purchase_cost_m',var('purchase_quantity'),('divide',1000),('round','down'))+
  calc('purchase_tail',var('purchase_quantity'),('mod',1000),('multiply',var('purchase_unit_k')))+
  calc('purchase_cost_m',var('purchase_cost_m'),('multiply',var('purchase_unit_k')))+
  calc('purchase_cost_k',var('purchase_cost_m'),('mod',1),('multiply',1000),('add',var('purchase_tail')))+
  calc('purchase_cost_m',var('purchase_cost_m'),('round','down'))+
  calc('purchase_carry',var('purchase_cost_k'),('divide',1000),('round','down'))+
  add('purchase_cost_m',var('purchase_carry'))+calc('purchase_cost_k',var('purchase_carry'),('multiply',-1000),('add',var('purchase_cost_k'))))
 payment='subtract_from_variable = { APDC_eco_cash_m = APDC_eco_purchase_cost_m }\nsubtract_from_variable = { APDC_eco_cash_k = APDC_eco_purchase_cost_k }\nAPDC_eco_normalize_cash = yes\n'+buy+'APDC_eco_prepare_purchase = yes\nAPDC_eco_calculate_budget = yes\n'
 s+=effect('purchase_equipment','APDC_eco_prepare_purchase = yes\n'+cond(check('purchase_quantity','>',0)+' '+check('cash_m','>=',0)+' OR = { '+check('cash_m','>',var('purchase_cost_m'))+' AND = { '+check('cash_m','=',var('purchase_cost_m'))+' '+check('cash_k','>=',var('purchase_cost_k'))+' } }',payment))
 s+=effect('nationalize_stock',nationalize+'clr_country_flag = APDC_eco_private_stock_dirty\n')
 write('common/scripted_effects/APDC_economy_equipment.txt',s)
 install_research_hooks(items)
 print('Generated',len(items),'private-equipment definitions in',len(families),'families')
 return items


def install_research_hooks(items):
 """Preserve existing callback limits while always invalidating the directory."""
 relevant={t for e in items for t in e['techs']+e['module_techs']}
 changed=[];hooked_files=[]
 for p in effective_files('common/technologies'):
  raw=p.read_text('utf-8-sig');edits=[]
  for wrapper in parse(raw):
   if wrapper.key!='technologies':continue
   for tech in wrapper.children:
    if tech.key not in relevant:continue
    hooked_files.append('common/technologies/'+p.name)
    callback=tech.get('on_research_complete');limit=tech.get('on_research_complete_limit')
    if callback and 'APDC_eco_equipment_unlocked' in raw[callback.start:callback.end]:continue
    old=raw[callback.value_start+1:callback.value_end-1] if callback else ''
    if limit:
     old='if = { limit = '+raw[limit.value_start:limit.value_end]+'\n'+old+'\n}\n'
     edits.append((limit.start,limit.end,''))
    body=block('on_research_complete',old+'\nhidden_effect = { APDC_eco_equipment_unlocked = yes }\n')
    if callback:edits.append((callback.start,callback.end,body))
    else:edits.append((tech.value_end-1,tech.value_end-1,'\n'+body))
  if edits:
   target=ROOT/'common/technologies'/p.name
   write(target.relative_to(ROOT),patches(raw,edits));changed.append(target.relative_to(ROOT).as_posix())
 (WORK/'equipment_research_hooks.json').write_text(json.dumps({'relevant_technologies':sorted(relevant),'hooked_files':sorted(set(hooked_files)),'updated_files':changed},ensure_ascii=False,indent=2),'utf-8')

if __name__=='__main__':build()
