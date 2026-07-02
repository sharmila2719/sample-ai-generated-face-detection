#!/usr/bin/env bash
# deploy_web_bundle.sh — Push web assets to S3 with cache-busting stamps
set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="ai-image-webui-${ACCOUNT}-${REGION}"
STAMP=$(date +%Y%m%d%H%M%S)

echo "==> Deploying web bundle to s3://${BUCKET}/ (stamp: ${STAMP})"

WEB_DIR="$(dirname "$0")/../web"

# Copy files with cache-busting stamp for JS/CSS
aws s3 sync "$WEB_DIR" "s3://${BUCKET}/" \
  --exclude "*.js" \
  --exclude "*.css" \
  --cache-control "max-age=86400" \
  --region "$REGION"

# JS/CSS: upload with stamp suffix and no-cache
for f in "$WEB_DIR"/*.js "$WEB_DIR"/*.css; do
  [ -f "$f" ] || continue
  fname=$(basename "$f")
  ext="${fname##*.}"
  base="${fname%.*}"
  stamped="${base}.${STAMP}.${ext}"
  aws s3 cp "$f" "s3://${BUCKET}/${stamped}" \
    --cache-control "max-age=31536000,immutable" \
    --region "$REGION"
  echo "  Uploaded: $stamped"
done

# Also upload originals (for direct reference)
for f in "$WEB_DIR"/*.js "$WEB_DIR"/*.css; do
  [ -f "$f" ] || continue
  fname=$(basename "$f")
  aws s3 cp "$f" "s3://${BUCKET}/${fname}" \
    --cache-control "no-cache,no-store" \
    --region "$REGION"
done

echo "==> Done."
