from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from dependencies import get_classifier_service
from services.classifier_service import ClassifierService

router = APIRouter()


class IntentRequest(BaseModel):
    text: str
    context: str | None = None


class FormationRequest(BaseModel):
    description: str


class YieldRequest(BaseModel):
    formation: str
    depth_m: float
    gps_lat: float | None = None
    gps_lng: float | None = None


class DuplicateRequest(BaseModel):
    first_name: str
    last_name: str
    phone: str | None = None
    dob: str | None = None
    existing_members: list[dict[str, Any]] = Field(default_factory=list)


class AnomalyRequest(BaseModel):
    agent_id: str
    action_sequence: list[str]


class LabelRequest(BaseModel):
    label: str
    labeled_by: str


@router.post("/intent")
async def classify_intent(req: IntentRequest, svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.classify_intent(req.text, req.context)


@router.post("/formation")
async def classify_formation(req: FormationRequest, svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.classify_formation(req.description)


@router.post("/yield")
async def predict_yield(req: YieldRequest, svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.predict_yield(req.formation, req.depth_m, gps_lat=req.gps_lat, gps_lng=req.gps_lng)


@router.post("/duplicates/member")
async def check_duplicate_member(req: DuplicateRequest, svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.check_duplicate(req.first_name, req.last_name, req.phone, req.dob, req.existing_members)


@router.post("/duplicate")
async def check_duplicate(req: DuplicateRequest, svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.check_duplicate(req.first_name, req.last_name, req.phone, req.dob, req.existing_members)


@router.post("/anomaly")
async def detect_anomaly(req: AnomalyRequest, svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.detect_anomaly(req.agent_id, req.action_sequence)


@router.post("/reload")
async def reload_models(svc: ClassifierService = Depends(get_classifier_service)) -> dict:
    return svc.reload_models()


@router.patch("/training-log/{log_id}/label")
async def label_training_record(
    log_id: str,
    req: LabelRequest,
    svc: ClassifierService = Depends(get_classifier_service),
) -> dict:
    await svc.label_training_record(log_id, req.label, req.labeled_by)
    return {"log_id": log_id, "label": req.label}


@router.get("/training-log/{classifier}/unlabeled")
async def get_unlabeled(
    classifier: str,
    limit: int = 50,
    svc: ClassifierService = Depends(get_classifier_service),
) -> dict:
    return {"records": await svc.get_unlabeled(classifier, limit)}
