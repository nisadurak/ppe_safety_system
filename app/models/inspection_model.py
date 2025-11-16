from pydantic import BaseModel
from typing import Optional, List


class SafetyInspection(BaseModel):
    id: int
    site_id: int
    inspector: str
    risk_level: str                   # low / medium / high
    notes: Optional[str] = None
    file_name: Optional[str] = None  
    detected_ppe: Optional[List[str]] = None
