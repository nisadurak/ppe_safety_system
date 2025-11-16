from typing import List, Dict, Any
import os
from collections import Counter

import cv2
from ultralytics import YOLO

from app.core.config import settings


class YoloPPEService:
    """
    Fotoğraf ve video için PPE tespiti yapan servis.
    Hem fine-tuned PPE modeli (best.pt),
    hem de pretrained YOLOv8n ile karşılaştırma yapar.
    """

    def __init__(self, ft_model_path: str = None, base_model_path: str = "yolov8n.pt") -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if ft_model_path is None:
            ft_model_path = os.path.join(base_dir, "..", "model", "best.pt")

        self.ft_model_path = os.path.abspath(ft_model_path)
        self.base_model_path = base_model_path  # ultralytics içinden indirilecek

        print("[YoloPPEService] Fine-tuned model yükleniyor:", self.ft_model_path)
        self.ft_model = YOLO(self.ft_model_path)

        print("[YoloPPEService] Pretrained YOLOv8n yükleniyor:", self.base_model_path)
        self.base_model = YOLO(self.base_model_path)

        try:
            self.ft_class_names = self.ft_model.model.names
        except AttributeError:
            self.ft_class_names = self.ft_model.names

        try:
            self.base_class_names = self.base_model.model.names
        except AttributeError:
            self.base_class_names = self.base_model.names

        print("[YoloPPEService] Fine-tuned sınıflar:", self.ft_class_names)
        print("[YoloPPEService] Base sınıflar:", self.base_class_names)

    # ---------- yardımcı: model ile analiz ----------
    def _analyze_with_model(self, model, class_names, image_path: str) -> List[Dict[str, Any]]:
        results = model(image_path)
        detections: List[Dict[str, Any]] = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    {
                        "class_id": cls_id,
                        "class_name": class_names.get(cls_id, str(cls_id)),
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                    }
                )

        return detections

    # ---------- sadece fine-tuned sonucu ----------
    def analyze_image(self, image_path: str) -> List[Dict[str, Any]]:
        return self._analyze_with_model(self.ft_model, self.ft_class_names, image_path)

    # ---------- fine-tuned vs pretrained karşılaştırma ----------
    def analyze_image_compare(self, image_path: str) -> Dict[str, Any]:
        ft_det = self._analyze_with_model(self.ft_model, self.ft_class_names, image_path)
        base_det = self._analyze_with_model(self.base_model, self.base_class_names, image_path)

        def summarize(dets: List[Dict[str, Any]]) -> Dict[str, int]:
            c = Counter()
            for d in dets:
                c[d["class_name"]] += 1
            return dict(c)

        return {
            "fine_tuned": {
                "detections": ft_det,
                "counts": summarize(ft_det),
            },
            "pretrained": {
                "detections": base_det,
                "counts": summarize(base_det),
            },
        }

    # ---------- VIDEO: fine-tuned model ile ----------
    def analyze_video(self, video_path: str, frame_stride: int = 15) -> Dict[str, Any]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("Video açılamadı: %s" % video_path)

        frame_idx = 0
        frames_analyzed = 0

        total_person = 0
        total_helmet = 0
        total_vest = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_stride != 0:
                frame_idx += 1
                continue

            results = self.ft_model.predict(source=frame, verbose=False)
            frames_analyzed += 1

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self.ft_class_names.get(cls_id, str(cls_id))

                    if cls_name.lower() == "person":
                        total_person += 1
                    elif cls_name.lower() == "helmet":
                        total_helmet += 1
                    elif cls_name.lower() == "vest":
                        total_vest += 1

            frame_idx += 1

        cap.release()

        helmet_ratio = float(total_helmet) / float(total_person) if total_person > 0 else 0.0
        vest_ratio = float(total_vest) / float(total_person) if total_person > 0 else 0.0

        risk = "low"
        if helmet_ratio < 0.5 or vest_ratio < 0.5:
            risk = "high"
        elif helmet_ratio < 0.8 or vest_ratio < 0.8:
            risk = "medium"

        return {
            "frames_analyzed": frames_analyzed,
            "total_person": total_person,
            "total_with_helmet": total_helmet,
            "total_with_vest": total_vest,
            "helmet_ratio": helmet_ratio,
            "vest_ratio": vest_ratio,
            "risk_level": risk,
        }
