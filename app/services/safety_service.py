from typing import List
from app.models.inspection_model import SafetyInspection
from app.models.site_model import Site


class SafetyService:
    def __init__(self) -> None:
        self._inspections: List[SafetyInspection] = []
        self._next_id: int = 1

    def list_inspections(self) -> List[SafetyInspection]:
        return self._inspections

    def create_inspection(
        self,
        site: Site,
        inspector: str,
        risk_level: str,
        notes: str,
        file_name: str,
        detected_ppe: List[str],
    ) -> SafetyInspection:
        inspection = SafetyInspection(
            id=self._next_id,
            site_id=site.id,
            inspector=inspector,
            risk_level=risk_level,
            notes=notes or None,
            file_name=file_name,
            detected_ppe=detected_ppe or [],
        )
        self._inspections.append(inspection)
        self._next_id += 1
        return inspection

    def summarize_risk(self) -> dict:
        total = len(self._inspections)
        low = len([i for i in self._inspections if i.risk_level == "low"])
        med = len([i for i in self._inspections if i.risk_level == "medium"])
        high = len([i for i in self._inspections if i.risk_level == "high"])
        return {
            "total": total,
            "low": low,
            "medium": med,
            "high": high,
        }
    def risk_by_site(self, sites: List[Site]) -> List[dict]:
        """
        Her şantiye için ortalama risk puanı ve etiket üretir.
        low=1, medium=2, high=3 ağırlıklarıyla hesaplar.
        """
        weights = {"low": 1, "medium": 2, "high": 3}
        result = []

        for site in sites:
            site_ins = [i for i in self._inspections if i.site_id == site.id]
            if not site_ins:
                result.append(
                    {
                        "site_id": site.id,
                        "site_name": site.name,
                        "total": 0,
                        "low": 0,
                        "medium": 0,
                        "high": 0,
                        "score": 0.0,
                        "label": "Denetim yok",
                    }
                )
                continue

            total = len(site_ins)
            low = len([i for i in site_ins if i.risk_level == "low"])
            med = len([i for i in site_ins if i.risk_level == "medium"])
            high = len([i for i in site_ins if i.risk_level == "high"])

            total_score = sum(weights.get(i.risk_level, 0) for i in site_ins)
            avg = total_score / float(total)

            if avg < 1.5:
                label = "Düşük risk"
            elif avg < 2.5:
                label = "Orta risk"
            else:
                label = "Yüksek risk"

            result.append(
                {
                    "site_id": site.id,
                    "site_name": site.name,
                    "total": total,
                    "low": low,
                    "medium": med,
                    "high": high,
                    "score": round(avg, 2),
                    "label": label,
                }
            )

        return result