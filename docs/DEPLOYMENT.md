# Deployment Guide

## Prerequisites

- AWS CLI v2 configured with `us-east-1` as the default region
- Python 3.12+
- Node.js 18+ and npm
- AWS CDK v2: `npm install -g aws-cdk`
- AWS account with access to Bedrock, SageMaker, Rekognition, Lambda, API Gateway

## Step 1: Bootstrap CDK (one-time)

```bash
./scripts/deploy.sh bootstrap
```

## Step 2: Create the Bedrock Guardrail (one-time)

```bash
./scripts/create_guardrail.sh
```

Note the guardrail ID from the output.

## Step 3: Deploy the Stack

```bash
./scripts/deploy.sh deploy
```

The stack outputs:
- `ApiEndpoint` — API Gateway base URL
- `IntakeBucketName` — S3 bucket for image uploads
- `AlertsTopicArn` — SNS topic ARN
- `WebUiUrl` — CloudFront URL

## Step 4: Post-deploy Configuration

### 4a. Set the Bedrock Guardrail ID

```bash
GUARDRAIL_ID="<your-guardrail-id>"
for FN in ai-image-detection ai-image-s3-event; do
  aws lambda update-function-configuration \
    --function-name $FN \
    --environment Variables="{BEDROCK_GUARDRAIL_ID=$GUARDRAIL_ID}"
done
```

### 4b. Deploy SageMaker endpoints

```bash
# Pixel detector
aws sagemaker create-endpoint \
  --endpoint-name ai-image-detector \
  --endpoint-config-name <your-config>

# Composite specialist
aws sagemaker create-endpoint \
  --endpoint-name ai-composite-specialist \
  --endpoint-config-name <your-config>

# Face-forensics AIGC ensemble
aws sagemaker create-endpoint \
  --endpoint-name ai-aigc-ensemble \
  --endpoint-config-name <your-config>
```

### 4c. Create the Web UI password secret

```bash
aws secretsmanager create-secret \
  --name "sample-ai-generated-face-detection/web-ui-password" \
  --secret-string '{"users":{"admin":"<strong-password>"}}'
```

### 4d. Set the CORS allowed origin on the session-check Lambda

```bash
CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
  --stack-name AiImageDetectionPipeline \
  --query "Stacks[0].Outputs[?OutputKey=='WebUiUrl'].OutputValue" \
  --output text | sed 's|https://||; s|/||')

aws lambda update-function-configuration \
  --function-name ai-image-webui-session-check \
  --environment Variables="{WEB_UI_ALLOWED_ORIGIN=https://$CLOUDFRONT_DOMAIN}"
```

### 4e. Subscribe an email to the alerts topic

```bash
aws sns subscribe \
  --topic-arn <AlertsTopicArn> \
  --protocol email \
  --notification-endpoint your@email.com
```

## Step 5: Push web assets

```bash
./scripts/deploy_web_bundle.sh
```

## Step 6: API Gateway Timeout Quota (recommended)

The detection cascade can take 20–35 seconds. To avoid 504 errors:

```bash
aws service-quotas request-service-quota-increase \
  --service-code apigateway \
  --quota-code L-E5AE38E3 \
  --desired-value 120000 \
  --region us-east-1
```

## Smoke Tests

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name AiImageDetectionPipeline \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)

# Health check
curl "$API_URL/health"

# Upload URL
curl -X POST "$API_URL/api/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"content_type":"image/jpeg","filename":"test.jpg"}'
```

## Rollback

```bash
./scripts/deploy.sh destroy
```

Note: S3 buckets and DynamoDB tables have `RemovalPolicy.RETAIN` — they
survive a stack destroy. Delete them manually if needed.
