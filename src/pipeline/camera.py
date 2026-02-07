"""Camera capture utility for arm-mounted and table-view cameras.

Supports both one-shot captures and persistent streaming via CameraStream.
Also provides FolderImageSource for dry-run / testing without hardware.
"""

import base64
import glob
import hashlib
import logging
import os
import time

import cv2

from src.config import ARM_CAMERA_INDEX, TABLE_CAMERA_INDEX

log = logging.getLogger(__name__)


class CameraStream:
    """Persistent camera stream. Keeps the feed open and grabs frames on demand.

    Usage:
        stream = CameraStream(camera_index=0)
        stream.start()

        # Grab a frame whenever the arm is in position
        frame = stream.grab()

        # When done
        stream.stop()

    Or as a context manager:
        with CameraStream(0) as stream:
            frame = stream.grab()
    """

    def __init__(self, camera_index: int = ARM_CAMERA_INDEX):
        self.camera_index = camera_index
        self._cap = None

    def start(self) -> None:
        """Open the camera stream."""
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera at index {self.camera_index}")
        # Let the camera warm up and auto-expose
        time.sleep(0.5)

    def stop(self) -> None:
        """Release the camera."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def grab(self) -> bytes:
        """Grab a single frame from the live stream as JPEG bytes."""
        if not self.is_open():
            raise RuntimeError("Camera stream is not open. Call start() first.")
        # Flush stale frames from the buffer by grabbing a few
        for _ in range(3):
            self._cap.grab()
        ret, frame = self._cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame from camera {self.camera_index}")
        _, jpeg = cv2.imencode(".jpg", frame)
        return jpeg.tobytes()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# --- One-shot capture functions (kept for backward compatibility) ---

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


def frame_hash(frame_bytes: bytes) -> str:
    """Compute a quick hash of a frame for same-page detection."""
    return hashlib.md5(frame_bytes).hexdigest()


class FolderImageSource:
    """Image source that reads from a folder of images instead of a camera.

    Used for --dry-run mode to walk the orchestrator through a simulated
    book without hardware. Images are returned in sorted filename order.
    Once all images are exhausted, the last image is returned repeatedly.

    Implements the same interface as CameraStream (start/stop/grab/context manager).
    """

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self._files: list[str] = []
        self._index = 0

    def start(self) -> None:
        """Load image file list from the folder."""
        patterns = ["*.jpg", "*.jpeg", "*.png"]
        self._files = []
        for pat in patterns:
            self._files.extend(glob.glob(os.path.join(self.folder_path, pat)))
        self._files.sort()
        self._index = 0

        if not self._files:
            raise RuntimeError(f"No images found in {self.folder_path}")
        log.info("FolderImageSource: loaded %d images from %s",
                 len(self._files), self.folder_path)

    def stop(self) -> None:
        """No-op for folder source."""
        pass

    def is_open(self) -> bool:
        return len(self._files) > 0

    def grab(self) -> bytes:
        """Return the next image as JPEG bytes."""
        if not self._files:
            raise RuntimeError("FolderImageSource has no images. Call start() first.")

        # Clamp to last image if we've gone past the end
        idx = min(self._index, len(self._files) - 1)
        filepath = self._files[idx]
        self._index += 1

        log.info("FolderImageSource: serving image %d/%d: %s",
                 idx + 1, len(self._files), os.path.basename(filepath))

        with open(filepath, "rb") as f:
            return f.read()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
