
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class TodoItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra= {
            "example": {
                "item": "Read the next chapter of the book"
            }
        }
    )
    item: str

class TodoItems(BaseModel):
    model_config = ConfigDict(
        json_schema_extra= {
            "example": {
                "todos" : [
                    {
                        "item": "Read the next chapter of the book"
                    },
                    {
                        "item": "Read another chapter of the book"
                    }
                ]
                
            }
        }
    )


    todos: List[TodoItem]



class Todo(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "item": "Buy groceries"
            }
        }
    )

    id: int
    item: str

