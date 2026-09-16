#!/bin/bash
set -e
cd "$(dirname "$0")/backend"
echo "Create your personal OMEN login. Choose a username and password."
.venv/bin/python manage.py createsuperuser
echo "Your login is ready. Open http://127.0.0.1:5173 while the app is running."
read -r -p "Press Enter to close."
