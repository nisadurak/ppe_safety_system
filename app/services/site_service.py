from typing import List, Optional
from app.models.site_model import Site


class SiteService:
    def __init__(self) -> None:
        self._sites: List[Site] = []
        self._next_id: int = 1

        # örnekseed
        self.create_site(
            name="Merkez Şantiye",
            location="İstanbul / Kağıthane",
            status="active",
            supervisor="Murat Demir",
        )

    def list_sites(self) -> List[Site]:
        return self._sites

    def get_site(self, site_id: int) -> Optional[Site]:
        for s in self._sites:
            if s.id == site_id:
                return s
        return None

    def create_site(
        self,
        name: str,
        location: str,
        status: str,
        supervisor: Optional[str],
    ) -> Site:
        site = Site(
            id=self._next_id,
            name=name,
            location=location,
            status=status,
            supervisor=supervisor,
        )
        self._sites.append(site)
        self._next_id += 1
        return site
