from prometheus_client import Counter, Gauge

# Security & Access Counters
ACCESS_REQUESTS_TOTAL = Counter(
    "access_sentinel_requests_total",
    "Total patient record access requests",
    ["role", "status", "action", "is_break_glass"],
)

BREAK_GLASS_TOTAL = Counter(
    "access_sentinel_break_glass_total",
    "Total emergency break-glass invocations (anomaly detection metric)",
    ["role", "patient_id"],
)

UNAUTHORIZED_ACCESS_TOTAL = Counter(
    "access_sentinel_unauthorized_total",
    "Total rejected or unauthorized access attempts",
    ["role", "reason"],
)

# Resilience & System State Gauges
AUDIT_STORE_HEALTHY = Gauge(
    "access_sentinel_audit_store_healthy",
    "Health status of the primary audit store (1 = healthy, 0 = degraded/offline)",
)

DEGRADED_BUFFERED_LOGS = Gauge(
    "access_sentinel_buffered_degraded_logs",
    "Current count of audit logs buffered in degraded fallback queue",
)

# Initialize Gauges
AUDIT_STORE_HEALTHY.set(1)
DEGRADED_BUFFERED_LOGS.set(0)
