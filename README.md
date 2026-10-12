# MatchVision AI - Image Evaluation & Match Engine

A multi-modal image evaluation and fidelity analysis engine that quantifies the structural, semantic, and perceptual match between original and AI-generated images.

---

## 🌟 Key Features

- **Multi-Modal Similarity Analysis**:
  - **Deep Perceptual Semantics**: High-level feature embedding extraction via MobileNetV2 (Cosine Similarity) with GPU/CUDA acceleration.
  - **Structural Coherence**: Gaussian Structural Similarity Index Measure (SSIM) capturing luminance and contrast degradation.
  - **Feature Correspondence**: ORB keypoint detection paired with RANSAC homography estimation to measure geometric landmark inliers.
  - **Color & Palette Harmony**: 3D HSV histogram correlation assessing chromatic fidelity and tone mapping.
  - **Edge & Contour Alignment**: Sobel/Canny edge gradient dice coefficient quantifying silhouette coherence.
  - **Frequency Domain Layout**: 2D Discrete Cosine Transform (pHash) measuring global spatial frequencies.
- **Visual Diagnostics**:
  - Difference heatmap overlays pinpointing exact localized deviation.
  - Keypoint inlier match vectors illustrating feature correspondences.
- **Evaluation Modes**:
  - `balanced`: Balanced weighting across deep semantic, structural, and color traits.
  - `strict_pixel`: Emphasizes pixel-exact SSIM, contours, and geometry.
  - `semantic_creative`: Tolerates stylistic shifts while prioritizing deep concept preservation.
- **Modern Web Application**: Responsive frontend built with React, Vite, and Lucide icons, served through FastAPI.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Python backend dependencies
pip install fastapi uvicorn pillow numpy opencv-python torch torchvision requests

# Frontend dependencies (optional if building dist)
cd frontend
npm install
npm run build
cd ..
```

### 2. Run the Application
```bash
python run.py
```
- Open your browser at: `http://127.0.0.1:8000`
- Interactive Swagger API docs: `http://127.0.0.1:8000/docs`

### 3. Run Automated Tests
```bash
python tests/test_api.py
```

---

## 📡 API Endpoints

- `GET /api/health`: System health and GPU/CUDA device status.
- `GET /api/samples`: Pre-generated sample image comparison pairs.
- `POST /api/compare`: Evaluate and score `original_image` vs `generated_image` with custom comparison modes.
