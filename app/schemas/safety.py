from pydantic import BaseModel
from typing import Optional, List

class SafetyInspection(BaseModel):
    id: int
    site_id: int
    inspector: str
    notes: Optional[str] = None
    risk_level: str      # low / medium / high
    image_filename: Optional[str] = None
    detected_ppe: Optional[List[str]] = None
