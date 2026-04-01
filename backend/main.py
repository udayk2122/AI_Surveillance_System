from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import cv2
from ultralytics import YOLO
import shutil
import time
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from backend import database, models, crud, alert_manager

# --- Environment & Security Setup ---
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Create Database tables (Bypassing Alembic for immediate startup)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="GuardianAI Surveillance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Define Paths & Mount Folders ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

uploads_path = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

# --- Load Dual YOLOv8 AI Models ---
model_dir = os.path.join(os.path.dirname(__file__), "ai_models")
try:
    # Standard COCO model for RGB cameras
    model_std = YOLO(os.path.join(model_dir, "yolov8n.pt"))
    print("✅ Standard YOLOv8 Model loaded.")
    
    # Custom Thermal model
    model_thm = YOLO(os.path.join(model_dir, "thermal_best.pt"))
    print("✅ Thermal YOLOv8 Model loaded.")
except Exception as e:
    print(f"⚠️ Warning: Could not load one or both YOLO models. Error: {e}")

# --- Pydantic Schemas ---
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class SendOTPRequest(BaseModel):
    email: EmailStr

class OTPRequest(BaseModel):
    email: EmailStr
    otp_code: str
    purpose: str

# --- JWT Token & Auth Dependency ---
def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = crud.get_user_by_email(db, email=email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.post("/api/auth/send-reg-otp")
def send_reg_otp(request: SendOTPRequest, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    if crud.get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    otp = crud.create_otp(db, request.email, purpose="registration")
    background_tasks.add_task(alert_manager.send_otp_email, request.email, otp, "registration")
    return {"status": "success", "message": "OTP sent in background."}

@app.post("/api/auth/verify-otp")
def verify_otp_endpoint(request: OTPRequest, db: Session = Depends(database.get_db)):
    if not crud.verify_otp(db, request.email, request.otp_code, request.purpose):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")
    return {"status": "success", "message": "OTP verified."}

@app.post("/api/auth/register")
def register_user(request: RegisterRequest, db: Session = Depends(database.get_db)):
    if crud.get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    crud.create_user(db, request.username, request.email, request.password)
    crud.mark_user_verified(db, request.email)
    return {"status": "success", "message": "Account created."}

@app.post("/api/auth/login")
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = crud.get_user_by_email(db, email=request.username)
    if not user or not crud.pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect credentials.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified.")
        
    access_token = create_access_token(data={"sub": user.email, "id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

# ==========================================
# DUAL-MODEL AI VIDEO PROCESSING
# ==========================================

@app.post("/api/surveillance/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    input_filepath = os.path.join(uploads_path, file.filename)
    with open(input_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    output_filename = f"annotated_{int(time.time())}.webm"
    output_filepath = os.path.join(uploads_path, output_filename)
    
    cap = cv2.VideoCapture(input_filepath)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    fourcc = cv2.VideoWriter_fourcc(*'vp80')
    out = cv2.VideoWriter(output_filepath, fourcc, fps, (width, height))

    # Save Video record to database
    db_video = models.Video(user_id=current_user.id, filename=file.filename, file_path=output_filepath, status="processed")
    db.add(db_video)
    db.commit()
    db.refresh(db_video)

    highest_confidence = 0.0
    top_threat_name = "Unknown"
    detected_unique_classes = set() # ANTI-SPAM: Tracks what we already found in this video

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        # 1. Run Standard Model
        res_std = model_std(frame, verbose=False)
        annotated_frame = res_std[0].plot() # Draw std boxes

        # 2. Run Thermal Model and draw over the same frame
        res_thm = model_thm(frame, verbose=False)
        annotated_frame = res_thm[0].plot(img=annotated_frame) 

        out.write(annotated_frame)

        # 3. Combine results to check for threats
        all_boxes = list(res_std[0].boxes) + list(res_thm[0].boxes)
        
        for box in all_boxes:
            conf = float(box.conf[0])
            
            # Figure out which model this box belongs to by checking standard classes first
            try:
                cls_name = model_std.names[int(box.cls[0])]
            except:
                cls_name = model_thm.names[int(box.cls[0])]

            if conf > 0.50:
                if conf > highest_confidence:
                    highest_confidence = conf
                    top_threat_name = cls_name

                # ANTI-SPAM: Only save to DB if we haven't logged this specific threat class in this video yet
                if cls_name not in detected_unique_classes:
                    detected_unique_classes.add(cls_name)

                    # Save Detection
                    db_detection = models.Detection(
                        video_id=db_video.id, 
                        timestamp_sec=cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                        object_class=cls_name,
                        confidence=conf
                    )
                    db.add(db_detection)
                    db.commit()

                    # Save Alert
                    db_alert = models.Alert(
                        user_id=current_user.id,
                        detection_id=db_detection.id,
                        alert_type="email",
                        message=f"Threat: {cls_name} detected at {(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0):.2f}s"
                    )
                    db.add(db_alert)
                    db.commit()

    cap.release()
    out.release()

    # Send exactly ONE email alert if anything was found in the whole video
    if len(detected_unique_classes) > 0:
        admin_email = os.getenv("SMTP_EMAIL", current_user.email)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        all_threats = ", ".join(list(detected_unique_classes))
        
        background_tasks.add_task(
            alert_manager.send_threat_alert_email, admin_email, all_threats, round(highest_confidence * 100, 2), current_time
        )

    return {
        "status": "success", 
        "video_url": f"/uploads/{output_filename}",
        "threat_found": len(detected_unique_classes) > 0, 
        "threat_details": ", ".join(list(detected_unique_classes)) if len(detected_unique_classes) > 0 else None
    }

# ==========================================
# DASHBOARD DYNAMIC DATA ROUTES
# ==========================================

@app.get("/api/surveillance/stats")
def get_dashboard_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    total_detections = db.query(models.Detection).join(models.Video).filter(models.Video.user_id == current_user.id).count()
    unread_alerts = db.query(models.Alert).filter(models.Alert.user_id == current_user.id, models.Alert.is_read == False).count()
    chart_data = [5, 12, 8, 22, 14, 19, total_detections]

    return {
        "active_cameras": 1, 
        "detections_today": total_detections,
        "unread_alerts": unread_alerts,
        "chart_data": chart_data
    }

@app.get("/api/surveillance/logs")
def get_recent_logs(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    recent_detections = db.query(models.Detection).join(models.Video)\
        .filter(models.Video.user_id == current_user.id)\
        .order_by(desc(models.Detection.detected_at)).limit(10).all()

    logs = []
    for d in recent_detections:
        logs.append({
            "time": d.detected_at.strftime("%H:%M:%S"),
            "source": d.video.filename,
            "threat": d.object_class,
            "confidence": f"{int(d.confidence * 100)}%"
        })
    return logs

# ==========================================
# FRONTEND HTML ROUTES (Must be at the bottom)
# ==========================================

@app.get("/")
def serve_home():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/{page_name}.html")
def serve_pages(page_name: str):
    file_path = os.path.join(frontend_path, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")

# --- Pydantic Schemas for Password Reset ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

# ==========================================
# EXTENDED AUTH ROUTES (Forgot/Reset)
# ==========================================

@app.post("/api/auth/forgot-password")
def forgot_password_endpoint(
    request: ForgotPasswordRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(database.get_db)
):
    # 1. Check if user exists
    user = crud.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered in GuardianAI.")

    # 2. Create OTP in database (using your existing crud logic)
    otp = crud.create_otp(db, request.email, purpose="password_reset")

    # 3. Send email in background (using your existing alert_manager)
    background_tasks.add_task(alert_manager.send_otp_email, request.email, otp, "password_reset")
    
    print(f"DEBUG: Reset OTP for {request.email} is {otp}") # Visible in terminal
    return {"status": "success", "message": "Reset OTP dispatched to email."}

@app.post("/api/auth/reset-password")
def reset_password_endpoint(request: ResetPasswordRequest, db: Session = Depends(database.get_db)):
    # 1. Verify OTP (using your existing crud logic)
    if not crud.verify_otp(db, request.email, request.otp_code, "password_reset"):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code.")

    # 2. Update the password (using your existing crud hashing)
    user = crud.get_user_by_email(db, request.email)
    hashed_pw = crud.pwd_context.hash(request.new_password)
    user.password_hash = hashed_pw
    db.commit()

    return {"status": "success", "message": "Password updated successfully."}

# ==========================================
# FRONTEND HTML ROUTES (Keep at the absolute bottom)
# ==========================================

@app.get("/")
def serve_home():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/{page_name}.html")
def serve_pages(page_name: str):
    file_path = os.path.join(frontend_path, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")
