# Architectural Trade-Off Analysis

This document details the design decisions and trade-offs evaluated across each implementation stage of `access-sentinel`.

---

## 1. Core Data Model & RBAC Scope (Stage 1)

* **Decision:** Enforce role-scoped data attribute boundaries at the API dependency layer.
* **Trade-Off:** Predictable, explicit policy evaluation prior to payload serialization vs. slight increase in router dependency logic.
* **Role Policy Scope:**
  - **Doctor:** Clinical notes + Billing metadata (full medical context).
  - **Nurse:** Clinical notes only; financial records set to `null`.
  - **Billing:** Financial/insurance data only; diagnosis notes set to `null`.
  - **Admin:** Direct read access to patient PHI/Billing records is **prohibited** (`403 Forbidden`). Admins manage platform health and audit logs only.

---

## 2. Cryptographic Immutability vs. Data Compliance (Stage 2)

* **Decision:** Store append-only access events linked with SHA-256 cryptographic parent hashes (`prev_hash`).
* **Trade-Off:** Cryptographic immutability guarantees audit integrity, but conflicts with privacy regulations requiring record purge rights (e.g., GDPR "Right to be Forgotten"). Real-world architectures solve this using pseudonymized lookup tables or Write-Once-Read-Many (WORM) storage.
* **Invariants:** Every access attempt (granted or denied) generates a log record. Deletion endpoints return `405 Method Not Allowed`.

---

## 3. Break-Glass Emergency Overrides (Stage 3)

* **Decision:** Provide an explicit mechanism for clinical personnel (`doctor`, `nurse`) to bypass standard scoping during emergency scenarios by supplying `X-Break-Glass: true` and `X-Break-Glass-Reason`.
* **Tension:** **Never block life-saving medical care** vs. **never create an unmonitored backdoor**.
* **Mitigations:**
  - Non-clinical roles (`admin`, `billing`) cannot break-glass (`403 Forbidden`).
  - Requests missing a valid `X-Break-Glass-Reason` are rejected (`400 Bad Request`).
  - Invocations emit warning logs and increment Prometheus anomaly counters (`access_sentinel_break_glass_total`).

---

## 4. Fail-Open vs. Fail-Closed Degradation Strategy (Stage 4)

* **Decision:** Implement a hybrid degradation strategy when the primary audit log store is unreachable.
* **Tension:** **Strict security compliance** vs. **high clinical availability**.
* **Policy Decision:**
  - **Clinical Reads (Doctor/Nurse):** *Fail-Open*. Requests succeed, return an `X-System-Degraded: true` header, and buffer audit entries to an in-memory degraded queue for post-recovery flushing.
  - **Non-Clinical Reads (Billing):** *Fail-Closed*. Requests are rejected with `503 Service Unavailable` to maintain privacy compliance when logging cannot be guaranteed.

---

## 5. Metric Cardinality vs. Observability (Stage 5)

* **Decision:** Expose Prometheus metrics on `/metrics` labeled by `role`, `status`, `action`, and `is_break_glass`.
* **Trade-Off:** Excluded high-cardinality labels (e.g., `patient_id` or `user_id`) from general request counters to prevent metric memory explosion, restricting entity identification to the audit trail log store.
