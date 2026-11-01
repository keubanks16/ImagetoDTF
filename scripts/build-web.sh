#!/bin/sh
# Copies the web app into www/ for the iOS app. The live site still serves from the repo root.
set -e
rm -rf www
mkdir -p www
cp index.html logo.png icon.png www/
echo "www/ ready"
