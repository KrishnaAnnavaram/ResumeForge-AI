"""Auth API router."""
from fastapi import APIRouter, HTTPException, status
from careeros.api.auth.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from careeros.api.auth.service import register_user, authenticate_user, create_access_token
from careeros.dependencies import CurrentUser, DB
from careeros.core.exceptions import AuthenticationError, DuplicateResourceError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: DB):
    try:
        user = await register_user(request.email, request.password, request.display_name, db)
        token = create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: DB):
    try:
        user = await authenticate_user(request.email, request.password, db)
        token = create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
    )
