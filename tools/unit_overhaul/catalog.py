"""Explicit names and routing, keyed by position in the 2026-09-15 design document."""
UNIT_IDS = '''militia infantry motorized wheeled_mechanized tracked_mechanized national_gendarmerie heavy_infantry mountaineers air_assault paratrooper airborne_mechanized marine amphibious_mechanized rangers nyto lyuba ump_sisters mbt light_tank atgm_vehicle spaag airborne_light_tank tank_support amphibious_tank attack_helicopter basic_robot doll_escort doll_small doll_large motorized_doll_escort motorized_doll_small motorized_doll_large wheeled_doll_escort wheeled_doll_small wheeled_doll_large tracked_doll_escort tracked_doll_small tracked_doll_large air_assault_doll_escort air_assault_doll_small air_assault_doll_large multipod goliath towed_artillery truck_artillery sp_artillery mlrs tactical_missile multipod_artillery combined_service transport_helicopter_support field_workshop frogmen hovercraft_support elite_doll_infiltration cbrn infantry_recon robot_recon motorized_recon mechanized_recon armor_recon uav_recon military_police engineer armored_engineer frontline_command aa02_support doomsday_dog_support sp_artillery_support towed_artillery_support mlrs_support truck_artillery_support spaag_support atgm_support reg_robot_artillery reg_mortar reg_spaag reg_atgm reg_sp_artillery reg_towed_artillery reg_infantry_aa reg_heavy_weapons'''.split()
assert len(UNIT_IDS) == 82
UNIT_IDS = ['apdc_' + x for x in UNIT_IDS]

# Model entities refer to independently verified desktop packs, not original game meshes.
R6 = 'APDC_r6_'
MODELS = {
    'infantry': R6+'infantry_entity', 'doll':R6+'tactical_doll_entity',
    'ump45':R6+'ump45_entity', 'ump9':R6+'ump9_entity', 'lyuba':R6+'lyuba_entity',
    'towed':R6+'towed_artillery_entity', 'nyto':'APDC_f1_nyto_final_entity',
    'atgm':'APDC_f1_wheeled_atgm_entity', 'spaag':'APDC_f1_self_propelled_aa_entity',
    'tank_support':'APDC_f1_tank_support_entity', 'spg':'APDC_f1_self_propelled_gun_entity',
    'mortar':'APDC_f1_self_propelled_mortar_entity', 'truck_art':'APDC_f1_truck_artillery_entity',
    'mlrs':'APDC_f1_truck_mlrs_entity', 'missile':'APDC_f1_truck_missile_entity',
    'multipod_art':'APDC_f1_multipod_artillery_entity', 'attack_helo':'APDC_f1_armed_helicopter_entity',
}
MODELS.update({
 'mbt':'APDC_v5_mbt_entity','truck':'APDC_v5_truck_entity','wheeled':'APDC_v5_wheeled_entity',
 'tracked':'APDC_v5_tracked_entity','amphib_mech':'APDC_v5_amphibious_entity',
 'basic_robot':'APDC_b2_automaton_entity','goliath':'APDC_b2_goliath_entity','multipod':'APDC_b2_multipod_entity',
 'doomsday_dog':'APDC_b2_doomdog_entity','aa02':'APDC_b2_aa02_entity','light_tank':'APDC_b2_light_tank_entity',
 'amphib_tank':'APDC_b2_amphibious_tank_entity','helo':'APDC_b2_helicopter_entity','engineer':'APDC_b2_armored_engineer_entity',
})
MODEL_BY_INDEX = {
 3:('truck','infantry'),4:'wheeled',5:'tracked',9:('helo','infantry'),11:'tracked',13:'amphib_mech',
 15:'nyto',16:('truck','lyuba'),17:('ump45','ump9'),18:'mbt',19:'light_tank',20:'atgm',21:'spaag',
 22:'light_tank',23:'tank_support',24:'amphib_tank',25:'attack_helo',26:'basic_robot',
 42:'multipod',43:'goliath',44:('towed','infantry'),45:'truck_art',46:'spg',47:'mlrs',48:'missile',49:'multipod_art',
 50:('truck','infantry'),51:'helo',52:'engineer',54:('amphib_mech','infantry'),55:'doll',58:'basic_robot',
 59:('truck','infantry'),60:'wheeled',61:'mbt',62:'infantry',65:'engineer',66:('truck','infantry'),
 67:'aa02',68:'doomsday_dog',69:'spg',70:('towed','infantry'),71:'mlrs',72:'truck_art',73:'spaag',
 74:'atgm',75:'multipod_art',76:'mortar',77:'spaag',78:'atgm',79:'spg',80:('towed','infantry')
}
for i in range(27,30):MODEL_BY_INDEX[i]=('doll','infantry') if i==27 else 'doll'
for start,vehicle in ((30,'truck'),(33,'wheeled'),(36,'tracked'),(39,'helo')):
    for i in range(start,start+3):MODEL_BY_INDEX[i]=(vehicle,'doll')

# English and Chinese design labels resolve to the same archetype. Three established
# basic archetypes remain shared with the project's logistics and starting armies.
EQUIPMENT_ALIASES = {
    'infantry_equipment':'infantry_equipment', '步兵装备':'infantry_equipment',
    'support_equipment':'support_equipment', '支援装备':'support_equipment',
    'motorized_equipment':'motorized_equipment', '卡车':'motorized_equipment',
    '轮式机械化装备':'wheeled_mech', '履带式机械化装备':'tracked_mech',
    '运输直升机':'transport_helo', '空降装甲战车':'airborne_ifv', '涅托装备':'nyto',
    'modern_tank_chassis':'mbt', '现代坦克':'mbt', '主战坦克':'mbt',
    'light_tank_chassis':'light_tank', '轻型坦克':'light_tank',
    '反坦克导弹发射车':'atgm', '野战自行防空车':'spaag',
    '空降轻型坦克':'airborne_tank', '坦克支援车':'tank_support',
    'amphibious_tank_chassis':'amphib_tank', '两栖坦克':'amphib_tank',
    '武装直升机':'attack_helo', '基础自动化机械':'basic_robot', '战术人形':'doll',
    '多足机械':'multipod', '自动化机械':'goliath', '歌莉娅装置':'goliath',
    'artillery_equipment':'towed_gun', '牵引式火炮':'towed_gun', '卡车炮':'truck_art',
    'modern_tank_artillery_chassis':'spg', '现代自行火炮':'spg', '自行火炮':'spg',
    'motorized_rocket_equipment':'mlrs', '自行火箭炮':'mlrs',
    '短程战术导弹':'missile', '多足机械火炮':'multipod_art',
    'armored_support_vehicle':'engineer_vehicle', '机械工厂':'engineer_vehicle', '装甲支援车':'engineer_vehicle',
    '气垫船':'hovercraft', '巡飞无人机':'uav', '机甲':'aa02', '末日魔犬':'doomsday_dog',
    '摩托化火炮':'truck_art', '自行迫击炮':'mortar', '步兵重武器':'heavy_weapons',
    'amphibious_mechanized_equipment':'amphib_mech', '两栖登陆载具':'amphib_mech',
}
EQUIPMENT_NAMES = {
    'wheeled_mech':'轮式机械化装备', 'tracked_mech':'履带式机械化装备',
    'transport_helo':'运输直升机', 'airborne_ifv':'空降装甲战车', 'nyto':'涅托装备',
    'mbt':'主战坦克', 'light_tank':'轻型坦克', 'atgm':'反坦克导弹发射车', 'spaag':'野战自行防空车',
    'airborne_tank':'空降轻型坦克', 'tank_support':'坦克支援车', 'amphib_tank':'两栖坦克',
    'attack_helo':'武装直升机', 'basic_robot':'基础自动化机械', 'doll':'战术人形',
    'multipod':'多足机械', 'goliath':'歌莉娅装置', 'towed_gun':'牵引式火炮',
    'truck_art':'卡车炮', 'spg':'自行火炮', 'mlrs':'多管火箭炮', 'missile':'短程战术导弹发射系统',
    'multipod_art':'多足机械火炮', 'engineer_vehicle':'装甲工程支援车', 'hovercraft':'气垫船',
    'uav':'巡飞无人机', 'aa02':'AA02类机甲', 'doomsday_dog':'末日魔犬',
    'mortar':'自行迫击炮', 'heavy_weapons':'步兵重武器', 'amphib_mech':'两栖机械化装备',
}

# Provisional FIRST-INTEGRATION equipment baselines, not values present in the DOCX.
# Columns: speed, soft, hard, piercing, armour, hardness, defence, breakthrough,
# IC, fuel, reliability. Kept centralized for later balance review.
BASELINES = {
 'wheeled_mech': (14,7,5,15,18,.45,25,8,10,1.8,.85),
 'tracked_mech': (10,6,9,25,30,.65,30,12,13,2.2,.85),
 'transport_helo': (18,0,0,0,0,.15,10,5,18,2.5,.8),
 'airborne_ifv': (10,6,7,20,18,.5,22,10,12,1.5,.85),
 'nyto': (6,30,20,55,25,.35,45,25,30,0,.95),
 'mbt': (10,40,45,100,90,.95,20,60,28,3.5,.85),
 'light_tank': (12,28,25,60,40,.8,16,40,15,2,.85),
 'atgm': (14,8,50,120,18,.45,12,8,14,1.8,.85),
 'spaag': (10,10,8,25,40,.8,15,15,18,2.5,.85),
 'airborne_tank': (12,24,24,60,28,.7,14,32,16,1.8,.85),
 'tank_support': (10,55,30,70,85,.95,25,50,27,3.5,.85),
 'amphib_tank': (10,30,30,75,35,.75,15,35,20,2.5,.85),
 'attack_helo': (18,30,45,100,8,.35,12,25,28,3.5,.8),
 'basic_robot': (4,6,2,8,8,.25,18,4,4,0,.9),
 'doll': (4,6,3,10,4,.1,18,4,5,0,.95),
 'multipod': (8,22,18,45,30,.75,24,20,13,1.2,.9),
 'goliath': (6,50,35,65,6,.5,2,12,8,0,.85),
 'towed_gun': (4,34,5,12,0,0,15,7,4,0,.85),
 'truck_art': (12,42,6,15,2,.15,12,8,10,1.5,.85),
 'spg': (10,50,8,25,45,.8,16,15,20,2.5,.85),
 'mlrs': (12,55,8,15,2,.15,10,10,15,1.8,.85),
 'missile': (10,75,30,80,2,.15,8,8,35,2,.8),
 'multipod_art': (8,45,12,35,25,.7,20,16,18,1.4,.85),
 'engineer_vehicle': (10,5,3,10,45,.8,25,20,14,1.8,.85),
 'hovercraft': (12,0,0,0,0,.1,3,0,15,2,.8),
 'uav': (12,6,10,50,0,.1,4,2,3,0,.85),
 'aa02': (8,40,40,85,60,.85,30,40,28,2,.85),
 'doomsday_dog': (8,60,50,100,70,.9,35,45,100,3,.85),
 'mortar': (10,25,3,8,15,.5,15,8,9,1.5,.85),
 'heavy_weapons': (4,10,6,35,0,0,12,3,1.5,0,.9),
 'amphib_mech': (10,6,8,20,20,.6,25,10,15,2,.85),
}

# Keep the semantic role of legacy references where a corresponding design exists.
LEGACY_MAP = {
 'infantry':2,'militia':1,'irregular_infantry':1,'penal_battalion':1,'cavalry':2,'camelry':2,'bicycle_battalion':2,
 'motorized':3,'bus':3,'mechanized':5,'armored_car':4,'infantry_fighting_vehicle':5,
 'marine':12,'amphibious_mechanized':13,'mountaineers':8,'paratrooper':10,'ranger_battalion':14,'rangers':14,
 'modern_armor':18,'medium_armor':18,'heavy_armor':18,'super_heavy_armor':18,'light_armor':19,'amphibious_armor':24,
 'transport_helicopter':9,'helicopter_gunship':25,
 'artillery_brigade':44,'mot_artillery_brigade':44,'rocket_artillery_brigade':47,'mot_rocket_artillery_brigade':47,'motorized_rocket_brigade':47,
 'sp_artillery_brigade':46,'modern_sp_artillery_brigade':46,'medium_sp_artillery_brigade':46,'light_sp_artillery_brigade':46,'heavy_sp_artillery_brigade':46,'super_heavy_sp_artillery_brigade':46,
 'sp_anti_air_brigade':21,'anti_air_brigade':21,'mot_anti_air_brigade':21,
 'anti_tank_brigade':20,'mot_anti_tank_brigade':20,
 'logistics_company':50,'field_hospital':50,'maintenance_company':50,'signal_company':66,
 'recon':57,'mot_recon':59,'armored_car_recon':60,'light_tank_recon':61,'rangers_support':57,
 'engineer':64,'armored_engineer':65,'military_police':63,'artillery':70,'rocket_artillery':71,
 'sp_artillery':69,'anti_air':73,'sp_anti_air':73,'anti_tank':74,
 'fire_support':82,'mot_fire_support':82,'field_guns':80,'rocket_battery':80,'anti_air_battery':81,'anti_tank_battery':82,
 'helicopter_logistics_company':51,'helicopter_recon':62,'helicopter_field_hospital':51,
}
LEGACY_MAP = {k:UNIT_IDS[v-1] for k,v in LEGACY_MAP.items()}
