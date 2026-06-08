"""Compat wrapper à la racine : exécute le traducteur depuis `src/`."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.xapi_progsnap2_translator.main import main


if __name__ == "__main__":
    main()
