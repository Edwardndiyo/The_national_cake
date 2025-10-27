# from app import create_app

# app = create_app()

# if __name__ == "__main__":
#     app.run(debug=True)

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # ✅ must match nginx upstream
    app.run(host="0.0.0.0", port=port)
