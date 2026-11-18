from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "web_templates"))
templates.env.globals["club_name"] = "Bits and Bots Code Club"
