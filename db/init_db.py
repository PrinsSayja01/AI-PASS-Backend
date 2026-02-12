from db.database import engine, Base
from db import models  # noqa: F401
from db.wallet_models import Wallet, UsageEvent

def main():
    Base.metadata.create_all(bind=engine)
    print("✅ SQLite DB ready: tables created")

if __name__ == "__main__":
    main()
