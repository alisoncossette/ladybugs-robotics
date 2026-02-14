"""Ladybug Robotics — Perception API & Orchestrator Dashboard.

FastAPI backend that exposes the robot's perception pipeline as a web service.
Upload a book image and watch the robot's brain analyze it in real-time.

Deploy on Vultr VM:
    pip install -r web/requirements.txt
    uvicorn web.app:app --host 0.0.0.0 --port 8000
"""

import logging
import os
import sys
import time

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Add project root to path so we can import src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import setup_logging, ANTHROPIC_API_KEY
from src.skills.perception import assess_scene, read_left, read_right
from src.pipeline.page_reader import classify_page, read_page

setup_logging()
log = logging.getLogger(__name__)

app = FastAPI(
    title="Ladybug Robotics — Perception API",
    description="The robot's brain, running in the cloud.",
    version="1.0.0",
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path) as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health():
    return {"status": "ok", "api_key_set": bool(ANTHROPIC_API_KEY)}


@app.post("/api/assess")
async def api_assess_scene(file: UploadFile = File(...)):
    """Step 1: Assess the scene — is there a book? open? closed?"""
    image_bytes = await file.read()
    t0 = time.time()
    state = assess_scene(image_bytes)
    elapsed = time.time() - t0
    return {
        "step": "assess_scene",
        "result": state,
        "description": {
            "no_book": "No book detected on the workspace",
            "book_closed": "Book is present but closed — robot would execute open_book skill",
            "book_open": "Book is open and pages are visible — proceeding to classify",
            "book_done": "Book is open to last page or back cover — robot would execute close_book skill",
        }.get(state, state),
        "elapsed_ms": round(elapsed * 1000),
    }


@app.post("/api/classify")
async def api_classify_page(file: UploadFile = File(...)):
    """Step 2: Classify the page type."""
    image_bytes = await file.read()
    t0 = time.time()
    page_type = classify_page(image_bytes)
    elapsed = time.time() - t0

    skip_types = {"blank", "index"}
    should_read = page_type not in skip_types

    return {
        "step": "classify_page",
        "result": page_type,
        "should_read": should_read,
        "description": {
            "blank": "Blank page — robot skips this",
            "index": "Index/glossary — robot skips this",
            "cover": "Cover page — robot reads this",
            "title": "Title page — robot reads this",
            "toc": "Table of contents — robot reads this",
            "content": "Content page — robot reads this",
        }.get(page_type, page_type),
        "elapsed_ms": round(elapsed * 1000),
    }


@app.post("/api/read")
async def api_read_page(file: UploadFile = File(...)):
    """Step 3: Read the page content using Claude Vision."""
    image_bytes = await file.read()
    t0 = time.time()
    text = read_page(image_bytes, mode="verbose")
    elapsed = time.time() - t0
    return {
        "step": "read_page",
        "text": text,
        "word_count": len(text.split()),
        "elapsed_ms": round(elapsed * 1000),
    }


@app.post("/api/read-spread")
async def api_read_spread(file: UploadFile = File(...)):
    """Read left page then right page separately."""
    image_bytes = await file.read()

    t0 = time.time()
    left_text = read_left(image_bytes, silent=True, mode="verbose")
    t1 = time.time()
    right_text = read_right(image_bytes, silent=True, mode="verbose")
    t2 = time.time()

    return {
        "step": "read_spread",
        "left_page": {
            "text": left_text,
            "word_count": len(left_text.split()),
            "elapsed_ms": round((t1 - t0) * 1000),
        },
        "right_page": {
            "text": right_text,
            "word_count": len(right_text.split()),
            "elapsed_ms": round((t2 - t1) * 1000),
        },
        "total_elapsed_ms": round((t2 - t0) * 1000),
    }


@app.post("/api/analyze")
async def api_full_pipeline(file: UploadFile = File(...)):
    """Run the FULL autonomous pipeline on a single image.

    This is what the robot's brain does for every spread:
    1. Assess scene -> decide what to do
    2. Classify page -> decide whether to read or skip
    3. Read left page -> read right page
    4. Turn page (simulated)
    """
    image_bytes = await file.read()
    pipeline = []
    t_start = time.time()

    # Step 1: Assess scene
    t0 = time.time()
    scene_state = assess_scene(image_bytes)
    t1 = time.time()
    pipeline.append({
        "step": 1,
        "action": "assess_scene",
        "result": scene_state,
        "decision": {
            "no_book": "STOP — no book to read",
            "book_closed": "MOTOR: execute open_book skill",
            "book_open": "CONTINUE — proceed to classify page",
            "book_done": "MOTOR: execute close_book skill, DONE",
        }.get(scene_state),
        "elapsed_ms": round((t1 - t0) * 1000),
    })

    if scene_state != "book_open":
        return {
            "pipeline": pipeline,
            "total_elapsed_ms": round((time.time() - t_start) * 1000),
            "outcome": f"Scene is '{scene_state}' — robot would take motor action, not read.",
        }

    # Step 2: Classify page
    t0 = time.time()
    page_type = classify_page(image_bytes)
    t1 = time.time()
    skip_types = {"blank", "index"}
    should_read = page_type not in skip_types
    pipeline.append({
        "step": 2,
        "action": "classify_page",
        "result": page_type,
        "decision": "READ this page" if should_read else "SKIP this page",
        "elapsed_ms": round((t1 - t0) * 1000),
    })

    if not should_read:
        pipeline.append({
            "step": 3,
            "action": "turn_page",
            "result": "skipped",
            "decision": f"Page type '{page_type}' — skip and turn page",
            "elapsed_ms": 0,
        })
        return {
            "pipeline": pipeline,
            "total_elapsed_ms": round((time.time() - t_start) * 1000),
            "outcome": f"Page classified as '{page_type}' — skipped. Robot would turn page.",
        }

    # Step 3: Read left page
    t0 = time.time()
    left_text = read_left(image_bytes, silent=True, mode="verbose")
    t1 = time.time()
    pipeline.append({
        "step": 3,
        "action": "read_left_page",
        "result": left_text[:200] + ("..." if len(left_text) > 200 else ""),
        "word_count": len(left_text.split()),
        "elapsed_ms": round((t1 - t0) * 1000),
    })

    # Step 4: Read right page
    t0 = time.time()
    right_text = read_right(image_bytes, silent=True, mode="verbose")
    t1 = time.time()
    pipeline.append({
        "step": 4,
        "action": "read_right_page",
        "result": right_text[:200] + ("..." if len(right_text) > 200 else ""),
        "word_count": len(right_text.split()),
        "elapsed_ms": round((t1 - t0) * 1000),
    })

    # Step 5: Turn page (simulated)
    pipeline.append({
        "step": 5,
        "action": "turn_page",
        "result": "simulated",
        "decision": "MOTOR: execute turn_page skill, verify page changed, loop",
        "elapsed_ms": 0,
    })

    return {
        "pipeline": pipeline,
        "left_page_full": left_text,
        "right_page_full": right_text,
        "total_elapsed_ms": round((time.time() - t_start) * 1000),
        "outcome": f"Read {len(left_text.split()) + len(right_text.split())} words. Robot would turn page and continue.",
    }