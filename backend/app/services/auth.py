from datetime import datetime, timedelta, timezone
import base64, hashlib, hmac, json
from app.core.config import get_settings
def create_token(user_id: int):
    # Small HS256 implementation keeps the demo runnable when PyJWT is absent.
    # Production may use PyJWT/OIDC; the token still has authenticated expiry.
    header={"alg":"HS256","typ":"JWT"}; payload={"sub":str(user_id),"exp":int((datetime.now(timezone.utc)+timedelta(hours=12)).timestamp())}
    def enc(x): return base64.urlsafe_b64encode(json.dumps(x,separators=(",", ":")).encode()).rstrip(b"=")
    signing=enc(header)+b"."+enc(payload); sig=hmac.new(get_settings().jwt_secret_key.encode(),signing,hashlib.sha256).digest()
    return (signing+b"."+base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
def decode_token(token: str):
    try:
        head,pay,sig=token.split("."); signing=(head+"."+pay).encode()
        expected=hmac.new(get_settings().jwt_secret_key.encode(),signing,hashlib.sha256).digest()
        actual=base64.urlsafe_b64decode(sig+"="*(-len(sig)%4))
        payload=json.loads(base64.urlsafe_b64decode(pay+"="*(-len(pay)%4)))
        return payload if hmac.compare_digest(expected,actual) and payload["exp"]>datetime.now(timezone.utc).timestamp() else None
    except Exception: return None
