#!/usr/bin/env bash
# deploy.sh — CDK bootstrap / deploy wrapper
set -euo pipefail

COMMAND="${1:-deploy}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo "==> Account: $ACCOUNT | Region: $REGION | Command: $COMMAND"

cd "$(dirname "$0")/../infrastructure"

case "$COMMAND" in
  bootstrap)
    cdk bootstrap "aws://$ACCOUNT/$REGION"
    ;;
  deploy)
    cdk deploy AiImageDetectionPipeline \
      --require-approval never \
      --context account="$ACCOUNT" \
      --context region="$REGION"
    ;;
  destroy)
    cdk destroy AiImageDetectionPipeline \
      --force \
      --context account="$ACCOUNT" \
      --context region="$REGION"
    ;;
  synth)
    cdk synth \
      --context account="$ACCOUNT" \
      --context region="$REGION"
    ;;
  *)
    echo "Usage: deploy.sh [bootstrap|deploy|destroy|synth]"
    exit 1
    ;;
esac
