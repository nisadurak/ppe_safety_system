from typing import List, Dict, Any
import os
import uuid
from collections import Counter

import cv2
from ultralytics import YOLO

from app.core.config import settings


class YoloPPEService:
    """
    Fotoğraf ve video için PPE tespiti yapan servis.
    Hem fine-tuned PPE modeli (best.pt),
    hem de pretrained YOLOv8n ile karşılaştırma yapar.
    Overlay edilmis (bbox çizili) görselleri kaydeder.
    """

    def __init__(self, ft_model_path: str = None, base_model_path: str = "yolov8n.pt") -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if ft_model_path is None:
            ft_model_path = os.path.join(base_dir, "..", "model", "best.pt")

        self.ft_model_path = os.path.abspath(ft_model_path)
        self.base_model_path = base_model_path

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

        # uploads klasörü yoksa oluştur
        self.upload_dir = os.path.join(base_dir, "..", "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

  
    #  YOLO sonucu görsele çiz → uploads içine kaydet
    # ================================================================
    def _save_overlay(self, result, prefix: str) -> str:
        frame = result.plot()     # YOLO'nun çizdiği (H,W,3) NumPy görseli

        filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(self.upload_dir, filename)

        cv2.imwrite(save_path, frame)
        return filename  # HTML'de gösterebilmen için yalnızca isim

    #  TEK MODEL ANALİZ (fotoğraf)
    # ================================================================
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        result = self.ft_model(image_path)[0]
        overlay_name = self._save_overlay(result, "ft")

        detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append({
                "class_id": cls_id,
                "class_name": self.ft_class_names.get(cls_id, str(cls_id)),
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            })

        return {
            "detections": detections,
            "overlay_image": overlay_name,
        }

   
    #  PRETRAINED + FINE-TUNED KARŞILAŞTIRMALI ANALİZ
    # ================================================================
    def analyze_image_compare(self, image_path: str) -> Dict[str, Any]:
        ft_res = self.ft_model(image_path)[0]
        base_res = self.base_model(image_path)[0]

        ft_overlay = self._save_overlay(ft_res, "ft")
        base_overlay = self._save_overlay(base_res, "base")

        def parse(result, class_names):
            dets = []
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                dets.append({
                    "class_id": cls_id,
                    "class_name": class_names.get(cls_id, str(cls_id)),
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })

            c = Counter([d["class_name"] for d in dets])

            return dets, dict(c)

        ft_det, ft_counts = parse(ft_res, self.ft_class_names)
        base_det, base_counts = parse(base_res, self.base_class_names)

        return {
            "fine_tuned": {
                "detections": ft_det,
                "counts": ft_counts,
                "overlay_image": ft_overlay,
            },
            "pretrained": {
                "detections": base_det,
                "counts": base_counts,
                "overlay_image": base_overlay,
            }
        }

  
        #  VIDEO: bbox çizilmiş video çıktısı
    # ================================================================
    def analyze_video(self, video_path: str, frame_stride: int = 10) -> Dict[str, Any]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Video açılamadı: {video_path}")
        
        out_name = f"video_result_{uuid.uuid4().hex}.mp4"
        out_path = os.path.join(self.upload_dir, out_name)
        
         # FPS güven
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0:
            fps = 25.0  # bazı videolar
            
            
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))    
        if w == 0 or h == 0:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                raise RuntimeError("Videodan frame okunamadı.")
            h, w = frame.shape[:2]
            # başa sar
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        fourcc = cv2.VideoWriter_fourcc(*"mpv4")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))    
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("VideoWriter açılamadı, codec sorunu olabilir.")

        

        frame_idx = 0
        frames_analyzed = 0

        total_person = 0
        total_helmet = 0
        total_vest = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_stride == 0:
                results = self.ft_model(frame)[0]
                frames_analyzed += 1

                # YOLO'nun çizili frame'i
                plotted = results.plot()
                writer.write(plotted)

                # sayaçlar
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    name = self.ft_class_names.get(cls_id, "")
                    if name == "Person":
                        total_person += 1
                    elif name == "helmet":
                        total_helmet += 1
                    elif name == "vest":
                        total_vest += 1
            else:
                
                writer.write(frame)

            frame_idx += 1

        cap.release()
        writer.release()

        # Risk analizi
        helmet_ratio = total_helmet / total_person if total_person > 0 else 0
        vest_ratio = total_vest / total_person if total_person > 0 else 0

        risk = "low"
        if helmet_ratio < 0.5 or vest_ratio < 0.5:
            risk = "high"
        elif helmet_ratio < 0.8 or vest_ratio < 0.8:
            risk = "medium"

        return {
            "video_overlay": out_name,
            "frames_analyzed": frames_analyzed,
            "total_person": total_person,
            "total_with_helmet": total_helmet,
            "total_with_vest": total_vest,
            "helmet_ratio": helmet_ratio,
            "vest_ratio": vest_ratio,
            "risk_level": risk,
        }