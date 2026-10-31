
import cv2
from app.media import sample_frames

video_path = r"C:\Users\workb\OneDrive\Desktop\cat_video.mp4"

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
cap.release()

frames = list(sample_frames(video_path))

print(f"Video duration: {duration:.1f} seconds")
print(f"FPS: {fps:.1f}")
print(f"Frames extracted: {len(frames)}")

for index, frame in frames:
    print(f"Frame {index} at {index / fps:.1f} seconds")

from app.main import registry

model = registry.get()

for index, frame in frames:
    detections = model.predict(frame)
    print(f"Frame {index}: {detections}")