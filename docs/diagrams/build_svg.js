const fs = require('fs');

// Helper functions
const rect = (x,y,w,h,fill,stroke,r=8) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>`;
const text = (x,y,msg,size,fill,anchor='middle',weight='normal') =>
  `<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" fill="${fill}" font-weight="${weight}" font-family="Arial,Helvetica,sans-serif">${msg}</text>`;
const line = (x1,y1,x2,y2,color,dash='') =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="1.5" stroke-dasharray="${dash}" marker-end="url(#arr)"/>`;
const arrow = (x1,y1,x2,y2,color='#6366f1',dash='') =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="1.5" stroke-dasharray="${dash}" marker-end="url(#arrowhead)"/>`;

// Box component: draws rect + 2 text lines
function box(x, y, w, h, stroke, icon, label, sub) {
  const cx = x + w/2;
  return [
    rect(x, y, w, h, '#1a1d27', stroke),
    text(cx, y+h*0.35, icon, 16, '#e2e8f0'),
    text(cx, y+h*0.60, label, 10, '#e2e8f0', 'middle', 'bold'),
    text(cx, y+h*0.80, sub, 8, '#8892a4'),
  ].join('\n');
}

// Step box for cascade
function step(x, y, w, h, stroke, num, name, sub) {
  const cx = x + w/2;
  return [
    rect(x, y, w, h, '#1a1d27', stroke, 6),
    text(cx, y+14, num, 11, '#6366f1', 'middle', 'bold'),
    text(cx, y+26, name, 9, '#e2e8f0'),
    text(cx, y+37, sub, 8, '#8892a4'),
  ].join('\n');
}

const W = 1100, H = 820;

let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
  <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="#6366f1"/>
  </marker>
  <marker id="arrowG" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="#22c55e"/>
  </marker>
  <marker id="arrowA" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="#f59e0b"/>
  </marker>
</defs>
<rect width="${W}" height="${H}" fill="#0f1117"/>

<!-- TITLE -->
<text x="${W/2}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#e2e8f0" font-family="Arial,Helvetica,sans-serif">AI Image Detection Pipeline — Architecture</text>

<!-- ── ROW 1: Browser → CloudFront → API GW ── -->
${box(10, 55, 110, 60, '#6366f1', '🌐', 'Browser', 'Web UI')}
${box(150, 55, 130, 60, '#f59e0b', '☁️', 'CloudFront', 'Lambda@Edge Auth')}
${box(310, 55, 120, 60, '#f59e0b', '🪣', 'S3 Web', 'Static assets')}
${box(460, 55, 130, 60, '#22c55e', '⚡', 'API Gateway', '/api/* /health')}

<!-- ── ROW 1 Lambdas ── -->
${box(620, 55, 115, 60, '#6366f1', 'λ', 'Detection', '3008MB · 60s')}
${box(755, 55, 115, 60, '#6366f1', 'λ', 'S3 Event', 'ObjectCreated')}
${box(890, 55, 115, 60, '#6366f1', 'λ', 'Upload URL', 'Presigned PUT')}
${box(890, 135, 115, 55, '#6366f1', 'λ', 'Session Check', 'HMAC auth')}
${box(755, 135, 115, 55, '#6366f1', 'λ', 'Health', 'GET /health')}

<!-- Arrows row1 -->
<line x1="120" y1="85" x2="148" y2="85" stroke="#6366f1" stroke-width="1.5" marker-end="url(#arrowhead)"/>
<line x1="280" y1="85" x2="308" y2="85" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#arrowA)"/>
<line x1="430" y1="85" x2="458" y2="85" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#arrowA)"/>
<line x1="590" y1="85" x2="618" y2="85" stroke="#22c55e" stroke-width="1.5" marker-end="url(#arrowG)"/>
<line x1="735" y1="85" x2="753" y2="85" stroke="#6366f1" stroke-width="1.5" marker-end="url(#arrowhead)"/>
<line x1="870" y1="85" x2="888" y2="85" stroke="#6366f1" stroke-width="1.5" marker-end="url(#arrowhead)"/>
<line x1="525" y1="115" x2="525" y2="148" stroke="#22c55e" stroke-width="1" stroke-dasharray="4,2"/>
<line x1="525" y1="148" x2="619" y2="148" stroke="#22c55e" stroke-width="1" stroke-dasharray="4,2" marker-end="url(#arrowG)"/>
<line x1="525" y1="148" x2="753" y2="160" stroke="#22c55e" stroke-width="1" stroke-dasharray="4,2" marker-end="url(#arrowG)"/>
<line x1="525" y1="148" x2="888" y2="160" stroke="#22c55e" stroke-width="1" stroke-dasharray="4,2" marker-end="url(#arrowG)"/>

<!-- S3 Intake -->
${box(620, 135, 115, 55, '#f59e0b', '🪣', 'S3 Intake', 'ai-images-to-analyze')}
<line x1="677" y1="115" x2="677" y2="133" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#arrowA)"/>
<line x1="812" y1="115" x2="812" y2="133" stroke="#6366f1" stroke-width="1" stroke-dasharray="3,2" marker-end="url(#arrowhead)"/>
<line x1="677" y1="190" x2="677" y2="216" stroke="#6366f1" stroke-width="1" stroke-dasharray="4,2" marker-end="url(#arrowhead)"/>

<!-- Arrow to orchestrator -->
<line x1="677" y1="115" x2="500" y2="216" stroke="#6366f1" stroke-width="1.5" marker-end="url(#arrowhead)"/>
`;

// ── ORCHESTRATOR BOX ──
svg += `
<!-- ORCHESTRATOR -->
<rect x="10" y="210" width="860" height="200" rx="10" fill="#0f1117" stroke="#6366f1" stroke-width="2" stroke-dasharray="8,4"/>
<text x="440" y="230" text-anchor="middle" font-size="12" font-weight="bold" fill="#6366f1" font-family="Arial,Helvetica,sans-serif">🔍 InlineAgentOrchestrator — 10-Step Detection Cascade</text>

${step(18,  238, 162, 46, '#f59e0b', '① Rekognition',  'Celebrities', 'Always first·~1s')}
${step(188, 238, 162, 46, '#f59e0b', '② EXIF Check',   'Camera metadata', 'Fast-path·50ms')}
${step(358, 238, 162, 46, '#22c55e', '③ SageMaker',    'Pixel CNN', '~400ms·short-circuit')}
${step(528, 238, 162, 46, '#6366f1', '④a Haiku 4.5',  '1st-pass vision', 'Parallel·~7s')}
${step(698, 238, 162, 46, '#6366f1', '④b Sonnet 4.6', '2nd opinion', 'Parallel·~17s')}

${step(18,  295, 162, 46, '#22c55e', '⑤ Face Forensics','DetectFaces+AIGC','~1.3s')}
${step(188, 295, 162, 46, '#ef4444', '⑥ Opus 4.7',    'Tiebreaker', 'Skipped in fast_mode')}
${step(358, 295, 162, 46, '#4b5563', '⑦ Phase B',     'Regions+crop Haiku', 'When region>0.60')}
${step(528, 295, 162, 46, '#4b5563', '⑧ Phase C',     'Specialist SageMaker', 'When crop>0.85')}
${step(698, 295, 162, 46, '#6366f1', '⑨⑩ Combine',  'Evidence→DynamoDB', 'Always last')}
`;

// ── AI SERVICES ──
svg += `
<!-- AI SERVICES ROW -->
<rect x="10"  y="425" width="340" height="115" rx="8" fill="#1a1d27" stroke="#6366f1" stroke-width="1.5"/>
<text x="180" y="443" text-anchor="middle" font-size="11" font-weight="bold" fill="#6366f1" font-family="Arial,Helvetica,sans-serif">Amazon Bedrock (eu-west-1)</text>
<text x="180" y="460" text-anchor="middle" font-size="9" fill="#8892a4" font-family="Arial">Global Inference Profiles</text>
<text x="30"  y="477" font-size="9" fill="#e2e8f0" font-family="Arial">▸ Claude Haiku 4.5   ~7s  $1/1k   first-pass vision</text>
<text x="30"  y="493" font-size="9" fill="#e2e8f0" font-family="Arial">▸ Claude Sonnet 4.6  ~17s $8/1k   second opinion</text>
<text x="30"  y="509" font-size="9" fill="#e2e8f0" font-family="Arial">▸ Claude Opus 4.7    ~12s $24/1k  tiebreaker only</text>
<text x="30"  y="525" font-size="9" fill="#8892a4" font-family="Arial">▸ Bedrock Guardrail applied on every invocation</text>

<rect x="360" y="425" width="340" height="115" rx="8" fill="#1a1d27" stroke="#22c55e" stroke-width="1.5"/>
<text x="530" y="443" text-anchor="middle" font-size="11" font-weight="bold" fill="#22c55e" font-family="Arial,Helvetica,sans-serif">Amazon SageMaker — Serverless</text>
<text x="30"  y="477" dx="330" font-size="9" fill="#e2e8f0" font-family="Arial">▸ ai-image-detector      Pixel CNN  ~300ms $0.02/1k</text>
<text x="30"  y="493" dx="330" font-size="9" fill="#e2e8f0" font-family="Arial">▸ ai-aigc-ensemble       Face AIGC  ~1.3s  $0.05/1k</text>
<text x="30"  y="509" dx="330" font-size="9" fill="#e2e8f0" font-family="Arial">▸ ai-composite-specialist Specialist ~1.5s  $0.06/1k</text>
<text x="30"  y="525" dx="330" font-size="9" fill="#8892a4" font-family="Arial">▸ Scale-to-zero between calls</text>

<rect x="710" y="425" width="370" height="115" rx="8" fill="#1a1d27" stroke="#f59e0b" stroke-width="1.5"/>
<text x="895" y="443" text-anchor="middle" font-size="11" font-weight="bold" fill="#f59e0b" font-family="Arial,Helvetica,sans-serif">Amazon Rekognition (us-east-1)</text>
<text x="720" y="460" font-size="9" fill="#e2e8f0" font-family="Arial">▸ RecognizeCelebrities — always runs, ~1s, $1/1k</text>
<text x="720" y="477" font-size="9" fill="#e2e8f0" font-family="Arial">▸ DetectFaces          — face forensics gate</text>
<text x="720" y="493" font-size="9" fill="#e2e8f0" font-family="Arial">▸ DetectLabels         — Phase B bounding boxes</text>
<text x="720" y="509" font-size="9" fill="#8892a4" font-family="Arial">▸ Confidence threshold: 85% for celebrities</text>

<!-- arrows to services -->
<line x1="440" y1="408" x2="180" y2="423" stroke="#6366f1" stroke-width="1.5" marker-end="url(#arrowhead)"/>
<line x1="440" y1="408" x2="530" y2="423" stroke="#22c55e" stroke-width="1.5" marker-end="url(#arrowG)"/>
<line x1="440" y1="408" x2="895" y2="423" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#arrowA)"/>
`;

// ── STORAGE ROW ──
svg += `
<!-- STORAGE ROW -->
${box(10,  555, 160, 58, '#6366f1', '🗄', 'DynamoDB', 'detection-results + GSI')}
${box(180, 555, 155, 58, '#6366f1', '🗄', 'Rate Limits', 'generation-rate-limits')}
${box(345, 555, 155, 58, '#f59e0b', '🔐', 'Secrets Manager', 'web-ui-password')}
${box(510, 555, 145, 58, '#f59e0b', '🔑', 'KMS', 'ECC_NIST_P256 C2PA')}
${box(665, 555, 145, 58, '#ef4444', '📣', 'SNS', 'ai-detection-alerts')}
${box(820, 555, 145, 58, '#22c55e', '📊', 'CloudWatch', 'Latency+Error Alarms')}

<!-- arrows to storage -->
<line x1="350" y1="408" x2="90"  y2="553" stroke="#6366f1" stroke-width="1" stroke-dasharray="3,2" marker-end="url(#arrowhead)"/>
<line x1="440" y1="408" x2="737" y2="553" stroke="#ef4444" stroke-width="1" stroke-dasharray="3,2" marker-end="url(#arrowhead)"/>
<line x1="440" y1="408" x2="892" y2="553" stroke="#22c55e" stroke-width="1" stroke-dasharray="3,2" marker-end="url(#arrowG)"/>
`;

// ── VERDICT TABLE ──
svg += `
<!-- VERDICT TABLE -->
<rect x="10" y="628" width="1070" height="130" rx="8" fill="#1a1d27" stroke="#2d3148" stroke-width="1"/>
<text x="545" y="647" text-anchor="middle" font-size="11" font-weight="bold" fill="#8892a4" font-family="Arial,Helvetica,sans-serif">VERDICT VARIANTS</text>
<text x="30"  y="665" font-size="9" fill="#22c55e" font-family="Arial">🟢 Real photo</text>
<text x="200" y="665" font-size="9" fill="#e2e8f0" font-family="Arial">NATURAL · probability ≤ 0.15</text>
<text x="30"  y="683" font-size="9" fill="#22c55e" font-family="Arial">🟢 Real photo with AI elements</text>
<text x="200" y="683" font-size="9" fill="#e2e8f0" font-family="Arial">NATURAL · probability &gt; 0.15</text>
<text x="30"  y="701" font-size="9" fill="#ef4444" font-family="Arial">🔴 AI-generated</text>
<text x="200" y="701" font-size="9" fill="#e2e8f0" font-family="Arial">AI_GENERATED classification</text>
<text x="30"  y="719" font-size="9" fill="#f59e0b" font-family="Arial">🟡 Real photo with AI-generated face</text>
<text x="200" y="719" font-size="9" fill="#e2e8f0" font-family="Arial">Face forensics ≥ 0.85 · vision mean &lt; 0.40 (face-swap)</text>
<text x="30"  y="737" font-size="9" fill="#f59e0b" font-family="Arial">🟡 Likely real / Likely AI (N% confident)</text>
<text x="200" y="737" font-size="9" fill="#e2e8f0" font-family="Arial">UNCERTAIN · directional with confidence %</text>

<!-- Region info -->
<text x="580" y="665" font-size="9" fill="#8892a4" font-family="Arial">Region: us-east-1   |   Bedrock: eu-west-1 (Global Inference)</text>
<text x="580" y="683" font-size="9" fill="#8892a4" font-family="Arial">Lambda: Python 3.12 · X86_64 · 3008 MB · 60s timeout</text>
<text x="580" y="701" font-size="9" fill="#8892a4" font-family="Arial">API GW: 29s integration timeout (configurable to 120s)</text>
<text x="580" y="719" font-size="9" fill="#8892a4" font-family="Arial">DynamoDB: PAY_PER_REQUEST · 24h content-hash cache</text>
<text x="580" y="737" font-size="9" fill="#8892a4" font-family="Arial">SageMaker: Serverless (scale-to-zero) · 3 endpoints</text>

<!-- Legend -->
<line x1="20"  y1="753" x2="50"  y2="753" stroke="#6366f1" stroke-width="2"/>
<text x="55"  y="757" font-size="8" fill="#8892a4" font-family="Arial">Lambda/DynamoDB</text>
<line x1="165" y1="753" x2="195" y2="753" stroke="#f59e0b" stroke-width="2"/>
<text x="200" y="757" font-size="8" fill="#8892a4" font-family="Arial">S3/CloudFront/KMS</text>
<line x1="310" y1="753" x2="340" y2="753" stroke="#22c55e" stroke-width="2"/>
<text x="345" y="757" font-size="8" fill="#8892a4" font-family="Arial">SageMaker/Rekognition</text>
<line x1="470" y1="753" x2="500" y2="753" stroke="#ef4444" stroke-width="2"/>
<text x="505" y="757" font-size="8" fill="#8892a4" font-family="Arial">Alerts (async)</text>
<line x1="580" y1="753" x2="610" y2="753" stroke="#4b5563" stroke-width="2" stroke-dasharray="4,2"/>
<text x="615" y="757" font-size="8" fill="#8892a4" font-family="Arial">Composite cascade (optional)</text>
</svg>`;

fs.writeFileSync('architecture.svg', svg);
console.log('Generated: architecture.svg  (' + svg.length + ' bytes)');
