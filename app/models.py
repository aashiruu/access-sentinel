import hashlib
import json
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Role(str, Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    BILLING = "billing"
    ADMIN = "admin"


class AccessStatus(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    BREAK_GLASS = "break_glass_granted"


class AuditEntry(BaseModel):
    id: int
    timestamp: str
    user_id: str
    role: Role
    patient_id: str
    action: str
    status: AccessStatus
    is_break_glass: bool = False
    break_glass_reason: Optional[str] = None
    reason: Optional[str] = None
    prev_hash: str
    hash: str

    def calculate_hash(self) -> str:
        payload = {
            "id": self.id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "role": self.role.value,
            "patient_id": self.patient_id,
            "action": self.action,
            "status": self.status.value,
            "is_break_glass": self.is_break_glass,
            "break_glass_reason": self.break_glass_reason,
            "reason": self.reason,
            "prev_hash": self.prev_hash,
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


class ClinicalRecord(BaseModel):
    primary_diagnosis: str
    medications: list[str]
    doctor_notes: str


class BillingRecord(BaseModel):
    insurance_provider: str
    account_balance: float
    outstanding_invoices: int


class PatientRecord(BaseModel):
    patient_id: str
    name: str
    date_of_birth: str
    clinical: Optional[ClinicalRecord] = None
    billing: Optional[BillingRecord] = None


MOCK_PATIENTS_DB: dict[str, dict] = {
    "P100": {
        "patient_id": "P100",
        "name": "Jane Doe",
        "date_of_birth": "1988-04-12",
        "clinical": {
            "primary_diagnosis": "Acute Appendicitis",
            "medications": ["Amoxicillin", "Ibuprofen"],
            "doctor_notes": "Patient admitted with severe lower right quadrant abdominal pain.",
        },
        "billing": {
            "insurance_provider": "HealthShield Mutual",
            "account_balance": 1450.00,
            "outstanding_invoices": 1,
        },
    }
}
