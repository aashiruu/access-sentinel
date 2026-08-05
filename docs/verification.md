# Real Verification Evidence & Execution Traces

This document records real terminal execution traces generated from testing `access-sentinel`.

---

## 1. RBAC Policy Enforcement

### Doctor Read (Clinical + Billing)
```bash
curl -s -H "X-User-Id: doc_1" -H "X-User-Role: doctor" http://localhost:8000/patients/P100
```
```JSON
{
  "patient_id": "P100",
  "name": "Jane Doe",
  "date_of_birth": "1988-04-12",
  "clinical": {
    "primary_diagnosis": "Acute Appendicitis",
    "medications": ["Amoxicillin", "Ibuprofen"],
    "doctor_notes": "Patient admitted with severe lower right quadrant abdominal pain."
  },
  "billing": {
    "insurance_provider": "HealthShield Mutual",
    "account_balance": 1450.0,
    "outstanding_invoices": 1
  }
}
```
### Nurse Read (Clinical Only)
```bash
curl -s -H "X-User-Id: nurse_1" -H "X-User-Role: nurse" http://localhost:8000/patients/P100
```
```JSON
{
  "patient_id": "P100",
  "name": "Jane Doe",
  "date_of_birth": "1988-04-12",
  "clinical": { ... },
  "billing": null
}
```
### Admin Read Attempt (Forbidden)
```bash
curl -s -i -H "X-User-Id: admin_1" -H "X-User-Role: admin" http://localhost:8000/patients/P100
```
```JSON
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"Forbidden: Administrative roles cannot directly inspect patient health/billing data."}
```


## 2. Immutable Audit Enforcement
```bash
curl -s -i -X DELETE http://localhost:8000/audit/logs
```
```JSON
HTTP/1.1 405 Method Not Allowed

{"detail":"Immutable store violation: Deletion or modification of audit logs is permanently prohibited."}
```

## 3. Break-Glass Emergency Access Logging
```bash
curl -s -H "X-User-Id: nurse_9" \
        -H "X-User-Role: nurse" \
        -H "X-Break-Glass: true" \
        -H "X-Break-Glass-Reason: Patient in ER trauma bay unconscious" \
        http://localhost:8000/patients/P100
```
```JSON
{
  "patient_id": "P100",
  "name": "Jane Doe",
  "clinical": { ... },
  "billing": { ... }
}
```

## 4. Degraded Mode & Outage Verification

### Simulate Outage

```bash
curl -s -X POST -H "X-User-Id: admin_1" -H "X-User-Role: admin" http://localhost:8000/system/simulate-outage
```
```JSON
{"status": "outage_simulated", "audit_store_healthy": false}
```
### Doctor Fail-Open Access
```bash
curl -s -i -H "X-User-Id: doc_1" -H "X-User-Role: doctor" http://localhost:8000/patients/P100
```
```JSON
HTTP/1.1 200 OK
x-system-degraded: true

{"patient_id": "P100", ...}
```
### Billing Fail-Closed Access
```bash
curl -s -i -H "X-User-Id: bill_1" -H "X-User-Role: billing" http://localhost:8000/patients/P100
```
```JSON
HTTP/1.1 503 Service Unavailable

{"detail":"Service degraded: Non-clinical patient record access is unavailable while audit store is offline."}
```

## 5. Load Testing Verification (k6 Results)
```bash
k6 run tests/load/degraded_load_test.js
```
```JSON
checks_succeeded...: 100.00% 1051 out of 1051
✓ doctor read succeeds under outage (200)
✓ degraded header present for doctor
✓ billing read blocked under outage (503)
```
