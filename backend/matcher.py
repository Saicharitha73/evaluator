import io
import base64
import numpy as np
import cv2
from PIL import Image, ImageOps
try:
    import torch
    import torchvision.transforms as transforms
    import torchvision.models as models
    HAS_TORCH = True
except ImportError:
    torch = None
    transforms = None
    models = None
    HAS_TORCH = False

# Initialize optional deep feature extractor
_deep_model = None
_deep_transform = None

def get_deep_feature_extractor():
    global _deep_model, _deep_transform
    if not HAS_TORCH:
        return None
    if _deep_model is None:
        try:
            # Using lightweight MobileNetV2 for fast inference
            weights = models.MobileNet_V2_Weights.DEFAULT
            model = models.mobilenet_v2(weights=weights)
            model.classifier = torch.nn.Identity()  # Extract 1280-dim feature vector
            model.eval()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            _deep_model = (model, device)
            _deep_transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        except Exception as e:
            print(f"[Warning] Deep feature extractor initialization fallback: {e}")
            _deep_model = False
    return _deep_model if _deep_model is not False else None


def load_image_bytes(image_bytes: bytes) -> Image.Image:
    """Load image from bytes with correct EXIF orientation handling."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def image_to_base64_jpeg(cv2_bgr_img: np.ndarray, quality: int = 85) -> str:
    """Convert OpenCV BGR image to base64 JPEG string."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode(".jpg", cv2_bgr_img, encode_param)
    if not success:
        return ""
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


def calculate_ssim(img1_gray: np.ndarray, img2_gray: np.ndarray):
    """
    Compute Structural Similarity Index (SSIM) between two grayscale images of identical size.
    Returns: ssim_score (0.0 to 1.0) and diff_map (0 to 255)
    """
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    img1 = img1_gray.astype(np.float64)
    img2 = img2_gray.astype(np.float64)

    kernel = cv2.getGaussianKernel(11, 1.5)
    window = np.outer(kernel, kernel.transpose())

    mu1 = cv2.filter2D(img1, -1, window)[5:-5, 5:-5]
    mu2 = cv2.filter2D(img2, -1, window)[5:-5, 5:-5]

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.filter2D(img1 ** 2, -1, window)[5:-5, 5:-5] - mu1_sq
    sigma2_sq = cv2.filter2D(img2 ** 2, -1, window)[5:-5, 5:-5] - mu2_sq
    sigma12 = cv2.filter2D(img1 * img2, -1, window)[5:-5, 5:-5] - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    score = float(np.mean(ssim_map))
    # Normalize score bounded to [0, 1]
    score = max(0.0, min(1.0, (score + 1.0) / 2.0 if score < 0 else score))

    # Difference map
    diff = cv2.absdiff(img1_gray, img2_gray)
    return score, diff


def calculate_color_histogram_similarity(img1_bgr: np.ndarray, img2_bgr: np.ndarray) -> float:
    """
    Compute color distribution similarity in HSV space using Histogram Correlation.
    """
    hsv1 = cv2.cvtColor(img1_bgr, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2_bgr, cv2.COLOR_BGR2HSV)

    # 3D HSV histogram: 30 bins for H, 32 for S, 32 for V
    hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [30, 32, 32], [0, 180, 0, 256, 0, 256])
    hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [30, 32, 32], [0, 180, 0, 256, 0, 256])

    cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    corr = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    corr = max(0.0, min(1.0, float(corr)))
    return corr


def calculate_orb_keypoint_match(img1_gray: np.ndarray, img2_gray: np.ndarray, img1_bgr: np.ndarray, img2_bgr: np.ndarray):
    """
    Detect local features with ORB, match using Lowe's ratio test and RANSAC homography.
    Returns: match_ratio (0.0 to 1.0) and visualization image.
    """
    orb = cv2.ORB_create(nfeatures=1500, fastThreshold=10)
    kp1, des1 = orb.detectAndCompute(img1_gray, None)
    kp2, des2 = orb.detectAndCompute(img2_gray, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        # Create empty side by side
        vis = np.hstack([img1_bgr, img2_bgr])
        return 0.0, vis, 0, 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(des1, des2, k=2)

    # Apply Lowe's ratio test
    good_matches = []
    for m_pair in matches:
        if len(m_pair) == 2:
            m, n = m_pair
            if m.distance < 0.80 * n.distance:
                good_matches.append(m)

    inliers_count = 0
    if len(good_matches) >= 4:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        try:
            _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if mask is not None:
                inliers_count = int(np.sum(mask))
        except Exception:
            inliers_count = len(good_matches)
    else:
        inliers_count = len(good_matches)

    # Keypoint match ratio calculation
    min_kp = min(len(kp1), len(kp2))
    ratio = inliers_count / max(1, min_kp)
    # Smooth score scaling: 100+ confident inliers represents very strong structural alignment
    scaled_score = min(1.0, ratio * 2.2 if ratio > 0.05 else ratio * 1.5)

    # Draw top matches visualization
    top_matches = sorted(good_matches, key=lambda x: x.distance)[:40]
    vis_matches = cv2.drawMatches(
        img1_bgr, kp1,
        img2_bgr, kp2,
        top_matches,
        None,
        matchColor=(0, 255, 128),
        singlePointColor=(60, 60, 255),
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    )

    return float(scaled_score), vis_matches, inliers_count, min_kp


def calculate_phash_similarity(img1_gray: np.ndarray, img2_gray: np.ndarray) -> float:
    """
    Calculate perceptual hash (DCT pHash) similarity.
    """
    def get_phash(img):
        resized = cv2.resize(img, (32, 32), interpolation=cv2.INTER_AREA)
        dct = cv2.dct(np.float32(resized))
        dct_low = dct[:8, :8]
        avg = np.mean(dct_low[1:])  # Ignore DC component
        hash_bits = (dct_low > avg).flatten()
        return hash_bits

    h1 = get_phash(img1_gray)
    h2 = get_phash(img2_gray)
    hamming_dist = np.count_nonzero(h1 != h2)
    similarity = 1.0 - (hamming_dist / 64.0)
    return max(0.0, min(1.0, float(similarity)))


def calculate_edge_similarity(img1_gray: np.ndarray, img2_gray: np.ndarray) -> float:
    """
    Calculate high-frequency edge and silhouette alignment.
    """
    edges1 = cv2.Canny(img1_gray, 80, 180)
    edges2 = cv2.Canny(img2_gray, 80, 180)

    # Dilate edges slightly to tolerate small generation variance
    kernel = np.ones((3, 3), np.uint8)
    edges1_dilated = cv2.dilate(edges1, kernel, iterations=1)
    edges2_dilated = cv2.dilate(edges2, kernel, iterations=1)

    intersection = np.logical_and(edges1_dilated > 0, edges2_dilated > 0)
    union = np.logical_or(edges1_dilated > 0, edges2_dilated > 0)
    union_sum = np.sum(union)
    if union_sum == 0:
        return 1.0
    jaccard = np.sum(intersection) / union_sum
    # Soft scaling for generated images where edges shift slightly
    score = min(1.0, jaccard * 1.8)
    return float(score)


def calculate_deep_semantic_similarity(pil_img1: Image.Image, pil_img2: Image.Image) -> float | None:
    """
    Compute deep feature cosine similarity using pretrained neural network.
    """
    extractor = get_deep_feature_extractor()
    if not extractor:
        return None
    model, device = extractor
    try:
        t1 = _deep_transform(pil_img1).unsqueeze(0).to(device)
        t2 = _deep_transform(pil_img2).unsqueeze(0).to(device)
        with torch.no_grad():
            f1 = model(t1).flatten(1)
            f2 = model(t2).flatten(1)
            cos_sim = torch.nn.functional.cosine_similarity(f1, f2, dim=1).item()
        # Cosine similarity typically ranges from ~0.2 to 1.0 for image features
        # Normalize to 0.0 - 1.0
        normalized = max(0.0, min(1.0, (cos_sim - 0.25) / 0.75))
        return float(normalized)
    except Exception as e:
        print(f"[Warning] Deep semantic similarity error: {e}")
        return None


def generate_heatmap_overlay(img_orig_bgr: np.ndarray, diff_gray: np.ndarray) -> np.ndarray:
    """
    Create a glowing difference heatmap overlaid on original image.
    """
    # Normalize diff to 0-255
    norm_diff = cv2.normalize(diff_gray, None, 0, 255, cv2.NORM_MINMAX)
    # Apply JET colormap for high contrast diff areas
    heatmap = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)
    # Blend with original
    blended = cv2.addWeighted(img_orig_bgr, 0.45, heatmap, 0.55, 0)
    return blended


def evaluate_image_match(orig_bytes: bytes, gen_bytes: bytes, mode: str = "balanced") -> dict:
    """
    Comprehensive multi-metric image comparison engine.
    """
    pil_orig = load_image_bytes(orig_bytes)
    pil_gen = load_image_bytes(gen_bytes)

    orig_meta = {
        "width": pil_orig.width,
        "height": pil_orig.height,
        "aspect_ratio": round(pil_orig.width / max(1, pil_orig.height), 2),
        "size_kb": round(len(orig_bytes) / 1024, 1),
        "mode": pil_orig.mode
    }
    gen_meta = {
        "width": pil_gen.width,
        "height": pil_gen.height,
        "aspect_ratio": round(pil_gen.width / max(1, pil_gen.height), 2),
        "size_kb": round(len(gen_bytes) / 1024, 1),
        "mode": pil_gen.mode
    }

    # Standardize image dimensions for evaluation (e.g. 512x512)
    EVAL_DIM = (512, 512)
    pil_orig_eval = pil_orig.resize(EVAL_DIM, Image.Resampling.LANCZOS)
    pil_gen_eval = pil_gen.resize(EVAL_DIM, Image.Resampling.LANCZOS)

    # Convert to OpenCV format (BGR & Gray)
    cv_orig_bgr = cv2.cvtColor(np.array(pil_orig_eval), cv2.COLOR_RGB2BGR)
    cv_gen_bgr = cv2.cvtColor(np.array(pil_gen_eval), cv2.COLOR_RGB2BGR)

    cv_orig_gray = cv2.cvtColor(cv_orig_bgr, cv2.COLOR_BGR2GRAY)
    cv_gen_gray = cv2.cvtColor(cv_gen_bgr, cv2.COLOR_BGR2GRAY)

    # Check if images are exact duplicates
    is_identical = (orig_bytes == gen_bytes) or np.array_equal(np.array(pil_orig_eval), np.array(pil_gen_eval))
    if is_identical:
        ssim_score = 1.0
        orb_score = 1.0
        color_score = 1.0
        edge_score = 1.0
        phash_score = 1.0
        deep_score = 1.0 if deep_score is not None else None
        inliers = 100
        total_kp = 100
        diff_map = np.zeros((512, 512), dtype=np.uint8)
        orb_vis = np.hstack([cv_orig_bgr, cv_gen_bgr])
    else:
        # 1. Structural Similarity (SSIM)
        ssim_score, diff_map = calculate_ssim(cv_orig_gray, cv_gen_gray)

        # 2. Keypoints & Landmarks (ORB + RANSAC)
        orb_score, orb_vis, inliers, total_kp = calculate_orb_keypoint_match(
            cv_orig_gray, cv_gen_gray, cv_orig_bgr, cv_gen_bgr
        )

        # 3. Color & Palette Distribution (HSV Histogram)
        color_score = calculate_color_histogram_similarity(cv_orig_bgr, cv_gen_bgr)

        # 4. Perceptual Hash (Frequency Domain)
        phash_score = calculate_phash_similarity(cv_orig_gray, cv_gen_gray)

        # 5. Edge / Silhouette Coherence
        edge_score = calculate_edge_similarity(cv_orig_gray, cv_gen_gray)

        # 6. Deep Semantic Cosine Similarity
        deep_score = calculate_deep_semantic_similarity(pil_orig_eval, pil_gen_eval)

    # Visualizations
    heatmap_bgr = generate_heatmap_overlay(cv_orig_bgr, diff_map)
    heatmap_b64 = image_to_base64_jpeg(heatmap_bgr, quality=80)
    keypoint_vis_b64 = image_to_base64_jpeg(orb_vis, quality=80)

    # Metric weights depending on comparison mode & deep feature availability
    if deep_score is not None:
        if mode == "strict_pixel":
            weights = {"ssim": 0.35, "edge": 0.20, "color": 0.20, "orb": 0.15, "deep": 0.10}
        elif mode == "semantic_creative":
            weights = {"deep": 0.40, "color": 0.25, "phash": 0.15, "orb": 0.10, "ssim": 0.10}
        else:  # balanced
            weights = {"deep": 0.30, "ssim": 0.25, "orb": 0.20, "color": 0.15, "edge": 0.10}

        composite_val = sum([
            weights.get("deep", 0) * deep_score,
            weights.get("ssim", 0) * ssim_score,
            weights.get("orb", 0) * orb_score,
            weights.get("color", 0) * color_score,
            weights.get("edge", 0) * edge_score,
            weights.get("phash", 0) * phash_score,
        ])
    else:
        if mode == "strict_pixel":
            weights = {"ssim": 0.40, "edge": 0.25, "color": 0.20, "orb": 0.15}
        elif mode == "semantic_creative":
            weights = {"phash": 0.35, "color": 0.30, "orb": 0.20, "ssim": 0.15}
        else:  # balanced
            weights = {"ssim": 0.35, "orb": 0.25, "color": 0.20, "edge": 0.10, "phash": 0.10}

        composite_val = sum([
            weights.get("ssim", 0) * ssim_score,
            weights.get("orb", 0) * orb_score,
            weights.get("color", 0) * color_score,
            weights.get("edge", 0) * edge_score,
            weights.get("phash", 0) * phash_score,
        ])

    overall_percentage = round(composite_val * 100, 1)
    overall_percentage = max(0.0, min(100.0, overall_percentage))

    # Determine Verdict Classification & Analysis
    if overall_percentage >= 88.0:
        grade = "High Fidelity Match"
        status_color = "#10B981"  # Emerald
        verdict = "The generated image demonstrates exceptional fidelity to the original. Structural landmarks, fine edge geometries, and color palette distributions are strongly preserved with minimal deviation."
    elif overall_percentage >= 72.0:
        grade = "Strong Stylistic / Content Match"
        status_color = "#3B82F6"  # Blue
        verdict = "The generated image closely follows the core subject, layout, and composition of the original, with slight creative variations in fine textures, lighting nuances, or rendering style."
    elif overall_percentage >= 55.0:
        grade = "Moderate Variation"
        status_color = "#F59E0B"  # Amber
        verdict = "Key subject matter and color tones show identifiable correspondence, but significant architectural or textural shifts are present between the original and generated output."
    elif overall_percentage >= 35.0:
        grade = "Low / Loose Inspiration"
        status_color = "#EC4899"  # Pink / Magenta
        verdict = "Weak correspondence detected. The images share scattered palette or abstract layout cues, but structural shapes and feature points diverge heavily."
    else:
        grade = "Divergent / Non-Matching"
        status_color = "#EF4444"  # Red
        verdict = "Substantial divergence across all metrics. The generated image does not meaningfully match the original's structure, color, or key features."

    # Breakdown item list
    metrics_breakdown = [
        {
            "name": "Structural Coherence (SSIM)",
            "key": "ssim",
            "score": round(ssim_score * 100, 1),
            "description": "Perceptual luminance, contrast, and spatial structure preservation.",
            "impact": "High"
        },
        {
            "name": "Feature Correspondence (ORB)",
            "key": "features",
            "score": round(orb_score * 100, 1),
            "description": f"Identified {inliers} robust geometric landmark matches out of {total_kp} keypoints.",
            "impact": "High"
        },
        {
            "name": "Color & Palette Harmony",
            "key": "color",
            "score": round(color_score * 100, 1),
            "description": "3D HSV color space distribution and lighting tone correlation.",
            "impact": "Medium"
        },
        {
            "name": "Edge & Contour Alignment",
            "key": "edge",
            "score": round(edge_score * 100, 1),
            "description": "High-frequency silhouette and boundary overlap fidelity.",
            "impact": "Medium"
        },
        {
            "name": "Frequency Layout (pHash)",
            "key": "phash",
            "score": round(phash_score * 100, 1),
            "description": "Discrete Cosine Transform (DCT) low-frequency spatial layout similarity.",
            "impact": "Medium"
        }
    ]

    if deep_score is not None:
        metrics_breakdown.insert(0, {
            "name": "Deep Perceptual Semantic",
            "key": "deep",
            "score": round(deep_score * 100, 1),
            "description": "Neural feature embedding similarity evaluating conceptual scene consistency.",
            "impact": "Crucial"
        })

    return {
        "matching_percentage": overall_percentage,
        "grade": grade,
        "status_color": status_color,
        "verdict": verdict,
        "mode": mode,
        "metadata": {
            "original": orig_meta,
            "generated": gen_meta
        },
        "breakdown": metrics_breakdown,
        "visualizations": {
            "heatmap": heatmap_b64,
            "keypoints": keypoint_vis_b64
        }
    }
