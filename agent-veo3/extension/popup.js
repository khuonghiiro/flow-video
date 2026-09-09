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

function badgeHtml(status, type = '', entry = null) {
  const isAsync = ['GEN_VID', 'GEN_VID_REF', 'UPSCALE'].includes(type);
  if (status === 'COMPLETED' || status === 'success' || (isAsync && entry?.outputUrl)) {
    return '<span class="badge badge-ok">&#10003; xong</span>';
  } else if (status === 'FAILED' || status === 'failed' || (typeof status === 'number' && status >= 400)) {
    return '<span class="badge badge-fail">&#10007; lỗi</span>';
  } else if (status === 'PROCESSING' || status === 'processing') {
    return '<span class="badge badge-proc">&#9203; đang tạo...</span>';
  } else {
    return '<span class="badge badge-proc">&#9203; đã gửi</span>';
  }
}

function renderLog(entries) {
  const list = document.getElementById('log-list');
  const countEl = document.getElementById('log-count');

  if (!entries || entries.length === 0) {
    list.innerHTML = '<div class="log-empty">Chưa có thao tác nào</div>';
    countEl.textContent = '0';
    return;
  }

  countEl.textContent = entries.length;

  list.innerHTML = entries.map((entry, i) => {
    const shortId = entry.id ? String(entry.id).slice(0, 8) : '—';
    const type = formatType(entry.type || entry.method, entry);
    const typeCls = getTypeClass(entry.type || entry.method, type);
    const time = formatTime(entry.time || entry.timestamp);
    const status = entry.status || 'pending';
    const error = entry.error || '';

    const urlDisplay = entry.url
      ? `<div class="detail-section">
           <div class="detail-label">URL</div>
           <div class="detail-value url" title="${escHtml(entry.url)}">${escHtml(entry.url)}</div>
         </div>`
      : '';

    const payloadDisplay = entry.payloadSummary
      ? `<div class="detail-section">
           <div class="detail-label">Dữ liệu gửi</div>
           <div class="detail-value">${escHtml(entry.payloadSummary)}</div>
         </div>`
      : '';

    const responseDisplay = entry.responseSummary
      ? `<div class="detail-section">
           <div class="detail-label">Kết quả${entry.httpStatus ? ` (${entry.httpStatus})` : ''}</div>
           <div class="detail-value">${escHtml(entry.responseSummary)}</div>
         </div>`
      : '';

    const errorDisplay = error
      ? `<div class="detail-section">
           <div class="detail-label">Lỗi</div>
           <div class="detail-value detail-error">${escHtml(error)}</div>
         </div>`
      : '';

    const hasDetails = entry.url || entry.payloadSummary || entry.responseSummary || error;

    return `<div class="entry" data-idx="${i}">
      <div class="entry-row">
        <span class="entry-id">${escHtml(shortId)}</span>
        <span class="entry-type ${typeCls}">${escHtml(type)}</span>
        <span class="entry-time">${escHtml(time)}</span>
        ${badgeHtml(status, entry.type, entry)}
        ${hasDetails ? '<span class="expand-icon">&#9654;</span>' : '<span class="expand-icon" style="visibility:hidden">&#9654;</span>'}
      </div>
      ${hasDetails ? `<div class="entry-details">${urlDisplay}${payloadDisplay}${responseDisplay}${errorDisplay}</div>` : ''}
    </div>`;
  }).join('');

  // Toggle expand on row click
  list.querySelectorAll('.entry-row').forEach((row) => {
    row.addEventListener('click', () => {
      const entry = row.closest('.entry');
      if (entry.querySelector('.entry-details')) {
        entry.classList.toggle('open');
      }
    });
  });
}

document.getElementById('btn-panel').addEventListener('click', () => {
  chrome.windows.getCurrent((win) => {
    chrome.sidePanel.open({ windowId: win.id });
  });
});

document.getElementById('btn-clear-log')?.addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'CLEAR_REQUEST_LOG' }, () => {
    if (chrome.runtime.lastError) return;
    renderLog([]);
  });
});

document.getElementById('btn-reload-ext')?.addEventListener('click', () => {
  const btn = document.getElementById('btn-reload-ext');
  btn.textContent = '...';
  chrome.runtime.sendMessage({ type: 'RELOAD_EXTENSION' });
  setTimeout(() => window.close(), 400);
});

chrome.runtime.sendMessage({ type: 'REQUEST_LOG' }, (data) => {
  if (chrome.runtime.lastError) return;
  if (data && data.log) renderLog(data.log);
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'REQUEST_LOG_UPDATE' && msg.log) {
    renderLog(msg.log);
  }
});
