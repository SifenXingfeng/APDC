"""Read-only validation of independent candidates, Cold War actions and rules."""
from pathlib import Path
import argparse,json,re,sys,hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,walk

FAMILIES={
    'candidate':('apdc_candidate_', ['setup','on_appoint_member','on_remove_member','on_appoint_chief','on_remove_chief']),
    'cold_war_action':('apdc_cw_action_', ['setup','on_execute','on_stop','on_daily']),
    'organization_rule':('apdc_cooperation_rule_', ['setup','on_enact','on_repeal','on_member_apply','on_member_remove','on_fail']),
}
PREFIXES=('apdc_parl_','apdc_nc_','apdc_na_','apdc_nr_','apdc_candidate_','apdc_cw_','apdc_cooperation_rule_','apdc_register_','apdc_unregister_','apdc_unlock_','apdc_appoint_','apdc_execute_','apdc_stop_','apdc_remove_','apdc_propose_')

def run(extra=None,report=None):
    sources=[ROOT]+([Path(extra)] if extra else [])
    definitions={};providers={k:{} for k in FAMILIES};checks=[];files=[]
    for source in sources:
        for folder in ['common/scripted_effects','common/scripted_triggers']:
            for p in sorted((source/folder).glob('*.txt')):
                text=p.read_text('utf-8-sig');nodes=parse(text)
                for node in nodes:
                    if node.key.startswith(PREFIXES):
                        assert node.key not in definitions,('Duplicate API',node.key,str(p),str(definitions.get(node.key)))
                        definitions[node.key]=p
                    for kind,(prefix,phases) in FAMILIES.items():
                        match=re.fullmatch(re.escape(prefix)+r'(\d+)_(.+)',node.key)
                        if match:
                            ident=int(match[1]);assert ident>0,('Nonpositive permanent ID',node.key)
                            providers[kind].setdefault(ident,{})[match[2]]=str(p)
                if any(n.key.startswith(PREFIXES) for n in nodes):
                    assert not p.read_bytes().startswith(b'\xef\xbb\xbf'),('BOM in script',str(p));files.append((p,nodes))
    checks.append('native_scripts_parse_and_api_names_are_unique')
    for kind,records in providers.items():
        for ident,parts in records.items():
            assert set(FAMILIES[kind][1])<=parts.keys(),('Missing lifecycle callback',kind,ident,sorted(set(FAMILIES[kind][1])-parts.keys()))
    checks.append('every_provider_has_setup_and_all_lifecycle_callbacks')
    def calls(nodes,in_meta=False):
        for node in nodes:
            if not (in_meta and '[' in node.key):yield node
            yield from calls(node.children,in_meta or node.key=='meta_effect')
    for p,nodes in files:
        for n in calls(nodes):
            if n.key.startswith(PREFIXES) and n.value=='yes':assert n.key in definitions,('Missing API',n.key,str(p))
    checks.append('literal_native_api_calls_resolve')
    for source in sources:
        for p in (source/'common/scripted_guis').glob('*.txt'):
            for n in calls(parse(p.read_text('utf-8-sig'))):
                if n.key.startswith(PREFIXES) and n.value=='yes':assert n.key in definitions,('Missing GUI API',n.key,str(p))
    checks.append('gui_native_api_calls_resolve')
    # Authored custom keys must have synchronized tokens. Characters are
    # engine tokens; portraits and names used as metadata are explicit here.
    tokens=set()
    for source in sources:
        for p in (source/'common/synchronized_dynamic_tokens').glob('*.txt'):
            tokens.update(re.findall(r'^[A-Za-z_][A-Za-z_0-9.\-]*$',p.read_text('utf-8-sig'),re.M))
    metadata_names={'apdc_nc_name','apdc_nc_portrait','apdc_nc_member_text','apdc_nc_chief_text','apdc_nc_character','apdc_na_name','apdc_na_desc','apdc_nr_name'}|{f'apdc_nr_option_{i}_{kind}' for i in range(1,5) for kind in ['name','effect']}
    for p,nodes in files:
        for n in walk(nodes):
            if n.key in metadata_names and n.value and n.value.startswith('token:'):
                key=n.value.removeprefix('token:');assert key in tokens,('Missing synchronized metadata token',key,str(p))
    checks.append('authored_metadata_tokens_are_registered')
    s=(ROOT/'common/scripted_guis/apdc_parliament.txt').read_text('utf-8')
    assert not re.search(r'apdc_parl_candidate_\d+_enabled',s)
    assert 'apdc_nc_ids^apdc_parl_candidate_context' in s
    checks.append('candidate_gui_uses_compact_registry_rows_and_permanent_ids')
    s=(ROOT/'common/scripted_localisation/APDC_cold_war.txt').read_text('utf-8')
    assert 'apdc_na_names^apdc_cw_law_row.GetTokenKey' in s
    s=(ROOT/'common/scripted_localisation/APDC_cold_war_view.txt').read_text('utf-8')
    assert not re.search(r'name\s*=\s*APDCCWLawSource\d+',s)
    assert 'name = APDCNativeCWSourceLines' in s
    checks.append('cold_war_names_descriptions_and_source_lines_are_dynamic')
    s=(ROOT/'common/scripted_localisation/APDC_cooperation_organizations_scripted_localisation.txt').read_text('utf-8')
    assert not re.search(r'localization_key\s*=\s*APDC_COOPERATION_LAW_GROUP_\d+',s)
    checks.append('organization_list_queue_and_ballot_names_are_dynamic')
    s=(ROOT/'common/scripted_effects/APDC_cooperation_legislation_scripted_effects.txt').read_text('utf-8')
    assert 'apdc_nr_enact = yes' in s and 'apdc_nr_repeal = yes' in s
    checks.append('organization_vote_resolver_routes_real_enact_and_repeal_callbacks')
    for source in sources:
        for p in (source/'common/scripted_localisation').glob('*.txt'):
            assert not re.search(r'(?m)^\s*localization_key\s*=\s*\[\s*$',p.read_text('utf-8-sig')),('Truncated dynamic localisation expression',str(p))
    checks.append('dynamic_localisation_expressions_are_complete')
    out={'status':'passed','checks':checks,'provider_counts':{k:len(v) for k,v in providers.items()},'api_definitions':len(definitions),'files_checked':len(files),'scope':'read_only_static_validation; not a game run'}
    if report:
        p=Path(report);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(out,ensure_ascii=False));return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--extra',type=Path,help='additional mod directory to validate with APDC');ap.add_argument('--report',type=Path);args=ap.parse_args();run(args.extra,args.report)
