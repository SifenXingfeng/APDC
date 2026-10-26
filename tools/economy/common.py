"""APDC economy build helpers. Game files are generated from the supplied design."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
WORK = ROOT / 'docs/economy'
sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
from cw import parse, walk, patches

def write(path, text, bom=False):
    if '/scripted_effects/' in '/'+str(path).replace('\\','/'):
        text = lower_math(text)
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8-sig' if bom else 'utf-8', newline='\n')

def lower_math(text):
    """Use the game's established arithmetic effects, including temp operands.

    Keep the accumulator temporary until commit, so self-referencing formulas
    retain the original value. This also avoids dynamic-token interpretation
    differences in the new script-math reader.
    """
    counter=0
    def lower(expr):
        nonlocal counter
        counter+=1; accumulator='APDC_eco_math_'+str(counter)
        lines=[]
        for item in expr.children:
            if item.key=='clamp':
                fields=' '.join(x.key+' = '+x.value for x in item.children)
                lines.append('clamp_temp_variable = { var = '+accumulator+' '+fields+' }')
                continue
            operand=item.value
            if operand is None:
                operand,sub=lower(item);lines.extend(sub)
            if item.key=='value': lines.append('set_temp_variable = { '+accumulator+' = '+operand+' }')
            elif item.key in ['add','subtract','multiply','divide','mod']:
                op={'add':'add_to','subtract':'subtract_from','multiply':'multiply','divide':'divide','mod':'modulo'}[item.key]
                lines.append(op+'_temp_variable = { '+accumulator+' = '+operand+' }')
            elif item.key in ['min','max']:
                field='max' if item.key=='min' else 'min'
                lines.append('clamp_temp_variable = { var = '+accumulator+' '+field+' = '+operand+' }')
            elif item.key=='round': lines.append('round_temp_variable = '+accumulator)
            else: raise ValueError('Unsupported arithmetic operation '+item.key)
        return accumulator,lines
    edits=[]
    for n in walk(parse(text)):
        if n.key not in ['set_variable','set_temp_variable'] or len(n.children)!=1:continue
        item=n.children[0]
        if item.value is not None or not item.get('value'):continue
        accumulator,lines=lower(item)
        lines.append(n.key+' = { '+item.key+' = '+accumulator+' }')
        edits.append((n.start,n.end,'\n'.join(lines)))
    return patches(text,edits)

def effective_files(folder):
    files = {p.name: p for p in (GAME / folder).glob('*.txt')}
    files.update({p.name: p for p in (ROOT / folder).glob('*.txt')})
    return sorted(files.values())

def block(name, text):
    return name + ' = {\n' + text + '\n}\n'

def setv(name, value):
    # HOI's fixed-point number reader overflows on long binary-float tails,
    # e.g. 0.08600000000000001. Emit a short plain decimal, never an exponent.
    if isinstance(value,float): value=format(value,'.5f').rstrip('0').rstrip('.') or '0'
    return f'set_variable = {{ APDC_eco_{name} = {value} }}\n'

def calc(name, value, *operations):
    expr = 'value = ' + str(value)
    floor = False
    for op, val in operations:
        if op == 'round' and val == 'down':
            floor = True
            continue
        expr += f' {op} = {val}'
    result = setv(name, '{ ' + expr + ' }')
    if floor:
        result += setv('round_original', 'APDC_eco_'+name)
        result += 'round_variable = APDC_eco_'+name+'\n'
        result += 'if = { limit = { check_variable = { APDC_eco_'+name+' > APDC_eco_round_original } } subtract_from_variable = { APDC_eco_'+name+' = 1 } }\n'
    return result

def check(name, op, value):
    if op in ['>=','<=','!=']:
        opposite={'>=':'<','<=':'>','!=':'='}[op]
        return 'NOT = { '+check(name,opposite,value)+' }'
    return f'check_variable = {{ APDC_eco_{name} {op} {value} }}'

def cond(test, effect, otherwise=''):
    s = 'if = { limit = { ' + test + ' }\n' + effect + '\n}\n'
    if otherwise:
        s += 'else = {\n' + otherwise + '\n}\n'
    return s
