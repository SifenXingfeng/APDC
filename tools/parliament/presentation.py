"""Colored source-complete tooltips and placeholder bill negotiations."""
from common import *
from ui import defined

PARTY_FUNCTIONS=['APDCCabinetPartyCommunismName','APDCCabinetPartySocialismName','APDCCabinetPartySocialDemocracyName','APDCCabinetPartyLiberalismName','APDCCabinetPartyConservatismName','APDCCabinetPartyAuthoritarianismName','APDCCabinetPartyDictatorshipName','APDCCabinetPartyFascismName','APDCCabinetPartyFundamentalismName']
BENEFITS=['建设速度','工厂产出','每月人口','生活消费品人口系数','稳定度','每日政治点数获取','议案审议速度','战争支持度','适役人口系数']


def generate(loc):
    sources=load_json('attitude_sources.json')['sources']
    defs=''
    for source in sources:loc[P+'source_'+source['key']]=source['name']
    for i,p in enumerate(PARTIES):
        for name,variable in [('Attitude','attitude_'+p),('Benefit','effective_'+p)]:
            defs+=defined('ApdcParl'+name+'Color'+str(i),[(ck(variable,'>',0),P+'green'),(ck(variable,'<',0),P+'red')],P+'yellow')
        loc[P+'contribution_'+p]='\n§W'+NAMES[i]+'支持率贡献：[ApdcParlContributionColor'+str(i)+'][?'+P+'contribution_'+p+'|+1]%§!'
        defs+=defined('ApdcParlContribution'+str(i),[(ck('contribution_'+p,'!=',0),P+'contribution_'+p)],P+'empty')
        defs+=defined('ApdcParlContributionColor'+str(i),[(ck('contribution_'+p,'>',0),P+'green')],P+'red')
        loc[P+'coalition_source_'+p]='\n§W执政联盟：§G+100%§!'
        loc[P+'ruling_source_'+p]='\n§W执政党固定支持：§G100%§!'
        defs+=defined('ApdcParlCoalitionSource'+str(i),[('has_government = '+p,P+'ruling_source_'+p),('has_country_flag = APDC_governing_coalition_'+p,P+'coalition_source_'+p)],P+'empty')
        fragments=''
        for source in sources:
            sid=source['id'];fn='ApdcParlSource'+str(i)+'_'+str(sid);variable='source_tip_'+p+'_'+str(sid)
            fragments+='['+fn+']'
            loc[P+'source_row_'+p+'_'+str(sid)]='\n§W$'+P+'source_'+source['key']+'$：['+fn+'Color][?'+P+variable+'|+1]%§!'
            defs+=defined(fn,[(ck(variable,'!=',0),P+'source_row_'+p+'_'+str(sid))],P+'empty')
            defs+=defined(fn+'Color',[(ck(variable,'>',0),P+'green')],P+'red')
        loc[P+'party_tip_'+p]='§Y['+PARTY_FUNCTIONS[i]+']§!\n§W议会席位：§Y[?'+P+'seats_'+p+'|0]§!\n§W对执政党支持率：[ApdcParlAttitudeColor'+str(i)+'][?'+P+'attitude_'+p+'|1]%§!\n§W------支持率获取------\n基础支持率：§Y[?'+P+'base_attitude_'+p+'|1]%§![ApdcParlCoalitionSource'+str(i)+']'+fragments+'\n§W------提供加成------\n'+BENEFITS[i]+'：[ApdcParlBenefitColor'+str(i)+'][?'+P+'effective_'+p+'|%1]§!'
    write('common/scripted_localisation/apdc_parliament_sources.txt',defs)
    # No permanent popularity or seat changes: every offer affects only the
    # existing bill attitude and is removed when that agenda ends.
    loc[P+'negotiation_title']='议案谈判'
    loc[P+'negotiation_desc']='就当前议案争取该党派支持。达成的支持安排持续至本项议程结束。'
    loc[P+'bribe']='支付100.00K£APDC_ruble_texticon£，争取支持（+20%）'
    loc[P+'concession']='作出政治让步，花费50政治点（+15%）'
    loc[P+'withdraw']='结束谈判'
    apply20='';apply15=''
    for i,p in enumerate(PARTIES,1):
        apply20+=iff(ck('negotiating_party','=',i),P+'change_'+p+'_bill_attitude = { VALUE = 20 }\n')
        apply15+=iff(ck('negotiating_party','=',i),P+'change_'+p+'_bill_attitude = { VALUE = 15 }\n')
    valid=ck('agenda','>',0)+' OR = { '+' '.join('AND = { '+ck('negotiating_party','=',i)+' '+ck('seats_'+p,'>',0)+' }' for i,p in enumerate(PARTIES,1))+' }'
    # Bank K is normalized in [0,1000); compare and deduct 100K accurately.
    money='OR = { check_variable = { APDC_eco_cash_m > 0 } AND = { check_variable = { APDC_eco_cash_m = 0 } check_variable = { APDC_eco_cash_k > 99.99999 } } }'
    payment='subtract_from_variable = { APDC_eco_cash_k = 100 }\nAPDC_eco_normalize_cash = yes\n'+apply20+'APDC_eco_calculate_budget = yes\n'
    event='id = apdc_parliament.1\ntitle = '+P+'negotiation_title\ndesc = '+P+'negotiation_desc\nis_triggered_only = yes\n'
    event+=block('option','name = '+P+'bribe\n'+block('trigger',valid+' '+money)+'ai_chance = { factor = 0 }\n'+iff(valid+' '+money,payment))
    event+=block('option','name = '+P+'concession\n'+block('trigger',valid+' has_political_power > 49')+'ai_chance = { factor = 0 }\n'+iff(valid+' has_political_power > 49','add_political_power = -50\n'+apply15))
    event+=block('option','name = '+P+'withdraw\nai_chance = { factor = 100 }')
    write('events/apdc_parliament.txt','add_namespace = apdc_parliament\n'+block('country_event',event))
