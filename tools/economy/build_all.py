"""Build in dependency order and stop immediately if any stage fails."""
from build_backend import build as backend
from build_data import build as data
from build_equipment import build as equipment
from build_ui import build as ui
from audit import main as audit

if __name__=='__main__':
 data()
 backend(runtime_only=True)
 equipment()
 ui()
 audit()
