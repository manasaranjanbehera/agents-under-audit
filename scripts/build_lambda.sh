#!/usr/bin/env bash
# Builds dist/comms-triage-lambda.zip for the Python 3.12 Lambda runtime.
# boto3 is provided by the runtime, so only pydantic and this package are bundled.
# Usage: scripts/build_lambda.sh [arm64|x86_64]   (arm64 is cheaper per GB-second)
set -euo pipefail

ARCH="${1:-arm64}"
case "$ARCH" in
  x86_64) PLATFORM="x86_64-manylinux2014" ;;
  arm64) PLATFORM="aarch64-manylinux2014" ;;
  *) echo "unknown architecture: $ARCH" >&2; exit 2 ;;
esac

cd "$(dirname "$0")/.."
BUILD=build/lambda
ZIP=dist/comms-triage-lambda.zip
PYDANTIC_VERSION="$(uv run --quiet python -c 'import pydantic; print(pydantic.VERSION)')"

rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD" dist

uv pip install --quiet \
  --target "$BUILD" \
  --python-version 3.12 \
  --python-platform "$PLATFORM" \
  --only-binary=:all: \
  "pydantic==$PYDANTIC_VERSION"

cp -R src/comms_triage "$BUILD/"
find "$BUILD" -name "__pycache__" -type d -prune -exec rm -rf {} +
(cd "$BUILD" && zip -qr "../../$ZIP" .)

echo "Built $ZIP ($ARCH, pydantic $PYDANTIC_VERSION)"
