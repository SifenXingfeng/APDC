"""Preserve existing public coalition APIs while refreshing their new clients."""
from common import *


def generate():
    rel='common/scripted_effects/APDC_governing_coalition_scripted_effects.txt'
    text=read(rel);edits=[]
    refresh='if = { limit = { has_country_flag = apdc_parl_initialized } APDC_update_cabinet_statistics = yes apdc_parl_refresh = yes apdc_parl_refresh_candidates = yes }\n'
    for node in parse(text):
        if not (node.key.startswith('APDC_add_') or node.key.startswith('APDC_remove_') or node.key=='APDC_clear_governing_coalition'):continue
        if node.key=='APDC_add_current_ruling_party_to_governing_coalition':continue
        body=text[node.value_start+1:node.value_end-1]
        if 'apdc_parl_refresh' in body:continue
        if node.key.startswith('APDC_add_') and node.key.endswith('_to_governing_coalition'):
            party=node.key.removeprefix('APDC_add_').removesuffix('_to_governing_coalition')
            if party not in PARTIES:continue
            body=iff('NOT = { has_country_flag = APDC_governing_coalition_'+party+' }',body+'\n'+refresh)
        else:body+='\n'+refresh
        edits.append((node.start,node.end,block(node.key,body)))
    write(rel,patches(text,edits))
