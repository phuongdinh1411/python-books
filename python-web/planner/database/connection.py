from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel, Session, create_engine


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    image: str
    description: str
    location: str
    tags: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))

class EventUpdate(SQLModel):
    title: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[list[str]] = None

database_file = "planner.db"
connection_str = f"sqlite:///{database_file}"
connection_args = {"check_same_thread": False}
engine_url = create_engine(connection_str, echo=True, connect_args=connection_args)

def conn():
    SQLModel.metadata.create_all(engine_url)

def get_session():
    with Session(engine_url) as session:
        yield session