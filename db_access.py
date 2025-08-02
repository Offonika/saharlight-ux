import logging
from datetime import datetime
from typing import List
from db import SessionLocal, Profile, Entry


def save_profile(user_id: int, icr: float, cf: float, target: float) -> None:
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)
        if not profile:
            profile = Profile(telegram_id=user_id)
            session.add(profile)
        profile.icr = icr
        profile.cf = cf
        profile.target_bg = target
        session.commit()


def get_profile(user_id: int) -> Profile | None:
    with SessionLocal() as session:
        return session.get(Profile, user_id)


def add_entry(entry_data: dict) -> None:
    with SessionLocal() as session:
        entry = Entry(**entry_data)
        session.add(entry)
        try:
            session.commit()
        except Exception:
            logging.exception("Failed to add entry")
            session.rollback()
            raise


def get_entries_since(user_id: int, date_from: datetime) -> List[Entry]:
    with SessionLocal() as s:
        return (
            s.query(Entry)
            .filter(Entry.telegram_id == user_id)
            .filter(Entry.event_time >= date_from)
            .order_by(Entry.event_time)
            .all()
        )
