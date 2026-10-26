"""Rebuild Cold War scripts. Pass --map only after geography/art changes."""
import sys
import build_backend,build_laws,build_view,build_ui,finish_assets,optimize_loading,world_style,entry_assets,button_feedback

if '--map' in sys.argv:
    import build_map
    build_map.build()
optimize_loading.apply()
world_style.apply_assets()
entry_assets.apply()
button_feedback.apply_assets()
build_backend.build()
build_laws.build()
build_view.build()
finish_assets.build()
build_ui.build()
