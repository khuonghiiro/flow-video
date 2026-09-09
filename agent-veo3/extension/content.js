/**
 * Content script — bridge between background.js and injected.js
 * Injects injected.js into MAIN world to access window.grecaptcha
 */
(function () {
  if (window.__FLOW_CONTENT_INJECTED__) return;
  window.__FLOW_CONTENT_INJECTED__ = true;

  // Keep service worker alive while Google Flow tab is open
  try {
    const _port = chrome.runtime.connect({ name: 'FLOW_KEEPALIVE' });
    _port.onDisconnect.addListener(() => {});
  } catch (e) {}

  try {
    const s = document.createElement('script');
    s.src = chrome.runtime.getURL('injected.js');
    s.onload = () => s.remove();
    (document.head || document.documentElement).appendChild(s);
  } catch (e) {}

  chrome.runtime.onMessage.addListener((msg, _, reply) => {
    if (msg.type !== 'GET_CAPTCHA') return;

    const { requestId, pageAction } = msg;

    const handler = (e) => {
      if (e.detail?.requestId === requestId) {
        window.removeEventListener('CAPTCHA_RESULT', handler);
        clearTimeout(timer);
        reply({ token: e.detail.token, error: e.detail.error });
      }
    };

    const timer = setTimeout(() => {
      window.removeEventListener('CAPTCHA_RESULT', handler);
      reply({ error: 'CONTENT_TIMEOUT' });
    }, 20000);

    window.addEventListener('CAPTCHA_RESULT', handler);

    window.dispatchEvent(new CustomEvent('GET_CAPTCHA', {
      detail: { requestId, pageAction },
    }));

    return true; // keep channel open for async reply
  });

  // ─── TRPC Media URL Monitor ─────────────────────────────────
  // Forward intercepted TRPC responses with media URLs to background.js
  window.addEventListener('TRPC_MEDIA_URLS', (e) => {
    const { url, body } = e.detail || {};
    if (!body) return;
    chrome.runtime.sendMessage({
      type: 'TRPC_MEDIA_URLS',
      trpcUrl: url,
      body,
    }).catch(() => {});
  });

  // ─── Direct Token Capture ───────────────────────────────────
  window.addEventListener('FLOW_TOKEN_CAPTURED', (e) => {
    const token = e.detail?.token;
    if (token) {
      chrome.runtime.sendMessage({
        type: 'TOKEN_CAPTURED',
        token,
      }).catch(() => {});
    }
  });

  // ─── API Sniffer Forwarder ──────────────────────────────────
  const _seenRecordIds = new Set();
  function forwardSniffedRecord(record) {
    if (!record || !record.id) return;
    if (_seenRecordIds.has(record.id)) return;
    _seenRecordIds.add(record.id);
    if (_seenRecordIds.size > 200) {
      const first = _seenRecordIds.values().next().value;
      _seenRecordIds.delete(first);
    }

    // Direct atomic write to storage so UI updates via storage.onChanged immediately
    try {
      chrome.storage.local.get(['sniffer_logs'], (res) => {
        if (chrome.runtime.lastError) return;
        const logs = Array.isArray(res?.sniffer_logs) ? res.sniffer_logs : [];
        const existingIdx = logs.findIndex(r => r.id === record.id);
        if (existingIdx !== -1) {
          logs[existingIdx] = record;
        } else {
          logs.push(record);
        }
        logs.sort((a, b) => {
          const tA = a.time ? new Date(a.time).getTime() : 0;
          const tB = b.time ? new Date(b.time).getTime() : 0;
          return tA - tB;
        });
        if (logs.length > 100) logs.shift();
        chrome.storage.local.set({ sniffer_logs: logs });
      });
    } catch {}

    // Also send runtime message to background and active side panels
    try {
      chrome.runtime.sendMessage({
        type: 'API_SNIFFED_RECORD',
        record,
      }).catch(() => {});
    } catch {}
  }

  window.addEventListener('FLOW_API_SNIFFED', (e) => {
    forwardSniffedRecord(e.detail);
  });

  window.addEventListener('message', (e) => {
    if (e.data && e.data.type === 'FLOW_API_SNIFFED_MSG' && e.data.record) {
      forwardSniffedRecord(e.data.record);
    }
  });

  // Sync config from storage to injected.js on startup
  try {
    chrome.storage.local.get(['sniffer_enabled', 'sniffer_patterns'], (res) => {
      if (chrome.runtime.lastError) return;
      if (res && res.sniffer_patterns) {
        window.dispatchEvent(new CustomEvent('UPDATE_SNIFFER_CONFIG', {
          detail: {
            enabled: res.sniffer_enabled !== undefined ? !!res.sniffer_enabled : true,
            patterns: res.sniffer_patterns || [],
          },
        }));
      }
    });
  } catch {}

  // Listen for config changes pushed from extension UI
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'SYNC_SNIFFER_CONFIG' && msg.config) {
      window.dispatchEvent(new CustomEvent('UPDATE_SNIFFER_CONFIG', {
        detail: msg.config,
      }));
      sendResponse({ ok: true });
      return true;
    }

    if (msg.type === 'CHECK_SNIFFER_INJECTION') {
      const isMainReady = document.documentElement.dataset.flowSnifferReady === 'true';
      sendResponse({
        ok: true,
        contentScriptReady: true,
        mainScriptReady: isMainReady,
        url: window.location.href,
        hostname: window.location.hostname,
        title: document.title,
        timestamp: Date.now(),
      });
      return true;
    }

    if (msg.type === 'RELOAD_FLOW_TAB') {
      window.location.reload();
      sendResponse({ ok: true });
      return true;
    }

    if (msg.type === 'REINJECT_SNIFFER') {
      try {
        const s = document.createElement('script');
        s.src = chrome.runtime.getURL('injected.js?t=' + Date.now());
        s.onload = () => s.remove();
        (document.head || document.documentElement).appendChild(s);
        sendResponse({ ok: true });
      } catch (err) {
        sendResponse({ ok: false, error: String(err) });
      }
      return true;
    }
  });
})();
