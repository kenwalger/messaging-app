#!/bin/bash
# Build script for Heroku deployment
# Builds frontend and ensures dist/ directory exists

set -e

echo "Building frontend..."
cd src/ui
npm install
npm run build
cd ../..

echo "Frontend build complete!"
echo "Dist directory: src/ui/dist/"
