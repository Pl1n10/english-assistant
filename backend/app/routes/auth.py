from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models import Teacher
from app.config import settings

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class TeacherRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone_number: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_teacher(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Teacher:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        teacher_id: int = payload.get("sub")
        if teacher_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Teacher).where(Teacher.id == int(teacher_id)))
    teacher = result.scalar_one_or_none()
    if teacher is None:
        raise credentials_exception
    return teacher


@router.post("/register", response_model=Token)
async def register(
    teacher_data: TeacherRegister,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Teacher).where(Teacher.email == teacher_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email già registrata")

    teacher = Teacher(
        name=teacher_data.name,
        email=teacher_data.email,
        phone_number=teacher_data.phone_number,
        hashed_password=get_password_hash(teacher_data.password),
        settings={
            "lesson_duration": 60,
            "price_per_lesson": 25,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "timezone": "Europe/Rome",
        },
    )

    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)

    access_token = create_access_token(data={"sub": str(teacher.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Teacher).where(Teacher.email == form_data.username)
    )
    teacher = result.scalar_one_or_none()

    if not teacher or not verify_password(form_data.password, teacher.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(teacher.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_teacher: Teacher = Depends(get_current_teacher)):
    return {
        "id": current_teacher.id,
        "name": current_teacher.name,
        "email": current_teacher.email,
        "phone_number": current_teacher.phone_number,
        "has_google_calendar": bool(current_teacher.google_refresh_token),
    }
