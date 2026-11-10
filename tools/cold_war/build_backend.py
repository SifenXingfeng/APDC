"""The validated Cold War backend is native and maintained directly."""
from common import ROOT
AXES=('political','economic','military')
def build():
    if not (ROOT/'common/scripted_effects/APDC_cold_war.txt').is_file():
        raise FileNotFoundError('Native Cold War backend is missing')
