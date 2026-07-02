#!/usr/bin/env bash
# create_guardrail.sh — Create the Bedrock guardrail for vision model invocations
set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-eu-west-1}"

echo "==> Creating Bedrock guardrail in $REGION"

GUARDRAIL_ID=$(aws bedrock create-guardrail \
  --name "ai-image-detection-guardrail" \
  --description "Guardrail for AI image detection vision model calls" \
  --content-policy-config '{"filtersConfig":[{"type":"HATE","inputStrength":"HIGH","outputStrength":"HIGH"},{"type":"VIOLENCE","inputStrength":"MEDIUM","outputStrength":"MEDIUM"}]}' \
  --sensitive-information-policy-config '{"piiEntitiesConfig":[{"type":"NAME","action":"ANONYMIZE"},{"type":"EMAIL","action":"BLOCK"}]}' \
  --region "$REGION" \
  --query "guardrailId" \
  --output text)

echo "==> Guardrail created: $GUARDRAIL_ID"
echo ""
echo "Next: update the Lambda environment variables:"
echo "  aws lambda update-function-configuration \\"
echo "    --function-name ai-image-detection \\"
echo "    --environment Variables={BEDROCK_GUARDRAIL_ID=$GUARDRAIL_ID,...}"
