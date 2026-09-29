from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, EmailStr, Field

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Full Name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=4, description="Password")
    role: str = Field("seeker", description="Role: seeker, recruiter, or admin")
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    skills: Optional[Union[str, List[str]]] = None
    company: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    skills: List[str] = []
    company: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    token_type: str = "bearer"

class ProfileUpdateRequest(BaseModel):
    email: EmailStr
    skills: Optional[Union[str, List[str]]] = None
    target_role: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
