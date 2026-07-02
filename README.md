# sample-ai-generated-face-detection — AI Image Detection Pipeline

> **Sample / reference implementation** based on the AWS Samples repository.  
> Not intended for production use without additional security hardening.

A serverless AWS pipeline that determines whether an uploaded image is:
- A **real photo**
- An **AI-generated image**
- A **real photo with AI-generated elements** (e.g. face-swap)

## Architecture

![Architecture Diagram](docs/diagrams/architecture.png)

## Detection Cascade

The pipeline runs a multi-stage forensic cascade:

1. **Rekognition Celebrity Recognition** — always runs first
2. **EXIF Inspection** — cheap fast-path for recent phone photos
3. **SageMaker Pixel Detector** — CNN-based pixel-level AI detection
4. **Claude Haiku 4.5** — first-pass vision (parallel with Sonnet on UI uploads)
5. **Claude Sonnet 4.6** — second opinion (parallel with Haiku on deep analysis)
6. **Claude Opus 4.7** — tiebreaker when Haiku + Sonnet disagree
7. **Face Forensics Check** — Rekognition DetectFaces + AIGC SageMaker endpoint
8. **Phase B Composite Cascade** — per-region Rekognition + Haiku crop analysis
9. **Phase C Specialist** — SageMaker specialist on highest-risk crops
10. **Combine Evidence** — persists to DynamoDB, returns final verdict

## Project Structure

```
.
├── src/                        # Detection library
│   ├── config.py
│   ├── exceptions.py
│   ├── logger.py
│   ├── utils.py
│   ├── aws_clients.py
│   ├── exif.py
│   ├── alerts.py
│   ├── rate_limit.py
│   ├── provenance.py
│   ├── storage.py
│   ├── detection.py
│   └── agent/
│       ├── inline_orchestrator.py
│       ├── pipeline.py
│       ├── runtime_client.py
│       ├── cache.py
│       └── tools/
├── lambda_handlers/            # AWS Lambda entry points
├── infrastructure/             # AWS CDK stack
│   ├── app.py
│   ├── stacks/pipeline_stack.py
│   └── edge/basic_auth.py
├── web/                        # Static web UI
├── docs/                       # Architecture & deployment docs
│   └── diagrams/
├── tests/                      # Unit, property, integration tests
└── scripts/                    # Deploy helpers
```

## Quick Start

### Prerequisites
- AWS CLI configured (`us-east-1`)
- Python 3.12+
- Node.js (for CDK)
- AWS CDK v2: `npm install -g aws-cdk`

### Deploy

```bash
# 1. Bootstrap CDK (one-time)
./scripts/deploy.sh bootstrap

# 2. Create Bedrock guardrail (one-time)
./scripts/create_guardrail.sh

# 3. Deploy the stack
./scripts/deploy.sh deploy

# 4. Push web UI assets
./scripts/deploy_web_bundle.sh
```

### API Usage

```bash
# Health check
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/health

# Detect a single image
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/api/detect \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-1" \
  -d '{"s3_bucket": "ai-images-to-analyze-<account>-us-east-1", "s3_key": "photo.jpg", "deep_analysis": true}'
```

## Verdict Types

| Verdict | Trigger |
|---|---|
| Real photo | NATURAL, probability ≤ 0.15 |
| Real photo with AI elements | NATURAL, probability > 0.15 |
| AI-generated | AI_GENERATED classification |
| Real photo with AI-generated face | Face-forensics ≥ 0.85 on face, vision mean < 0.40 |
| Likely real / Likely AI (N% confident) | UNCERTAIN classification |

## AWS Services Used

- **Amazon S3** — Image intake bucket + static web UI hosting
- **Amazon API Gateway** — REST API endpoints
- **AWS Lambda** — Detection, health, upload-url, session-check, S3-event handlers
- **Amazon DynamoDB** — Detection results + rate limits
- **Amazon Rekognition** — Celebrity recognition, face detection, region analysis
- **Amazon SageMaker** — Pixel detector + composite specialist endpoints
- **Amazon Bedrock** — Claude Haiku 4.5, Sonnet 4.6, Opus 4.7 via Global Inference Profiles
- **Amazon CloudFront** — Web UI CDN + Lambda@Edge auth
- **AWS KMS** — C2PA verification key (asymmetric ECC_NIST_P256)
- **Amazon SNS** — Detection alerts
- **Amazon CloudWatch** — Alarms on latency and errors
- **AWS Secrets Manager** — Web UI password storage

## Docs

| Doc | Scope |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Cascade decision tree, module boundaries, data flow |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | CDK deploy, post-deploy wire-up, smoke tests |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Runbook: alarms, common incidents |
| [docs/COST_ANALYSIS.md](docs/COST_ANALYSIS.md) | Per-model cost breakdown |
| [docs/openapi.yaml](docs/openapi.yaml) | REST API spec |

## Tests

```bash
pytest tests/unit tests/property    # 418 tests, ~2 min warm
pytest tests/integration            # moto-backed end-to-end flows
```

## License

This sample is licensed under the MIT-0 License. See [LICENSE](LICENSE).
