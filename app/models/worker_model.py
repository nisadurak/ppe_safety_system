from pydantic import BaseModel
from typing import Optional


class Worker(BaseModel):
    id: int
    name: str
    role: str                     # usta, mühendis, işçi...
    site_id: Optional[int] = None
    ppe_status: str               # full / partial / none
