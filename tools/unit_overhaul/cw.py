"""Small lossless-span Clausewitz parser for deterministic, scoped migrations."""
from dataclasses import dataclass, field
import re

TOKEN = re.compile(r'#[^\r\n]*|"(?:\\.|[^"\\])*"|[{}]|[=<>!?]+|[^\s{}=<>!?#"]+')

@dataclass
class Node:
    key: str
    value: str | None
    children: list = field(default_factory=list)
    start: int = 0
    end: int = 0
    value_start: int = 0
    value_end: int = 0
    op: str = '='

    def get(self, key, default=None):
        return next((n for n in self.children if n.key == key), default)

    def val(self, key, default=None):
        n = self.get(key)
        return n.value.strip('"') if n and n.value is not None else default

def parse(text):
    tokens = [m for m in TOKEN.finditer(text) if not m.group().startswith('#')]
    i = 0
    def sequence(close=False):
        nonlocal i
        result = []
        while i < len(tokens):
            m = tokens[i]
            if m.group() == '}':
                if not close:
                    raise ValueError('Unexpected closing brace at line '+str(text.count('\n',0,m.start())+1))
                i += 1
                return result
            key = m.group(); start = m.start(); i += 1
            if key == '{':
                # Save files contain anonymous records inside arrays, e.g.
                # enabled_units = { { apdc_infantry yes } }.
                kids = sequence(True)
                result.append(Node('__anonymous__', None, kids, start, tokens[i-1].end(), start, tokens[i-1].end(), ''))
                continue
            if i < len(tokens) and tokens[i].group() in ('=', '>', '<', '>=', '<=', '!=', '?='):
                op = tokens[i].group(); i += 1
                v = tokens[i]; i += 1
                if v.group() == '{':
                    kids = sequence(True)
                    result.append(Node(key, None, kids, start, tokens[i-1].end(), v.start(), tokens[i-1].end(), op))
                else:
                    result.append(Node(key, v.group(), [], start, v.end(), v.start(), v.end(), op))
            else:
                result.append(Node(key, key, [], start, m.end(), start, m.end(), ''))
        if close:
            raise ValueError('Unclosed block')
        return result
    return sequence()

def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.children)

def patches(text, edits):
    end = len(text)+1
    for start, stop, replacement in sorted(edits, reverse=True):
        assert 0 <= start <= stop <= end, (start, stop, end)
        text = text[:start] + replacement + text[stop:]
        end = start
    return text

def render_value(v, indent=0):
    if isinstance(v, dict):
        return '{\n' + render(v, indent+1) + '\t'*indent + '}'
    if isinstance(v, (tuple,list)):
        return '{ ' + ' '.join(str(x) for x in v) + ' }'
    if isinstance(v,float):
        return format(v,'.8g')
    return str(v)

def render(data, indent=0):
    pairs = data.items() if isinstance(data,dict) else data
    return ''.join('\t'*indent + str(k) + ' = ' + render_value(v,indent) + '\n' for k,v in pairs)
