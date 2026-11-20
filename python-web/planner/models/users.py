from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from models.events import Event


class User(BaseModel):
    model_config = ConfigDict(
            json_schema_extra= {
                "example": {
                    "email": "fastapi@packt.com",
                    "username": "strong!!!",
                    "events": [],
                }
            }
        )
    email: EmailStr
    password: str
    events: Optional[list[Event]] = None


class NewUser(BaseModel):
    model_config = ConfigDict(
        json_schema_extra= {
            "example": {
                "email": "fastapi@packt.com",
                "password": "strong!!!",
            }
        }
    )
    email: EmailStr
    password: str