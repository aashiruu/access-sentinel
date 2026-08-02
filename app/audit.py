from datetime import datetime, timezone
from typing import List, Optional
from app.models import AuditEntry, Role, AccessStatus


class AuditStoreUnavailableException(Exception):
    """Raised when the primary audit persistence layer is unreachable."""

    pass


class ImmutableAuditStore:

    def __init__(self):
        self._logs: List[AuditEntry] = []
        self._fallback_buffer: List[AuditEntry] = []
        self._genesis_hash = (
            "0000000000000000000000000000000000000000000000000000000000000000"
        )
        self.is_healthy: bool = True  # Simulated outage toggle

    def log_access(
        self,
        user_id: str,
        role: Role,
        patient_id: str,
        action: str,
        status: AccessStatus,
        is_break_glass: bool = False,
        break_glass_reason: Optional[str] = None,
        reason: Optional[str] = None,
        degraded_mode: bool = False,
    ) -> AuditEntry:
        if not self.is_healthy and not degraded_mode:
            raise AuditStoreUnavailableException(
                "Primary audit store connection unreachable."
            )

        prev_hash = self._logs[-1].hash if self._logs else self._genesis_hash
        entry_id = len(self._logs) + len(self._fallback_buffer) + 1
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
            reason=f"[DEGRADED_MODE] {reason}" if degraded_mode and reason else (reason or ("DEGRADED_MODE_BUFFERED" if degraded_mode else None)),
            prev_hash=prev_hash,
            hash="",
        )
        entry.hash = entry.calculate_hash()

        if degraded_mode or not self.is_healthy:
            self._fallback_buffer.append(entry)
        else:
            self._logs.append(entry)

        return entry

    def recover_and_flush(self) -> int:
        """Flushes buffered degraded entries into main chain once store recovers."""
        self.is_healthy = True
        flushed_count = 0
        while self._fallback_buffer:
            entry = self._fallback_buffer.pop(0)
            # Recalculate hash chain attachment
            entry.prev_hash = (
                self._logs[-1].hash if self._logs else self._genesis_hash
            )
            entry.hash = entry.calculate_hash()
            self._logs.append(entry)
            flushed_count += 1
        return flushed_count

    def get_logs(self) -> List[AuditEntry]:
        return [log.model_copy() for log in self._logs]

    def get_fallback_buffer(self) -> List[AuditEntry]:
        return [log.model_copy() for log in self._fallback_buffer]

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
