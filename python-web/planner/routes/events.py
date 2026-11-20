from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from database.connection import Event, EventUpdate, get_session


event_router = APIRouter(tags=["Events"])


@event_router.get("/", response_model=list[Event])
async def get_events(session=Depends(get_session)) -> list[Event]:
    return session.exec(select(Event)).all()


@event_router.get("/{id}", response_model=Event)
async def get_event(id: int, session=Depends(get_session)) -> Event:
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event with supplied ID does not exist",
        )
    return event


@event_router.post("/new")
async def create(event: Event, session=Depends(get_session)) -> dict:
    session.add(event)
    session.commit()
    session.refresh(event)
    return {"message": "Event created successfully"}


@event_router.put("/{id}", response_model=Event)
async def update_event(id: int, updated: EventUpdate, session=Depends(get_session)) -> Event:
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event with supplied ID does not exist",
        )
    data = updated.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(event, key, value)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@event_router.delete("/{id}")
async def delete_event(id: int, session=Depends(get_session)) -> dict:
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event with supplied ID does not exist",
        )
    session.delete(event)
    session.commit()
    return {"message": "Event deleted successfully"}


@event_router.delete("/")
async def delete_all_events(session=Depends(get_session)) -> dict:
    events = session.exec(select(Event)).all()
    for event in events:
        session.delete(event)
    session.commit()
    return {"message": "Events deleted successfully"}
