/**
 * Architecture diagram generator.
 * Run: node generate_diagram.js
 * Outputs: architecture.html (open in browser to view/screenshot)
 */

const fs = require('fs');

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>AI Image Detection — Architecture</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f1117; font-family: Arial, sans-serif; padding: 20px; }
h1 { color: #e2e8f0; text-align: center; margin-bottom: 24px; font-size: 20px; }

.diagram { display: flex; flex-direction: column; gap: 16px; max-width: 1100px; margin: 0 auto; }

/* Row layouts */
.row { display: flex; gap: 12px; align-items: stretch; justify-content: center; }

.box {
  background: #1a1d27;
  border-radius: 8px;
  padding: 10px 14px;
  text-align: center;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
}
.box .icon { font-size: 20px; }
.box .label { color: #e2e8f0; font-size: 12px; font-weight: 600; }
.box .sub { color: #8892a4; font-size: 10px; }

.box.purple { border: 1.5px solid #6366f1; }
.box.amber  { border: 1.5px solid #f59e0b; }
.box.green  { border: 1.5px solid #22c55e; }
.box.red    { border: 1.5px solid #ef4444; }
.box.gray   { border: 1.5px solid #4b5563; }

/* Arrow */
.arrow { display: flex; align-items: center; justify-content: center; color: #4b5563; font-size: 22px; }
.arrow.down { transform: rotate(90deg); }

/* Orchestrator big box */
.orchestrator {
  background: #0f1117;
  border: 2px dashed #6366f1;
  border-radius: 12px;
  padding: 16px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
.orchestrator h2 { color: #6366f1; font-size: 13px; text-align: center; margin-bottom: 12px; }
.steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.step {
  background: #1a1d27;
  border-radius: 6px;
  padding: 8px 6px;
  text-align: center;
}
.step .num { color: #6366f1; font-size: 13px; font-weight: 700; }
.step .name { color: #e2e8f0; font-size: 10px; margin-top: 2px; }
.step .detail { color: #8892a4; font-size: 9px; margin-top: 1px; }
.step.rek   { border: 1px solid #f59e0b; }
.step.exif  { border: 1px solid #f59e0b; }
.step.sm    { border: 1px solid #22c55e; }
.step.haiku { border: 1px solid #6366f1; }
.step.face  { border: 1px solid #22c55e; }
.step.opus  { border: 1px solid #ef4444; }
.step.phb   { border: 1px solid #4b5563; }
.step.phc   { border: 1px solid #4b5563; }
.step.comb  { border: 1px solid #6366f1; }
.step.ddb   { border: 1px solid #6366f1; }

/* Services row */
.services { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; max-width: 1100px; margin: 0 auto; width: 100%; }
.svc-group {
  background: #1a1d27;
  border-radius: 8px;
  padding: 12px;
}
.svc-group h3 { font-size: 11px; font-weight: 700; margin-bottom: 8px; }
.svc-group.bedrock { border: 1.5px solid #6366f1; }
.svc-group.bedrock h3 { color: #6366f1; }
.svc-group.sagemaker { border: 1.5px solid #22c55e; }
.svc-group.sagemaker h3 { color: #22c55e; }
.svc-group.rekognition { border: 1.5px solid #f59e0b; }
.svc-group.rekognition h3 { color: #f59e0b; }
.svc-item { color: #e2e8f0; font-size: 10px; padding: 3px 0; border-bottom: 1px solid #2d3148; }
.svc-item:last-child { border-bottom: none; }
.svc-sub { color: #8892a4; font-size: 9px; }

/* Storage row */
.storage { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; max-width: 1100px; margin: 0 auto; width: 100%; }

/* Legend */
.legend { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; padding: 10px; }
.leg-item { display: flex; align-items: center; gap: 6px; }
.leg-color { width: 30px; height: 3px; border-radius: 2px; }
.leg-text { color: #8892a4; font-size: 10px; }

/* Verdict table */
.verdict-table { max-width: 1100px; margin: 0 auto; width: 100%; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1d27; color: #8892a4; font-size: 10px; padding: 6px 10px; text-align: left; border-bottom: 1px solid #2d3148; }
td { color: #e2e8f0; font-size: 10px; padding: 6px 10px; border-bottom: 1px solid #2d3148; }
tr:last-child td { border-bottom: none; }
.verdict-green { color: #22c55e; }
.verdict-amber { color: #f59e0b; }
.verdict-red   { color: #ef4444; }
</style>
</head>
<body>
<h1>🔍 AI Image Detection Pipeline — Architecture</h1>
<div class="diagram">

  <!-- Row 1: User → CloudFront → API Gateway -->
  <div class="row">
    <div class="box amber">
      <div class="icon">🌐</div>
      <div class="label">Browser</div>
      <div class="sub">Web UI</div>
    </div>
    <div class="arrow">→</div>
    <div class="box amber">
      <div class="icon">☁️</div>
      <div class="label">CloudFront</div>
      <div class="sub">+ Lambda@Edge Auth</div>
    </div>
    <div class="arrow">→</div>
    <div class="box amber">
      <div class="icon">🪣</div>
      <div class="label">S3 Web Bucket</div>
      <div class="sub">Static assets</div>
    </div>
    <div class="arrow" style="color:transparent">→</div>
    <div class="box green">
      <div class="icon">⚡</div>
      <div class="label">API Gateway</div>
      <div class="sub">REST /api/* /health</div>
    </div>
    <div class="arrow">→</div>
    <div class="box purple">
      <div class="icon">λ</div>
      <div class="label">Detection Lambda</div>
      <div class="sub">3008 MB · 60s · X86_64</div>
    </div>
    <div class="arrow">→</div>
    <div class="box gray">
      <div class="icon">🪣</div>
      <div class="label">S3 Intake</div>
      <div class="sub">ai-images-to-analyze</div>
    </div>
  </div>

  <!-- Row 2: Other Lambdas -->
  <div class="row">
    <div class="box purple">
      <div class="icon">λ</div>
      <div class="label">Upload URL Lambda</div>
      <div class="sub">Presigned PUT URL</div>
    </div>
    <div class="box purple">
      <div class="icon">λ</div>
      <div class="label">Health Lambda</div>
      <div class="sub">GET /health</div>
    </div>
    <div class="box purple">
      <div class="icon">λ</div>
      <div class="label">Session Check</div>
      <div class="sub">HMAC cookie auth</div>
    </div>
    <div class="box purple">
      <div class="icon">λ</div>
      <div class="label">S3 Event Lambda</div>
      <div class="sub">ObjectCreated trigger</div>
    </div>
  </div>

  <div class="arrow down" style="font-size:18px;text-align:center;color:#6366f1;">↓ Detection Cascade</div>

  <!-- Orchestrator -->
  <div class="orchestrator">
    <h2>🔍 InlineAgentOrchestrator — 10-Step Detection Cascade</h2>
    <div class="steps">
      <div class="step rek">
        <div class="num">①</div>
        <div class="name">Rekognition</div>
        <div class="detail">Celebrity Recognition</div>
      </div>
      <div class="step exif">
        <div class="num">②</div>
        <div class="name">EXIF Check</div>
        <div class="detail">Fast-path: recent camera</div>
      </div>
      <div class="step sm">
        <div class="num">③</div>
        <div class="name">Pixel CNN</div>
        <div class="detail">SageMaker pixel detector</div>
      </div>
      <div class="step haiku">
        <div class="num">④a</div>
        <div class="name">Claude Haiku 4.5</div>
        <div class="detail">1st-pass vision</div>
      </div>
      <div class="step haiku">
        <div class="num">④b</div>
        <div class="name">Claude Sonnet 4.6</div>
        <div class="detail">Parallel 2nd opinion</div>
      </div>
      <div class="step face">
        <div class="num">⑤</div>
        <div class="name">Face Forensics</div>
        <div class="detail">DetectFaces + AIGC SageMaker</div>
      </div>
      <div class="step opus">
        <div class="num">⑥</div>
        <div class="name">Claude Opus 4.7</div>
        <div class="detail">Tiebreaker / composite-zoom</div>
      </div>
      <div class="step phb">
        <div class="num">⑦</div>
        <div class="name">Phase B Regions</div>
        <div class="detail">Rekognition + crop Haiku</div>
      </div>
      <div class="step phc">
        <div class="num">⑧</div>
        <div class="name">Phase C Specialist</div>
        <div class="detail">SageMaker composite</div>
      </div>
      <div class="step comb">
        <div class="num">⑨⑩</div>
        <div class="name">Combine + Persist</div>
        <div class="detail">Evidence → DynamoDB</div>
      </div>
    </div>
  </div>

  <!-- AI Services -->
  <div class="services">
    <div class="svc-group bedrock">
      <h3>Amazon Bedrock — Global Inference (eu-west-1)</h3>
      <div class="svc-item">Claude Haiku 4.5 <span class="svc-sub">~7s · $1/1k</span></div>
      <div class="svc-item">Claude Sonnet 4.6 <span class="svc-sub">~17s · $8/1k</span></div>
      <div class="svc-item">Claude Opus 4.7 <span class="svc-sub">~12s · $24/1k · tiebreaker only</span></div>
      <div class="svc-item">Bedrock Guardrail <span class="svc-sub">Applied on every call</span></div>
    </div>
    <div class="svc-group sagemaker">
      <h3>Amazon SageMaker — Serverless Endpoints</h3>
      <div class="svc-item">ai-image-detector <span class="svc-sub">Pixel CNN · ~300ms · $0.02/1k</span></div>
      <div class="svc-item">ai-aigc-ensemble <span class="svc-sub">Face AIGC · ~1.3s · $0.05/1k</span></div>
      <div class="svc-item">ai-composite-specialist <span class="svc-sub">Crop specialist · ~1.5s</span></div>
    </div>
    <div class="svc-group rekognition">
      <h3>Amazon Rekognition (us-east-1)</h3>
      <div class="svc-item">RecognizeCelebrities <span class="svc-sub">Always runs · ~1s</span></div>
      <div class="svc-item">DetectFaces <span class="svc-sub">Face forensics gate</span></div>
      <div class="svc-item">DetectLabels <span class="svc-sub">Phase B bounding boxes</span></div>
    </div>
  </div>

  <!-- Storage & Support Services -->
  <div class="storage">
    <div class="box purple">
      <div class="icon">🗄</div>
      <div class="label">DynamoDB</div>
      <div class="sub">ai-detection-results</div>
      <div class="sub">+ content-hash GSI</div>
    </div>
    <div class="box amber">
      <div class="icon">🔐</div>
      <div class="label">Secrets Manager</div>
      <div class="sub">Web UI password</div>
    </div>
    <div class="box amber">
      <div class="icon">🔑</div>
      <div class="label">KMS</div>
      <div class="sub">ECC_NIST_P256</div>
      <div class="sub">C2PA verify key</div>
    </div>
    <div class="box red">
      <div class="icon">📣</div>
      <div class="label">SNS</div>
      <div class="sub">ai-detection-alerts</div>
    </div>
    <div class="box green">
      <div class="icon">📊</div>
      <div class="label">CloudWatch</div>
      <div class="sub">Latency + Error alarms</div>
    </div>
  </div>

  <!-- Verdict table -->
  <div class="verdict-table">
    <table>
      <tr><th>Verdict</th><th>Trigger</th><th>Banner</th></tr>
      <tr><td class="verdict-green">Real photo</td><td>NATURAL · probability ≤ 0.15</td><td>🟢 Green</td></tr>
      <tr><td class="verdict-green">Real photo with AI elements</td><td>NATURAL · probability &gt; 0.15</td><td>🟢 Green</td></tr>
      <tr><td class="verdict-red">AI-generated</td><td>AI_GENERATED classification</td><td>🔴 Red</td></tr>
      <tr><td class="verdict-amber">Real photo with AI-generated face</td><td>Face forensics ≥ 0.85 · vision mean &lt; 0.40</td><td>🟡 Amber</td></tr>
      <tr><td class="verdict-amber">Likely real / Likely AI (N%)</td><td>UNCERTAIN classification</td><td>🟡 Amber</td></tr>
    </table>
  </div>

  <!-- Legend -->
  <div class="legend">
    <div class="leg-item"><div class="leg-color" style="background:#6366f1"></div><div class="leg-text">Lambda / DynamoDB</div></div>
    <div class="leg-item"><div class="leg-color" style="background:#f59e0b"></div><div class="leg-text">S3 / CloudFront / KMS</div></div>
    <div class="leg-item"><div class="leg-color" style="background:#22c55e"></div><div class="leg-text">SageMaker / Rekognition</div></div>
    <div class="leg-item"><div class="leg-color" style="background:#ef4444"></div><div class="leg-text">SNS Alerts</div></div>
    <div class="leg-item"><div class="leg-color" style="background:#4b5563;border-style:dashed"></div><div class="leg-text">Phase B/C Composite Cascade</div></div>
    <div class="leg-item" style="margin-left:auto"><div class="leg-text">Region: us-east-1 · Bedrock: eu-west-1 · SageMaker: Serverless</div></div>
  </div>

</div>
</body>
</html>`;

fs.writeFileSync('architecture.html', html);
console.log('Generated: architecture.html');
