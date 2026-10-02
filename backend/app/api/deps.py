from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.services.auth import decode_token
security = HTTPBearer(auto_error=False)
def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    user = db.get(User, payload.get("sub")) if payload else None
    if not user: raise HTTPException(status_code=401, detail="Invalid or expired demo token")
    return user
