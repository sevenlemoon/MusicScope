"""Create the empty local personal user after migrations, idempotently."""

from app.constants import PERSONAL_USER_ID
from app.db import SessionLocal
from app.models import User, UserSettings


def main() -> None:
    db = SessionLocal()
    try:
        if db.get(User, PERSONAL_USER_ID) is None:
            db.add(User(id=PERSONAL_USER_ID))
        if db.get(UserSettings, PERSONAL_USER_ID) is None:
            db.add(UserSettings(user_id=PERSONAL_USER_ID))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
