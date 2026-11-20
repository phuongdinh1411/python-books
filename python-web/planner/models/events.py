
from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(
        json_schema_extra= {
            "example": {
                "title": "FastAPI Book Launch",
                "image": "https://linktomyimage.com/image.png",
                "description": "We will be discussing the contents of the FastAPI book in this event. Ensure to come with your own copy to win gifts!",
                "tags": ["python", "fastapi", "book", "launch"],
                "location": "Google Meet"
            }
        }
    )

    id: int
    title: str
    image: str
    description: str
    tags: list[str]
    location: str