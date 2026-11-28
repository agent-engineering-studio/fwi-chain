#!/bin/sh
# Copy Bootstrap Italia (CSS and fonts) into static/vendor: the page needs no CDN.
set -eu
cd "$(dirname "$0")"
npm install --no-audit --no-fund --silent
rm -rf static/vendor/bootstrap-italia
mkdir -p static/vendor/bootstrap-italia
cp -R node_modules/bootstrap-italia/dist/css node_modules/bootstrap-italia/dist/fonts static/vendor/bootstrap-italia/
echo "static/vendor/bootstrap-italia ready"
