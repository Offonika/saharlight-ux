#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(dirname "$(dirname "$0")")"
SPEC="$ROOT_DIR/libs/contracts/openapi.yaml"
OUT_DIR="$ROOT_DIR/libs/ts-sdk"
TMP_DIR="$(mktemp -d)"

openapi-generator-cli generate \
  -i "$SPEC" \
  -g typescript-fetch \
  -o "$TMP_DIR" \
  --additional-properties=typescriptThreePlus=true,npmName=@offonika/diabetes-ts-sdk

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
cp -r "$TMP_DIR/src"/* "$OUT_DIR/"
cp -r "$TMP_DIR/.openapi-generator" "$OUT_DIR/"
cp "$TMP_DIR/.openapi-generator-ignore" "$OUT_DIR/.openapi-generator-ignore"
cat <<'JSON' > "$OUT_DIR/package.json"
{
  "name": "@offonika/diabetes-ts-sdk",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "index.ts",
  "types": "index.ts",
  "description": "TypeScript SDK for the Diabetes Assistant API",
  "license": "MIT"
}
JSON

( cd "$OUT_DIR" && { find apis models -type f | sort; echo index.ts; echo runtime.ts; } > .openapi-generator/FILES )

rm -rf "$TMP_DIR"

# Fix imports of SDK runtime to include the `.ts` extension in UI code.
# Vite's ESM resolver requires explicit extensions when the runtime is
# generated as a single `runtime.ts` file instead of a directory.
if [ ! -d "$ROOT_DIR/libs/ts-sdk/runtime" ] && [ -f "$ROOT_DIR/libs/ts-sdk/runtime.ts" ]; then
  find "$ROOT_DIR/services/webapp/ui/src" -type f -name "*.ts*" \
    -exec sed -i "s|from ['\"]@sdk/runtime['\"]|from '@sdk/runtime.ts'|g" {} +
fi
