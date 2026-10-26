"""APDC Cold War generators. Runtime output is generated from current project data."""
from pathlib import Path
import sys, json

ROOT = Path(__file__).resolve().parents[2]
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
ART = Path('D:/Desktop/冷战美术素材')
OUT = ROOT / 'docs/cold-war/20261024'
sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
from cw import parse

def write(rel, body):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.rstrip()+'\n', encoding='utf-8-sig' if p.suffix=='.yml' else 'utf-8')

def block(name, body):
    return name+' = {\n'+body+'\n}\n'

def setv(name, value): return f'set_variable = {{ {name} = {value} }}\n'
def add(name, value): return f'add_to_variable = {{ {name} = {value} }}\n'
def iff(test, body, otherwise=''):
    return 'if = { limit = { '+test+' }\n'+body+'\n}\n'+('else = {\n'+otherwise+'\n}\n' if otherwise else '')

def metadata(): return json.loads((OUT/'geometry.json').read_text('utf-8'))

def map_progress_steps(g):
    # Frame zero is unused. Keep one extra state above the largest packed frame.
    return len(g['palette_ids'])*len(g['scales'])+1
