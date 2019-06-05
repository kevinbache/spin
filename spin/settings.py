from pathlib import Path

PACKAGE_ROOT_PATH = Path(__file__).parent.resolve()

PROJECT_ROOT_PATH = (PACKAGE_ROOT_PATH / '..').resolve()
TEMPLATES_PATH = PROJECT_ROOT_PATH / 'templates'

