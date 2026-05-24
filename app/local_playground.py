from __future__ import annotations

def main() -> None:
    print("This legacy local app has been replaced by the split frontend/backend setup.")
    print("Run the API with: uv run uvicorn backend.main:app --reload --port 8000")
    print("Run the frontend with: cd frontend && npm install && npm run dev")


if __name__ == "__main__":
    main()
