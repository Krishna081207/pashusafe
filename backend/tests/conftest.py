import sys
from pathlib import Path

# Make `scripts.seed` importable when pytest is run from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
