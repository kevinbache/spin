from pathlib import Path

PACKAGE_ROOT_PATH = Path(__file__).parent.resolve()

PROJECT_ROOT_PATH = (PACKAGE_ROOT_PATH / '..').resolve()
TEMPLATES_PATH = PROJECT_ROOT_PATH / 'templates'

SPIN_RC_FILENAME = '.spinrc'
SPIN_RC_PATH = Path.home() / SPIN_RC_FILENAME
