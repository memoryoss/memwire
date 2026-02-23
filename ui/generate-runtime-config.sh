#!/bin/sh
# Inject runtime environment variables into the app at container startup.
# Replaces the __RUNTIME_CONFIG__ placeholder in index.html.

CONFIG_FILE=/usr/share/nginx/html/index.html

if [ -f "$CONFIG_FILE" ]; then
  sed -i "s|__VITE_API_URL__|${VITE_API_URL:-http://localhost:8000}|g" "$CONFIG_FILE"
fi
