from sqlalchemy.orm import Session
from passlib.context import CryptContext
import random
import string
from . import models  # Add the dot here

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, username: str, email: str, password: str):
    hashed_password = pwd_context.hash(password)
    db_user = models.User(username=username, email=email, password_hash=hashed_password, is_verified=False)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def mark_user_verified(db: Session, email: str):
    user = get_user_by_email(db, email)
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    return user

def generate_otp_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def create_otp(db: Session, email: str, purpose: str):
    db.query(models.OTP).filter(models.OTP.email == email, models.OTP.purpose == purpose).delete()
    db.commit()
    otp_code = generate_otp_code()
    db_otp = models.OTP(email=email, otp_code=otp_code, purpose=purpose)
    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)
    return otp_code

def verify_otp(db: Session, email: str, otp_code: str, purpose: str):
    otp_record = db.query(models.OTP).filter(
        models.OTP.email == email, models.OTP.otp_code == otp_code, models.OTP.purpose == purpose
    ).first()
    if not otp_record: return False
    db.delete(otp_record)
    db.commit()
    return True