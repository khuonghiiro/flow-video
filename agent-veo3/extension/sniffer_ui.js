/**
 * Flow Kit — API Sniffer UI Controller
 * Manages tab switching, preset saving/loading, dynamic pattern inputs,
 * live log rendering, AI log formatting, and diff comparisons.
 */

(function () {
  'use strict';

  // ── Default Presets ──────────────────────────────────────────────
  const DEFAULT_PRESETS = [
    {
      id: 'preset_veo3',
      name: '⚡ [Mẫu 1] Veo3 Video & Interpolate',
      reason: 'Phân tích tham số request & response khi tạo video Veo3 hoặc nối frame',
      patterns: [
        { url: 'batchexecute?rpcids=YhhmEf', desc: 'Tạo video Veo3 từ prompt (T2V Veo 3.1)' },
        { url: 'batchexecute?rpcids=jwpduf', desc: 'Kiểm tra trạng thái render video (Poll Video Status)' },
        { url: 'batchexecute?rpcids=nprQif', desc: 'Nối frame video giữa 2 ảnh (Start-End Frame Interpolate)' },
        { url: 'batchexecute?rpcids=eb1hJf', desc: 'Tạo video Veo3 từ 1 ảnh hoặc prompt (I2V / T2V)' },
        { url: 'batchexecute?rpcids=MZZa6b', desc: 'Tạo video từ ảnh tham chiếu nhân vật (R2V)' },
        { url: 'batchAsyncGenerateVideo', desc: 'API tạo video Veo3 bất đồng bộ (REST)' },
      ],
    },
    {
      id: 'preset_project',
      name: '📁 [Mẫu 2] Dự Án & Đổi Tên Asset',
      reason: 'Bắt các API quản lý dự án (jHPbke, o8DA4) và đổi tên asset (mYWVGd)',
      patterns: [
        { url: 'batchexecute?rpcids=jHPbke', desc: 'Tạo mới dự án trên Google Flow (Create Project)' },
        { url: 'batchexecute?rpcids=o8DA4', desc: 'Cập nhật tiêu đề dự án (Sync Project Title)' },
        { url: 'batchexecute?rpcids=mYWVGd', desc: 'Đổi tên asset / media node (Rename Asset)' },
      ],
    },
    {
      id: 'preset_images',
      name: '🎨 [Mẫu 3] Tạo & Upload Ảnh Ref',
      reason: 'Bắt API upload ảnh và sinh ảnh tham chiếu từ prompt',
      patterns: [
        { url: 'uploadImage', desc: 'Tải ảnh lên hệ thống Flow (Upload Image)' },
        { url: 'batchexecute?rpcids=ogiZ0b', desc: 'Tạo ảnh từ text prompt (Image Generation)' },
        { url: 'batchexecute?rpcids=maseQ', desc: 'RPC tải lên file media ảnh' },
      ],
    },
  ];

  let _presets = [...DEFAULT_PRESETS];
  let _currentPresetId = 'preset_veo3';
  let _snifferLogs = [];
  let _isSnifferEnabled = true;

  // ── Toast Notification Helper ────────────────────────────────────
  function showToast(message) {
    let toast = document.getElementById('sniffer-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'sniffer-toast';
      toast.className = 'toast-msg';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2400);
  }

  // ── Tab Navigation & Injection Status ─────────────────────────────
  let _statusInterval = null;
  let _lastTargetTabId = null;

  async function checkInjectionStatus(manual = false) {
    const dot = document.getElementById('hook-status-dot');
    const title = document.getElementById('hook-status-title');
    const sub = document.getElementById('hook-status-sub');
    const btnFix = document.getElementById('btn-fix-injection');
    const btnOpen = document.getElementById('btn-open-flow');
    const banner = document.querySelector('.status-banner-card');

    if (!dot || !title || !sub) return;

    try {
      const allTabs = await chrome.tabs.query({});
      const tabs = allTabs.filter(t => t.url && (
        t.url.includes('flow.google.com') ||
        t.url.includes('labs.google') ||
        t.url.includes('aisandbox')
      ));

      if (!tabs || tabs.length === 0) {
        if (banner) banner.className = 'sniffer-card-box status-banner-card error-state';
        dot.className = 'status-dot';
        title.textContent = '⚪ Chưa mở tab Google Flow';
        sub.textContent = 'Nhấp "Mở Flow" để mở trang và bắt đầu';
        if (btnFix) btnFix.style.display = 'none';
        if (btnOpen) btnOpen.style.display = 'inline-flex';
        _lastTargetTabId = null;
        if (manual) showToast('Chưa tìm thấy tab Google Flow nào đang mở.');
        return;
      }

      const [currentActive] = await chrome.tabs.query({ active: true, currentWindow: true });
      const targetTab = (currentActive && currentActive.url && (currentActive.url.includes('flow.google.com') || currentActive.url.includes('labs.google')))
        ? currentActive
        : tabs[0];

      _lastTargetTabId = targetTab.id;

      let response = null;
      try {
        response = await chrome.tabs.sendMessage(targetTab.id, { type: 'CHECK_SNIFFER_INJECTION' });
      } catch (sendErr) {
        // Tab exists but content script hasn't responded (e.g. extension just reloaded)
      }

      // If not ready, attempt auto-injection on the fly via chrome.scripting
      if (!response || !response.mainScriptReady) {
        try {
          if (chrome.scripting) {
            await chrome.scripting.executeScript({
              target: { tabId: targetTab.id },
              files: ['content.js'],
            });
            await chrome.scripting.executeScript({
              target: { tabId: targetTab.id },
              world: 'MAIN',
              files: ['injected.js'],
            });
            response = await chrome.tabs.sendMessage(targetTab.id, { type: 'CHECK_SNIFFER_INJECTION' }).catch(() => null);
          }
        } catch (injectErr) {
          console.warn('[SnifferUI] Auto-inject attempt failed:', injectErr);
        }
      }

      if (response && response.mainScriptReady) {
        if (banner) banner.className = 'sniffer-card-box status-banner-card';
        dot.className = 'status-dot active pulse';
        title.textContent = '🟢 Hook JS: Đã Inject (Sẵn sàng)';
        const displayUrl = (targetTab.url || '').replace(/^https?:\/\//i, '').split('?')[0];
        sub.textContent = `Tab: ${targetTab.title || displayUrl}`;
        if (btnFix) btnFix.style.display = 'none';
        if (btnOpen) btnOpen.style.display = 'none';
        if (manual) showToast('🟢 Hook JS đang hoạt động ổn định trên tab Flow!');
      } else {
        if (banner) banner.className = 'sniffer-card-box status-banner-card warning-state';
        dot.className = 'status-dot warning pulse';
        title.textContent = '🟠 Hook JS: Chưa nạp vào trang Flow';
        sub.textContent = 'Extension vừa tải lại. Nhấp "Tải lại tab" để nạp hook';
        if (btnFix) btnFix.style.display = 'inline-flex';
        if (btnOpen) btnOpen.style.display = 'none';
        if (manual) showToast('Cần tải lại tab Flow để kích hoạt hook script.');
      }
    } catch (e) {
      console.warn('[SnifferUI] checkInjectionStatus error:', e);
    }
  }

  function initTabs() {
    const tabOpsBtn = document.getElementById('tab-btn-ops');
    const tabSniffBtn = document.getElementById('tab-btn-sniff');
    const tabOpsView = document.getElementById('tab-view-ops');
    const tabSniffView = document.getElementById('tab-view-sniff');

    if (!tabOpsBtn || !tabSniffBtn || !tabOpsView || !tabSniffView) return;

    tabOpsBtn.addEventListener('click', () => {
      tabOpsBtn.classList.add('active');
      tabSniffBtn.classList.remove('active');
      tabOpsView.style.display = 'flex';
      tabSniffView.style.display = 'none';
      if (_statusInterval) {
        clearInterval(_statusInterval);
        _statusInterval = null;
      }
    });

    tabSniffBtn.addEventListener('click', () => {
      tabSniffBtn.classList.add('active');
      tabOpsBtn.classList.remove('active');
      tabOpsView.style.display = 'none';
      tabSniffView.style.display = 'flex';
      checkInjectionStatus();
      if (!_statusInterval) {
        _statusInterval = setInterval(checkInjectionStatus, 2500);
      }
    });
  }

  // ── Preset Management ────────────────────────────────────────────
  function renderPresetDropdown() {
    const select = document.getElementById('sniffer-preset-select');
    if (!select) return;

    select.innerHTML = '';

    // Custom option
    const customOpt = document.createElement('option');
    customOpt.value = '__custom__';
    customOpt.textContent = '✏️ -- Tùy chỉnh (Nhập mới) --';
    select.appendChild(customOpt);

    _presets.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      if (p.id === _currentPresetId) opt.selected = true;
      select.appendChild(opt);
    });

    if (_currentPresetId === '__custom__') {
      customOpt.selected = true;
    }
  }

  function applyPreset(presetId) {
    _currentPresetId = presetId;
    const titleEl = document.getElementById('sniffer-title');
    const reasonEl = document.getElementById('sniffer-reason');

    if (presetId === '__custom__') {
      if (titleEl) {
        titleEl.value = '';
        titleEl.placeholder = 'Nhập tên tiêu đề cho cấu hình mới...';
        titleEl.focus();
      }
      if (reasonEl) reasonEl.value = '';
      renderPatternInputs(['']);
      saveActiveConfig();
      return;
    }

    const preset = _presets.find(p => p.id === presetId);
    if (!preset) return;

    if (titleEl) {
      titleEl.value = preset.name.replace(/^[^\w\sÀ-ỹ\[\]]+/u, '').trim();
    }
    if (reasonEl) reasonEl.value = preset.reason || '';

    renderPatternInputs(preset.patterns || []);
    saveActiveConfig();
  }

  function loadPresetsFromStorage() {
    chrome.storage.local.get(['sniffer_presets', 'sniffer_current_preset', 'sniffer_enabled', 'sniffer_title', 'sniffer_reason', 'sniffer_patterns', 'sniffer_logs'], (res) => {
      if (chrome.runtime.lastError) return;

      if (Array.isArray(res.sniffer_presets) && res.sniffer_presets.length > 0) {
        _presets = res.sniffer_presets;
      } else {
        _presets = [...DEFAULT_PRESETS];
      }

      if (res.sniffer_enabled !== undefined) {
        _isSnifferEnabled = !!res.sniffer_enabled;
      }

      const toggle = document.getElementById('sniffer-active-toggle');
      const text = document.getElementById('sniffer-status-text');
      if (toggle) toggle.checked = _isSnifferEnabled;
      if (text) {
        text.textContent = _isSnifferEnabled ? 'ĐANG BẬT' : 'ĐÃ TẮT';
        text.className = `switch-badge ${_isSnifferEnabled ? 'active' : 'inactive'}`;
      }

      _currentPresetId = res.sniffer_current_preset || _presets[0].id;
      renderPresetDropdown();

      const currentPreset = _presets.find(p => p.id === _currentPresetId);
      if (currentPreset) {
        const titleEl = document.getElementById('sniffer-title');
        const reasonEl = document.getElementById('sniffer-reason');
        if (titleEl) titleEl.value = currentPreset.name.replace(/^[^\w\sÀ-ỹ\[\]]+/u, '').trim();
        if (reasonEl) reasonEl.value = currentPreset.reason || '';
        renderPatternInputs(currentPreset.patterns || []);
      } else if (res.sniffer_patterns && res.sniffer_patterns.length > 0) {
        const titleEl = document.getElementById('sniffer-title');
        const reasonEl = document.getElementById('sniffer-reason');
        if (titleEl && res.sniffer_title) titleEl.value = res.sniffer_title;
        if (reasonEl && res.sniffer_reason) reasonEl.value = res.sniffer_reason;
        renderPatternInputs(res.sniffer_patterns);
      } else {
        applyPreset(_currentPresetId);
      }

      if (Array.isArray(res.sniffer_logs)) {
        _snifferLogs = sortLogsAsc(res.sniffer_logs);
        renderLogList();
      }
    });
  }

  function saveCurrentAsPreset({ notify = true } = {}) {
    const rawTitle = (document.getElementById('sniffer-title')?.value || '').trim();
    const reason = document.getElementById('sniffer-reason')?.value || '';
    const patterns = getActivePatterns();

    if (patterns.length === 0) {
      alert('Vui lòng nhập ít nhất 1 pattern URL trước khi lưu bộ lọc!');
      return null;
    }

    // Auto-generate a readable title if empty
    let title = rawTitle;
    if (!title) {
      const firstPatUrl = typeof patterns[0] === 'object' ? (patterns[0].url || '') : String(patterns[0] || '');
      const firstPat = firstPatUrl.replace(/^.*[?&]rpcids=/, '').replace(/^\/+/, '').slice(0, 24);
      title = firstPat ? `Bắt API ${firstPat}` : `Mẫu Bắt API ${new Date().toLocaleTimeString('vi-VN')}`;
      const titleEl = document.getElementById('sniffer-title');
      if (titleEl) titleEl.value = title;
    }

    const isSystemDefault = ['preset_veo3', 'preset_project', 'preset_images'].includes(_currentPresetId);
    let targetId = _currentPresetId;

    if (isSystemDefault || _currentPresetId === '__custom__') {
      targetId = 'preset_' + Date.now();
      const newPreset = {
        id: targetId,
        name: `💾 ${title}`,
        reason,
        patterns,
      };
      _presets.push(newPreset);
    } else {
      const existing = _presets.find(p => p.id === targetId);
      if (existing) {
        existing.name = `💾 ${title.replace(/^💾\s*/, '')}`;
        existing.reason = reason;
        existing.patterns = patterns;
      } else {
        targetId = 'preset_' + Date.now();
        _presets.push({ id: targetId, name: `💾 ${title}`, reason, patterns });
      }
    }

    _currentPresetId = targetId;

    chrome.storage.local.set({
      sniffer_presets: _presets,
      sniffer_current_preset: _currentPresetId,
      sniffer_title: title,
      sniffer_reason: reason,
      sniffer_patterns: patterns,
      sniffer_enabled: _isSnifferEnabled,
    }, () => {
      renderPresetDropdown();
      // Synchronize config to open tabs and background
      chrome.runtime.sendMessage({
        type: 'SYNC_SNIFFER_CONFIG',
        config: { enabled: _isSnifferEnabled, patterns, reason, title },
      }).catch(() => {});
      if (notify) {
        showToast(`Đã lưu mẫu "${title}" vào Combobox & áp dụng!`);
      }
    });

    return targetId;
  }

  function deleteCurrentPreset() {
    if (_currentPresetId.startsWith('preset_veo3') || _currentPresetId.startsWith('preset_project') || _currentPresetId.startsWith('preset_images')) {
      alert('Không thể xóa mẫu mặc định của hệ thống!');
      return;
    }
    if (!confirm('Bạn có chắc muốn xóa mẫu cấu hình này?')) return;

    _presets = _presets.filter(p => p.id !== _currentPresetId);
    _currentPresetId = _presets[0]?.id || '__custom__';

    chrome.storage.local.set({ sniffer_presets: _presets, sniffer_current_preset: _currentPresetId }, () => {
      renderPresetDropdown();
      applyPreset(_currentPresetId);
      showToast('Đã xóa mẫu cấu hình.');
    });
  }

  // ── Dynamic Pattern Inputs ───────────────────────────────────────
  function getActivePatterns() {
    const list = document.getElementById('pattern-list');
    if (!list) return [];
    const cards = list.querySelectorAll('.pattern-card');
    const patterns = [];
    cards.forEach(card => {
      const url = card.querySelector('.pattern-input')?.value.trim() || '';
      const desc = card.querySelector('.pattern-desc-input')?.value.trim() || '';
      if (url) {
        patterns.push({ url, desc });
      }
    });
    return patterns;
  }

  function createPatternRow(patternData = '', index = 1) {
    const urlVal = typeof patternData === 'object' ? (patternData.url || '') : String(patternData || '');
    const descVal = typeof patternData === 'object' ? (patternData.desc || '') : '';

    const card = document.createElement('div');
    card.className = 'pattern-card';

    // Header row
    const headerRow = document.createElement('div');
    headerRow.className = 'pattern-header-row';

    const label = document.createElement('span');
    label.className = 'pattern-badge-title';
    label.textContent = `API #${index}`;

    const delBtn = document.createElement('button');
    delBtn.className = 'btn-del-pattern';
    delBtn.innerHTML = '&times;';
    delBtn.title = 'Xóa API này khỏi bộ lọc';
    delBtn.addEventListener('click', () => {
      card.remove();
      saveActiveConfig();
      document.querySelectorAll('#pattern-list .pattern-badge-title').forEach((el, i) => {
        el.textContent = `API #${i + 1}`;
      });
    });

    headerRow.appendChild(label);
    headerRow.appendChild(delBtn);

    // Main row: URL pattern input
    const mainRow = document.createElement('div');
    mainRow.className = 'pattern-main-row';

    const urlInput = document.createElement('input');
    urlInput.type = 'text';
    urlInput.className = 'pattern-input';
    urlInput.placeholder = 'URL pattern (ví dụ: batchexecute?rpcids=nprQif)';
    urlInput.value = urlVal;

    urlInput.addEventListener('input', () => {
      if (_currentPresetId !== '__custom__' && ['preset_veo3', 'preset_project', 'preset_images'].includes(_currentPresetId)) {
        document.getElementById('sniffer-preset-select').value = '__custom__';
        _currentPresetId = '__custom__';
      }
    });

    mainRow.appendChild(urlInput);

    // Description row: API purpose description for AI
    const descInput = document.createElement('input');
    descInput.type = 'text';
    descInput.className = 'pattern-desc-input';
    descInput.placeholder = '💡 Mô tả chức năng API cho AI hiểu (ví dụ: Nối frame video giữa 2 ảnh...)';
    descInput.value = descVal;

    descInput.addEventListener('input', () => {
      if (_currentPresetId !== '__custom__' && ['preset_veo3', 'preset_project', 'preset_images'].includes(_currentPresetId)) {
        document.getElementById('sniffer-preset-select').value = '__custom__';
        _currentPresetId = '__custom__';
      }
    });

    card.appendChild(headerRow);
    card.appendChild(mainRow);
    card.appendChild(descInput);

    return card;
  }

  function renderPatternInputs(patterns = []) {
    const list = document.getElementById('pattern-list');
    if (!list) return;
    list.innerHTML = '';

    if (patterns.length === 0) {
      list.appendChild(createPatternRow('', 1));
    } else {
      patterns.forEach((p, idx) => list.appendChild(createPatternRow(p, idx + 1)));
    }
  }

  function addPatternInput(patternData = '') {
    const list = document.getElementById('pattern-list');
    if (!list) return;
    const count = list.querySelectorAll('.pattern-card').length + 1;
    const card = createPatternRow(patternData, count);
    list.appendChild(card);
    card.querySelector('.pattern-input')?.focus();
  }

  // ── Sync and Save Config ─────────────────────────────────────────
  function saveActiveConfig() {
    const title = document.getElementById('sniffer-title')?.value || '';
    const reason = document.getElementById('sniffer-reason')?.value || '';
    const patterns = getActivePatterns();
    const enabled = _isSnifferEnabled;

    const payload = {
      sniffer_enabled: enabled,
      sniffer_title: title,
      sniffer_reason: reason,
      sniffer_patterns: patterns,
      sniffer_current_preset: _currentPresetId,
    };

    chrome.storage.local.set(payload, () => {
      // Broadcast to background and all open tabs
      chrome.runtime.sendMessage({
        type: 'SYNC_SNIFFER_CONFIG',
        config: { enabled, patterns, reason, title },
      }).catch(() => {});

      // Direct broadcast to all Flow tabs
      chrome.tabs.query({}).then((allTabs) => {
        const flowTabs = allTabs.filter(t => t.url && (t.url.includes('flow.google.com') || t.url.includes('labs.google')));
        for (const t of flowTabs) {
          chrome.tabs.sendMessage(t.id, {
            type: 'SYNC_SNIFFER_CONFIG',
            config: { enabled, patterns, reason, title },
          }).catch(() => {});
        }
      }).catch(() => {});
    });
  }

  // ── Live Sniffer Log Rendering ───────────────────────────────────
  function updateCounters() {
    const total = _snifferLogs.length;
    const countEl = document.getElementById('sniffer-count');
    const badgeEl = document.getElementById('sniffer-badge');
    if (countEl) countEl.textContent = total;
    if (badgeEl) {
      badgeEl.textContent = total;
      if (total > 0) {
        badgeEl.classList.add('highlight');
        setTimeout(() => badgeEl.classList.remove('highlight'), 800);
      }
    }
  }

  function sortLogsAsc(logs) {
    if (!Array.isArray(logs)) return [];
    return [...logs].sort((a, b) => {
      const tA = a.time ? new Date(a.time).getTime() : 0;
      const tB = b.time ? new Date(b.time).getTime() : 0;
      return tA - tB; // Từ sớm nhất đến muộn nhất (Top: sớm, Bottom: muộn)
    });
  }

  function renderLogList() {
    const container = document.getElementById('sniffer-log-items');
    if (!container) return;

    _snifferLogs = sortLogsAsc(_snifferLogs);
    updateCounters();

    if (_snifferLogs.length === 0) {
      container.innerHTML = `
        <div class="sniffer-empty-box">
          <div class="empty-icon">🎯</div>
          <div class="empty-title">Chưa Bắt Được API Nào</div>
          <div class="empty-desc">
            1. Đảm bảo trạng thái Hook ở trên đang báo <strong>🟢 Đã Inject</strong>.<br>
            2. Thao tác trên web Flow (tạo video, nối frame, v.v...).<br>
            3. Các API khớp bộ lọc sẽ tự động xuất hiện tại đây.
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = '';

    _snifferLogs.forEach((rec, idx) => {
      const card = document.createElement('div');
      card.className = 'sniffer-card';
      card.dataset.id = rec.id;

      const method = (rec.method || 'POST').toUpperCase();
      const status = rec.status || '...';
      const statusCls = status >= 200 && status < 300 ? 'ok' : (status >= 400 ? 'fail' : 'wait');
      const timeStr = rec.time ? new Date(rec.time).toLocaleTimeString('vi-VN') : '—';
      const shortUrl = (rec.url || '').replace('https://flow.google.com', '').split('?')[0];

      // Decode batchexecute or JSON
      const decodedReq = window.SnifferCore ? window.SnifferCore.decodeBatchexecuteReq(rec.body) : null;
      const parsedResp = window.SnifferCore ? window.SnifferCore.parseResponseBody(rec.responseBody) : null;
      const curlCmd = window.SnifferCore ? window.SnifferCore.generateCurl(rec) : '';

      card.innerHTML = `
        <div class="sniffer-card-header">
          <span class="seq-pill">#${idx + 1}</span>
          <span class="method-pill ${method}">${method}</span>
          <span class="status-pill ${statusCls}">${status}</span>
          <span class="card-title" title="${escapeHtml(rec.url)}">${escapeHtml(shortUrl)}</span>
          ${rec.matchedDesc ? `<span class="desc-pill" title="${escapeHtml(rec.matchedDesc)}">🎯 ${escapeHtml(rec.matchedDesc)}</span>` : ''}
          <span class="card-time">${timeStr}</span>
          <span class="card-expand-icon">&#9654;</span>
        </div>
        <div class="sniffer-card-body">
          ${rec.matchedDesc ? `
          <div class="sub-block">
            <div class="sub-block-title">
              <span>Chức năng / Mô tả API (cho AI):</span>
            </div>
            <div style="color: #93c5fd; font-weight: 600; font-size: 10px;">🎯 ${escapeHtml(rec.matchedDesc)}</div>
          </div>
          ` : ''}
          <div class="sub-block">
            <div class="sub-block-title">
              <span>Đường dẫn đầy đủ:</span>
            </div>
            <div class="code-snippet" style="max-height:50px;">${escapeHtml(rec.url)}</div>
          </div>

          <div class="sub-block">
            <div class="sub-block-title">
              <span>Lệnh cURL:</span>
              <button class="btn-mini-copy btn-copy-curl">Sao chép cURL</button>
            </div>
            <div class="code-snippet">${escapeHtml(curlCmd)}</div>
          </div>

          <div class="sub-block">
            <div class="sub-block-title">
              <span>Dữ liệu gửi (Request Payload):</span>
              <button class="btn-mini-copy btn-copy-req">Sao chép</button>
            </div>
            <div class="code-snippet">${escapeHtml(
              decodedReq ? JSON.stringify(decodedReq.calls, null, 2) : (rec.body || '(Trống)')
            )}</div>
          </div>

          <div class="sub-block">
            <div class="sub-block-title">
              <span>Kết quả nhận (Response Body):</span>
              <button class="btn-mini-copy btn-copy-resp">Sao chép</button>
            </div>
            <div class="code-snippet">${escapeHtml(
              parsedResp?.chunks ? JSON.stringify(parsedResp.chunks, null, 2) : (rec.responseBody || '(Chưa có)')
            )}</div>
          </div>
        </div>
      `;

      // Toggle accordion on header click
      card.querySelector('.sniffer-card-header').addEventListener('click', () => {
        card.classList.toggle('open');
      });

      // Mini copy buttons
      card.querySelector('.btn-copy-curl').addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(curlCmd).then(() => showToast('Đã copy lệnh cURL!'));
      });

      card.querySelector('.btn-copy-req').addEventListener('click', (e) => {
        e.stopPropagation();
        const content = decodedReq ? JSON.stringify(decodedReq.calls, null, 2) : (rec.body || '');
        navigator.clipboard.writeText(content).then(() => showToast('Đã copy Request Payload!'));
      });

      card.querySelector('.btn-copy-resp').addEventListener('click', (e) => {
        e.stopPropagation();
        const content = parsedResp?.chunks ? JSON.stringify(parsedResp.chunks, null, 2) : (rec.responseBody || '');
        navigator.clipboard.writeText(content).then(() => showToast('Đã copy Response Body!'));
      });

      container.appendChild(card);
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Actions ──────────────────────────────────────────────────────
  function copyAiReport() {
    if (_snifferLogs.length === 0) {
      alert('Chưa có request nào trong nhật ký để xuất báo cáo cho AI!');
      return;
    }

    const title = (document.getElementById('sniffer-title')?.value || '').trim();
    const reason = document.getElementById('sniffer-reason')?.value || '';
    const currentPreset = _presets.find(p => p.id === _currentPresetId);
    const configName = title || (currentPreset ? currentPreset.name : 'Tùy chỉnh');

    if (!window.SnifferCore) {
      alert('Lỗi: Chưa tải được engine sniffer_core.js');
      return;
    }

    const isCompact = document.getElementById('chk-compact-report')?.checked !== false;
    const useSharedRefs = document.getElementById('chk-shared-refs')?.checked !== false;

    const reportMarkdown = window.SnifferCore.compileAiReport({
      title,
      reason,
      records: _snifferLogs,
      configName,
      compact: isCompact,
      useSharedRefs: useSharedRefs,
    });

    navigator.clipboard.writeText(reportMarkdown).then(() => {
      let toastMsg = '📋 Đã copy báo cáo cho AI!';
      if (isCompact && useSharedRefs) {
        toastMsg = '⚡ Đã copy báo cáo tối ưu token (Tinh gọn + Tham chiếu biến)!';
      } else if (isCompact) {
        toastMsg = '⚡ Đã copy báo cáo tinh gọn (tiết kiệm token)!';
      }
      showToast(toastMsg);
    }).catch(err => {
      alert('Không thể sao chép vào Clipboard: ' + err);
    });
  }

  function clearSnifferLogs() {
    _snifferLogs = [];
    renderLogList();
    chrome.storage.local.set({ sniffer_logs: [] }, () => {
      showToast('🧹 Đã xóa sạch nhật ký bắt API.');
    });
    chrome.runtime.sendMessage({ type: 'CLEAR_SNIFFER_LOGS' }).catch(() => {});
  }

  // ── Init Event Listeners ─────────────────────────────────────────
  function initEvents() {
    // Preset change
    document.getElementById('sniffer-preset-select')?.addEventListener('change', (e) => {
      const val = e.target.value;
      applyPreset(val);
    });

    // Title input change
    document.getElementById('sniffer-title')?.addEventListener('input', () => {
      if (_currentPresetId !== '__custom__' && ['preset_veo3', 'preset_project', 'preset_images'].includes(_currentPresetId)) {
        document.getElementById('sniffer-preset-select').value = '__custom__';
        _currentPresetId = '__custom__';
      }
    });

    // Reason input change
    document.getElementById('sniffer-reason')?.addEventListener('input', () => {
      if (_currentPresetId !== '__custom__' && ['preset_veo3', 'preset_project', 'preset_images'].includes(_currentPresetId)) {
        document.getElementById('sniffer-preset-select').value = '__custom__';
        _currentPresetId = '__custom__';
      }
    });

    // Save / Delete preset
    document.getElementById('btn-save-preset')?.addEventListener('click', () => {
      saveCurrentAsPreset({ notify: true });
    });
    document.getElementById('btn-delete-preset')?.addEventListener('click', deleteCurrentPreset);

    // Reload Flow tab button
    document.getElementById('btn-fix-injection')?.addEventListener('click', async () => {
      showToast('Đang kết nối lại tab Google Flow...');
      const allTabs = await chrome.tabs.query({});
      const flowTabs = allTabs.filter(t => t.url && (t.url.includes('flow.google.com') || t.url.includes('labs.google')));
      const targetId = _lastTargetTabId || (flowTabs[0] ? flowTabs[0].id : null);

      if (targetId) {
        try {
          if (chrome.scripting) {
            await chrome.scripting.executeScript({ target: { tabId: targetId }, files: ['content.js'] }).catch(() => {});
            await chrome.scripting.executeScript({ target: { tabId: targetId }, world: 'MAIN', files: ['injected.js'] }).catch(() => {});
          }
          await chrome.tabs.reload(targetId);
        } catch {
          await chrome.tabs.reload(targetId);
        }
        setTimeout(() => checkInjectionStatus(false), 2000);
      } else {
        chrome.tabs.create({ url: 'https://flow.google.com/' });
      }
    });

    // Open Flow tab button
    document.getElementById('btn-open-flow')?.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://flow.google.com/' });
    });

    // Manual refresh status button
    document.getElementById('btn-refresh-status')?.addEventListener('click', () => {
      checkInjectionStatus(true);
    });

    // Active switch toggle
    document.getElementById('sniffer-active-toggle')?.addEventListener('change', (e) => {
      _isSnifferEnabled = e.target.checked;
      const text = document.getElementById('sniffer-status-text');
      if (text) {
        text.textContent = _isSnifferEnabled ? 'ĐANG BẬT' : 'ĐÃ TẮT';
        text.className = `switch-badge ${_isSnifferEnabled ? 'active' : 'inactive'}`;
      }
      saveActiveConfig();
      showToast(_isSnifferEnabled ? 'Bắt API: ĐÃ BẬT' : 'Bắt API: ĐÃ TẮT');
    });

    // Add pattern button
    document.getElementById('btn-add-pattern')?.addEventListener('click', () => {
      addPatternInput({ url: '', desc: '' });
    });

    // Quick chips
    document.querySelectorAll('.chips-row .chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const url = chip.dataset.pattern || chip.textContent.trim();
        const desc = chip.dataset.desc || '';
        addPatternInput({ url, desc });
        saveActiveConfig();
        showToast(`Đã thêm bộ lọc: ${url}`);
      });
    });

    // Apply & Save button: Saves as preset into combobox AND activates sniffer
    document.getElementById('btn-apply-config')?.addEventListener('click', () => {
      saveCurrentAsPreset({ notify: true });
    });

    // Test Capture Button (Gửi request mẫu để kiểm tra thông luồng)
    document.getElementById('btn-test-capture')?.addEventListener('click', async () => {
      try {
        const allTabs = await chrome.tabs.query({});
        const flowTabs = allTabs.filter(t => t.url && (
          t.url.includes('flow.google.com') ||
          t.url.includes('labs.google') ||
          t.url.includes('aisandbox')
        ));
        const targetId = _lastTargetTabId || (flowTabs[0] ? flowTabs[0].id : null);
        if (!targetId) {
          showToast('⚠️ Vui lòng mở tab Google Flow trước khi thử nghiệm!');
          return;
        }

        showToast('🚀 Đang gửi request test tới tab Google Flow...');
        await chrome.scripting.executeScript({
          target: { tabId: targetId },
          world: 'MAIN',
          func: () => {
            // Send a test probe fetch matching batchexecute?rpcids=nprQif
            fetch('/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=nprQif&source=test_sniffer_probe', {
              method: 'POST',
              headers: {
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'x-probe-test': 'sniffer-verification',
              },
              body: 'f.req=' + encodeURIComponent('[[["nprQif","[{\\"probe\\":true,\\"test\\":123}]",null,"generic"]]]'),
            }).then(r => r.text()).catch(() => {});
          },
        });

        setTimeout(() => {
          showToast('✅ Đã phát request test! Kiểm tra log bên dưới.');
        }, 300);
      } catch (err) {
        showToast('❌ Lỗi gửi test: ' + err.message);
      }
    });

    // Copy AI Report button
    document.getElementById('btn-copy-ai-log')?.addEventListener('click', copyAiReport);

    // Clear Sniffer button
    document.getElementById('btn-clear-sniffer')?.addEventListener('click', clearSnifferLogs);

    // Reactive update via storage changes (instant 10ms sync)
    chrome.storage.onChanged.addListener((changes, areaName) => {
      if (areaName === 'local' && changes.sniffer_logs) {
        const newLogs = changes.sniffer_logs.newValue;
        if (Array.isArray(newLogs)) {
          _snifferLogs = sortLogsAsc(newLogs);
          renderLogList();
        }
      }
    });

    // Listen for runtime updates from background or content script
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'SNIFFER_RECORD_CAPTURED' && msg.record) {
        const existingIdx = _snifferLogs.findIndex(r => r.id === msg.record.id);
        if (existingIdx !== -1) {
          _snifferLogs[existingIdx] = msg.record;
        } else {
          _snifferLogs.push(msg.record);
        }
        _snifferLogs = sortLogsAsc(_snifferLogs);
        if (_snifferLogs.length > 100) _snifferLogs.shift();
        renderLogList();
      }
      if (msg.type === 'SNIFFER_LOG_UPDATED' && Array.isArray(msg.logs)) {
        _snifferLogs = sortLogsAsc(msg.logs);
        renderLogList();
      }
    });

    // Fallback sync with storage every 1.5s
    setInterval(() => {
      chrome.storage.local.get(['sniffer_logs'], (res) => {
        if (Array.isArray(res?.sniffer_logs) && res.sniffer_logs.length !== _snifferLogs.length) {
          _snifferLogs = sortLogsAsc(res.sniffer_logs);
          renderLogList();
        }
      });
    }, 1500);
  }

  // ── Auto Init On DOM Ready (Fix race condition) ───────────────────
  function bootSniffer() {
    initTabs();
    initEvents();
    loadPresetsFromStorage();
    checkInjectionStatus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootSniffer);
  } else {
    bootSniffer();
  }
})();
