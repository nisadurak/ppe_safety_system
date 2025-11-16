from pydantic import BaseModel
from typing import Optional

class Site(BaseModel):
    id: int
    name: str
    location: str
    status: str  # active / paused / completed
    supervisor: Optional[str] = None
