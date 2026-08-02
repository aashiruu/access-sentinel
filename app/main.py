import logging
from typing import Annotated
from fastapi import FastAPI, Header, HTTPException, Depends, status, Response
from app.models import Role, PatientRecord, AccessStatus, MOCK_PATIENTS_DB
from app.audit import audit_store, AuditStoreUnavailableException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("access-sentinel")

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
async def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok" if audit_store.is_healthy else "degraded",
        "service": "access-sentinel",
        "audit_store_healthy": audit_store.is_healthy,
        "buffered_degraded_logs": len(audit_store.get_fallback_buffer()),
    }


@app.get("/patients/{patient_id}", response_model=PatientRecord)
async def get_patient_record(
    patient_id: str,
    response: Response,
    current_user: Annotated[tuple[str, Role], Depends(get_current_user)],
    x_break_glass: Annotated[bool | None, Header()] = False,
    x_break_glass_reason: Annotated[str | None, Header()] = None,
):
    user_id, role = current_user

    if patient_id not in MOCK_PATIENTS_DB:
        try:
            audit_store.log_access(
                user_id=user_id,
                role=role,
                patient_id=patient_id,
                action="GET_PATIENT",
                status=AccessStatus.DENIED,
                reason="Patient ID not found",
            )
        except AuditStoreUnavailableException:
            pass
        raise HTTPException(status_code=404, detail="Patient record not found")

    raw_patient = MOCK_PATIENTS_DB[patient_id]

    # Break-glass logic
    if x_break_glass:
        if role in [Role.ADMIN, Role.BILLING]:
            try:
                audit_store.log_access(
                    user_id=user_id,
                    role=role,
                    patient_id=patient_id,
                    action="GET_PATIENT_BREAK_GLASS",
                    status=AccessStatus.DENIED,
                    is_break_glass=True,
                    break_glass_reason=x_break_glass_reason,
                    reason=f"Role '{role.value}' is unauthorized to invoke break-glass clinical overrides.",
                )
            except AuditStoreUnavailableException:
                pass
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Break-glass override permitted only for clinical personnel.",
            )

        if not x_break_glass_reason or len(x_break_glass_reason.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Break-glass access requires a valid justification (X-Break-Glass-Reason header).",
            )

        # Attempt audit logging with degraded fallback handling
        try:
            audit_store.log_access(
                user_id=user_id,
                role=role,
                patient_id=patient_id,
                action="GET_PATIENT_BREAK_GLASS",
                status=AccessStatus.BREAK_GLASS,
                is_break_glass=True,
                break_glass_reason=x_break_glass_reason,
            )
        except AuditStoreUnavailableException:
            logger.warning(
                f"AUDIT STORE OUTAGE - DEGRADED BREAK-GLASS: Buffering log for {user_id}"
            )
            audit_store.log_access(
                user_id=user_id,
                role=role,
                patient_id=patient_id,
                action="GET_PATIENT_BREAK_GLASS",
                status=AccessStatus.BREAK_GLASS,
                is_break_glass=True,
                break_glass_reason=x_break_glass_reason,
                degraded_mode=True,
            )
            response.headers["X-System-Degraded"] = "true"

        return raw_patient

    # Standard RBAC Evaluation
    if role == Role.ADMIN:
        try:
            audit_store.log_access(
                user_id=user_id,
                role=role,
                patient_id=patient_id,
                action="GET_PATIENT",
                status=AccessStatus.DENIED,
                reason="Admin role forbidden from direct PHI read",
            )
        except AuditStoreUnavailableException:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative roles cannot directly inspect patient health/billing data.",
        )

    # Standard Read Audit Attempt
    try:
        audit_store.log_access(
            user_id=user_id,
            role=role,
            patient_id=patient_id,
            action="GET_PATIENT",
            status=AccessStatus.GRANTED,
        )
    except AuditStoreUnavailableException:
        # FAIL-OPEN for clinical personnel (Doctors/Nurses) with degraded buffer
        if role in [Role.DOCTOR, Role.NURSE]:
            logger.warning(
                f"AUDIT STORE OUTAGE - FAIL-OPEN CLINICAL READ: User {user_id}"
            )
            audit_store.log_access(
                user_id=user_id,
                role=role,
                patient_id=patient_id,
                action="GET_PATIENT",
                status=AccessStatus.GRANTED,
                degraded_mode=True,
            )
            response.headers["X-System-Degraded"] = "true"
        else:
            # FAIL-CLOSED for non-clinical roles (e.g. billing) during logging outages
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service degraded: Non-clinical patient record access is unavailable while audit store is offline.",
            )

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


# System Administration & Outage Simulation Endpoints
@app.post("/system/simulate-outage")
async def simulate_outage(
    current_user: Annotated[tuple[str, Role], Depends(get_current_user)],
):
    _, role = current_user
    if role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required.")
    audit_store.is_healthy = False
    return {"status": "outage_simulated", "audit_store_healthy": False}


@app.post("/system/recover")
async def recover_system(
    current_user: Annotated[tuple[str, Role], Depends(get_current_user)],
):
    _, role = current_user
    if role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required.")
    flushed = audit_store.recover_and_flush()
    return {
        "status": "recovered",
        "audit_store_healthy": True,
        "flushed_buffered_logs": flushed,
    }


@app.get("/audit/logs")
async def get_audit_logs(
    current_user: Annotated[tuple[str, Role], Depends(get_current_user)],
):
    user_id, role = current_user
    if role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrative roles can query the system audit log.",
        )
    return {
        "integrity_verified": audit_store.verify_integrity(),
        "total_entries": len(audit_store.get_logs()),
        "buffered_degraded_entries": len(audit_store.get_fallback_buffer()),
        "logs": audit_store.get_logs(),
        "buffered_logs": audit_store.get_fallback_buffer(),
    }


@app.delete("/audit/logs")
async def delete_audit_logs():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Immutable store violation: Deletion or modification of audit logs is permanently prohibited.",
    )
