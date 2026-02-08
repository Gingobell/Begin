import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from urllib.parse import urlencode

from ..models.user import User
from ..core.config import BACKEND_URL, FRONTEND_URL
from ..core.db import supabase

router = APIRouter()
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    birthday: Optional[date] = None
    timezone: Optional[str] = "Asia/Shanghai"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class AppleSignInRequest(BaseModel):
    id_token: str
    full_name: Optional[str] = None  # Apple 只在首次登录时提供

class GoogleSignInRequest(BaseModel):
    id_token: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

# MARK: - Authentication Helper
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """认证用户 - 仅支持生产模式"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息"
        )

    token = credentials.credentials

    # 验证 Supabase JWT
    try:
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = user_response.user.id
        user_email = user_response.user.email
        
        # 从 profiles 表获取用户生日信息
        birth_date = None
        try:
            profile_response = supabase.table("profiles").select("birth_datetime").eq("id", user_id).single().execute()
            if profile_response.data and profile_response.data.get("birth_datetime"):
                birth_datetime_str = profile_response.data.get("birth_datetime")
                # birth_datetime 现在是 timestamp without time zone，直接解析
                birth_date = datetime.fromisoformat(birth_datetime_str).date()
        except Exception as e:
            logger.warning(f"[AUTH] 无法获取用户生日: user_id={user_id}, error={e}")
        
        return User(
            id=user_id,
            email=user_email,
            birth_date=birth_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )

# MARK: - Auth Endpoints
@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """注册新用户 - 使用 Supabase Auth"""
    try:
        logger.info(f"[REGISTER] 开始注册: email={request.email}")
        
        # 准备用户元数据
        user_metadata = {}
        if request.full_name:
            user_metadata["full_name"] = request.full_name
        if request.timezone:
            user_metadata["timezone"] = request.timezone
        if request.birthday:
            user_metadata["birthday"] = request.birthday.isoformat()
        
        # 使用 Supabase Auth 注册用户
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": user_metadata
            }
        })
        
        if not auth_response.user:
            logger.error(f"[REGISTER] 注册失败: email={request.email}")
            raise HTTPException(status_code=400, detail="注册失败")
        
        logger.info(f"[REGISTER] 注册成功: user_id={auth_response.user.id}, email={auth_response.user.email}")
        
        # 检查 session 是否存在（如果启用邮箱验证，session 可能为 None）
        if not auth_response.session:
            logger.warning(f"[REGISTER] 注册成功但需要邮箱验证: email={request.email}")
            # 返回特殊响应，前端需处理此情况
            return AuthResponse(
                access_token="",  # 空token表示需要验证
                refresh_token="",
                user={
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "full_name": user_metadata.get("full_name")
                }
            )
        
        # 返回认证响应（包含 access_token 和 refresh_token）
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "full_name": user_metadata.get("full_name")
            }
        )
    except Exception as e:
        logger.error(f"[REGISTER] 注册异常: email={request.email}, error={str(e)}")
        raise HTTPException(status_code=400, detail=f"注册失败: {str(e)}")

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """用户登录 - 使用 Supabase Auth"""
    try:
        logger.info(f"[LOGIN] 登录请求: email={request.email}")
        
        # 使用 Supabase Auth 登录
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            logger.warning(f"[LOGIN] 登录失败: email={request.email}")
            raise HTTPException(status_code=401, detail="登录失败")
        
        logger.info(f"[LOGIN] 登录成功: user_id={auth_response.user.id}, email={auth_response.user.email}")
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
        )
    except Exception as e:
        logger.error(f"[LOGIN] 登录异常: email={request.email}, error={str(e)}")
        raise HTTPException(status_code=401, detail="用户名或密码错误")

@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """刷新访问令牌"""
    try:
        logger.info(f"[REFRESH] 刷新令牌请求")
        auth_response = supabase.auth.refresh_session(request.refresh_token)
        logger.info(f"[REFRESH] 令牌刷新成功: user_id={auth_response.user.id}")
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
        )
    except Exception as e:
        logger.error(f"[REFRESH] 刷新令牌失败: error={str(e)}")
        raise HTTPException(status_code=401, detail="刷新令牌无效")

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出"""
    try:
        logger.info(f"[LOGOUT] 用户登出: user_id={current_user.id}")
        supabase.auth.sign_out()
        logger.info(f"[LOGOUT] 登出成功: user_id={current_user.id}")
        return {"message": "登出成功"}
    except Exception as e:
        logger.error(f"[LOGOUT] 登出失败: user_id={current_user.id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"登出失败: {str(e)}")

@router.post("/apple/signin", response_model=AuthResponse)
async def apple_signin(request: AppleSignInRequest):
    """Apple Sign-In - 使用 identityToken 登录"""
    try:
        logger.info("[APPLE-SIGNIN] 开始 Apple 登录")

        # 使用 Supabase sign_in_with_id_token
        auth_response = supabase.auth.sign_in_with_id_token({
            "provider": "apple",
            "token": request.id_token
        })

        if not auth_response.user:
            logger.error("[APPLE-SIGNIN] 登录失败")
            raise HTTPException(status_code=401, detail="Apple 登录失败")

        logger.info(f"[APPLE-SIGNIN] 登录成功: user_id={auth_response.user.id}, email={auth_response.user.email}")

        # 如果是首次登录且提供了 full_name，更新 profiles 表
        if request.full_name:
            try:
                supabase.table("profiles").update({
                    "full_name": request.full_name
                }).eq("id", auth_response.user.id).execute()
                logger.info(f"[APPLE-SIGNIN] 已更新用户名: {request.full_name}")
            except Exception as e:
                logger.warning(f"[APPLE-SIGNIN] 更新用户名失败: {e}")

        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "full_name": request.full_name
            }
        )
    except Exception as e:
        logger.error(f"[APPLE-SIGNIN] 异常: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Apple 登录失败: {str(e)}")

@router.post("/google/signin", response_model=AuthResponse)
async def google_signin(request: GoogleSignInRequest):
    """Google Sign-In - 使用 idToken 登录"""
    try:
        logger.info("[GOOGLE-SIGNIN] 开始 Google 登录")

        # 使用 Supabase sign_in_with_id_token
        auth_response = supabase.auth.sign_in_with_id_token({
            "provider": "google",
            "token": request.id_token
        })

        if not auth_response.user:
            logger.error("[GOOGLE-SIGNIN] 登录失败")
            raise HTTPException(status_code=401, detail="Google 登录失败")

        logger.info(f"[GOOGLE-SIGNIN] 登录成功: user_id={auth_response.user.id}, email={auth_response.user.email}")

        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
        )
    except Exception as e:
        logger.error(f"[GOOGLE-SIGNIN] 异常: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Google 登录失败: {str(e)}")
