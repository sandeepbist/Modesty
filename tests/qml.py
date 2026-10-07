"""Load production QML in a temporary shell without touching desktop state."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(source, marker, timeout=20):
    with tempfile.TemporaryDirectory(prefix='modesty-qml-') as directory:
        workspace = Path(directory)
        for name in ('components', 'modules', 'assets', 'theme', 'services', 'scripts'):
            (workspace / name).symlink_to(ROOT / name, target_is_directory=True)
        (workspace / 'shell.qml').write_text(source)
        environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', MODESTY_PREVIEW='1',
                           QSG_RHI_BACKEND='software', QS_NO_RELOAD_POPUP='1',
                           XDG_STATE_HOME=str(workspace / 'state'),
                           XDG_CACHE_HOME=str(workspace / 'cache'))
        result = subprocess.run(['qs', '--no-color', '-p', str(workspace)],
                                env=environment, capture_output=True, text=True, timeout=timeout)
        output = result.stdout + result.stderr
        if result.returncode or marker not in output or 'ReferenceError' in output or 'TypeError' in output:
            raise AssertionError(output)
        print(marker)
