import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # ✅ must match nginx upstream
    print(f"🚀 Starting Flask app on port {port}")  # Debug line
    app.run(host="0.0.0.0", port=port)
