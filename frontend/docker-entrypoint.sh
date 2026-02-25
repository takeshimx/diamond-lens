#!/bin/sh
# ランタイム環境変数でプレースホルダーを置換
if [ -n "$VITE_APP_PASSWORD" ]; then
  find /usr/share/nginx/html -name '*.js' -exec \
    sed -i "s/__VITE_APP_PASSWORD_PLACEHOLDER__/$VITE_APP_PASSWORD/g" {} +
fi

exec nginx -g 'daemon off;'