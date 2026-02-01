"""Camera capture utility for arm-mounted and table-view cameras."""

import base64
import cv2

from src.config import ARM_CAMERA_INDEX, TABLE_CAMERA_INDEX


def capture_frame(camera_index: int) -> bytes:
    """Capture a single frame from a camera and return it as JPEG bytes."""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera at index {camera_index}")
    try:
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame from camera {camera_index}")
        _, jpeg = cv2.imencode(".jpg", frame)
        return jpeg.tobytes()
    finally:
        cap.release()


def capture_arm_camera() -> bytes:
    """Capture a frame from the arm-mounted camera."""
    return capture_frame(ARM_CAMERA_INDEX)


def capture_table_camera() -> bytes:
    """Capture a frame from the table-view camera."""
    return capture_frame(TABLE_CAMERA_INDEX)


def capture_both() -> dict[str, bytes]:
    """Capture frames from both cameras."""
    return {
        "arm": capture_arm_camera(),
        "table": capture_table_camera(),
    }


def frame_to_base64(frame_bytes: bytes) -> str:
    """Convert JPEG bytes to a base64-encoded string."""
    return base64.b64encode(frame_bytes).decode("utf-8")
