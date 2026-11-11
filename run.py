"""Punjab Air Quality System - Simple Startup Script."""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print(" Starting Punjab Air Quality Platform on http://127.0.0.1:9000")
    print(" Open http://127.0.0.1:9000 in your browser to view the dashboard.")
    print("=" * 60)
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=9000, reload=True)
