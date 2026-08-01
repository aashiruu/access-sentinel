from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    BILLING = "billing"
    ADMIN = "admin"


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


# Mock database store
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
