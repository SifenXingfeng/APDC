"""Unified entry point for APDC development generators; never run by the game."""
from pathlib import Path
import argparse
import os
import runpy
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGETS = {
    'parliament': ('parliament/build.py', 'Rebuild parliament scripts and artwork'),
    'parliament-check': ('parliament/verify.py', 'Check parliament scripts and numerical rules'),
    'parliament-ui-check': ('parliament/verify_ui_corrections.py', 'Check parliament UI bindings'),
    'cold-war': ('cold_war/build.py', 'Rebuild Cold War scripts; --map also rebuilds geography'),
    'economy': ('economy/build_all.py', 'Rebuild economy; check original-document inputs first'),
    'economy-backend': ('economy/build_backend.py', 'Rebuild the economy backend'),
    'economy-equipment': ('economy/build_equipment.py', 'Rebuild the private-equipment catalogue'),
    'economy-ui': ('economy/build_ui.py', 'Rebuild the economy interface'),
    'economy-market': ('economy/build_market.py', 'Rebuild the consumer-goods market'),
    'economy-law-display': ('economy/build_law_stat_display.py', 'Rebuild law modifier presentation'),
    'loading-images': ('loading_screens/import_images.py', 'Import the selected loading-screen artwork'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='list available generators without running them')
    parser.add_argument('target', nargs='?', choices=TARGETS)
    parser.add_argument('arguments', nargs=argparse.REMAINDER, help='arguments forwarded to the selected generator')
    args = parser.parse_args(argv)
    if args.list or args.target is None:
        for name, (entry, description) in TARGETS.items():
            print(f'{name:24} {description}\n{"":24} tools/{entry}')
        return 0
    relative, description = TARGETS[args.target]
    if any(value in ('-h', '--help') for value in args.arguments):
        print(f'{args.target}: {description}\nImplementation: tools/{relative}\nSee tools/README.md and the subsystem maintenance notes.')
        return 0
    entry = ROOT / 'tools' / relative
    if not entry.is_file():
        parser.error(f'generator is missing: {entry}')
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    os.chdir(ROOT)
    sys.path.insert(0, str(entry.parent))
    sys.argv = [str(entry), *arguments]
    runpy.run_path(str(entry), run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
