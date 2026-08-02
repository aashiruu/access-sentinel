from datetime import datetime, timezone
from typing import List
from app.models import AuditEntry, Role, AccessStatus


class ImmutableAuditStore:
    def __init__(self):
        self._logs: List[AuditEntry] = []
        self._genesis_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    def log_access(
        self,
        user_id: str,
        role: Role,
        patient_id: str,
        action: str,
        status: AccessStatus,
        is_break_glass: bool = False,
        break_glass_reason: str | None = None,
        reason: str | None = None,
    ) -> AuditEntry:
        prev_hash = self._logs[-1].hash if self._logs else self._genesis_hash
        entry_id = len(self._logs) + 1
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = AuditEntry(
            id=entry_id,
            timestamp=timestamp,
            user_id=user_id,
            role=role,
            patient_id=patient_id,
            action=action,
            status=status,
            is_break_glass=is_break_glass,
            break_glass_reason=break_glass_reason,
            reason=reason,
            prev_hash=prev_hash,
            hash="",
        )
        entry.hash = entry.calculate_hash()
        self._logs.append(entry)
        return entry

    def get_logs(self) -> List[AuditEntry]:
        return [log.model_copy() for log in self._logs]

    def verify_integrity(self) -> bool:
        prev_hash = self._genesis_hash
        for entry in self._logs:
            if entry.prev_hash != prev_hash:
                return False
            if entry.hash != entry.calculate_hash():
                return False
            prev_hash = entry.hash
        return True


audit_store = ImmutableAuditStore()
