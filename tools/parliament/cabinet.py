"""Candidate records and office callbacks are native, author-owned game files.

The parliament builder intentionally preserves them. Add independent records
under common/scripted_effects/apdc_candidates_*.txt; see tools/native_content.md.
"""
from common import ROOT

def generate(loc):
    if not (ROOT/'common/scripted_effects/apdc_parliament_cabinet.txt').is_file():
        raise FileNotFoundError('Native candidate framework is missing')


def native_candidate_ids():
    import re
    return {int(ident) for path in (ROOT/'common/scripted_effects').glob('*.txt')
            for ident in re.findall(r'^apdc_candidate_(\d+)_setup\s*=',path.read_text('utf-8-sig'),re.M)}
