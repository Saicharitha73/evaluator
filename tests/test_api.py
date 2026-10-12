import sys
import os
import io
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from main import app
from samples import create_sample_pair_1

def test_health():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    print("[PASS] Health endpoint OK:", data)

def test_samples():
    client = TestClient(app)
    res = client.get("/api/samples")
    assert res.status_code == 200
    data = res.json()
    assert "samples" in data
    assert len(data["samples"]) >= 2
    print("[PASS] Samples endpoint OK. Found", len(data["samples"]), "sample pairs.")

def test_compare_endpoint():
    client = TestClient(app)
    orig_b, gen_b = create_sample_pair_1()

    files = {
        "original_image": ("original.jpg", io.BytesIO(orig_b), "image/jpeg"),
        "generated_image": ("generated.jpg", io.BytesIO(gen_b), "image/jpeg")
    }
    data = {"mode": "balanced"}

    res = client.post("/api/compare", files=files, data=data)
    assert res.status_code == 200, res.text
    result = res.json()
    assert "matching_percentage" in result
    assert "grade" in result
    assert "breakdown" in result
    assert "visualizations" in result
    print("[PASS] Compare endpoint OK:")
    print("  Matching %:", result["matching_percentage"])
    print("  Grade:", result["grade"])
    print("  Breakdown items:", len(result["breakdown"]))
    print("  Visualizations:", list(result["visualizations"].keys()))

def test_root_frontend():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "MatchVision AI" in res.text or "<div id=\"root\">" in res.text
    print("[PASS] Root frontend serving OK")

if __name__ == "__main__":
    test_health()
    test_samples()
    test_compare_endpoint()
    test_root_frontend()
    print("\nAll integration tests passed successfully!")
