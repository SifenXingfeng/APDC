"""Economy panel using APDC cabinet/organization window and list conventions."""
import json,shutil
from PIL import Image,ImageDraw,ImageFont
from common import *
from build_data import TRACKS,LAWS
from build_backend import effect, var, mod, add, lim, P
from presentation import augment
from number_format import CompactNumbers, panel_numbers

def icon(name,sprite,x,y,extra=''):
 return block('iconType',f'name = "{name}" position = {{ x = {x} y = {y} }} spriteType = "{sprite}" alwaystransparent = yes '+extra)
def text(name,key,x,y,w=180,h=28,font='hoi_24header',extra='',align='center'):
 return block('instantTextboxType',f'name = "{name}" position = {{ x = {x} y = {y} }} font = "{font}" text = "{key}" maxWidth = {w} maxHeight = {h} fixedsize = yes format = {align} vertical_alignment = center alwaystransparent = yes '+extra)
def number_text(*args,**kwargs):
 # Amounts must stay readable rather than replacing their significant digits
 # or unit suffix with an ellipsis. Geometry is checked against bitmap fonts.
 kwargs['extra'] = kwargs.get('extra','') + ' truncate = no'
 return text(*args,**kwargs)
def button(name,sprite,x,y,w,h,tip='',extra=''):
 return block('buttonType',f'name = "{name}" position = {{ x = {x} y = {y} }} size = {{ x = {w} y = {h} }} spriteType = "{sprite}" clicksound = click_default '+(f'pdx_tooltip = "{tip}" ' if tip else '')+extra)
def window(name,body,w,h,x=0,y=0,extra=''):
 return block('containerWindowType',f'name = "{name}" position = {{ x = {x} y = {y} }} size = {{ width = {w} height = {h} }} '+extra+'\n'+body)
def scroll(name,listname,entry,w,h,x,y,slotw,sloth):
 grid=block('gridBoxType',f'name = "{listname}" position = {{ x = 0 y = 0 }} size = {{ width = {slotw} height = 100% }} slotsize = {{ width = {slotw} height = {sloth} }} max_slots_horizontal = 1 format = "UPPER_LEFT"')
 return window(name,'background = { name = "Background" spriteType = "GFX_tiled_window_transparent" }\n'+grid,w,h,x,y,'clipping = yes verticalScrollbar = "right_vertical_slider" autohide_scrollbars = yes smooth_scrolling = yes scroll_wheel_factor = '+str(sloth)+' margin = { top = 0 right = 10 bottom = 0 }')

def build():
 data=json.loads((WORK/'design_data.json').read_text('utf-8')); items=json.loads((WORK/'equipment_catalogue.json').read_text('utf-8'))
 assets=ROOT/'gfx/interface/APDC/economy';assets.mkdir(parents=True,exist_ok=True)
 source=Path('D:/Desktop/经济面板美术素材')
 sprites=[]
 def sprite(name,filename,frames=1):
  sprites.append(block('spriteType',f'name = "GFX_APDC_eco_{name}" texturefile = "gfx/interface/APDC/economy/{filename}" noOfFrames = {frames}'))
 # The background is maintained in the project, with the exit as a real button.
 assert (assets/'panel.png').exists()
 sprite('panel','panel.png')
 files={'tray':'民生发展度背景托盘.png','welfare':'民生发展度进度条.png','construction':'私营产业建设进度条.png','eq_row':'私营军工装备背景条.png','eq_progress':'私营军工装备生产进度条.png','buy':'购入按钮.png','direction':'消费品贸易方向条.png','trade_menu':'消费品贸易国菜单.png','trade_toggle':'消费品贸易国菜单展开按钮.png'}
 for key,name in files.items():
  shutil.copy2(source/name,assets/(key+'.png'));sprite(key,key+'.png',2 if key=='trade_toggle' else 3 if key in ['tray','welfare','construction','direction'] else 1)
 # A real sprite is required here: the native standard_button_88 is a textSprite.
 for name,w,h in [('quantity',108,32),('maximum',145,30),('accept',185,42)]:
  sprites.append(block('corneredTileSpriteType',f'name = "GFX_APDC_eco_button_{name}" texturefile = "gfx/interface/standard_button_88.dds" size = {{ x = {w} y = {h} }} borderSize = {{ x = 8 y = 8 }}'))
 # Rebuild the font glyph at y=2 (previous origin -1): exactly three pixels
 # lower, with the same 15x20 text-icon metrics and no change to text baselines.
 ruble=Image.new('RGBA',(15,20));ImageDraw.Draw(ruble).text((1,2),'₽',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18),fill='white',stroke_width=1,stroke_fill='black')
 ruble.save(assets/'ruble.tga')
 sprites.append(block('spriteType','name = "GFX_APDC_ruble_texticon" texturefile = "gfx/interface/APDC/economy/ruble.tga" legacy_lazy_load = no noOfFrames = 1'))
 # Native button input follows the sprite dimensions. Never share a 100px
 # transparent texture with smaller controls or it steals neighbouring input.
 for key,w,h in [('hitbox',74,74),('allocation_hitbox',28,25),('trade_hitbox',56,52),('cash_hitbox',258,40),('weekly_hitbox',310,40),('weekly_change_hitbox',76,25),('domestic_hitbox',119,51),('distribution_hitbox',61,50),('build_hitbox',333,68)]:
  Image.new('RGBA',(w,h)).save(assets/(key+'.tga'));sprite(key,key+'.tga')
 # Split strips into small atlases: every individual pixel of progress is
 # addressable without exceeding the GPU's maximum texture dimensions.
 def progress_atlas(key,frame_w,pieces):
  im=Image.open(source/files[key]).convert('RGBA');height=im.height;pw=frame_w//pieces
  for part in range(pieces):
   left=part*pw;right=frame_w if part==pieces-1 else left+pw;width=right-left
   atlas=Image.new('RGBA',(width*(width+1)*3,height))
   for mode in range(3):
    tile=im.crop((mode*frame_w+left,0,mode*frame_w+right,height))
    for fill in range(width+1):
     frame=mode*(width+1)+fill
     if fill:atlas.paste(tile.crop((0,0,fill,height)),(frame*width,0))
   name=f'{key}_{part}';atlas.save(assets/(name+'.png'));sprite(name,name+'.png',(width+1)*3)
  return pw
 progress_atlas('welfare',78,2);progress_atlas('construction',333,9)
 # Equipment progress is one color and one unit per bar.
 im=Image.open(source/files['eq_progress']).convert('RGBA');pw=37
 for part in range(7):
  atlas=Image.new('RGBA',(37*38,9));tile=im.crop((37*part,0,37*(part+1),9))
  for fill in range(38):
   if fill:atlas.paste(tile.crop((0,0,fill,9)),(fill*37,0))
  atlas.save(assets/f'eqp_{part}.png');sprite(f'eqp_{part}',f'eqp_{part}.png',38)
 write('interface/APDC_economy_panel.gfx',block('spriteTypes',''.join(sprites)))

 loc={
 'APDC_ECO_TITLE':'经济面板','APDC_ECO_CASH':'国库：[?APDC_eco_cash_display_m|3]M₽',
 'APDC_ECO_WEEKLY':'每周变化：[?APDC_eco_weekly_balance_m|3+]M₽',
 'APDC_ECO_PUBLIC':'国营民工','APDC_ECO_PUBLIC_COUNT':'[?APDC_eco_public_civ|0]','APDC_ECO_PRIVATE':'私营民工','APDC_ECO_PRIVATE_COUNT':'[?APDC_eco_private_civ_raw|0]',
 'APDC_ECO_DOMESTIC':'总消费品\\n[?APDC_eco_domestic_m|3]M','APDC_ECO_DISTRIBUTION':'分配率\\n[?APDC_eco_distribution|%1]',
 'APDC_ECO_SUPPLY':'供给\\n[?APDC_eco_supply_m|3]M','APDC_ECO_DEMAND':'需求\\n[?APDC_eco_demand_m|3]M',
 'APDC_ECO_EXTRA_IN':'额外输入消费品\\n[?APDC_eco_extra_input|3]M','APDC_ECO_EXTRA_OUT':'额外输出消费品\\n[?APDC_eco_extra_output|3]M',
 'APDC_ECO_TRADE':'贸易消费品\\n[?APDC_eco_trade_net_m|3+]M',
 'APDC_ECO_PRIVATE_MIL':'私营军用工厂：[?APDC_eco_private_mil_raw|0]',
 'APDC_ECO_PLUS':'+','APDC_ECO_MINUS':'−','APDC_ECO_BACK':'返回',
 'APDC_ECO_CIV_BUILD':'私营民工：剩余[?APDC_eco_civ_days|0]天',
 'APDC_ECO_MIL_BUILD':'私营军工：剩余[?APDC_eco_mil_days|0]天',
 'APDC_ECO_CIV_STOP':'私营民工：停止建设','APDC_ECO_MIL_STOP':'私营军工：停止建设',
 'APDC_ECO_CIV_CLOSE':'私营民工：正在缩减','APDC_ECO_MIL_CLOSE':'私营军工：正在缩减',
 'APDC_ECO_BUY':'购入','APDC_ECO_CLOSE':'关闭','APDC_ECO_LAW_TITLE':'[APDCEconomyLawGroupName]',
 'APDC_ECO_LAW_NAME':'[APDCEconomyLawName]','APDC_ECO_LAW_COST':'[APDCEconomyLawBlocked][APDCEconomyLawCost]',
 'APDC_ECO_LAW_COST_ENOUGH':'£pol_power §Y150§!','APDC_ECO_LAW_COST_SHORT':'£pol_power §R150§!','APDC_ECO_LAW_BLOCKED':'£trigger_no ',
 'APDC_ECO_LAW_TOOLTIP':'[APDCEconomyLawTooltip]\\n\\n更换花费：[APDCEconomyLawCost]\\n国库为负数时禁止更换。',
 'APDC_ECO_EQ_NAME':'[APDCEconomyEquipmentName]','APDC_ECO_EQ_STOCK':'[?APDC_eco_ui_stock^APDC_eco_equipment_id|0]',
 'APDC_ECO_PURCHASE_TITLE':'购入装备','APDC_ECO_PURCHASE_NAME':'[APDCEconomyPurchaseName]',
 'APDC_ECO_PURCHASE_QUANTITY':'购入数量：[?APDC_eco_purchase_quantity|0]',
 'APDC_ECO_PURCHASE_STOCK':'可购库存：[?APDC_eco_purchase_stock|0]',
 'APDC_ECO_PURCHASE_COST':'总价：[?APDC_eco_purchase_cost_m|2]M + [?APDC_eco_purchase_cost_k|2]K₽',
 'APDC_ECO_BUY_TIP':'立即付款，装备立即加入国家库存。国库余额不足时无法购买。',
 'APDC_ECO_TRADE_COUNTRY_AMOUNT':'[?ROOT.APDC_eco_trade_amounts^APDC_eco_trade_index|3+]M',
 'APDC_ECO_SOCIETY_TIP':'[APDCEconomySocietyDescription]',
 'APDC_ECO_CASH_TIP':'每周收入：[?APDC_eco_weekly_income_m|3]M₽\\n人口税：[?APDC_eco_head_tax_m|3]M₽\\n消费税：[?APDC_eco_consumption_tax_m|3]M₽\\n关税：[?APDC_eco_tariffs_m|3]M₽\\n\\n每周开支：[?APDC_eco_weekly_expenses_m|3]M₽\\n人口开支：[?APDC_eco_welfare_cost_m|3]M₽\\n消费补贴：[?APDC_eco_subsidies_m|3]M₽\\n消费品工厂投资：[?APDC_eco_investment_cost_m|3]M₽\\n建设维护：[?APDC_eco_construction_cost_m|3]M₽\\n军工生产维护：[?APDC_eco_production_cost_m|3]M₽\\n船坞生产维护：[?APDC_eco_naval_production_cost_m|3]M₽\\n科研维护：[?APDC_eco_research_cost_m|3]M₽\\n专项计划维护：[?APDC_eco_projects_cost_m|3]M₽\\n陆军维护：[?APDC_eco_army_cost_m|3]M₽\\n海军维护：[?APDC_eco_navy_cost_m|3]M₽\\n空军维护：[?APDC_eco_air_cost_m|3]M₽',
 'APDC_ECO_PUBLIC_TIP':'分配国营民工生产消费品。外国提供的可支配民工同样可以分配。',
 'APDC_ECO_DISTRIBUTION_TIP':'消费品在分配前合计，再乘以分配率得到实际供给。\\n基础分配率：[?APDC_eco_distribution|%1]'
 }
 for k,label,*_ in TRACKS:
  loc['APDC_ECO_'+k.upper()]=label
  loc['APDC_ECO_'+k.upper()+'_WEEKLY']='[?APDC_eco_'+k+'_change|2+]/周'
  for j,e in enumerate(data[k]['entries'],1):loc[f'APDC_ECO_{k}_{j}_TIP']=e['name']+'\\n'+'\\n'.join(e['source'])
 for k,label,*_ in LAWS:
  loc['APDC_ECO_'+k.upper()]=label
 for n in ['1','10','100','1000']:loc['APDC_ECO_PLUS_'+n]='+'+n;loc['APDC_ECO_MINUS_'+n]='−'+n
 loc['APDC_ECO_MAX']='最大'

 # Scripted text resolves list parameters within the correct player scope.
 sl=''
 def defined(name,rows,fallback):
  return block('defined_text','name = '+name+'\n'+''.join('text = { trigger = { '+tr+' } localization_key = '+key+' }\n' for tr,key in rows)+'text = { localization_key = '+fallback+' }\n')
 sl+=defined('APDCEconomyLawGroupName',[(check('selected_group','=',i),'APDC_ECO_GROUP_'+k) for i,(k,*_) in enumerate(LAWS,1)],'APDC_ECO_TITLE')
 for mode in ['Name','Description']:
  sl+=defined('APDCEconomyLaw'+mode,[(check('selected_group','=',i)+' '+check('law_level','=',j),P+k+'_'+str(j)+('_desc' if mode=='Description' else '')) for i,(k,*_) in enumerate(LAWS,1) for j in range(1,6)],'APDC_ECO_TITLE')
 sl+=defined('APDCEconomyEquipmentName',[(check('equipment_id','=',e['index']),e['id']) for e in items],'APDC_ECO_BUY')
 sl+=defined('APDCEconomyPurchaseName',[(check('purchase_id','=',e['index']),e['id']) for e in items],'APDC_ECO_BUY')
 sl+=defined('APDCEconomySocietyDescription',[('has_idea = '+P+'society_'+str(j),P+'society_'+str(j)+'_desc') for j in range(1,6)],'APDC_ECO_TITLE')
 numbers=CompactNumbers(loc,defined)
 presentation_sl,presentation_ui=augment(data,loc,defined,numbers)
 purchase_number=panel_numbers(numbers,loc)
 sl+=presentation_sl
 sl+=numbers.sl

 props=[];triggers=[];clicks=[];gui=[]
 # Reusable list entries follow the organization system's numeric/country lists.
 row=button(P+'law_button','GFX_idea_entry_bg_3',3,0,462,74,'APDC_ECO_LAW_TOOLTIP')
 row+=icon(P+'law_current','GFX_idea_entry_bg_3',3,0,'frame = 2')
 row+=button(P+'law_icon','GFX_idea_generic_build_infrastructure',12,4,60,68,'APDC_ECO_LAW_TOOLTIP')
 row+=text(P+'law_name','APDC_ECO_LAW_NAME',84,-13,160,'100%%','hoi_18mbs',align='left')
 row+=block('instantTextboxType','name = "APDC_eco_law_cost" position = { x = 200 y = 32 } font = "hoi_16mbs" text = "APDC_ECO_LAW_COST" maxWidth = 142 maxHeight = 10 format = center alwaystransparent = yes')
 gui.append(window(P+'law_row',row,462,74))
 tr='OR = { '+' '.join('AND = { '+check('selected_group','=',i)+' '+check('law_level','=',j)+' has_idea = '+P+k+'_'+str(j)+' }' for i,(k,*_) in enumerate(LAWS,1) for j in range(1,6))+' }'
 triggers.append(P+'law_current_visible = { '+tr+' }')
 enough_pp='NOT = { has_political_power < 150 }'
 selectable=enough_pp+' '+check('cash_m','>=',0)+' NOT = { '+tr+' }\n'+ 'OR = { NOT = { '+check('selected_group','=',9)+' } AND = { '+P+'is_planned = yes '+check('law_level','=',5)+' } AND = { '+P+'is_planned = no '+check('law_level','<',5)+' } }'
 visual='OR = { '+tr+' AND = { '+selectable+' } }'
 for control in ['law_button','law_icon']:
  triggers.append(P+control+'_click_enabled = { '+visual+' }')
  clicks.append(P+control+'_click = { '+cond(selectable,setv('requested_law',var('law_level'))+'APDC_eco_change_law = yes\nclear_variable = APDC_eco_selected_group\nAPDC_eco_sync_ui = yes')+' }')
 sl+=defined('APDCEconomyLawCost',[(enough_pp,'APDC_ECO_LAW_COST_ENOUGH')],'APDC_ECO_LAW_COST_SHORT')
 sl+=defined('APDCEconomyLawBlocked',[('NOT = { '+visual+' }','APDC_ECO_LAW_BLOCKED')],'APDC_ECO_EMPTY')
 write('common/scripted_localisation/APDC_economy_ui.txt',sl)
 row=icon(P+'eq_row_bg','GFX_APDC_eco_eq_row',0,0)
 row+=text(P+'eq_name','APDC_ECO_EQ_NAME',9,4,125,23,'hoi_16mbs')
 row+=text(P+'eq_stock','APDC_ECO_EQ_STOCK',136,5,61,21,'vic_18_black')
 row+=button(P+'eq_buy','GFX_APDC_eco_buy',208,9,62,21,'APDC_ECO_BUY_TIP')+text(P+'eq_buy_text','APDC_ECO_BUY',208,8,62,23,'vic_18_black')
 for part in range(7):
  name=P+'eq_bar_'+str(part);row+=icon(name,'GFX_APDC_eco_eqp_'+str(part),7+part*37,34)
  props.append(name+' = { frame = APDC_eco_ui_eqp_'+str(part)+'^APDC_eco_equipment_id }')
 gui.append(window(P+'equipment_row',row,277,45))
 clicks.append(P+'eq_buy_click = { '+setv('purchase_id',var('equipment_id'))+setv('purchase_quantity',1)+setv('purchase_open',1)+'APDC_eco_prepare_purchase = yes APDC_eco_refresh_purchase_number_ui = yes }')
 row=icon(P+'trade_flag','GFX_APDC_cooperation_organization_flag_small_unfiltered',19,15,'scale = 0.5 centerposition = yes')+number_text(P+'trade_amount','APDC_ECO_TRADE_COUNTRY_AMOUNT',42,0,100,30,'vic_18_black')
 gui.append(window(P+'trade_row',row,157,30))
 props.append(P+'trade_flag = { image = "[THIS.GetFlag]" }')

 body=icon(P+'panel_art','GFX_APDC_eco_panel',0,0)
 body+=button(P+'back','GFX_APDC_custom_panel_exit',12,11,96,47,'APDC_ECO_BACK')
 body+=text(P+'title','APDC_ECO_TITLE',20,66,230,40,'hoi_36header')
 body+=number_text(P+'cash','APDC_ECO_CASH',485,65,258,40,'hoi_24header')
 body+=button(P+'cash_tip','GFX_APDC_eco_cash_hitbox',485,65,258,40,'APDC_ECO_CASH_TIP')
 body+=number_text(P+'weekly','APDC_ECO_WEEKLY',742,65,310,40,'hoi_24header')
 body+=button(P+'weekly_tip','GFX_APDC_eco_weekly_hitbox',742,65,310,40,'APDC_ECO_WEEKLY_TIP')
 clicks.append(P+'back_click = { clear_variable = APDC_eco_panel_open clear_variable = APDC_eco_selected_group clear_variable = APDC_eco_purchase_open clear_variable = APDC_eco_trade_open }')
 for r,k in enumerate(['food','education','medical']):
  y=125+r*88
  body+=text(P+k+'_heading','APDC_ECO_'+k.upper(),20,y+17,180,42,'hoi_36header')
  for segment in range(4):
   for part in range(2):
    name=P+f'{k}_bar_{segment}_{part}';body+=icon(name,'GFX_APDC_eco_welfare_'+str(part),277+segment*136+39*part,y+24)
    props.append(name+' = { frame = '+name+' }')
  for tier in range(1,6):
   x=210+(tier-1)*136;name=P+f'{k}_tier_{tier}'
   body+=icon(name+'_tray','GFX_APDC_eco_tray',x,y)
   props.append(name+'_tray = { frame = '+name+'_frame }')
   body+=icon(name+'_icon','GFX_idea_generic_build_infrastructure',x+37,y+37,'centerposition = yes')
   body+=button(name+'_tip','GFX_APDC_eco_hitbox',x,y,74,74,'APDC_ECO_'+k+'_'+str(tier)+'_TIP')
   loc['APDC_ECO_TIER_'+str(tier)]=str(tier)
  body+=number_text(P+k+'_weekly','APDC_ECO_'+k.upper()+'_WEEKLY',840,y+24,76,25,'hoi_16mbs')
  body+=button(P+k+'_weekly_tip','GFX_APDC_eco_weekly_change_hitbox',840,y+24,76,25,'APDC_ECO_'+k.upper()+'_WEEKLY_TIP')
  group={'food':2,'education':3,'medical':4}[k]
  body+=button(P+k+'_law','GFX_idea_generic_build_infrastructure',920,y+1,70,70,'APDC_ECO_ACTIVE_'+LAWS[group-1][0])
  clicks.append(P+k+'_law_click = { '+setv('selected_group',group)+' }')
 # Four spending/tax groups occupy the same row after the requested addition.
 for col,(key,group) in enumerate([('tax',1),('development',5),('research',6),('military',7)]):
  x=20+col*263;body+=text(P+key+'_label','APDC_ECO_'+key.upper(),x,421,177,40,'hoi_24header')
  body+=button(P+key+'_law','GFX_idea_generic_build_infrastructure',x+178,405,70,70,'APDC_ECO_ACTIVE_'+key)
  clicks.append(P+key+'_law_click = { '+setv('selected_group',group)+' }')
 for col,(key,group) in enumerate([('investment',8),('distribution',9),('consumption',10)]):
  x=20+col*235;body+=text(P+key+'_label','APDC_ECO_'+key.upper(),x,793,145,40,'hoi_24header')
  body+=button(P+key+'_law','GFX_idea_generic_build_infrastructure',x+145,780,70,70,'APDC_ECO_ACTIVE_'+key)
  clicks.append(P+key+'_law_click = { '+setv('selected_group',group)+' }')
 body+=text(P+'public','APDC_ECO_PUBLIC',27,574,145,22,'hoi_18mbs')
 body+=text(P+'public_count','APDC_ECO_PUBLIC_COUNT',63,599,70,24,'hoi_18mbs')
 body+=button(P+'public_plus','GFX_APDC_eco_allocation_hitbox',140,598,28,25)+text(P+'plus','APDC_ECO_PLUS',140,598,28,25,'hoi_18mbs')
 body+=button(P+'public_minus','GFX_APDC_eco_allocation_hitbox',29,598,28,25)+text(P+'minus','APDC_ECO_MINUS',29,598,28,25,'hoi_18mbs')
 clicks.append(P+'public_plus_click = { '+add('public_civ',1)+'APDC_eco_refresh_current_supply = yes APDC_eco_calculate_budget = yes APDC_eco_sync_ui = yes }')
 clicks.append(P+'public_minus_click = { '+add('public_civ',-1)+'APDC_eco_refresh_current_supply = yes APDC_eco_calculate_budget = yes APDC_eco_sync_ui = yes }')
 triggers.append(P+'public_plus_click_enabled = { '+check('public_civ','<',var('public_available'))+' }')
 triggers.append(P+'public_minus_click_enabled = { '+check('public_civ','>',0)+' }')
 body+=text(P+'private','APDC_ECO_PRIVATE',27,673,145,22,'hoi_18mbs')
 body+=text(P+'private_count','APDC_ECO_PRIVATE_COUNT',27,698,145,24,'hoi_18mbs')
 for name,key,x,y,w,h in [('domestic','DOMESTIC',279,622,119,51),('dist','DISTRIBUTION_VALUE',455,625,61,50),('extra_in','EXTRA_IN',201,721,117,45),('extra_out','EXTRA_OUT',357,721,117,45)]:
  body+=number_text(P+name,'APDC_ECO_'+key,x,y,w,h,'vic_18_black',extra='multiline = yes')
 body+=button(P+'domestic_tip','GFX_APDC_eco_domestic_hitbox',279,622,119,51,'APDC_ECO_DOMESTIC_TIP')
 body+=button(P+'distribution_tip','GFX_APDC_eco_distribution_hitbox',455,625,61,50,'APDC_ECO_DISTRIBUTION_TIP')
 for k,x in [('supply',580),('demand',637)]:
  body+=text(P+k+'_heading','APDC_ECO_'+k.upper()+'_HEADING',x,606,54,30,'hoi_18mbs')
  # Separate the amount centres by 63px; the widest positive compact value
  # (999.99Qa including outline) needs 60px in the Chinese 16px font.
  body+=number_text(P+k+'_value','APDC_ECO_'+k.upper()+'_VALUE',572 if k=='supply' else 635,666,64,30,'hoi_16mbs')
 body+=number_text(P+'trade_label','APDC_ECO_TRADE',279,523,130,44,'hoi_18mbs',extra='multiline = yes')
 body+=icon(P+'direction','GFX_APDC_eco_direction',331,574)
 props.append(P+'direction = { frame = APDC_eco_trade_frame }')
 body+=icon(P+'trade_toggle_icon','GFX_APDC_eco_trade_toggle',409,534)+button(P+'trade_toggle','GFX_APDC_eco_trade_hitbox',401,519,56,52)
 props.append(P+'trade_toggle_icon = { frame = APDC_eco_trade_toggle_frame }')
 clicks.append(P+'trade_toggle_click = { if = { limit = { has_variable = APDC_eco_trade_open } clear_variable = APDC_eco_trade_open set_variable = { APDC_eco_trade_toggle_frame = 1 } } else = { set_variable = { APDC_eco_trade_open = 1 } set_variable = { APDC_eco_trade_toggle_frame = 2 } } }')
 trade=icon(P+'trade_menu_bg','GFX_APDC_eco_trade_menu',0,0)
 trade+=scroll(P+'trade_scroll',P+'trade_list',P+'trade_row',178,208,5,4,157,30)
 gui.append(window(P+'trade_menu',trade,188,222))
 body+=window(P+'trade_hook','',1,1,274,292,'clipping = no')
 body+=text(P+'private_mil','APDC_ECO_PRIVATE_MIL',742,533,310,42,'hoi_24header')
 body+=scroll(P+'equipment_scroll',P+'equipment_list',P+'equipment_row',293,303,750,604,277,45)
 for c,kind in enumerate(['civ','mil']):
  for part in range(9):
   name=P+kind+'_build_'+str(part);body+=icon(name,'GFX_APDC_eco_construction_'+str(part),25+c*363+37*part,875)
   props.append(name+' = { frame = '+name+'_frame }')
  for suffix in ['build','stop','close']:
   name=P+kind+'_construction_'+suffix;body+=text(name,'APDC_ECO_'+kind.upper()+'_'+suffix.upper(),31+c*363,900,319,30,'hoi_18mbs')
   triggers.append(name+'_visible = { '+check(kind+'_velocity','>' if suffix=='build' else '=' if suffix=='stop' else '<',0)+' }')
  body+=button(P+kind+'_build_tip','GFX_APDC_eco_build_hitbox',25+c*363,875,333,68,'APDC_ECO_'+kind.upper()+'_BUILD_TIP')
 # The side selector is a child of the draggable main panel, with no clipping.
 side=text(P+'law_title','APDC_ECO_LAW_TITLE',15,8,450,30,'hoi_20b')
 side+=scroll(P+'law_scroll',P+'law_list',P+'law_row',488,504,8,54,462,74)
 side+=button(P+'law_close','GFX_closebutton',450,5,40,40,'APDC_ECO_CLOSE')
 gui.append(window(P+'law_side', 'background = { name = "Background" spriteType = "GFX_tiled_plain_bg" }\n'+side,500,590,574,80,'show_position = { x = 1074 y = 80 } show_animation_type = decelerated hide_animation_type = accelerated animation_time = 300 clipping = no'))
 clicks.append(P+'law_close_click = { clear_variable = APDC_eco_selected_group }')
 # Reserve the selector's width when placing the main panel. The combined
 # 1578px layout fits at 1920x1080 without dragging a clipped sidebar back in.
 # The draggable window owns its input surface. Large child backgrounds must
 # not capture all clicks or become the draggable surface themselves.
 root='background = { name = "Background" spriteType = "GFX_tiled_window_transparent" }\n'
 root+=window(P+'law_hook','',1,1,extra='clipping = no')
 root+=body
 root+=window(P+'purchase_hook','',1,1,276,180,'clipping = no')
 gui.append(window(P+'panel',root,1078,972,x=-250,extra='orientation = center origo = center moveable = yes click_to_front = yes clipping = no'))
 # Procurement popup reuses the vanilla market purchase background and fonts.
 buy='background = { name = "Background" spriteType = "GFX_diplo_action_lend_lease_bg" }\n'
 buy+=text(P+'purchase_title','APDC_ECO_PURCHASE_TITLE',100,28,327,32)
 buy+=text(P+'purchase_name','APDC_ECO_PURCHASE_NAME',30,83,467,36)
 buy+=text(P+'purchase_stock','APDC_ECO_PURCHASE_STOCK',30,170,467,30,'hoi_20b')
 buy+=text(P+'purchase_quantity','APDC_ECO_PURCHASE_QUANTITY',30,220,467,30,'hoi_20b')
 buy+=number_text(P+'purchase_cost','APDC_ECO_PURCHASE_COST',30,440,467,40,'hoi_20b')
 for j,amount in enumerate([1,10,100,1000]):
  for sign,y in [(1,315),(-1,355)]:
   name=P+('qty_add_' if sign>0 else 'qty_remove_')+str(amount);key='APDC_ECO_'+('PLUS_' if sign>0 else 'MINUS_')+str(amount)
   buy+=button(name,'GFX_APDC_eco_button_quantity',34+j*116,y,108,32)+text(name+'_label',key,34+j*116,y,108,32,'hoi_18mbs')
 buy+=button(P+'qty_max','GFX_APDC_eco_button_maximum',190,395,145,30)+text(P+'qty_max_text','APDC_ECO_MAX',190,395,145,30,'hoi_18mbs')
 buy+=button(P+'purchase_accept','GFX_APDC_eco_button_accept',170,510,185,42,'APDC_ECO_BUY_TIP')+text(P+'purchase_accept_text','APDC_ECO_BUY',170,510,185,42,'hoi_20b')
 buy+=button(P+'purchase_close','GFX_closebutton',477,9,40,40,'APDC_ECO_CLOSE')
 gui.append(window(P+'purchase',buy,527,612,extra='click_to_front = yes clipping = no'))
 write('interface/APDC_economy_panel.gui',block('guiTypes',''.join(gui)).replace('vic_18_black','hoi_18mbs'))

 dynamic=block(P+'law_list','array = APDC_eco_law_levels value = APDC_eco_law_level entry_container = "APDC_eco_law_row"')
 dynamic+=block(P+'equipment_list','array = APDC_eco_equipment_rows value = APDC_eco_equipment_id entry_container = "APDC_eco_equipment_row"')
 dynamic+=block(P+'trade_list','array = APDC_eco_trade_partners index = APDC_eco_trade_index change_scope = yes country_scope_entry_container = "APDC_eco_trade_row"')
 # The trade menu's row-level predicate uses ROOT, because entries change scope.
 def only(rows, prefix, matching):return '\n'.join(s for s in rows if s.startswith(prefix)==matching)
 # Separate GUI instances own complete window visibility, including backgrounds
 # and scrollbars. The sidebar hook precedes the opaque main body, as diplomacy does.
 sg=block(P+'panel_ui','context_type = player_context\nwindow_name = "APDC_eco_panel"\nvisible = { has_variable = APDC_eco_panel_open }\n'+block('properties',only(props,P+'trade_flag',False))+block('triggers',only(triggers,P+'law_',False))+block('effects',only(clicks,P+'law_',False))+block('dynamic_lists',block(P+'equipment_list','array = APDC_eco_equipment_rows value = APDC_eco_equipment_id entry_container = "APDC_eco_equipment_row"')))
 sg+=block(P+'law_side_ui','context_type = player_context\nparent_window_name = "APDC_eco_law_hook"\nwindow_name = "APDC_eco_law_side"\nvisible = { has_variable = APDC_eco_panel_open check_variable = { APDC_eco_selected_group > 0 } }\n'+block('triggers',only(triggers,P+'law_',True))+block('effects',only(clicks,P+'law_',True))+block('dynamic_lists',block(P+'law_list','array = APDC_eco_law_levels value = APDC_eco_law_level entry_container = "APDC_eco_law_row"')))
 sg+=block(P+'trade_ui','context_type = player_context\nparent_window_name = "APDC_eco_trade_hook"\nwindow_name = "APDC_eco_trade_menu"\nvisible = { has_variable = APDC_eco_panel_open has_variable = APDC_eco_trade_open }\n'+block('properties',only(props,P+'trade_flag',True))+block('dynamic_lists',block(P+'trade_list','array = APDC_eco_trade_partners index = APDC_eco_trade_index change_scope = yes country_scope_entry_container = "APDC_eco_trade_row"')))
 buyclick=[]
 for amount in [1,10,100,1000]:
  for sign in [1,-1]:
   name=P+('qty_add_' if sign>0 else 'qty_remove_')+str(amount)
   buyclick.append(block(name+'_click',add('purchase_quantity',amount*sign)+'APDC_eco_prepare_purchase = yes APDC_eco_refresh_purchase_number_ui = yes'))
 buyclick.append(block(P+'qty_max_click',setv('purchase_quantity',var('purchase_stock'))+'APDC_eco_prepare_purchase = yes APDC_eco_refresh_purchase_number_ui = yes'))
 buyclick.append(block(P+'purchase_close_click','clear_variable = APDC_eco_purchase_open'))
 buyclick.append(block(P+'purchase_accept_click','APDC_eco_purchase_equipment = yes\nAPDC_eco_sync_ui = yes'))
 sg+=block(P+'purchase_ui','context_type = player_context\nparent_window_name = "APDC_eco_purchase_hook"\nwindow_name = "APDC_eco_purchase"\nvisible = { has_variable = APDC_eco_panel_open has_variable = APDC_eco_purchase_open }\n'+block('effects',''.join(buyclick))+block('triggers',block(P+'purchase_accept_click_enabled',check('purchase_quantity','>',0)+' '+check('cash_m','>=',0)+' OR = { '+check('cash_m','>',var('purchase_cost_m'))+' AND = { '+check('cash_m','=',var('purchase_cost_m'))+' '+check('cash_k','>=',var('purchase_cost_k'))+' } }')))
 # Refresh only after data or an input changes, including side selectors and
 # quantity buttons which do not otherwise call the full display calculation.
 sg=sg.replace('context_type = player_context\n','context_type = player_context\ndirty = APDC_eco_ui_revision\n')
 edits=[]
 for node in walk(parse(sg)):
  if node.key=='effects':
   for callback in node.children:
    edits.append((callback.value_end-1,callback.value_end-1,'\nadd_to_variable = { APDC_eco_ui_revision = 1 }\n'))
 sg=patches(sg,edits)
 write('common/scripted_guis/APDC_economy_panel_ui.txt',block('scripted_gui',sg))
 # Derived UI values have no treasury, construction or production side effects.
 ui='APDC_eco_ensure_equipment = yes\nAPDC_eco_render_trade = yes\n'
 ui+=cond('NOT = { check_variable = { APDC_eco_law_levels^num = 5 } }','clear_array = APDC_eco_law_levels\n'+''.join('add_to_array = { array = APDC_eco_law_levels value = '+str(i)+' }\n' for i in range(1,6)))
 for k in ['stock']+['eqp_'+str(i) for i in range(7)]:
  size=str(max((e['index'] for e in items),default=0)+1)
  ui+=cond('NOT = { check_variable = { APDC_eco_ui_'+k+'^num = '+size+' } }','resize_array = { array = APDC_eco_ui_'+k+' size = '+size+' value = 0 }\n')
 row='set_variable = { APDC_eco_ui_stock^APDC_eco_ui_equipment_index = APDC_eco_stocks^APDC_eco_ui_equipment_index }\n'
 row+='set_variable = { global.APDC_eco_equipment_lookup_id = APDC_eco_ui_equipment_index }\n'
 row+=setv('ui_equipment_cost','global.APDC_eco_equipment_costs^global.APDC_eco_equipment_lookup_id')
 for part in range(7):
  fill=calc('ui_fill','APDC_eco_production_progress^APDC_eco_ui_equipment_index',('divide',var('ui_equipment_cost')),('multiply',259),('subtract',part*37),('clamp','{ min = 0 max = 37 }'),('add',1),('round','yes'))
  row+=cond(check('ui_equipment_cost','>',0),fill)
  row+=f'set_variable = {{ APDC_eco_ui_eqp_{part}^APDC_eco_ui_equipment_index = APDC_eco_ui_fill }}\n'
 ui+='for_each_loop = { array = APDC_eco_equipment_rows\nset_temp_variable = { APDC_eco_ui_equipment_index = v }\n'+row+'}\n'
 for k in ['food','education','medical']:
  ui+=setv(k+'_change',mod(k+'_weekly'))
  if k=='food':ui+=add(k+'_change',var('food_penalty'))
  for tier in range(1,6):
   name=k+'_tier_'+str(tier)+'_frame';ui+=setv(name,1)
   ui+=cond(check(k,'>=',tier),setv(name,2))+cond(check(k,'>=',tier+1),setv(name,3))
  for segment in range(4):
   for part in range(2):
    name=f'{k}_bar_{segment}_{part}';ui+=setv(name,1)
    ui+=cond(check(k,'>=',segment+2),setv(name,80))
    fill=calc(name,var(k),('subtract',segment+1),('multiply',78),('subtract',part*39),('clamp','{ min = 0 max = 39 }'),('add',1),('round','yes'))
    fill+=cond(check(k+'_change','=',0),add(name,40))+cond(check(k+'_change','<',0),add(name,80))
    ui+=cond(check(k,'>=',segment+1)+' '+check(k,'<',segment+2),fill)
 for kind,cost in [('civ',10800),('mil',7200)]:
  for part in range(9):
   name=kind+'_build_'+str(part)+'_frame';ui+=calc(name,var(kind+'_progress'),('divide',cost),('multiply',333),('subtract',37*part),('clamp','{ min = 0 max = 37 }'),('add',1),('round','yes'))
   ui+=cond(check(kind+'_velocity','=',0),add(name,38))+cond(check(kind+'_velocity','<',0),add(name,76))
  ui+=setv(kind+'_days',0)+cond(check(kind+'_velocity','>',0),calc(kind+'_days',cost,('subtract',var(kind+'_progress')),('divide',var(kind+'_velocity')),('round','yes')))
 ui+=setv('trade_frame',2)+cond(check('imports_m','>',0),setv('trade_frame',1))+cond(check('exports_m','>',0),setv('trade_frame',3))
 ui+=setv('trade_toggle_frame',1)+cond('has_variable = APDC_eco_trade_open',setv('trade_toggle_frame',2))
 ui+=calc('trade_net_m',var('imports_m'),('subtract',var('exports_m')))
 ui+=presentation_ui
 ui+='APDC_eco_refresh_number_ui = yes\n'
 ui+='add_to_variable = { APDC_eco_ui_revision = 1 }\n'
 write('common/scripted_effects/APDC_economy_ui.txt',effect('sync_ui',ui)+effect('refresh_number_ui',numbers.effects())+effect('refresh_purchase_number_ui',purchase_number.effect))
 # Every existing economic-system icon enters through this one display API.
 p=ROOT/'common/scripted_guis/APDC_economic_system_scripted_gui.txt';s=p.read_text('utf-8-sig')
 s=s.replace('set_variable = { APDC_eco_panel_open = 1 }','set_variable = { APDC_eco_panel_open = 1 } APDC_eco_sync_ui = yes APDC_eco_calculate_budget = yes') if 'APDC_eco_sync_ui' not in s else s
 # Opening the panel is a fresh read of research activity and country formulas.
 s=s.replace('APDC_eco_sync_ui = yes APDC_eco_calculate_budget = yes','clr_country_flag = APDC_eco_research_counted_today APDC_eco_refresh_current_supply = yes APDC_eco_sync_ui = yes APDC_eco_calculate_budget = yes') if 'clr_country_flag = APDC_eco_research_counted_today' not in s else s
 s=s.replace('set_variable = { APDC_eco_panel_open = 1 }','clear_variable = APDC_eco_selected_group clear_variable = APDC_eco_purchase_open clear_variable = APDC_eco_trade_open set_variable = { APDC_eco_panel_open = 1 }') if 'clear_variable = APDC_eco_selected_group' not in s else s
 # Source amounts must be cached after the fresh budget they describe.
 s=s.replace('APDC_eco_sync_ui = yes APDC_eco_calculate_budget = yes','APDC_eco_calculate_budget = yes APDC_eco_sync_ui = yes')
 write(str(p.relative_to(ROOT)),s)
 loc['APDC_ECO_DISTRIBUTION_VALUE']='分配率\\n[?APDC_eco_distribution|%1]'
 for k,label in [('SUPPLY','供给'),('DEMAND','需求')]:
  loc['APDC_ECO_'+k+'_HEADING']=label
 loc={k:v.replace('|3','|2').replace('₽','£APDC_ruble_texticon£') for k,v in loc.items()}
 for language in ['simp_chinese','english']:
  write(f'localisation/{language}/APDC_economy_panel_l_{language}.yml','l_'+language+':\n'+''.join(f' {k}:0 "{v}"\n' for k,v in loc.items()),True)
 print('Generated economy panel, political-style side selector, private market and procurement popup')

if __name__=='__main__':build()
