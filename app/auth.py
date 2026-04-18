import bcrypt
from fastapi_login import LoginManager
import os
from datetime import timedelta
from app.database import get_db
from sqlalchemy import text

SECRET = os.getenv("SECRET_KEY")

# Manages JWT tokens, puts them into cookies and fetch tokens from there to identify user
manager = LoginManager(SECRET, token_url="/auth/login", default_expiry=timedelta(days=1),
                       use_cookie=True)  # use_cookie means to look for token in cookies instead of headers

# For how long user is going to be logged in
COOKIE_TIME = timedelta(days=1)


# --- Helper funcs ---
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


@manager.user_loader()
async def load_user(user_id: str):
    # TODO: specify which fields of user to fetch
    async for db in get_db():
        query = text("SELECT id, email, first_name FROM users WHERE id = :id")
        result = await db.execute(query, {"id": int(user_id)})
        return result.fetchone()
    return None
