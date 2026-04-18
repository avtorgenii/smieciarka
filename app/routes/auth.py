from fastapi import APIRouter, Depends, HTTPException, Response, Form
from fastapi.responses import RedirectResponse

from sqlalchemy import text
from app.auth import hash_password, manager, verify_password
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


# --- ROUTES ---
@router.post("/register")
async def register(
        email: str = Form(...),
        password: str = Form(...),
        first_name: str = Form(...),
        last_name: str = Form(...),
        phone: str = Form(...),
        db=Depends(get_db)
):
    print(f"DEBUG: Register attempt for {email}, password length: {len(password)}")

    if len(password) < 11:
        raise HTTPException(status_code=400,
                            detail=f"Password too short, should be at least 12 characters, current length: {len(password)}")

    # Hash password before writing
    hashed = hash_password(password)

    query = text("""
                 INSERT INTO users (email, password, first_name, last_name, phone)
                 VALUES (:email, :password, :first_name, :last_name, :phone)
                 RETURNING id
                 """)
    try:
        result = await db.execute(query,
                                  {
                                      "email": email, "password": hashed,
                                      "first_name": first_name, "last_name": last_name, "phone": phone
                                  })
        user_id = result.scalar()  # Get id of freshly created user
        await db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # --- AUTO LOGIN ---
    # Create token for that new user
    access_token = manager.create_access_token(
        data={'sub': str(user_id)}
    )

    # Redirect to main page and set the cookie
    response = RedirectResponse(url="/", status_code=302)
    manager.set_cookie(response, access_token)

    return response


@router.post("/login")
async def login(
        email: str = Form(...),
        password: str = Form(...),
        db=Depends(get_db)
):
    # Search user by emails
    query = text("SELECT id, email, password FROM users WHERE email = :email")
    res = await db.execute(query, {"email": email})
    user = res.fetchone()

    print(f"DEBUG: Login attempt for {email}, password length: {len(password)}")

    # Check existence and password
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create JWT token
    access_token = manager.create_access_token(
        data={'sub': str(user.id)}
    )

    # Put token into cookie
    resp = RedirectResponse(url="/", status_code=302)
    manager.set_cookie(resp, access_token)
    return resp


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=302)
    manager.set_cookie(resp, "")  # Clear cookie
    return resp
