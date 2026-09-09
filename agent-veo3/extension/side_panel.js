/**
 * Flow Kit — Side Panel
 * Displays live connection status, metrics, and request log.
 */

const reloadOnce = new URLSearchParams(window.location.search).get('reload_once');
if (reloadOnce) {
  const lastReload = sessionStorage.getItem('last_reload_once');
  if (lastReload !== reloadOnce) {
    sessionStorage.setItem('last_reload_once', reloadOnce);
    try { chrome.runtime.sendMessage({ type: 'RELOAD_EXTENSION' }); } catch (e) {}
  }
}

// ── Type label map ───────────────────────────────────────────

const TYPE_LABELS = {
  // Hình ảnh
  GEN_IMG:                    'Tạo ảnh',
  GENERATE_IMAGE:             'Tạo ảnh',
  IMAGE_GENERATION:           'Tạo ảnh',
  REGEN_IMG:                  'Tạo lại ảnh',
  REGENERATE_IMAGE:           'Tạo lại ảnh',
  EDIT_IMG:                   'Sửa ảnh',
  EDIT_IMAGE:                 'Sửa ảnh',
  GEN_CHARACTER_IMAGE:        'Tạo ảnh ref',
  REGENERATE_CHARACTER_IMAGE: 'Tạo lại ref',
  EDIT_CHARACTER_IMAGE:       'Sửa ảnh ref',
  GEN_REF:                    'Tạo ảnh ref',

  // Tải lên & Tải về
  UPLOAD:                     'Up ảnh',
  UPLOAD_IMAGE:               'Up ảnh',
  uploadImage:                'Up ảnh',
  FETCH_BLOB:                 'Tải ảnh',
  fetch_blob:                 'Tải ảnh',
  DOWNLOAD:                   'Tải ảnh/video',
  DOWNLOAD_IMAGE:             'Tải ảnh',
  MEDIA:                      'Tải media',

  // Video
  GEN_VID:                    'Tạo video',
  GEN_VID_INTERPOLATE:        'Nối frame video',
  GENERATE_VIDEO:             'Tạo video',
  VIDEO_GENERATION:           'Tạo video',
  GEN_VID_REF:                'Tạo video ref',
  GENERATE_VIDEO_REFS:        'Tạo video ref',
  UPSCALE:                    'Nâng cấp video',
  UPSCALE_VIDEO:              'Nâng cấp video',
  UPS_IMG:                    'Nâng cấp ảnh',
  POLL:                       'Check video',

  // Dự án & Quản lý
  CREATE_PROJECT:             'Tạo dự án',
  RENAME:                     'Đổi tên',
  RENAME_ASSET:               'Đổi tên asset',
  RENAME_PROJECT:             'Đổi tên dự án',
  LIST_MEDIA:                 'DS media',

  // Hệ thống & Xác thực
  REFRESH_TOKEN:              'Lấy token',
  TOKEN_CAPTURED:             'Đã nhận token',
  CAPTCHA:                    'Giải captcha',
  URL_REFRESH:                'Làm mới link',
  TRACKING:                   'Theo dõi Flow',
  TRPC:                       'TRPC Link',
  API:                        'API Flow',

  // Fallback Google RPC Codes
  'RPC:ogiZ0b':               'Tạo ảnh',
  'ogiZ0b':                   'Tạo ảnh',
  'RPC:eb1hJf':               'Tạo video',
  'eb1hJf':                   'Tạo video',
  'RPC:nprQif':               'Nối frame video',
  'nprQif':                   'Nối frame video',
  'RPC:MZZa6b':               'Tạo video ref',
  'MZZa6b':                   'Tạo video ref',
  'RPC:maseQ':                'Up ảnh',
  'maseQ':                    'Up ảnh',
  'RPC:mYWVGd':               'Đổi tên',
  'mYWVGd':                   'Đổi tên',
  'RPC:jHPbke':               'Tạo dự án',
  'jHPbke':                   'Tạo dự án',
  'RPC:o8DA4':                'Đổi tên dự án',
  'o8DA4':                    'Đổi tên dự án',
  'RPC:wXbhsf':               'Check video',
  'wXbhsf':                   'Check video',
  'RPC:kFhKBc':               'Tải media',
  'kFhKBc':                   'Tải media',
  'RPC:vv2eKe':               'DS media',
  'vv2eKe':                   'DS media',
};

function formatType(type, entry = null) {
  if (!type) return '—';
  if (TYPE_LABELS[type]) return TYPE_LABELS[type];

  // Try stripping 'RPC:'
  const stripped = String(type).replace(/^RPC:/i, '');
  if (TYPE_LABELS[stripped]) return TYPE_LABELS[stripped];

  // Inspect URL or fallback
  const url = entry?.url || '';
  if (url.includes('uploadImage') || stripped === 'maseQ') return 'Up ảnh';
  if (url.includes('batchGenerateImages') || stripped === 'ogiZ0b') return 'Tạo ảnh';
  if (url.includes('batchAsyncGenerateVideo') || stripped === 'eb1hJf') return 'Tạo video';
  if (stripped === 'nprQif') return 'Nối frame video';
  if (stripped === 'MZZa6b') return 'Tạo video ref';
  if (url.includes('ReferenceImages')) return 'Tạo video ref';
  if (url.includes('UpsampleVideo')) return 'Nâng cấp video';
  if (url.includes('createProject') || stripped === 'jHPbke') return 'Tạo dự án';
  if (url.includes('rename') || stripped === 'mYWVGd' || stripped === 'o8DA4') return 'Đổi tên';
  if (url.includes('fetch_blob') || url.includes('/media/')) return 'Tải ảnh';

  return type.length > 12 ? type.slice(0, 12) : type;
}

function getTypeClass(type, label = '') {
  const l = (label || '').toLowerCase();
  if (l.includes('ảnh') && !l.includes('up') && !l.includes('tải')) return 'type-img';
  if (l.includes('up')) return 'type-upload';
  if (l.includes('tải')) return 'type-download';
  if (l.includes('video')) return 'type-vid';
  if (l.includes('dự án')) return 'type-project';
  if (l.includes('tên')) return 'type-rename';
  return '';
}

// ── Time formatting ──────────────────────────────────────────

function formatTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  } catch {
    return '—';
  }
}

// ── Status update ────────────────────────────────────────────

function updateStatus(data) {
  if (!data) return;

  // Connection dot
  const dot = document.getElementById('conn-dot');
  const connected = data.agentConnected;
  dot.className = connected ? 'on' : '';

  // Toggle state
  const toggle = document.getElementById('main-toggle');
  const toggleLabel = document.getElementById('toggle-label');
  const isOn = data.state !== 'off';
  toggle.checked = isOn;
  toggleLabel.textContent = isOn ? 'ON' : 'OFF';

  // State badge
  const stateBadge = document.getElementById('state-badge');
  const st = data.state || 'off';
  stateBadge.textContent = st;
  stateBadge.className = st; // idle | running | off

  // Token status
  const tokenEl = document.getElementById('token-status');
  if (data.flowKeyPresent) {
    const ageMs = data.tokenAge || 0;
    const ageMin = Math.round(ageMs / 60000);
    if (ageMs > 3600000) {
      tokenEl.textContent = `token expired — open Flow to refresh`;
      tokenEl.className = 'warn';
    } else {
      tokenEl.textContent = `token synced ${ageMin}m`;
      tokenEl.className = 'ok';
    }
    // Auto-refresh when token age > 55 min and connected
    if (ageMs > 3300000 && data.agentConnected) {
      chrome.runtime.sendMessage({ type: 'REFRESH_TOKEN' });
    }
  } else {
    tokenEl.textContent = 'no token';
    tokenEl.className = 'bad';
  }

  // Metrics
  const m = data.metrics || {};
  document.getElementById('m-total').textContent   = m.requestCount || 0;
  document.getElementById('m-success').textContent = m.successCount || 0;
  document.getElementById('m-failed').textContent  = m.failedCount  || 0;
}

// ── Request log ──────────────────────────────────────────────

function updateRequestLog(entries) {
  const tbody = document.getElementById('log-body');
  const countEl = document.getElementById('log-count');

  if (!entries || entries.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="log-empty">No requests yet</td></tr>';
    countEl.textContent = '0';
    return;
  }

  countEl.textContent = entries.length;
  _logEntries = entries;

  // Render newest first (entries already sorted DESC by background.js)
  const rows = entries.map((entry) => {
    const shortId = entry.id ? String(entry.id).slice(0, 8) : '—';
    const type   = formatType(entry.type || entry.method, entry);
    const typeCls = getTypeClass(entry.type || entry.method, type);
    const time   = formatTime(entry.time || entry.timestamp || entry.createdAt);
    const status = entry.status || entry.state || 'pending';
    const error  = entry.error || '';

    const isAsync = ['GEN_VID', 'GEN_VID_REF', 'UPSCALE'].includes(entry.type);
    let badgeHtml;
    if (status === 'COMPLETED' || status === 'success' || (isAsync && entry.outputUrl)) {
      badgeHtml = '<span class="badge badge-ok">&#10003; xong</span>';
    } else if (status === 'FAILED' || status === 'failed' || (typeof status === 'number' && status >= 400)) {
      badgeHtml = '<span class="badge badge-fail">&#10007; lỗi</span>';
    } else if (status === 'PROCESSING' || status === 'processing') {
      badgeHtml = '<span class="badge badge-proc">&#9203; đang tạo...</span>';
    } else {
      badgeHtml = '<span class="badge badge-proc">&#9203; đã gửi</span>';
    }

    const errorDisplay = error
      ? `<td class="td-error" title="${escHtml(error)}">${escHtml(truncate(error, 28))}</td>`
      : `<td class="td-error empty">—</td>`;

    return `<tr>
      <td class="td-id" data-request-id="${escHtml(entry.id || '')}">${escHtml(shortId)}</td>
      <td class="td-type ${typeCls}">${escHtml(type)}</td>
      <td class="td-time">${escHtml(time)}</td>
      <td>${badgeHtml}</td>
      ${errorDisplay}
    </tr>`;
  });

  tbody.innerHTML = rows.join('');

  // Attach click handlers to ID cells
  tbody.querySelectorAll('.td-id[data-request-id]').forEach(td => {
    td.addEventListener('click', () => {
      const reqId = td.getAttribute('data-request-id');
      if (reqId) showRequestDetail(reqId);
    });
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(str, len) {
  if (!str || str.length <= len) return str;
  return str.slice(0, len) + '…';
}

// ── Request detail modal ────────────────────────────────────

let _logEntries = [];

function showRequestDetail(reqId) {
  const entry = _logEntries.find(e => e.id === reqId);
  if (!entry) return;

  const overlay = document.getElementById('detail-overlay');
  const title = document.getElementById('detail-title');
  const body = document.getElementById('detail-body');

  title.textContent = `Chi tiết thao tác ${String(reqId).slice(0, 12)}`;

  const fields = [
    ['Mã ID', entry.id],
    ['Thao tác', formatType(entry.type || entry.method, entry)],
    ['Thời gian', formatTime(entry.time || entry.timestamp || entry.createdAt)],
    ['Trạng thái', entry.status || entry.state || 'pending'],
    ['Mã HTTP', entry.httpStatus || '—'],
    ['Đường dẫn URL', entry.url || '—'],
    ['Dữ liệu gửi', entry.payloadSummary || '—'],
    ['Kết quả nhận', entry.responseSummary || '—'],
    ['Thông báo lỗi', entry.error || '—'],
  ];

  body.innerHTML = fields.map(([label, value]) => {
    let cls = 'detail-value';
    if (label === 'Error' && value && value !== '—') cls += ' error';
    if (label === 'Status' && (value === 'COMPLETED' || value === 'success')) cls += ' ok';
    return `<div class="detail-row">
      <div class="detail-label">${escHtml(label)}</div>
      <div class="${cls}">${escHtml(String(value || '—'))}</div>
    </div>`;
  }).join('');

  overlay.classList.add('open');
}

document.getElementById('detail-close').addEventListener('click', () => {
  document.getElementById('detail-overlay').classList.remove('open');
});

document.getElementById('detail-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) {
    e.currentTarget.classList.remove('open');
  }
});

// ── Initial data fetch ───────────────────────────────────────

function fetchStatus() {
  chrome.runtime.sendMessage({ type: 'STATUS' }, (data) => {
    if (chrome.runtime.lastError) return;
    updateStatus(data);
  });
}

function fetchLog() {
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG' }, (data) => {
    if (chrome.runtime.lastError) return;
    if (data && data.log) updateRequestLog(data.log);
  });
}

// ── Message listener (push updates) ─────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'STATUS_PUSH') {
    fetchStatus();
  }
  if (msg.type === 'REQUEST_LOG_UPDATE') {
    if (msg.log) updateRequestLog(msg.log);
  }
});

// ── Toggle (connect / disconnect) ───────────────────────────

document.getElementById('main-toggle').addEventListener('change', (e) => {
  const msgType = e.target.checked ? 'RECONNECT' : 'DISCONNECT';
  chrome.runtime.sendMessage({ type: msgType }, () => {
    if (chrome.runtime.lastError) return;
    setTimeout(fetchStatus, 400);
  });
});

// ── Action buttons ───────────────────────────────────────────

document.getElementById('btn-flow').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'OPEN_FLOW_TAB' }, () => {
    if (chrome.runtime.lastError) return;
  });
});

document.getElementById('btn-token').addEventListener('click', () => {
  const btn = document.getElementById('btn-token');
  btn.textContent = 'Opening...';
  btn.disabled = true;
  chrome.runtime.sendMessage({ type: 'REFRESH_TOKEN' }, () => {
    if (chrome.runtime.lastError) { /* ignore */ }
    btn.textContent = 'Refresh Token';
    btn.disabled = false;
  });
});

document.getElementById('btn-clear-log').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'CLEAR_REQUEST_LOG' }, () => {
    if (chrome.runtime.lastError) return;
    updateRequestLog([]);
  });
});

document.getElementById('btn-reload-ext')?.addEventListener('click', () => {
  const btn = document.getElementById('btn-reload-ext');
  btn.textContent = 'Reloading...';
  chrome.runtime.sendMessage({ type: 'RELOAD_EXTENSION' });
  setTimeout(() => window.location.reload(), 600);
});

// ── Init ─────────────────────────────────────────────────────

function bootOps() {
  // Keep background worker alive while side panel is open
  try {
    const _port = chrome.runtime.connect({ name: 'FLOW_KEEPALIVE' });
    _port.onDisconnect.addListener(() => {});
  } catch (e) {}

  fetchStatus();
  fetchLog();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootOps);
} else {
  bootOps();
}
