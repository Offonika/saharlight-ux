#!/usr/bin/env bash
set -euo pipefail

# Replace SDK runtime imports to include explicit .ts extension.
find . -type f -name "*.ts*" -exec sed -i "s|from '@sdk/runtime'|from '@sdk/runtime.ts'|g" {} +

# Handle direct imports from libs/ts-sdk runtime regardless of path depth.
find . -type f -name "*.ts*" -exec sed -i -E 's|from "(.*/)?libs/ts-sdk/runtime"|from "\1libs/ts-sdk/runtime.ts"|g' {} +
