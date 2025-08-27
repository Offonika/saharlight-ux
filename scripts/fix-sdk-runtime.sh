#!/usr/bin/env bash
set -euo pipefail

find . -type f -name "*.ts*" -exec sed -i "s|from '@sdk/runtime'|from '@sdk/runtime.ts'|g" {} +
find . -type f -name "*.ts*" -exec sed -i 's|from "../../../../libs/ts-sdk/runtime"|from "../../../../libs/ts-sdk/runtime.ts"|g' {} +
