#!/usr/bin/env bash
set -e
for f in telegram-init.js telegram-theme.js; do
    curl -sSI "https://bot.offonika.ru/$f" | \
      grep -q 'HTTP/1.1 200' && \
      grep -q 'Content-Type: application/javascript' || exit 1
done
echo 'OK'
