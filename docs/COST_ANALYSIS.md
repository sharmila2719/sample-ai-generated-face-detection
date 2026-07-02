# Cost Analysis

## Per-upload cost breakdown (deep_analysis=true, fast_mode=true)

| Tool | p50 Latency | Cost / 1000 calls | When |
|---|---|---|---|
| EXIF check | ~50 ms | free (CPU) | every request |
| Rekognition celebrities | ~500–1500 ms | ~$1.00 | every request |
| SageMaker pixel detector | ~300–500 ms | ~$0.02 | every request |
| Claude Haiku 4.5 | ~7 s | ~$1.00 | every request (parallel) |
| Claude Sonnet 4.6 | ~17 s | ~$8.00 | every request (parallel on deep) |
| Claude Opus 4.7 | ~8–15 s | ~$24.00 | tiebreaker / composite-zoom only |
| Face forensics | ~1.3 s | ~$0.05 | every request |
| Rekognition regions | ~400 ms | ~$1.00 | any region > 0.60 |
| Per-crop Haiku (×3) | ~9 s | ~$3.00 | Phase B triggered |
| Specialist composite | ~1.5 s | ~$0.06 | any Phase B crop > 0.85 |

## Typical UI path

- **Median** (deep_analysis=true, fast_mode=true, clean photo): ~17 s, ~$0.014
- **Worst case UI** (fast_mode=true, borderline composite): ~25 s, ~$0.020
- **Worst case async** (fast_mode=false, full cascade): ~30 s, ~$0.05

## Monthly idle baseline

AWS costs even with zero uploads:

| Resource | Monthly cost (idle) |
|---|---|
| API Gateway | ~$3.50 (per million requests) |
| Lambda | Free tier covers most usage |
| DynamoDB (PAY_PER_REQUEST) | $0 idle |
| CloudFront | ~$1.00 minimum |
| SageMaker serverless (cold) | $0 idle |
| CloudWatch | ~$0.50 |
| **Total idle** | **~$5–10/month** |

## Cost optimisation tips

1. Use `fast_mode=true` on UI calls to skip Opus and Phase B/C
2. Content-hash cache (24h TTL) avoids re-analyzing identical images
3. SageMaker serverless scales to zero between calls
4. Bedrock Global Inference Profiles route to the cheapest available region
