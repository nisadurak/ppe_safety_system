import os
import shutil
from typing import List

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.services.site_service import SiteService
from app.services.worker_service import WorkerService
from app.services.safety_service import SafetyService
from app.services.yolo_ppe_service import YoloPPEService

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

site_service = SiteService()
worker_service = WorkerService()
safety_service = SafetyService()
yolo_service = YoloPPEService()


# ---------- DASHBOARD ----------
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    sites = site_service.list_sites()
    workers = worker_service.list_workers()
    inspections = safety_service.list_inspections()
    risk_summary = safety_service.summarize_risk()
    site_risks = safety_service.risk_by_site(sites)  # Şantiyelere göre risk analizi

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "sites": sites,
            "workers": workers,
            "inspections": inspections,
            "risk_summary": risk_summary,
            "site_risks": site_risks,
        },
    )


# ---------- SITES ----------
@router.get("/sites", response_class=HTMLResponse)
async def sites_page(request: Request):
    return templates.TemplateResponse(
        "sites.html",
        {"request": request, "sites": site_service.list_sites()},
    )


@router.post("/sites", response_class=HTMLResponse)
async def create_site(
    request: Request,
    name: str = Form(...),
    location: str = Form(...),
    status: str = Form(...),
    supervisor: str = Form(""),
):
    site_service.create_site(
        name=name,
        location=location,
        status=status,
        supervisor=supervisor or None,
    )
    return await sites_page(request)


# ---------- WORKERS ----------
@router.get("/workers", response_class=HTMLResponse)
async def workers_page(request: Request):
    return templates.TemplateResponse(
        "workers.html",
        {
            "request": request,
            "workers": worker_service.list_workers(),
            "sites": site_service.list_sites(),
        },
    )


@router.post("/workers", response_class=HTMLResponse)
async def create_worker(
    request: Request,
    name: str = Form(...),
    role: str = Form(...),
    site_id: int = Form(...),
    ppe_status: str = Form(...),
):
    worker_service.add_worker(
        name=name,
        role=role,
        site_id=site_id,
        ppe_status=ppe_status,
    )
    return await workers_page(request)


# ---------- SAFETY: GET ----------
@router.get("/safety", response_class=HTMLResponse)
async def safety_page(request: Request):
    inspections = safety_service.list_inspections()
    return templates.TemplateResponse(
        "safety.html",
        {
            "request": request,
            "inspections": inspections,
            "sites": site_service.list_sites(),
            "last_image_detections_ft": None,
            "last_image_detections_base": None,
            "last_image_counts_ft": None,
            "last_image_counts_base": None,
            "ft_overlay": None,
            "base_overlay": None,
            "last_video_summary": None,
            "video_overlay": None,
        },
    )


# ---------- SAFETY: FOTOĞRAF ----------
@router.post("/safety/image", response_class=HTMLResponse)
async def safety_image(
    request: Request,
    site_id: int = Form(...),
    inspector: str = Form(...),
    risk_level: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
):
    site = site_service.get_site(site_id)
    image_filename = file.filename
    save_path = os.path.join(settings.UPLOAD_DIR, image_filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ---- KARŞILAŞTIRMA: fine-tuned vs pretrained ----
    compare = yolo_service.analyze_image_compare(save_path)
    ft_detections = compare["fine_tuned"]["detections"]
    base_detections = compare["pretrained"]["detections"]
    ft_counts = compare["fine_tuned"]["counts"]
    base_counts = compare["pretrained"]["counts"]

   
    ft_overlay = compare["fine_tuned"]["overlay_image"]
    base_overlay = compare["pretrained"]["overlay_image"]

    # Denetim kaydı için sadece fine-tuned sınıfları
    detected_ppe_classes = sorted(list(set(d["class_name"] for d in ft_detections)))

    safety_service.create_inspection(
        site=site,
        inspector=inspector,
        risk_level=risk_level,
        notes=notes,
        file_name=image_filename,
        detected_ppe=detected_ppe_classes,
    )

    inspections = safety_service.list_inspections()
    return templates.TemplateResponse(
        "safety.html",
        {
            "request": request,
            "inspections": inspections,
            "sites": site_service.list_sites(),
            "last_image_detections_ft": ft_detections,
            "last_image_detections_base": base_detections,
            "last_image_counts_ft": ft_counts,
            "last_image_counts_base": base_counts,
            "ft_overlay": ft_overlay,
            "base_overlay": base_overlay,
            "last_video_summary": None,
            "video_overlay": None,
        },
    )

# ---------- SAFETY: VIDEO ----------
@router.post("/safety/video", response_class=HTMLResponse)
async def safety_video(
    request: Request,
    site_id: int = Form(...),
    inspector: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
):
    site = site_service.get_site(site_id)
    video_filename = file.filename
    save_path = os.path.join(settings.UPLOAD_DIR, video_filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    summary = yolo_service.analyze_video(save_path, frame_stride=15)
    risk_level = summary["risk_level"]


    video_overlay = summary.get("video_overlay")

    safety_service.create_inspection(
        site=site,
        inspector=inspector,
        risk_level=risk_level,
        notes=notes,
        file_name=video_filename,  # orijinal video adı log’da dursun
        detected_ppe=[],
    )

    inspections = safety_service.list_inspections()
    return templates.TemplateResponse(
        "safety.html",
        {
            "request": request,
            "inspections": inspections,
            "sites": site_service.list_sites(),
            "last_image_detections_ft": None,
            "last_image_detections_base": None,
            "last_image_counts_ft": None,
            "last_image_counts_base": None,
            "last_video_summary": summary,
            "ft_overlay": None,
            "base_overlay": None,
            "video_overlay": summary["video_overlay"],  
        },
    )