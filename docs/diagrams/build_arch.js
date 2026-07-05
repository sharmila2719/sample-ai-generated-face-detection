/**
 * Generates architecture.svg in the AWS-style diagram matching the reference image.
 * Run: node build_arch.js
 */
const fs = require('fs');

const W = 1200, H = 780;

// ── colour palette (matching AWS icon colours) ──────────────────────────
const C = {
  bg:         '#FFFFFF',
  awsBorder:  '#232F3E',
  awsFill:    '#F8F8F8',
  lambda:     '#FF9900',   // orange
  apigw:      '#E7157B',   // pink/magenta
  s3:         '#3F8624',   // green
  cloudfront: '#8C4FFF',   // purple
  cognito:    '#BF0816',
  dynamodb:   '#C7131F',   // red
  rekognition:'#01A88D',   // teal
  bedrock:    '#01A88D',
  sagemaker:  '#01A88D',
  sns:        '#E7157B',
  cloudwatch: '#E7157B',
  secrets:    '#DD344C',
  kms:        '#DD344C',
  orchestrator:'#F4B942',  // gold box
  bedrockBox: '#D1F5F0',   // light teal
  edge:       '#FF9900',
  user:       '#666666',
  arrow:      '#555555',
  textDark:   '#1A1A1A',
  textGray:   '#555555',
  textSmall:  '#777777',
};

// ── helpers ─────────────────────────────────────────────────────────────
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function roundRect(x,y,w,h,r,fill,stroke,sw=1.5,dash='') {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" ry="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${dash?`stroke-dasharray="${dash}"`:''}/>`;
}

function label(x,y,lines,size=10,fill=C.textDark,anchor='middle',weight='normal') {
  return lines.map((l,i)=>
    `<text x="${x}" y="${y+i*13}" text-anchor="${anchor}" font-size="${size}" fill="${fill}" font-weight="${weight}" font-family="Arial,Helvetica,sans-serif">${esc(l)}</text>`
  ).join('\n');
}

// Rounded-square service icon
function icon(cx,cy,size,fill,symbol) {
  const half=size/2;
  return [
    `<rect x="${cx-half}" y="${cy-half}" width="${size}" height="${size}" rx="${size*0.2}" fill="${fill}"/>`,
    `<text x="${cx}" y="${cy+size*0.18}" text-anchor="middle" font-size="${size*0.55}" fill="#FFF" font-family="Arial">${symbol}</text>`,
  ].join('\n');
}

// Arrow with optional label
function arrow(x1,y1,x2,y2,color=C.arrow,dash='',lx,ly,ltext,bend=false) {
  let path;
  if (bend) {
    // right-angle via mid
    const mx = x1 + (x2-x1)*0.5;
    path = `M${x1},${y1} L${mx},${y1} L${mx},${y2} L${x2},${y2}`;
  } else {
    path = `M${x1},${y1} L${x2},${y2}`;
  }
  const markId = 'arr_'+color.replace('#','');
  let out = `<path d="${path}" stroke="${color}" stroke-width="1.5" fill="none" ${dash?`stroke-dasharray="${dash}"`:''}  marker-end="url(#${markId})"/>`;
  if (ltext) out += label(lx,ly,[ltext],9,C.textGray);
  return out;
}

// ── marker definitions ──────────────────────────────────────────────────
function markers(...colors) {
  return colors.map(c => {
    const id = 'arr_'+c.replace('#','');
    return `<marker id="${id}" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0,0 L8,3 L0,6 Z" fill="${c}"/>
    </marker>`;
  }).join('\n');
}

// ── Build SVG ────────────────────────────────────────────────────────────
let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
${markers(C.arrow,'#FF9900','#E7157B','#8C4FFF','#01A88D','#C7131F','#E7157B','#F4B942','#555555','#999999')}
</defs>
<rect width="${W}" height="${H}" fill="${C.bg}"/>
`;

// ── TITLE ────────────────────────────────────────────────────────────────
s += label(W/2, 28, ['sample-ai-generated-face-detection — Architecture'], 16, C.textDark, 'middle', 'bold');

// ── AWS CLOUD BORDER ─────────────────────────────────────────────────────
s += roundRect(90,45, W-100, H-60, 8, C.awsFill, C.awsBorder, 2, '6,3');
// AWS logo area
s += `<rect x="90" y="45" width="110" height="26" rx="4" fill="${C.awsBorder}"/>`;
s += label(148, 63, ['AWS Cloud'], 11, '#FF9900', 'middle', 'bold');

// ── USER / BROWSER ───────────────────────────────────────────────────────
// Person icon (simple SVG)
s += `<circle cx="45" cy="320" r="14" fill="none" stroke="${C.user}" stroke-width="2"/>`;
s += `<line x1="45" y1="334" x2="45" y2="375" stroke="${C.user}" stroke-width="2"/>`;
s += `<line x1="20" y1="350" x2="70" y2="350" stroke="${C.user}" stroke-width="2"/>`;
s += `<line x1="45" y1="375" x2="20" y2="400" stroke="${C.user}" stroke-width="2"/>`;
s += `<line x1="45" y1="375" x2="70" y2="400" stroke="${C.user}" stroke-width="2"/>`;
s += label(45, 420, ['User / Browser'], 10, C.textGray);

// HTTPS label + arrow to CloudFront
s += arrow(75, 340, 150, 340, C.arrow,'',110,332,'HTTPS');

// ── CLOUDFRONT ───────────────────────────────────────────────────────────
s += icon(185, 340, 44, C.cloudfront, '⛅');
s += label(185, 395, ['CloudFront'], 10, C.textDark);

// ── LAMBDA@EDGE ──────────────────────────────────────────────────────────
s += icon(185, 265, 40, C.edge, 'λ');
s += label(185, 315, ['Lambda@Edge', '(Auth)'], 9, C.textDark);

// Arrow CloudFront → Lambda@Edge
s += arrow(185, 318, 185, 362, '#8C4FFF','4,2');
// Label
s += label(196, 342, ['Auth'], 8, C.textSmall);

// Arrow CloudFront → API GW
s += arrow(207, 340, 285, 340, C.arrow);

// ── API GATEWAY ───────────────────────────────────────────────────────────
s += icon(320, 340, 44, C.apigw, '⚡');
s += label(320, 395, ['API Gateway'], 10, C.textDark);

// ── WEB UI (S3) ───────────────────────────────────────────────────────────
s += icon(255, 255, 40, C.s3, '🪣');
s += label(255, 302, ['Web UI'], 9, C.textDark);
// CloudFront → Web UI
s += arrow(195, 300, 238, 272, '#3F8624','4,2');

// ── SESSION CHECK LAMBDA ──────────────────────────────────────────────────
s += icon(390, 210, 40, C.lambda, 'λ');
s += label(390, 258, ['Session Check', 'Lambda'], 9, C.textDark);
// API GW → Session Check
s += arrow(338, 318, 390, 252, C.arrow,'4,2');

// ── SECRETS MANAGER ──────────────────────────────────────────────────────
s += icon(500, 210, 40, C.secrets, '🔐');
s += label(500, 258, ['Secrets', 'Manager'], 9, C.textDark);
// Session → Secrets
s += arrow(412, 210, 478, 210, C.arrow,'4,2');

// ── UPLOAD URL LAMBDA ─────────────────────────────────────────────────────
s += icon(390, 310, 40, C.lambda, 'λ');
s += label(390, 357, ['Upload URL', 'Lambda'], 9, C.textDark);
// API GW → Upload URL
s += arrow(342, 330, 368, 325, C.arrow);

// ── DETECTION LAMBDA ──────────────────────────────────────────────────────
s += icon(390, 400, 40, C.lambda, 'λ');
s += label(390, 448, ['Detection', 'Lambda'], 9, C.textDark);
// API GW → Detection
s += arrow(342, 350, 368, 405, C.arrow);

// ── S3 INTAKE BUCKET ──────────────────────────────────────────────────────
s += icon(220, 490, 42, C.s3, '🪣');
s += label(220, 542, ['S3 Intake', 'Bucket'], 9, C.textDark);
// Upload URL → S3 Intake (presigned)
s += arrow(375, 330, 240, 470, '#3F8624','4,2');

// S3 Event arrow label
s += label(238, 475, ['S3 Event'], 8, C.textSmall);

// ── S3 EVENT LAMBDA ───────────────────────────────────────────────────────
s += icon(350, 490, 40, C.lambda, 'λ');
s += label(350, 540, ['S3 Event', 'Lambda'], 9, C.textDark);
// S3 → S3 Event Lambda
s += arrow(243, 511, 328, 511, C.arrow);

// ── BEDROCK AGENTCORE ORCHESTRATOR BOX ───────────────────────────────────
s += roundRect(510, 270, 170, 130, 12, '#FFF8E7', C.orchestrator, 2.5);
s += icon(575, 295, 38, '#7B5EA7', '🤖');
s += label(575, 343, ['Bedrock AgentCore'], 10, C.textDark, 'middle', 'bold');
s += label(575, 357, ['Agent Orchestrator'], 9, '#555');
s += label(575, 370, ['(Detection Cascade)'], 9, '#555');

// Detection Lambda → Orchestrator
s += arrow(412, 400, 510, 340, C.arrow);
// S3 Event Lambda → Orchestrator
s += arrow(372, 490, 510, 380, C.arrow,'4,2');
// "Send result" label
s += label(450, 425, ['Send result'], 8, C.textSmall);

// ── REKOGNITION ───────────────────────────────────────────────────────────
s += icon(720, 200, 44, C.rekognition, '👁');
s += label(720, 252, ['Rekognition'], 10, C.textDark);
// Orchestrator → Rekognition
s += arrow(682, 290, 720, 248, C.rekognition);

// ── SAGEMAKER SERVERLESS ──────────────────────────────────────────────────
s += icon(720, 345, 44, C.sagemaker, '🧠');
s += label(720, 398, ['SageMaker', 'Serverless', '(Pixel Detector)'], 9, C.textDark);
// Orchestrator → SageMaker
s += arrow(682, 335, 700, 345, C.sagemaker);

// ── AMAZON BEDROCK BOX ────────────────────────────────────────────────────
s += roundRect(820, 270, 340, 160, 10, C.bedrockBox, '#01A88D', 2);
s += `<rect x="820" y="270" width="120" height="22" rx="5" fill="#01A88D"/>`;
s += label(880, 286, ['Amazon Bedrock'], 10, '#FFF', 'middle', 'bold');
// Models inside
s += roundRect(832, 298, 100, 28, 5, '#FFF', '#01A88D', 1);
s += label(882, 317, ['Nova Pro'], 9, C.textDark);
s += roundRect(940, 298, 105, 28, 5, '#FFF', '#01A88D', 1);
s += label(992, 317, ['Claude Haiku 4.5'], 9, C.textDark);
s += roundRect(1053, 298, 95, 28, 5, '#FFF', '#01A88D', 1);
s += label(1100, 317, ['Claude Sonnet 4.6'], 8, C.textDark);
s += roundRect(886, 336, 120, 28, 5, '#FFF', '#01A88D', 1);
s += label(946, 355, ['Claude Opus 4.7', '(Tiebreaker)'], 8, C.textDark);
// Bedrock icon
s += icon(840, 398, 40, C.bedrock, '⚡');
s += label(840, 448, ['Bedrock'], 9, C.textDark);
// Orchestrator → Bedrock box
s += arrow(682, 325, 820, 340, '#01A88D');
// "Celebrity alert" label
s += arrow(720, 248, 720, 140, '#999999','4,2');
s += label(735, 180, ['Celebrity alert'], 8, C.textSmall);

// ── DYNAMODB ──────────────────────────────────────────────────────────────
s += icon(720, 490, 44, C.dynamodb, '🗄');
s += label(720, 543, ['DynamoDB', '(Results)'], 9, C.textDark);
// Orchestrator → DynamoDB
s += arrow(595, 400, 698, 490, C.dynamodb);

// ── SNS ───────────────────────────────────────────────────────────────────
s += icon(720, 600, 44, C.sns, '📣');
s += label(720, 653, ['SNS', '(Alerts)'], 9, C.textDark);
// DynamoDB → SNS (alert)
s += arrow(720, 537, 720, 578, C.arrow,'4,2');

// ── CLOUDWATCH ────────────────────────────────────────────────────────────
s += icon(570, 590, 44, C.cloudwatch, '📊');
s += label(570, 643, ['CloudWatch'], 9, C.textDark);
// Detection Lambda → CloudWatch
s += arrow(412, 420, 548, 590, C.arrow,'4,2');
// CloudWatch → SNS
s += arrow(614, 612, 698, 620, C.arrow,'4,2');

// ── KMS ───────────────────────────────────────────────────────────────────
s += icon(500, 140, 38, C.kms, '🔑');
s += label(500, 188, ['KMS'], 9, C.textDark);

// ── LEGEND BOX ────────────────────────────────────────────────────────────
s += roundRect(100, 680, 860, 55, 6, '#F8F8F8', '#CCCCCC', 1);
s += label(120, 698, ['Legend:'], 9, C.textGray, 'start', 'bold');

const legendItems = [
  [150, C.lambda,     'Lambda Function'],
  [290, C.apigw,      'API Gateway'],
  [420, C.s3,         'S3 Bucket'],
  [545, C.cloudfront, 'CloudFront'],
  [680, C.dynamodb,   'DynamoDB'],
  [800, C.rekognition,'AI Services (Bedrock/Rekognition/SageMaker)'],
];
legendItems.forEach(([x, clr, lbl]) => {
  s += `<rect x="${x}" y="690" width="16" height="16" rx="3" fill="${clr}"/>`;
  s += label(x+20, 702, [lbl], 9, C.textGray, 'start');
});
s += label(120, 720, ['Solid arrows = synchronous  |  Dashed arrows = async/optional  |  Region: us-east-1  |  Bedrock: eu-west-1'], 8, C.textSmall, 'start');

s += `</svg>`;

fs.writeFileSync('architecture.svg', s);
console.log('Done — architecture.svg  (' + s.length + ' bytes)');
