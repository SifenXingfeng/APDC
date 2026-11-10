"""Action providers are ordinary native scripted effects, not a JSON build."""
from common import ROOT
def build():
    if not (ROOT/'common/scripted_effects/APDC_cold_war_laws.txt').is_file():
        raise FileNotFoundError('Native Cold War action definitions are missing')
if __name__=='__main__':build()
