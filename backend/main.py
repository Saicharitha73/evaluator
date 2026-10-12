import os
import base64
import time
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

from matcher import evaluate_image_match
from samples import create_sample_pair_1, create_sample_pair_2

app = FastAPI(
    title="Image Fidelity & Generation Match Engine API",
    description="Production-ready multi-metric image comparison engine for original vs generated images",
    version="1.0.0"
)

# Enable CORS for local dev and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff", "image/gif", "application/octet-stream"
}

@app.get("/api/health")
async def health_check():
    import torch
    return {
        "status": "healthy",
        "service": "Image Match Engine",
        "timestamp": time.time(),
        "gpu_available": torch.cuda.is_available(),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    }

@app.get("/api/samples")
async def get_sample_pairs():
    """Provides bundled demo pairs for instant 1-click evaluation."""
    p1_orig, p1_gen = create_sample_pair_1()
    p2_orig, p2_gen = create_sample_pair_2()

    def to_data_uri(b_bytes):
        return f"data:image/jpeg;base64,{base64.b64encode(b_bytes).decode('utf-8')}"

    return {
        "samples": [
            {
                "id": "cyberpunk_city",
                "title": "Neon City vs AI Stylized Variant",
                "category": "Style Transfer & Lighting",
                "original_data_uri": to_data_uri(p1_orig),
                "generated_data_uri": to_data_uri(p1_gen)
            },
            {
                "id": "nature_emblem",
                "title": "Geometric Emblem vs High-Res Diffusion",
                "category": "High Fidelity Reproduction",
                "original_data_uri": to_data_uri(p2_orig),
                "generated_data_uri": to_data_uri(p2_gen)
            }
        ]
    }

@app.post("/api/compare")
async def compare_images(
    original_image: UploadFile = File(..., description="Original reference image"),
    generated_image: UploadFile = File(..., description="Generated image to compare"),
    mode: Optional[str] = Form("balanced", description="Comparison mode: balanced, strict_pixel, or semantic_creative")
):
    """
    Evaluates similarity and matching percentage between an original image and a generated image.
    """
    start_time = time.time()

    # Validate filenames and content types
    for label, upload in [("Original image", original_image), ("Generated image", generated_image)]:
        ext = os.path.splitext(upload.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS and upload.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label} has unsupported format '{ext}'. Allowed: JPEG, PNG, WEBP, BMP."
            )

    try:
        orig_bytes = await original_image.read()
        gen_bytes = await generated_image.read()

        if len(orig_bytes) == 0:
            raise HTTPException(status_code=400, detail="Original image file is empty.")
        if len(gen_bytes) == 0:
            raise HTTPException(status_code=400, detail="Generated image file is empty.")

        if len(orig_bytes) > MAX_FILE_SIZE or len(gen_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB."
            )

        # Run comparison engine
        result = evaluate_image_match(orig_bytes, gen_bytes, mode=mode or "balanced")
        result["execution_time_seconds"] = round(time.time() - start_time, 3)

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating image similarity: {str(e)}"
        )

# Serve built frontend if static dist folder exists
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
