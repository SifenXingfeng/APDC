"""Read every development/law value from the user's Word source, without edits."""
import json, re, zipfile
from lxml import etree
from common import ROOT, WORK, write, block

SOURCE = 'D:/Desktop/发展度加经济系统.docx'
TRACKS = [('society','社会发展等级',3,70),('science','科研发展等级',71,120),
          ('defense','国防发展等级',121,183),('food','温饱水平',190,222),
          ('education','教育水平',223,260),('medical','医疗水平',261,295)]
LAWS = [('tax','赋税力度',297,332),('food_spending','温饱法案',333,348),
        ('education_spending','教育法案',349,364),('medical_spending','医疗法案',365,380),
        ('development','发展开支',381,423),('research','科研开支',424,454),
        ('military','国防开支',455,506),('investment','投资生产',507,530),
        ('distribution','分配控制',531,554),('consumption','消费控制',555,577)]
NATIVE = {
 '战略资源获取效率':'local_resources_factor','每月人口':'monthly_population',
 '补给消耗':'supply_consumption_factor','建设速度':'production_speed_buildings_factor',
 '降低缺乏电力的惩罚':'out_of_power_impact_factor','生产效率上限':'production_factory_max_efficiency_factor',
 '科研速度':'research_speed_factor','工厂产出':'industrial_capacity_factory',
 '海军船坞产出':'industrial_capacity_dockyard','工厂受轰炸易损性':'industry_air_damage_factor',
 '燃油容量':'max_fuel_factor','每日政治点数获取':'political_power_gain',
 '空军学说花费':'air_doctrine_cost_factor','陆军学说花费':'land_doctrine_cost_factor',
 '海军学说花费':'naval_doctrine_cost_factor','特种部队战术消耗':'special_forces_doctrine_cost_factor',
 '专项计划速度':'special_project_speed_factor','空军顾问花费':'air_advisor_cost_factor',
 '海军顾问花费':'navy_advisor_cost_factor','陆军顾问花费':'army_advisor_cost_factor',
 '陆军师训练时间':'training_time_factor','陆军组织度':'army_org_factor',
 '适役人口系数':'conscription_factor','陆军师攻击':'army_attack_factor','陆军师防御':'army_defence_factor',
 '稳定度':'stability_factor','可征募人口':'conscription',
 '陆军学说精通度获取':'land_mastery_gain_factor',
 '海军学说精通度获取':'naval_mastery_gain_factor',
 '空军学说精通度获取':'air_mastery_gain_factor',
 '特种部队精通度获取':'special_forces_mastery_gain_factor',
 '战争支持度':'war_support_factor',
 '海军组织度':'navy_org_factor','舰队协同性':'naval_coordination',
 '空军事故几率':'air_accidents_factor','空军任务效率':'air_mission_efficiency'
}
CUSTOM = {
 '建造维护费':'construction_maintenance_factor','军工生产维护费':'mil_maintenance_factor',
 '船坞生产维护费':'nav_maintenance_factor','民用工厂消费品产出':'civ_goods',
 '科研维护费':'research_maintenance_factor','专项计划维护费':'project_maintenance_factor',
 '陆军维护费':'army_maintenance_factor','空军维护费':'air_maintenance_factor','海军维护费':'navy_maintenance_factor',
 '生活消费品人口系数':'population_factor','每周基础人口税':'head_tax',
 '每周基础消费税':'consumption_tax','私营民工扩张速度':'private_civ_expansion_factor',
 '私营军工扩张速度':'private_mil_expansion_factor','每周温饱人口支出':'food_cost',
 '每周教育人口支出':'education_cost','每周医疗人口支出':'medical_cost',
 '每周消费补贴':'subsidy','每周基础建造维护费':'construction_maintenance',
 '每周基础军工生产维护费':'mil_maintenance','每周基础船坞生产维护费':'nav_maintenance',
 '每周基础科研维护费':'research_maintenance','每周基础专项计划维护费':'project_maintenance',
 '每周基础陆军人口维护费':'army_maintenance','每周基础海军人口维护费':'navy_maintenance',
 '每周基础空军人口维护费':'air_maintenance','每日基础私营民工扩张速度':'civ_expansion_base',
 '每日基础私营军工扩张速度':'mil_expansion_base','民用工厂消费品系数':'goods_output_factor',
 '每周消费品民用工厂投资':'investment_cost','分配率':'distribution_bonus',
 '基础政治点数获取分配率':'planned_pp_distribution','科研槽':'research_slots'
}
for k,n,a,b in TRACKS:
 CUSTOM['每周'+n+'增长']=k+'_weekly'

def load():
 with zipfile.ZipFile(SOURCE) as z:
  root=etree.fromstring(z.read('word/document.xml'))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 paragraphs=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in root.xpath('//w:body/w:p',namespaces=ns)]
 result={}
 for key,label,start,end in TRACKS+LAWS:
  entries=[]; current=None
  for line in paragraphs[start:end]:
   if not line or line in ['设定规则：','【无效果】'] or line.startswith('×'): continue
   if '：' not in line:
    current={'name':line,'native':{},'custom':{},'source':[]}; entries.append(current); continue
   attr,txt=line.split('：',1)
   m=re.search(r'[-+]?\d+(?:\.\d+)?',txt)
   if not m: raise ValueError(line)
   val=float(m.group())*(1000000 if 'M' in txt else 1000 if 'K' in txt else 1)
   if '%' in txt: val/=100
   target=NATIVE.get(attr) or ('APDC_eco_'+CUSTOM[attr] if attr in CUSTOM else None)
   if not target: raise ValueError('Undefined design attribute: '+attr)
   current['native' if attr in NATIVE else 'custom'][target]=val
   current['source'].append(line)
  assert len(entries)==5,(key,len(entries))
  result[key]={'label':label,'entries':entries,'kind':'track' if (key,label,start,end) in TRACKS else 'law'}
 WORK.mkdir(parents=True,exist_ok=True)
 (WORK/'design_data.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return result

def build():
 data=load(); modifiers={}
 # Supply/population are stored in millions, money rates remain in rubles.
 # Custom modifiers retain their human-readable source values in tooltips.
 loc={}; ideatext={k:[] for k in ['city_idea','society_development_idea','poverty_level_idea','hidden_ideas']}
 cats={'society':'society_development_idea','science':'city_idea','defense':'poverty_level_idea'}
 for gi,(key,g) in enumerate(data.items(),1):
  loc['APDC_ECO_GROUP_'+key]=g['label']
  for level,e in enumerate(g['entries'],1):
   eid=f'APDC_eco_{key}_{level}'; loc[eid]=e['name']
   loc[eid+'_desc']='\\n'.join(e['source']) or '无额外修正'
   vals={**e['native'],**e['custom']}
   for attr in list(e['custom']):
    if attr=='APDC_eco_civ_goods' or attr=='APDC_eco_investment_cost' or attr in ['APDC_eco_'+v for v in ['construction_maintenance','mil_maintenance','nav_maintenance','research_maintenance','project_maintenance']]:
     vals[attr]/=1000000
   for attr in e['custom']: modifiers[attr]=next(k for k,v in CUSTOM.items() if attr=='APDC_eco_'+v)
   pictures={'society':['tribal_society','agrarian_society','outdated_industry','modern_society','modern_society'],
             'science':['poor_science_base','better_science_base','proper_science_base','big_science_base','big_science_base'],
             'defense':['poverty5','poverty4','poverty3','poverty1','no_poverty']}
   picture=pictures[key][level-1] if key in cats else 'generic_build_infrastructure'
   # Political development tiers must all appear in the native selector.
   # Only the active tier is available/coloured; other tiers stay listed but
   # unavailable. Selecting the already active idea cannot change its level.
   listed='yes' if key in cats else 'no'
   available='has_idea = '+eid if key in cats else 'always = no'
   body=f'picture = {picture}\nallowed = {{ always = {listed} }}\navailable = {{ {available} }}\nallowed_civil_war = {{ always = yes }}\ncost = -1\nremoval_cost = -1\ncancel_if_invalid = no\n'
   if key in cats: body+='traits = { '+{'society':'society_idea','science':'science_idea','defense':'poverty_idea'}[key]+' }\n'
   body+='modifier = {\n'+''.join(f'{k} = {v:g}\n' for k,v in vals.items())+'}\n'
   if key=='society' and level==1: body+='rule = { can_join_factions = no can_access_market = no }\n'
   ideatext[cats.get(key,'hidden_ideas')].append(block(eid,body))
 write('common/ideas/APDC_economy_laws.txt',block('ideas',''.join(block(k,('law = yes\nuse_list_view = yes\n' if k!='hidden_ideas' else '')+''.join(v)) for k,v in ideatext.items())))
 # External consumer-goods modifiers are migrated to the population modifier.
 modifiers['APDC_eco_population_factor']='生活消费品人口系数'
 modifiers['APDC_eco_population_base']='人口消费品基础系数'
 modifiers['APDC_eco_consumer_trade_freedom']='消费品贸易度'
 modifiers['APDC_eco_consumer_tariff']='消费品进出口税（卢布／单位）'
 # The native consumer-goods field also changes factory allocation. Keep
 # population consumption custom; presentation must not restore native use.
 native=ROOT/'common/ideas/_economic.txt'
 raw=native.read_text('utf-8-sig'); edits=[]; traits=[]
 coefficients={'undisturbed_isolation':1,'isolation':1,'civilian_economy':1,
               'low_economic_mobilisation':.85,'partial_economic_mobilisation':.7,
               'war_economy':.55,'tot_economic_mobilisation':.4}
 from common import parse,patches
 for idea in parse(raw)[0].get('economy').children:
  if idea.key not in coefficients:continue
  value=coefficients[idea.key];tid='APDC_eco_population_base_'+str(round(value*100))
  modifier=idea.get('modifier')
  if modifier:
   for n in modifier.children:
    if n.key=='APDC_eco_population_base':edits.append((n.value_start,n.value_end,str(value)))
    if n.key=='consumer_goods_expected_value':edits.append((n.start,n.end,''))
   if not modifier.get('APDC_eco_population_base'):
    edits.append((modifier.value_end-1,modifier.value_end-1,'\nAPDC_eco_population_base = '+str(value)+'\n'))
  old=idea.get('traits')
  if old:
   kept=[n.key for n in old.children if not n.key.startswith('APDC_eco_population_base_')]
   edits.append((old.value_start,old.value_end,'{ '+' '.join(kept)+' }') if kept else (old.start,old.end,''))
 write(native.relative_to(ROOT),patches(raw,edits))
 mods=''
 for k,label in modifiers.items():
  percentage=k.endswith(('_factor','_bonus','_distribution','_freedom'))
  mods+=block(k,'color_type = '+('neutral' if k=='APDC_eco_population_base' else 'bad' if k.endswith('_cost') or 'maintenance' in k else 'good')+'\nvalue_type = '+('percentage' if percentage else 'number')+'\nprecision = 2\ncategory = country')
  if k in ['APDC_eco_'+v for v in ['civ_goods','investment_cost','construction_maintenance','mil_maintenance','nav_maintenance','research_maintenance','project_maintenance']]: label+='（百万单位）' if k.endswith('civ_goods') else '（百万卢布）'
  loc[k]=label;loc['modifier_'+k]=label
 write('common/modifier_definitions/APDC_economy_modifiers.txt',mods)
 write('common/synchronized_dynamic_tokens/APDC_economy_tokens.txt','\n'.join(sorted(modifiers))+ '\nAPDC_eco_private_civ\nAPDC_eco_private_mil\n')
 from presentation import descriptions
 loc.update(descriptions(data))
 write('localisation/simp_chinese/APDC_economy_l_simp_chinese.yml','l_simp_chinese:\n'+''.join(f' {k}:0 "{v}"\n' for k,v in loc.items()),True)
 # English fallback uses the same supplied names; no missing keys in other UI languages.
 write('localisation/english/APDC_economy_l_english.yml','l_english:\n'+''.join(f' {k}:0 "{v}"\n' for k,v in loc.items()),True)
 for language in ['simp_chinese','english']:
  write('localisation/replace/zzzz_APDC_economy_slots_l_'+language+'.yml','l_'+language+':\n city_idea:0 "科研发展度"\n society_development_idea:0 "社会发展度"\n poverty_level_idea:0 "国防发展度"\n EFFECT_CHANGE_LAW_city_idea:0 "将科研发展度改为“$NAME|Y$”，效果为（$DESC$）。"\n EFFECT_CHANGE_LAW_society_development_idea:0 "将社会发展度改为“$NAME|Y$”，效果为（$DESC$）。"\n EFFECT_CHANGE_LAW_poverty_level_idea:0 "将国防发展度改为“$NAME|Y$”，效果为（$DESC$）。"\n',True)
 from build_law_stat_display import build as build_law_stat_display
 build_law_stat_display()
 print('Loaded 6 development tracks, 10 law groups, 80 tiers; generated',len(modifiers),'custom modifiers')
 return data

if __name__=='__main__': build()
