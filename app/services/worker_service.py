from typing import List
from app.models.worker_model import Worker


class WorkerService:
    def __init__(self) -> None:
        self._workers: List[Worker] = []
        self._next_id: int = 1

        # örnekseed
        self.add_worker("Ali Yılmaz", "usta", site_id=1, ppe_status="full")
        self.add_worker("Ahmet Kaya", "işçi", site_id=1, ppe_status="partial")

    def list_workers(self) -> List[Worker]:
        return self._workers

    def add_worker(
        self,
        name: str,
        role: str,
        site_id: int,
        ppe_status: str,
    ) -> Worker:
        worker = Worker(
            id=self._next_id,
            name=name,
            role=role,
            site_id=site_id,
            ppe_status=ppe_status,
        )
        self._workers.append(worker)
        self._next_id += 1
        return worker
