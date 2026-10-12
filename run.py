import sys
import os
import webbrowser
import uvicorn

# Ensure backend directory is in python path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def main():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    url = f"http://{host}:{port}"

    print("=" * 65)
    print("  MatchVision AI - Production Image Matching Engine")
    print("=" * 65)
    print(f"  Web Application & API URL : {url}")
    print(f"  Interactive API Docs      : {url}/docs")
    print("=" * 65)

    uvicorn.run("main:app", host=host, port=port, reload=False, app_dir=backend_dir)

if __name__ == "__main__":
    main()
