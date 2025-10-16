from pathlib import Path
from fastapi.templating import Jinja2Templates

TEMPLATES = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)



# Base directory of the project
