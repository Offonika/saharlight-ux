#!/usr/bin/env bash
set -euo pipefail

# This script fixes SDK runtime imports by appending an explicit `.ts` extension.
# Run from the repository root with a clean working tree so that only files under
# `services/webapp/ui` and `libs/ts-sdk` are affected.

# Replace SDK runtime imports to include explicit .ts extension.
find services/webapp/ui libs/ts-sdk -type f -name "*.ts*" \
  -exec sed -i "s|from '@sdk/runtime'|from '@sdk/runtime.ts'|g" {} +

# Handle direct imports from libs/ts-sdk runtime regardless of path depth.
find services/webapp/ui libs/ts-sdk -type f -name "*.ts*" \
  -exec sed -i -E 's|from "(.*/)?libs/ts-sdk/runtime"|from "\1libs/ts-sdk/runtime.ts"|g' {} +
