from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from database.models import MachineInspection, InspectionStatus, MahjongTable, TableStatus


class InspectionService:
    def __init__(self, db: Session):
        self.db = db

    def create_inspection(self, table_id: int, inspection_date: date, **kwargs) -> MachineInspection:
        table = self.db.query(MahjongTable).filter(MahjongTable.id == table_id).first()
        if not table:
            raise ValueError("麻将桌不存在")

        inspection = MachineInspection(
            table_id=table_id,
            inspection_date=inspection_date,
            inspector=kwargs.get("inspector"),
            status=kwargs.get("status", InspectionStatus.PENDING),
            tiles_complete=kwargs.get("tiles_complete"),
            dice_normal=kwargs.get("dice_normal"),
            power_supply_normal=kwargs.get("power_supply_normal"),
            operation_normal=kwargs.get("operation_normal"),
            cleaning_done=kwargs.get("cleaning_done"),
            issues_found=kwargs.get("issues_found"),
            actions_taken=kwargs.get("actions_taken"),
            next_inspection_date=kwargs.get("next_inspection_date", inspection_date + timedelta(days=7)),
            remark=kwargs.get("remark"),
            created_at=datetime.now()
        )
        self.db.add(inspection)
        self.db.commit()
        self.db.refresh(inspection)
        return inspection

    def get_inspection(self, inspection_id: int) -> Optional[MachineInspection]:
        return self.db.query(MachineInspection).filter(MachineInspection.id == inspection_id).first()

    def get_inspections_by_table(self, table_id: int) -> List[MachineInspection]:
        return self.db.query(MachineInspection).filter(
            MachineInspection.table_id == table_id
        ).order_by(MachineInspection.inspection_date.desc()).all()

    def get_inspections_by_date(self, inspection_date: date) -> List[MachineInspection]:
        return self.db.query(MachineInspection).filter(
            MachineInspection.inspection_date == inspection_date
        ).order_by(MachineInspection.created_at.desc()).all()

    def get_pending_inspections(self) -> List[MachineInspection]:
        return self.db.query(MachineInspection).filter(
            MachineInspection.status == InspectionStatus.PENDING
        ).order_by(MachineInspection.inspection_date.asc()).all()

    def get_due_inspections(self, due_date: date = None) -> List[MachineInspection]:
        due_date = due_date or date.today()
        return self.db.query(MachineInspection).filter(
            MachineInspection.next_inspection_date <= due_date,
            MachineInspection.status.in_([InspectionStatus.PENDING, InspectionStatus.ABNORMAL])
        ).order_by(MachineInspection.next_inspection_date.asc()).all()

    def get_tables_needing_inspection(self) -> List[dict]:
        tables = self.db.query(MahjongTable).filter(
            MahjongTable.status != TableStatus.MAINTENANCE
        ).all()
        result = []
        today = date.today()

        for table in tables:
            last_inspection = self.db.query(MachineInspection).filter(
                MachineInspection.table_id == table.id
            ).order_by(MachineInspection.inspection_date.desc()).first()

            needs_inspection = False
            days_since = None
            next_date = None

            if last_inspection:
                if last_inspection.next_inspection_date:
                    next_date = last_inspection.next_inspection_date
                    if last_inspection.next_inspection_date <= today:
                        needs_inspection = True
                days_since = (today - last_inspection.inspection_date).days
                if days_since >= 7:
                    needs_inspection = True
            else:
                needs_inspection = True

            result.append({
                "table": table,
                "last_inspection": last_inspection,
                "needs_inspection": needs_inspection,
                "days_since": days_since,
                "next_date": next_date
            })

        return result

    def update_inspection(self, inspection_id: int, **kwargs) -> Optional[MachineInspection]:
        inspection = self.get_inspection(inspection_id)
        if not inspection:
            return None

        all_normal = all([
            kwargs.get("tiles_complete", inspection.tiles_complete),
            kwargs.get("dice_normal", inspection.dice_normal),
            kwargs.get("power_supply_normal", inspection.power_supply_normal),
            kwargs.get("operation_normal", inspection.operation_normal),
            kwargs.get("cleaning_done", inspection.cleaning_done)
        ])

        for key, value in kwargs.items():
            if hasattr(inspection, key) and value is not None:
                setattr(inspection, key, value)

        if "status" not in kwargs:
            inspection.status = InspectionStatus.NORMAL if all_normal else InspectionStatus.ABNORMAL

        if inspection.status == InspectionStatus.NORMAL and not inspection.next_inspection_date:
            inspection.next_inspection_date = inspection.inspection_date + timedelta(days=7)

        self.db.commit()
        self.db.refresh(inspection)
        return inspection

    def complete_inspection(self, inspection_id: int, is_normal: bool, **kwargs) -> Optional[MachineInspection]:
        status = InspectionStatus.NORMAL if is_normal else InspectionStatus.ABNORMAL
        kwargs["status"] = status
        return self.update_inspection(inspection_id, **kwargs)

    def mark_repaired(self, inspection_id: int, actions_taken: str = None) -> Optional[MachineInspection]:
        inspection = self.get_inspection(inspection_id)
        if not inspection:
            return None

        inspection.status = InspectionStatus.REPAIRED
        if actions_taken:
            inspection.actions_taken = actions_taken
        inspection.next_inspection_date = date.today() + timedelta(days=3)
        self.db.commit()
        self.db.refresh(inspection)
        return inspection

    def delete_inspection(self, inspection_id: int) -> bool:
        inspection = self.get_inspection(inspection_id)
        if not inspection:
            return False
        self.db.delete(inspection)
        self.db.commit()
        return True

    def batch_create_weekly_inspections(self, inspector: str = None) -> int:
        tables = self.db.query(MahjongTable).filter(
            MahjongTable.status != TableStatus.MAINTENANCE
        ).all()
        today = date.today()
        count = 0

        for table in tables:
            existing = self.db.query(MachineInspection).filter(
                MachineInspection.table_id == table.id,
                MachineInspection.inspection_date == today,
                MachineInspection.status == InspectionStatus.PENDING
            ).first()
            if not existing:
                self.create_inspection(
                    table_id=table.id,
                    inspection_date=today,
                    inspector=inspector
                )
                count += 1

        return count
