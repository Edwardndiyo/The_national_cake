# File: start.sh
#!/bin/bash
set -e  # stop on any error

pip install -r requirements.txt
alembic upgrade head          # <-- runs migration
python run.py                 # <-- your original command