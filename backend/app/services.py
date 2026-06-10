from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine
from app.models import AuditLog

EXCLUDE_TABLES = {"backup_records", "audit_logs"}


def audit_log(db: Session, user_id: int | None, module: str, action: str, detail: str) -> None:
    entry = AuditLog(user_id=user_id, module=module, action=action, detail=detail)
    db.add(entry)
    db.commit()


def _convert_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def dump_database_snapshot() -> dict[str, list[dict[str, Any]]]:
    snapshot: dict[str, list[dict[str, Any]]] = {}
    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name in EXCLUDE_TABLES:
                continue
            rows = connection.execute(table.select()).mappings().all()
            snapshot[table.name] = [
                {column: _convert_value(value) for column, value in dict(row).items()} for row in rows
            ]
    return snapshot


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        for parser in (datetime.fromisoformat, date.fromisoformat):
            try:
                return parser(value)
            except ValueError:
                continue
    return value


def restore_database_snapshot(db: Session, snapshot: dict[str, list[dict[str, Any]]]) -> None:
    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in EXCLUDE_TABLES:
                continue
            db.execute(text(f"TRUNCATE TABLE {table.name}"))

        for table in Base.metadata.sorted_tables:
            if table.name in EXCLUDE_TABLES:
                continue
            rows = snapshot.get(table.name, [])
            if not rows:
                continue
            normalized_rows = [
                {column: _normalize_value(value) for column, value in row.items()} for row in rows
            ]
            db.execute(insert(table), normalized_rows)

        db.commit()
    finally:
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def write_snapshot_file(snapshot: dict[str, Any], filename: str) -> str:
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / filename
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def read_snapshot_file(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
