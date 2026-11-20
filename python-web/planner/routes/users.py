from fastapi import APIRouter, HTTPException, status

from models.users import NewUser, User


user_router = APIRouter(
    tags = ["User"]
)

users = {}

@user_router.post("/signup")
async def sign_up(data: NewUser) -> dict:
    if data.email in users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with supplied username exists"
        )
    users[data.email] = data
    return {"message" : "User successfully registered"}


@user_router.post("/signin")
async def sign_in(user: User) -> dict:
    if user.email not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist"
        )

    if users[user.email].password != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong credentials passed"
        )
    return { "message": "User signed in successfully" }