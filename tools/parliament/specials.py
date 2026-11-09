"""Country-extensible special bill catalogue and lifecycle dispatchers."""
from common import *


def generate(loc):
    bills=load_json('special_bills.json')['bills']
    assert len({b['id'] for b in bills})==len(bills)
    refresh='';submit='';passed='';failed=''
    for b in bills:
        ident=int(b['id']);assert ident>0
        name=P+'special_'+str(ident)+'_name';desc=P+'special_'+str(ident)+'_desc'
        loc[name]=b['name'];loc[desc]=b.get('description','')
        countries=b.get('countries',[])
        scope='OR = { '+' '.join('original_tag = '+c for c in countries)+' } ' if countries else ''
        visible=scope+b.get('visible_condition','always = yes')
        register=P+'register_special_bill = { ID = '+str(ident)+' NAME = '+name+' DESC = '+desc+' COST = '+str(b.get('cost',0))+' }\n'
        enabled=P+'set_special_bill_availability = { ID = '+str(ident)+' AVAILABLE = 1 }\n'
        disabled=P+'set_special_bill_availability = { ID = '+str(ident)+' AVAILABLE = 0 }\n'
        refresh+=iff(visible,register+iff(b.get('available_condition','always = yes'),enabled,disabled),P+'remove_special_bill = { ID = '+str(ident)+' }\n')
        submit+=iff(ck('bill_target','=',ident),b.get('on_submit',''))
        passed+=iff(ck('last_passed_special_id','=',ident),b.get('on_pass',''))
        failed+=iff(ck('last_failed_special_id','=',ident),b.get('on_fail',''))
    write('common/scripted_effects/apdc_parliament_special_catalogue.txt',effect('refresh_special_catalogue',refresh)+effect('special_submitted_dispatch',submit)+effect('special_passed_dispatch',passed)+effect('special_failed_dispatch',failed))
