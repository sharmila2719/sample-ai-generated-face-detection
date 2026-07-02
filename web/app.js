/* AI Image Detector — frontend application */
'use strict';

// Probability threshold above which the headline says "AI elements" instead of "Real"
const _AI_PROBABILITY_HEADLINE_THRESHOLD = 0.15;

const cfg = window.APP_CONFIG || { apiBase: '', tenantId: 'web-demo' };

/* ── State ── */
let selectedFile = null;
let selectedS3Key = null;
let selectedS3Bucket = null;

/* ── Element refs ── */
const loginPanel  = document.getElementById('login-panel');
const appPanel    = document.getElementById('app-panel');
const loginForm   = document.getElementById('login-form');
const loginError  = document.getElementById('login-error');
const dropZone    = document.getElementById('drop-zone');
const fileInput   = document.getElementById('file-input');
const previewCont = document.getElementById('preview-container');
const previewImg  = document.getElementById('preview-img');
const overlayCanvas = document.getElementById('overlay-canvas');
const analyzeBtn  = document.getElementById('analyze-btn');
const resultPanel = document.getElementById('result-panel');
const verdictBanner = document.getElementById('verdict-banner');
const evidenceList  = document.getElementById('evidence-list');
const signalsList   = document.getElementById('signals-list');
const spinner     = document.getElementById('spinner');
const deepCheck   = document.getElementById('deep-analysis');

/* ── Login ── */
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.classList.add('hidden');
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    try {
      const resp = await fetch(`${cfg.apiBase}/api/session-check`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (resp.ok) {
        loginPanel.classList.add('hidden');
        appPanel.classList.remove('hidden');
        // Warm SageMaker endpoint
        _warmEndpoint();
      } else {
        loginError.textContent = 'Invalid username or password.';
        loginError.classList.remove('hidden');
      }
    } catch {
      loginError.textContent = 'Sign-in failed. Check your connection.';
      loginError.classList.remove('hidden');
    }
  });
}

/* ── File selection ── */
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) _selectFile(fileInput.files[0]);
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) _selectFile(file);
});

function _selectFile(file) {
  selectedFile = file;
  selectedS3Key = null;
  analyzeBtn.disabled = false;
  resultPanel.classList.add('hidden');

  const reader = new FileReader();
  reader.onload = (ev) => {
    previewImg.src = ev.target.result;
    previewCont.classList.remove('hidden');
    // Clear canvas overlay
    const ctx = overlayCanvas.getContext('2d');
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  };
  reader.readAsDataURL(file);
}

/* ── Analyze ── */
analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  analyzeBtn.disabled = true;
  spinner.classList.remove('hidden');
  resultPanel.classList.add('hidden');

  try {
    // 1. Get pre-signed upload URL
    const urlResp = await fetch(`${cfg.apiBase}/api/upload-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_type: selectedFile.type, filename: selectedFile.name }),
    });
    const { upload_url, s3_bucket, s3_key } = await urlResp.json();

    // 2. Upload directly to S3
    await fetch(upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': selectedFile.type },
      body: selectedFile,
    });
    selectedS3Bucket = s3_bucket;
    selectedS3Key = s3_key;

    // 3. Request detection
    const detectResp = await fetch(`${cfg.apiBase}/api/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': cfg.tenantId,
      },
      body: JSON.stringify({
        s3_bucket: s3_bucket,
        s3_key: s3_key,
        force_fresh: true,
        deep_analysis: deepCheck.checked,
        fast_mode: true,
      }),
    });
    const result = await detectResp.json();
    _renderResult(result);
  } catch (err) {
    verdictBanner.textContent = `Error: ${err.message}`;
    verdictBanner.className = 'verdict-amber';
    resultPanel.classList.remove('hidden');
  } finally {
    spinner.classList.add('hidden');
    analyzeBtn.disabled = false;
  }
});

/* ── Render result ── */
function _renderResult(r) {
  // Headline
  let headline, bannerClass;
  const composite = r.composite_signal || {};
  if (composite.has_ai_face_with_real_context) {
    const count = composite.face_count > 1 ? 'faces' : 'face';
    headline = `Real photo with an AI-generated ${count}`;
    bannerClass = 'verdict-amber';
  } else if (r.classification === 'AI_GENERATED') {
    headline = 'This looks AI-generated';
    bannerClass = 'verdict-red';
  } else if (r.classification === 'UNCERTAIN') {
    const pct = Math.round(Math.abs(r.probability_score - 0.5) * 200);
    headline = r.probability_score > 0.5
      ? `Likely AI-generated (${pct}% confident)`
      : `Likely real (${pct}% confident)`;
    bannerClass = 'verdict-amber';
  } else {
    // NATURAL
    if (r.probability_score > _AI_PROBABILITY_HEADLINE_THRESHOLD) {
      headline = 'Real photo with some AI-generated elements';
    } else {
      headline = 'This looks like a real photo';
    }
    bannerClass = 'verdict-green';
  }

  verdictBanner.textContent = headline;
  verdictBanner.className = bannerClass;

  // Celebrity deepfake signal
  if (r.celebrities && r.celebrities.length > 0 && r.classification === 'AI_GENERATED') {
    const names = r.celebrities.map(c => c.name).join(', ');
    verdictBanner.textContent += ` — may be a deepfake of ${names}`;
  }

  // Evidence cards
  evidenceList.innerHTML = '';
  const evidence = r.evidence || [];
  evidence.forEach((item) => {
    const div = document.createElement('div');
    div.className = 'evidence-item';
    div.textContent = item;
    evidenceList.appendChild(div);
  });

  // Signals consulted
  const signals = r.signals_consulted || [];
  signalsList.innerHTML = 'Signals: ' + signals.map(s => `<span>${s}</span>`).join(' · ');

  // Bounding box overlay
  _drawRegions(r);

  resultPanel.classList.remove('hidden');
}

/* ── Bounding-box overlay ── */
function _drawRegions(r) {
  const regions = (r.composite_analysis || {}).regions || [];
  if (!regions.length) return;

  const img = previewImg;
  overlayCanvas.width  = img.naturalWidth  || img.clientWidth;
  overlayCanvas.height = img.naturalHeight || img.clientHeight;
  overlayCanvas.style.width  = img.clientWidth + 'px';
  overlayCanvas.style.height = img.clientHeight + 'px';

  const ctx = overlayCanvas.getContext('2d');
  ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  regions.forEach((region) => {
    const [x, y, w, h] = region.bbox || [];
    if (x == null) return;
    const px = x * overlayCanvas.width;
    const py = y * overlayCanvas.height;
    const pw = w * overlayCanvas.width;
    const ph = h * overlayCanvas.height;
    const score = region.ai_likelihood || 0;
    const color = score >= 0.65 ? '#ef4444' : score >= 0.40 ? '#f59e0b' : '#22c55e';

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(px, py, pw, ph);

    ctx.fillStyle = color;
    ctx.font = '11px sans-serif';
    ctx.fillText(`${region.label || 'region'} ${Math.round(score * 100)}%`, px + 4, py + 14);
  });
}

/* ── SageMaker warm-up ── */
async function _warmEndpoint() {
  try {
    await fetch(`${cfg.apiBase}/health`);
  } catch { /* ignore */ }
}
