#!/bin/bash
set -e

# Create required directories
mkdir -p services/api services/bot libs infra docs/ADR

# Add .gitkeep files for empty directories
: > services/bot/.gitkeep
: > libs/.gitkeep
: > infra/.gitkeep
: > docs/ADR/.gitkeep

# Move webapp into services
if [ -d webapp ]; then
    mv webapp services/webapp
fi

# Ensure webapp is accessible from api service for backward compatibility
# Remove any old link in services/api/app/webapp
if [ -L services/api/app/webapp ]; then
    rm services/api/app/webapp
fi
if [ ! -e services/api/webapp ] && [ -d services/webapp ]; then
    ln -s ../webapp services/api/webapp
fi
