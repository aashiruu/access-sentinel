from typing import Annotated
from fastapi import FastAPI, Header, HTTPException, Depends, status
from app.models import Role, PatientRecord, ClinicalRecord, BillingRecord, MOCK_PATIENTS_DB

app = FastAPI(
    title="access-sentinel",
    description="Simulated patient-records access system exploring resilience vs. strict access control.",
    version="0.1.0",
)


async def get_current_user(
    x_user_id: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
) -> tuple[str, Role]:
    if not x_user_id or not x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication headers: X-User-Id and X-User-Role",
        )

    try:
        role = Role(x_user_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{x_user_role}'. Valid roles are: {[r.value for r in Role]}",
        )

    return x_user_id, role


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "access-sentinel"}


@app.get("/patients/{patient_id}", response_model=PatientRecord)
async def get_patient_record(
    patient_id: str,
    current_user: Annotated[tuple[str, Role], Depends(get_current_user)],
):
    user_id, role = current_user

    if patient_id not in MOCK_PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Patient record not found")

    raw_patient = MOCK_PATIENTS_DB[patient_id]

    # Admins are prohibited from viewing raw medical/billing patient details
    if role == Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative roles cannot directly inspect patient health/billing data.",
        )

    # Construct response according to role scopes
    filtered_record = {
        "patient_id": raw_patient["patient_id"],
        "name": raw_patient["name"],
        "date_of_birth": raw_patient["date_of_birth"],
        "clinical": None,
        "billing": None,
    }

    if role in [Role.DOCTOR, Role.NURSE]:
        filtered_record["clinical"] = raw_patient["clinical"]

    if role in [Role.DOCTOR, Role.BILLING]:
        filtered_record["billing"] = raw_patient["billing"]

    return filtered_record
