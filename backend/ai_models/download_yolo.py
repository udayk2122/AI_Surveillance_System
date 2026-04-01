from ultralytics import YOLO

print("Downloading YOLOv8n...")
# This line automatically connects to the internet and downloads the weights
model = YOLO("yolov8n.pt") 
print("Download complete! Check your folder for yolov8n.pt")



#commands:
# python -m venv venv
# .\venv\Scripts\activate
# pip install -r backend/requirements.txt
# uvicorn backend.main:app --reload