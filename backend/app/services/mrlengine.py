import hashlib
import json
from datetime import date, timedelta
from app.models.mrl import Animal, VeterinaryDrug, AuditLedger, ComplianceStatus

class MRLEngine:

    @staticmethod
    def compute_withdrawal(end_date: date, drug: VeterinaryDrug, commodity_type: str = "milk") -> date:
        days = drug.milk_withdrawal_days if commodity_type == "milk" else drug.meat_withdrawal_days
        return end_date + timedelta(days=days)

    @staticmethod
    def verify_procurement_safety(animal: Animal, check_date: date) -> dict:
        if animal.withdrawal_end_date and check_date < animal.withdrawal_end_date:
            days_remaining = (animal.withdrawal_end_date - check_date).days
            return {
                "eligible": False,
                "status": ComplianceStatus.WITHDRAWAL_ACTIVE,
                "days_remaining": days_remaining,
                "safe_date": animal.withdrawal_end_date.isoformat(),
                "alert": "REJECT: Milk/meat exceeds permissible MRL under FSSAI regulations."
            }
        return {
            "eligible": True,
            "status": ComplianceStatus.SAFE,
            "days_remaining": 0,
            "safe_date": str(animal.withdrawal_end_date) if animal.withdrawal_end_date else None,
            "alert": "ACCEPT: Clear for procurement."
        }

    @staticmethod
    def generate_audit_entry(record_id: str, action: str, previous_hash: str, payload: dict) -> AuditLedger:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        raw = f"{previous_hash}{record_id}{action}{serialized}"
        cur_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        return AuditLedger(
            record_id=record_id,
            action=action,
            previous_hash=previous_hash,
            current_hash=cur_hash,
            payload_snapshot=serialized
        )