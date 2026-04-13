import os
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select

# 1. Define your Model
class ATMLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    prompt: str
    response: str
    status: str
    reason: Optional[str] = None
    tokens: float
    latency: float
    timestamp: Optional[float] = None


# 2. Setup the Absolute Path (Corrected for app/db/session.py)
# Path of this file: project/app/db/session.py
# Level 1 (dirname): project/app/db
# Level 2 (dirname): project/app
# Level 3 (dirname): project/ <--- THIS IS THE ROOT
current_file_path = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))

DB_PATH = os.path.join(BASE_DIR, "atm_logs.db")
sqlite_url = f"sqlite:///{DB_PATH}"

# For debugging: This will print exactly where it's looking when you run it
print(f"📂 Database Path target: {DB_PATH}")

engine = create_engine(sqlite_url, echo=False)


# 3. Helper Functions
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)



def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("🧹 Database wiped and reset successfully.")

def log_event(log_entry: ATMLog):
    with Session(engine) as session:
        session.add(log_entry)
        session.commit()
        session.refresh(log_entry)
