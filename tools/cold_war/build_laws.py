"""Registered law definitions. Presets are confined to Germany and its test targets."""
import json
from common import ROOT, write, block, setv

def build():
    laws=json.loads((ROOT/'tools/cold_war/laws.json').read_text('utf-8'))
    definitions=[];initial=''
    for law in laws:
        body=''.join(setv('apdc_cw_'+k,v) for k,v in {
            'id':law['id'],'target':law['target'],'axis':law['axis'],
            'beneficiary':law['beneficiary'],'rate':law['rate'],
            'execute_cost':law['cost'],
            'self':int(law['owner']==law['target']),'locked':0}.items())
        body+='apdc_cw_register_law = yes\n'+setv('apdc_cw_law_record_'+str(law['id']),'apdc_cw_law_index')+'apdc_cw_notify_controls = yes\n'
        definitions.append(block('apdc_cw_unlock_law_'+str(law['id']),body))
        if law.get('initially_unlocked',False):initial+=block(law['owner'],'apdc_cw_unlock_law_'+str(law['id'])+' = yes')
    definitions.append(block('apdc_cw_register_test_laws',initial))
    write('common/scripted_effects/APDC_cold_war_laws.txt',''.join(definitions))

if __name__=='__main__':build()
