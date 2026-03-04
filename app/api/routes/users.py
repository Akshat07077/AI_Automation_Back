from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.services.user_service import create_user, get_all_users, verify_user_password

router = APIRouter(tags=["users"])


class RegisterUserRequest(BaseModel):
    username: str
    password: str


class RegisterUserResponse(BaseModel):
    message: str
    username: str


class UserResponse(BaseModel):
    username: str
    created_at: str


class UsersListResponse(BaseModel):
    users: list[UserResponse]


@router.post("/register-user", response_model=RegisterUserResponse)
async def register_user(
    request: RegisterUserRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterUserResponse:
    """
    Register a new user. Requires admin authentication (check via middleware/cookie).
    """
    if len(request.username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters"
        )
    
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )
    
    try:
        user = await create_user(db, request.username, request.password)
        return RegisterUserResponse(
            message=f"User '{user.username}' registered successfully",
            username=user.username
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register user: {str(e)}"
        )


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
) -> UsersListResponse:
    """
    List all registered users. Requires admin authentication.
    """
    users = await get_all_users(db)
    return UsersListResponse(
        users=[
            UserResponse(
                username=user.username,
                created_at=user.created_at.isoformat()
            )
            for user in users
        ]
    )


@router.post("/verify-user")
async def verify_user(
    request: RegisterUserRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify user credentials. Used for login.
    """
    is_valid = await verify_user_password(db, request.username, request.password)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"valid": True, "username": request.username}
