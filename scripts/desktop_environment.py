"""Keep the desktop session environment; remove the embedding editor's runtime."""
import os

def clean_environment(source=None):
    env = dict(os.environ if source is None else source)
    env.pop('ELECTRON_RUN_AS_NODE', None)
    # T3's bundled libraries/schema directory are private to T3, not desktop apps.
    for key in ('LD_LIBRARY_PATH', 'GSETTINGS_SCHEMA_DIR', 'GI_TYPELIB_PATH'):
        if key in env:
            parts = [p for p in env[key].split(':') if '/t3code' not in p]
            if parts: env[key] = ':'.join(parts)
            else: env.pop(key, None)
    return env
