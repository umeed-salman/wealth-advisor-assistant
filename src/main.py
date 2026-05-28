from pathlib import Path
import sys

# Support both `uvicorn src.main:app` and `uvicorn main:app --app-dir src`.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
	sys.path.insert(0, str(SRC_DIR))

from wealth_advisor.api.routes import create_app

app = create_app()
