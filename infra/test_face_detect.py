import os
import subprocess
import cv2

def test_face_detection_on_video(video_path: str):
    print(f"Testing face detection on {video_path}...")
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        return

    # Extract 2 frames at 3s and 8s
    tmp_frames = ["/tmp/frame_1.jpg", "/tmp/frame_2.jpg"]
    timestamps = [3.0, 8.0]
    for t, out_f in zip(timestamps, tmp_frames):
        cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-vframes", "1", "-q:v", "2", out_f]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    detected_faces = []
    for out_f in tmp_frames:
        if not os.path.exists(out_f):
            continue
        img = cv2.imread(out_f)
        if img is None:
            continue
        h_img, w_img = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        print(f"Frame {out_f} ({w_img}x{h_img}): Found {len(faces)} faces: {faces}")
        for (x, y, w, h) in faces:
            detected_faces.append((x, y, w, h, w_img, h_img))

    if not detected_faces:
        print("No faces detected in sampled frames.")
        return

    # Filter for webcam candidate regions (avoiding center gameplay area)
    # Gameplay center is roughly x in [0.35*W, 0.65*W] and y in [0.35*H, 0.75*H]
    webcam_faces = []
    for (x, y, w, h, W, H) in detected_faces:
        cx = x + w / 2
        cy = y + h / 2
        is_center_gameplay = (0.35 * W < cx < 0.65 * W) and (0.35 * H < cy < 0.75 * H)
        region = "unknown"
        if cx < 0.45 * W:
            region = "top_left" if cy < 0.45 * H else ("middle_left" if cy < 0.75 * H else "bottom_left")
        elif cx > 0.55 * W:
            region = "top_right" if cy < 0.45 * H else ("middle_right" if cy < 0.75 * H else "bottom_right")
        elif cy < 0.40 * H:
            region = "top_center"

        print(f"Face at ({x}, {y}, {w}, {h}) -> center=({cx:.1f}, {cy:.1f}), region={region}, is_center={is_center_gameplay}")
        if not is_center_gameplay:
            webcam_faces.append((x, y, w, h, W, H, region))

    print(f"\nFinal Identified Webcam Faces: {len(webcam_faces)}")
    if webcam_faces:
        fx, fy, fw, fh, W, H, region = webcam_faces[0]
        crop_w = min(W, max(int(fw * 3.0), 540))
        crop_h = min(H, int(crop_w / 1.421))
        crop_x = max(0, min(W - crop_w, int(fx + fw / 2 - crop_w / 2)))
        crop_y = max(0, min(H - crop_h, int(fy + fh / 2 - crop_h / 2.2)))
        print(f"Calculated Smart Crop Filter: crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:760 (Region: {region})")

if __name__ == "__main__":
    import glob
    captures = glob.glob("/scratch/captures/*.mp4")
    if captures:
        test_face_detection_on_video(captures[0])
    else:
        print("No captures found in /scratch/captures")
