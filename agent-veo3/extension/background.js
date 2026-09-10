const AGENT_WS_URL = 'ws://127.0.0.1:9222';
const API_KEY = 'AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY';
const RECAPTCHA_SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

const flowUrls = [
  'https://flow.google.com/*',
  'https://labs.google/fx/tools/flow*',
  'https://labs.google/fx/*/tools/flow*',
];
const FLOW_TAB_URL = 'https://flow.google.com/';

// ─── Side Panel on Action Click ────────────────────────────
if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.warn('Failed to setPanelBehavior:', error));
}

if (chrome.action && chrome.action.onClicked) {
  chrome.action.onClicked.addListener(async (tab) => {
    try {
      if (chrome.sidePanel && chrome.sidePanel.open) {
        if (tab && tab.windowId) {
          await chrome.sidePanel.open({ windowId: tab.windowId });
        } else {
          const [currentTab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (currentTab) {
            await chrome.sidePanel.open({ windowId: currentTab.windowId });
          }
        }
      }
    } catch (err) {
      console.warn('Fallback sidePanel.open failed:', err);
    }
  });
}

let ws = null;
let flowKey = null;
let callbackSecret = null;
let state = 'off';
let manualDisconnect = false;
let metrics = {
  tokenCapturedAt: null,
  requestCount: 0,
  successCount: 0,
  failedCount: 0,
  lastError: null,
};

// ─── URL → Log Type Classifier ─────────────────────────────

// Visible log types — only these appear in the request log
const _VISIBLE_TYPES = new Set([
  'GEN_IMG', 'GEN_VID', 'GEN_VID_INTERPOLATE', 'GEN_VID_REF', 'UPLOAD', 'FETCH_BLOB',
  'UPSCALE', 'CREATE_PROJECT', 'RENAME', 'RENAME_ASSET', 'RENAME_PROJECT',
  'TRACKING', 'URL_REFRESH'
]);

function _classifyRpc(rpcid) {
  if (rpcid === 'ogiZ0b') return 'GEN_IMG';
  if (rpcid === 'eb1hJf') return 'GEN_VID';
  if (rpcid === 'nprQif') return 'GEN_VID_INTERPOLATE';
  if (rpcid === 'MZZa6b') return 'GEN_VID_REF';
  if (rpcid === 'maseQ')  return 'UPLOAD';
  if (rpcid === 'mYWVGd') return 'RENAME';
  if (rpcid === 'jHPbke') return 'CREATE_PROJECT';
  if (rpcid === 'o8DA4')  return 'RENAME_PROJECT';
  if (rpcid === 'wXbhsf') return 'POLL';
  if (rpcid === 'kFhKBc') return 'MEDIA';
  if (rpcid === 'vv2eKe') return 'LIST_MEDIA';
  return `RPC:${rpcid}`;
}

function _classifyApiUrl(url) {
  if (url.includes('uploadImage'))                     return 'UPLOAD';
  if (url.includes('batchGenerateImages'))              return 'GEN_IMG';
  if (url.includes('UpsampleVideo'))                   return 'UPSCALE';
  if (url.includes('ReferenceImages'))                 return 'GEN_VID_REF';
  if (url.includes('batchAsyncGenerateVideo'))          return 'GEN_VID';
  if (url.includes('batchCheckAsync'))                  return 'POLL';
  if (url.includes('upsampleImage'))                   return 'UPS_IMG';
  if (url.includes('/media/'))                         return 'MEDIA';
  if (url.includes('/credits'))                        return 'CREDITS';
  if (url.includes('fetch_blob'))                      return 'FETCH_BLOB';
  return 'API';
}

// ─── Request Log ────────────────────────────────────────────

let requestLog = [];

function addRequestLog(entry) {
  requestLog.unshift(entry);
  if (requestLog.length > 100) requestLog.pop();
  broadcastRequestLog();
}

function updateRequestLog(id, updates) {
  const entry = requestLog.find((e) => e.id === id);
  if (entry) Object.assign(entry, updates);
  broadcastRequestLog();
}

function broadcastRequestLog() {
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG_UPDATE', log: requestLog }).catch(() => {});
}

// ─── Sniffer Logs Storage & Broadcast ───────────────────────
let snifferLogs = [];

function addSnifferLog(record) {
  const existingIdx = snifferLogs.findIndex(r => r.id === record.id);
  if (existingIdx !== -1) {
    snifferLogs[existingIdx] = record;
  } else {
    snifferLogs.push(record);
  }
  snifferLogs.sort((a, b) => {
    const tA = a.time ? new Date(a.time).getTime() : 0;
    const tB = b.time ? new Date(b.time).getTime() : 0;
    return tA - tB;
  });
  if (snifferLogs.length > 100) snifferLogs.shift();
  chrome.storage.local.set({ sniffer_logs: snifferLogs }).catch(() => {});
  chrome.runtime.sendMessage({ type: 'SNIFFER_RECORD_CAPTURED', record }).catch(() => {});
}

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local' && changes.sniffer_logs) {
    snifferLogs = Array.isArray(changes.sniffer_logs.newValue) ? changes.sniffer_logs.newValue : [];
  }
});

let initializationPromise = null;

chrome.runtime.onInstalled.addListener(() => {
  void ensureInitialized();
});
chrome.runtime.onStartup.addListener(() => {
  void ensureInitialized();
});
chrome.alarms.onAlarm.addListener(async (alarm) => {
  await ensureInitialized();
  if (alarm.name === 'reconnect') connectToAgent();
  if (alarm.name === 'keepAlive') keepAlive();
  if (alarm.name === 'token-refresh') {
    await captureTokenFromFlowTab();
  }
});

function ensureInitialized() {
  if (!initializationPromise) {
    initializationPromise = initialize().catch((error) => {
      initializationPromise = null;
      console.error('[FlowAgent] Initialization failed', error);
      throw error;
    });
  }
  return initializationPromise;
}

async function initialize() {
  const data = await chrome.storage.local.get(['flowKey', 'metrics', 'callbackSecret', 'sniffer_logs']);
  if (data.flowKey) flowKey = data.flowKey;
  if (data.metrics) Object.assign(metrics, data.metrics);
  if (data.callbackSecret) callbackSecret = data.callbackSecret;
  if (Array.isArray(data.sniffer_logs)) snifferLogs = data.sniffer_logs;
  connectToAgent();
  chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
  void autoInjectFlowTabs();
}

async function autoInjectFlowTabs() {
  try {
    const allTabs = await chrome.tabs.query({});
    const flowTabs = allTabs.filter(t => t.url && (t.url.includes('flow.google.com') || t.url.includes('labs.google')));
    for (const tab of flowTabs) {
      try {
        await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
      } catch {}
      try {
        await chrome.scripting.executeScript({ target: { tabId: tab.id }, world: 'MAIN', files: ['injected.js'] });
      } catch {}
    }
  } catch {}
}

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && (tab.url.includes('flow.google.com') || tab.url.includes('labs.google'))) {
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
    } catch {}
    try {
      await chrome.scripting.executeScript({ target: { tabId }, world: 'MAIN', files: ['injected.js'] });
    } catch {}
  }
});

// MV3 workers can be suspended and restarted without onStartup firing.
// Rehydrate the persisted Flow key on every worker start.
void ensureInitialized();

// ─── Token Capture ──────────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details?.requestHeaders?.length) return;
    const authHeader = details.requestHeaders.find(
      (h) => h.name?.toLowerCase() === 'authorization',
    );
    const value = authHeader?.value || '';
    if (!value.startsWith('Bearer ya29.')) return;

    const token = value.replace(/^Bearer\s+/i, '').trim();
    if (!token) return;

    // Always update — even if same token string, refresh the timestamp
    flowKey = token;
    metrics.tokenCapturedAt = Date.now();
    chrome.storage.local.set({ flowKey, metrics });
    console.log('[FlowAgent] Bearer token captured');

    // Notify agent
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
  },
  { urls: ['<all_urls>'] },
  ['requestHeaders', 'extraHeaders'],
);

let _latestVideoUrls = [];
if (chrome.webRequest?.onBeforeRequest) {
  chrome.webRequest.onBeforeRequest.addListener(
    (details) => {
      const u = details.url || '';
      if (u.includes('.mp4') || u.includes('/video/') || u.includes('flow-content.google') || (u.includes('/asb/') && !u.includes('=s512') && !u.includes('=s32'))) {
        console.log('[FlowAgent] Captured media URL:', u);
        _latestVideoUrls.push({ url: u, time: Date.now(), method: details.method });
        if (_latestVideoUrls.length > 50) _latestVideoUrls.shift();
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'video_request_captured', url: u }));
        }
      }
    },
    { urls: ['<all_urls>'] }
  );
}

let _capturedBatches = [];
if (chrome.webRequest?.onBeforeRequest) {
  chrome.webRequest.onBeforeRequest.addListener(
    (details) => {
      try {
        if (details.url && details.url.includes('batchexecute')) {
          const raw = details.requestBody?.raw;
          let bodyStr = null;
          if (raw && raw.length > 0 && raw[0].bytes) {
            bodyStr = new TextDecoder().decode(new Uint8Array(raw[0].bytes));
          } else if (details.requestBody?.formData) {
            bodyStr = JSON.stringify(details.requestBody.formData);
          }
          if (bodyStr && (bodyStr.includes('eb1hJf') || bodyStr.includes('f.req'))) {
            console.log('[CAPTURED BATCHEXECUTE]:', details.url, bodyStr.slice(0, 500));
            _capturedBatches.push({
              url: details.url,
              time: Date.now(),
              body: bodyStr
            });
            if (_capturedBatches.length > 20) _capturedBatches.shift();
          }
        }
      } catch (e) {}
    },
    { urls: ['https://flow.google.com/*'] },
    ['requestBody']
  );
}

let _openingFlowTab = false;

async function captureTokenFromFlowTab() {
  const tabs = await chrome.tabs.query({
    url: ['https://flow.google.com/*', 'https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*', 'https://labs.google/*'],
  });
  if (!tabs.length) {
    if (_openingFlowTab) {
      console.log('[FlowAgent] Flow tab already opening, skipping');
      return;
    }
    _openingFlowTab = true;
    try {
      console.log('[FlowAgent] No Flow tab found — opening one in background');
      await chrome.tabs.create({ url: 'https://flow.google.com/', active: false });
      await sleep(3000);
      const retryTabs = await chrome.tabs.query({
        url: ['https://flow.google.com/*', 'https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*', 'https://labs.google/*'],
      });
      if (!retryTabs.length) {
        console.log('[FlowAgent] Flow tab not ready yet after open');
        return;
      }
      await chrome.scripting.executeScript({
        target: { tabId: retryTabs[0].id },
        files: ['content.js'],
      });
      console.log('[FlowAgent] Token refresh triggered on newly opened Flow tab');
    } catch (e) {
      console.error('[FlowAgent] Token refresh failed after opening tab:', e);
    } finally {
      _openingFlowTab = false;
    }
    return;
  }
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      files: ['content.js'],
    });
    console.log('[FlowAgent] Token refresh triggered on Flow tab');
  } catch (e) {
    console.error('[FlowAgent] Token refresh failed:', e);
  }
}

// ─── WebSocket to Agent ─────────────────────────────────────

function connectToAgent() {
  if (manualDisconnect) return;
  if (ws?.readyState === WebSocket.CONNECTING) return;
  if (ws?.readyState === WebSocket.OPEN) return;

  try {
    ws = new WebSocket(AGENT_WS_URL);
  } catch (e) {
    console.error('[FlowAgent] WS connect error:', e);
    scheduleReconnect();
    return;
  }

let _heartbeatTimer = null;
function startWsHeartbeat() {
  if (_heartbeatTimer) clearInterval(_heartbeatTimer);
  _heartbeatTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, 10000);
}

if (chrome.runtime?.onConnect) {
  chrome.runtime.onConnect.addListener((port) => {
    if (port.name === 'FLOW_KEEPALIVE') {
      port.onDisconnect.addListener(() => {});
    }
  });
}

  ws.onopen = () => {
    console.log('[FlowAgent] Connected to agent');
    chrome.alarms.clear('reconnect');
    setState('idle');
    startWsHeartbeat();

    // Token refresh alarm — 45 min gives buffer before ~60 min expiry
    chrome.alarms.create('token-refresh', { periodInMinutes: 45 });

    // Send current state + resend token if we have one
    ws.send(JSON.stringify({
      type: 'extension_ready',
      flowKeyPresent: !!flowKey,
      tokenAge: flowKey && metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
    }));
    if (flowKey) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
  };

  ws.onmessage = async ({ data }) => {
    try {
      const msg = JSON.parse(data);

      if (msg.method === 'batch_rpc') {
        await handleBatchRpc(msg);
      } else if (msg.method === 'api_request') {
        await handleApiRequest(msg);
      } else if (msg.method === 'trpc_request') {
        await handleTrpcRequest(msg);
      } else if (msg.method === 'solve_captcha') {
        await handleSolveCaptcha(msg);
      } else if (msg.method === 'reload_extension') {
        sendToAgent({ id: msg.id, result: { reloading: true } });
        setTimeout(() => chrome.runtime.reload(), 100);
      } else if (msg.method === 'navigate_tab') {
        const { tabId, url } = msg.params || {};
        try {
          let target = tabId;
          if (!target) {
            const act = await chrome.tabs.query({ active: true, currentWindow: true });
            target = act[0]?.id;
          }
          if (target && url) {
            const shouldActivate = msg.params?.active === true;
            await chrome.tabs.update(target, { url, ...(shouldActivate ? { active: true } : {}) });
            sendToAgent({ id: msg.id, result: { updated: true, tabId: target, url } });
          } else {
            sendToAgent({ id: msg.id, error: 'NO_TARGET_OR_URL' });
          }
        } catch (e) {
          sendToAgent({ id: msg.id, error: e.message });
        }
      } else if (msg.method === 'get_status') {
        const allTabs = await chrome.tabs.query({});
        const localData = await chrome.storage.local.get(null);
        if (!flowKey && localData?.flowKey) {
          flowKey = localData.flowKey;
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
          }
        }
        sendToAgent({
          id: msg.id,
          result: {
            state,
            flowKeyPresent: !!flowKey,
            storageKeys: Object.keys(localData || {}),
            manualDisconnect,
            tokenAge: metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
            metrics,
            tabs: allTabs.map(t => ({ id: t.id, url: t.url, active: t.active, title: t.title })),
          },
        });
      } else if (msg.method === 'fetch_blob') {
        const { url } = msg.params || {};
        if (url) {
          addRequestLog({
            id: msg.id,
            type: 'FETCH_BLOB',
            time: new Date().toISOString(),
            status: 'processing',
            url: url.slice(0, 100),
            payloadSummary: 'Tải media blob',
          });
        }
        try {
          const fetchHeaders = {};
          if (flowKey) fetchHeaders['authorization'] = `Bearer ${flowKey}`;
          const resp = await fetch(url, { headers: fetchHeaders, credentials: 'include' });
          if (!resp.ok) {
            updateRequestLog(msg.id, { status: 'failed', error: `HTTP_${resp.status}` });
            sendToAgent({ id: msg.id, status: resp.status, error: `HTTP_${resp.status}` });
          } else {
            const buffer = await resp.arrayBuffer();
            let binary = '';
            const bytes = new Uint8Array(buffer);
            const len = bytes.byteLength;
            const chunkSize = 8192;
            for (let i = 0; i < len; i += chunkSize) {
              binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunkSize, len)));
            }
            const base64Data = btoa(binary);
            updateRequestLog(msg.id, { status: 'success', responseSummary: `${len} bytes` });
            sendToAgent({ id: msg.id, status: 200, size: len, data: base64Data });
          }
        } catch (e) {
          updateRequestLog(msg.id, { status: 'failed', error: e.message });
          sendToAgent({ id: msg.id, status: 500, error: e.message });
        }
      } else if (msg.method === 'get_captured_video_urls') {
        sendToAgent({ id: msg.id, result: _latestVideoUrls });
      } else if (msg.method === 'get_captured_batches') {
        chrome.storage.local.get(['sniffer_logs'], (res) => {
          sendToAgent({ id: msg.id, result: res?.sniffer_logs || [] });
        });
      } else if (msg.method === 'get_sniffer_logs') {
        chrome.storage.local.get(['sniffer_logs'], (res) => {
          sendToAgent({ id: msg.id, result: res?.sniffer_logs || [] });
        });
      } else if (msg.method === 'exec_tab') {
        const { tabId, code } = msg.params || {};
        try {
          let target = tabId;
          if (!target) {
            const tabs = await chrome.tabs.query({ url: flowUrls });
            const projTab = tabs.find(t => t.url && t.url.includes('/project/'));
            const activeTab = tabs.find(t => t.active);
            target = (activeTab?.url && activeTab.url.includes('/project/')) ? activeTab.id : (projTab?.id || activeTab?.id || tabs[0]?.id);
          }
          if (code === 'list_tabs') {
            const all = await chrome.tabs.query({});
            sendToAgent({ id: msg.id, result: all.map(t => ({ id: t.id, url: t.url, title: t.title, active: t.active })) });
          } else if (!target) {
            sendToAgent({ id: msg.id, error: 'NO_TARGET_TAB' });
          } else if (code === 'reload') {
            await chrome.tabs.reload(target);
            sendToAgent({ id: msg.id, result: { success: true, reloaded: true, tabId: target } });
          } else if (code === 'inspect_f2f_ui') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const chips = Array.from(document.querySelectorAll('button, [role="button"]')).filter(e => {
                  const val = (e.innerText || e.getAttribute('aria-label') || '').trim();
                  return val === 'Start' || val === 'End';
                }).map(b => ({
                  text: (b.innerText || '').trim(),
                  tag: b.tagName,
                  class: b.className,
                  html: b.outerHTML.slice(0, 300),
                  parentHtml: b.parentElement?.parentElement?.outerHTML?.slice(0, 600)
                }));
                const promptBar = document.querySelector('textarea, [contenteditable="true"], input[type="text"]')?.outerHTML?.slice(0, 300);
                return {
                  chips,
                  promptBar,
                  activeElement: document.activeElement ? {
                    tag: document.activeElement.tagName,
                    text: document.activeElement.innerText?.slice(0, 50),
                    class: document.activeElement.className
                  } : null
                };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'inspect_full_flow_state') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const chips = Array.from(document.querySelectorAll('.ingredient-bar-container *')).map(e => ({
                  tag: e.tagName,
                  class: e.className,
                  text: (e.innerText || '').trim(),
                  aria: e.getAttribute('aria-label'),
                  src: e.src || e.querySelector('img')?.src,
                }));
                const allButtons = Array.from(document.querySelectorAll('button, mat-select, [role="button"], [role="combobox"]')).map(b => ({
                  tag: b.tagName,
                  class: b.className,
                  text: (b.innerText || '').trim().replace(/\s+/g, ' '),
                  aria: b.getAttribute('aria-label'),
                })).filter(b => b.text && (
                  b.text.includes('Veo') || b.text.includes('Lite') || b.text.includes('Low') ||
                  b.text.includes('Priority') || b.text.includes('Start') || b.text.includes('End') ||
                  b.text.includes('Generate') || b.text.includes('Tạo') || b.text.includes('Video')
                ));
                const canvasImages = Array.from(document.querySelectorAll('img')).map((im, idx) => {
                  const card = im.closest('[role="button"], button, div.card, .card-container, [tabindex]');
                  return {
                    idx,
                    src: im.src?.slice(0, 120),
                    alt: im.alt,
                    class: im.className,
                    cardClass: card?.className,
                    cardTag: card?.tagName,
                  };
                }).filter(i => i.src && (i.src.includes('flow-content.google') || i.src.includes('googleusercontent')));
                return { chips, allButtons, canvasImages };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'get_sniffer_logs_internal') {
            chrome.storage.local.get(['sniffer_logs'], (res) => {
              sendToAgent({ id: msg.id, result: res?.sniffer_logs || [] });
            });
          } else if (code === 'inspect_settings_menu') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const btn = document.querySelector('button.settings-trigger-button, .settings-trigger-button');
                if (btn) btn.click();
                const overlays = Array.from(document.querySelectorAll('.cdk-overlay-pane, mat-dialog-container, [role="menu"], [role="dialog"]')).map(o => ({
                  tag: o.tagName,
                  class: o.className,
                  text: (o.innerText || '').trim().slice(0, 1000),
                  items: Array.from(o.querySelectorAll('button, mat-radio-button, mat-option, [role="menuitem"], [role="option"]')).map(i => ({
                    tag: i.tagName,
                    class: i.className,
                    text: (i.innerText || '').trim(),
                    aria: i.getAttribute('aria-label')
                  }))
                }));
                return { btnFound: !!btn, overlays };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'inspect_cards_and_canvas') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const canvasTiles = Array.from(document.querySelectorAll('img')).map((im, idx) => {
                  const container = im.closest('flow-asset-card, .asset-card, [role="button"], div[tabindex], div.card');
                  return {
                    idx,
                    src: im.src.slice(0, 100),
                    alt: im.alt,
                    containerTag: container?.tagName,
                    containerClass: container?.className,
                    containerText: container?.innerText?.trim()?.replace(/\s+/g, ' ')?.slice(0, 80),
                    containerHtml: container?.outerHTML?.slice(0, 400)
                  };
                }).filter(i => i.src && (i.src.includes('flow-content.google') || i.src.includes('googleusercontent')));
                return { canvasTiles };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'click_canvas_image_and_inspect') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: async () => {
                const allImgs = Array.from(document.querySelectorAll('img')).filter(im => {
                  return im.src.includes('flow-content.google') && !im.closest('.ingredient-bar-container');
                });
                if (!allImgs.length) return { error: 'No canvas images found' };
                const targetImg = allImgs[1] || allImgs[0];
                const card = targetImg.closest('[role="button"], button, div.card, .card-container, [tabindex]') || targetImg;
                card.click();
                await new Promise(r => setTimeout(r, 400));
                
                const buttons = Array.from(document.querySelectorAll('button, [role="menuitem"], [role="button"], a.action')).map(b => ({
                  tag: b.tagName,
                  class: b.className,
                  text: (b.innerText || '').trim().replace(/\s+/g, ' '),
                  aria: b.getAttribute('aria-label'),
                  title: b.getAttribute('title')
                })).filter(b => b.text || b.aria || b.title);
                
                const chips = Array.from(document.querySelectorAll('.ingredient-bar-container *')).map(c => ({
                  tag: c.tagName,
                  class: c.className,
                  text: (c.innerText || '').trim(),
                  aria: c.getAttribute('aria-label')
                }));
                
                return {
                  clickedImg: targetImg.src.slice(0, 100),
                  clickedCardTag: card.tagName,
                  clickedCardClass: card.className,
                  chips,
                  toolbars: buttons.filter(b => {
                    const t = (b.text + ' ' + (b.aria||'') + ' ' + (b.title||'')).toLowerCase();
                    return t.includes('frame') || t.includes('start') || t.includes('end') || t.includes('add') || t.includes('use') || t.includes('prompt');
                  })
                };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'click_swap_frames') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const swapBtn = document.querySelector('button[aria-label="Swap first and last frames"], button.flow-icon-button-transparent:has(mat-icon:contains("swap_horiz"))');
                const allButtons = Array.from(document.querySelectorAll('button'));
                const targetBtn = swapBtn || allButtons.find(b => b.getAttribute('aria-label') === 'Swap first and last frames' || (b.innerText || '').includes('swap_horiz'));
                if (!targetBtn) return { success: false, error: 'Swap button not found' };
                targetBtn.click();
                return { success: true, clicked: 'Swap first and last frames' };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'inspect_canvas_nodes_and_videos') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const nodes = Array.from(document.querySelectorAll('flow-asset-card, .asset-card, .card, div.card-container, [role="button"], div[tabindex]')).map(c => ({
                  tag: c.tagName,
                  class: c.className,
                  text: (c.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 150),
                  hasVideo: !!c.querySelector('video'),
                  hasImg: !!c.querySelector('img'),
                  imgSrc: c.querySelector('img')?.src?.slice(0, 80),
                  videoSrc: c.querySelector('video')?.src?.slice(0, 80)
                })).filter(c => (c.text && c.text.length > 2) || c.hasVideo || c.hasImg);
                const videos = Array.from(document.querySelectorAll('video')).map(v => ({
                  src: v.src,
                  currentSrc: v.currentSrc,
                  duration: v.duration,
                  paused: v.paused,
                  parentText: v.parentElement?.innerText?.slice(0, 100)
                }));
                return {
                  url: window.location.href,
                  title: document.title,
                  nodesCount: nodes.length,
                  nodes: nodes.slice(0, 30),
                  videos
                };
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'inspect_prompt_controls') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: () => {
                const textarea = document.querySelector('textarea, [contenteditable="true"]');
                const container = textarea?.closest('.prompt-container, .prompt-bar, .bottom-bar, form, .input-container') || textarea?.parentElement?.parentElement?.parentElement;
                const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                  tag: b.tagName,
                  class: b.className,
                  text: (b.innerText || '').trim().replace(/\s+/g, ' '),
                  aria: b.getAttribute('aria-label'),
                  title: b.getAttribute('title'),
                  icon: b.querySelector('mat-icon')?.innerText
                })).filter(b => b.aria || b.title || b.text || b.icon);
                return {
                  textareaFound: !!textarea,
                  textareaPlaceholder: textarea?.getAttribute('placeholder'),
                  buttonsCount: buttons.length,
                  buttons
                };
              }
            });
          } else if (code === 'populate_f2f_both_frames') {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: async () => {
                // Step 1: Check what is currently in Start and End
                const chips = Array.from(document.querySelectorAll('.ingredient-bar-container *'));
                const endEmpty = !!document.querySelector('button.empty-chip');
                const swapBtn = Array.from(document.querySelectorAll('button')).find(b => b.getAttribute('aria-label') === 'Swap first and last frames' || (b.innerText || '').includes('swap_horiz'));
                
                // Get canvas images
                const canvasImages = Array.from(document.querySelectorAll('img')).filter(im => {
                  return im.src.includes('flow-content.google') && !im.closest('.ingredient-bar-container');
                });
                
                const report = { initialEndEmpty: endEmpty, canvasImagesCount: canvasImages.length, steps: [] };
                
                // If Start has an image and End is empty, clicking swap moves that image to End!
                if (swapBtn && endEmpty) {
                  swapBtn.click();
                  report.steps.push('Clicked swap button to move Start to End');
                  await new Promise(r => setTimeout(r, 600));
                }
                
                // Now Start is empty (or End has the image). Let's click the first canvas image!
                if (canvasImages.length > 0) {
                  const card0 = canvasImages[0].closest('[role="button"], button, div.card, .card-container, [tabindex]') || canvasImages[0];
                  card0.click();
                  report.steps.push('Clicked first canvas card (frame 1)');
                  await new Promise(r => setTimeout(r, 600));
                }
                
                // Inspect result chips
                const finalChips = Array.from(document.querySelectorAll('.ingredient-bar-container button, .ingredient-bar-container .empty-chip, .ingredient-bar-container img')).map(e => ({
                  tag: e.tagName,
                  class: e.className,
                  text: (e.innerText || '').trim(),
                  src: e.src?.slice(0, 100),
                  aria: e.getAttribute('aria-label')
                }));
                report.finalChips = finalChips;
                return report;
              }
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code === 'click_start_chip' || code === 'click_end_chip') {
            const isEnd = code === 'click_end_chip';
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: (isEndTarget) => {
                const chips = Array.from(document.querySelectorAll('button, [role="button"], .empty-chip, .chip, a')).filter(e => {
                  const v = (e.innerText || e.getAttribute('aria-label') || e.title || '').trim();
                  return v === 'Start' || v === 'End';
                });
                const targetBtn = isEndTarget 
                  ? chips.find(c => (c.innerText || c.getAttribute('aria-label') || '').trim() === 'End') 
                  : chips.find(c => (c.innerText || c.getAttribute('aria-label') || '').trim() === 'Start');
                if (!targetBtn) {
                  return { success: false, error: 'Target chip not found', chipsFound: chips.length, chips: chips.map(c => ({ tag: c.tagName, text: c.innerText })) };
                }
                targetBtn.click();
                targetBtn.focus();
                return {
                  success: true,
                  target: isEndTarget ? 'End' : 'Start',
                  btnClass: targetBtn.className,
                  btnText: targetBtn.innerText,
                  activeElement: document.activeElement ? {
                    tag: document.activeElement.tagName,
                    class: document.activeElement.className,
                    text: document.activeElement.innerText?.slice(0, 30)
                  } : null
                };
              },
              args: [isEnd]
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else if (code && (code.startsWith('http://') || code.startsWith('https://') || code.startsWith('nav:'))) {
            const destUrl = code.startsWith('nav:') ? code.slice(4).trim() : code.trim();
            await chrome.tabs.update(target, { url: destUrl });
            sendToAgent({ id: msg.id, result: { success: true, navigated: true, tabId: target, url: destUrl } });
          } else if (code && code.startsWith('js:')) {
            const rawJs = code.slice(3);
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: (expr) => {
                try {
                  const res = eval(expr);
                  return { success: true, result: res };
                } catch (err) {
                  return { success: false, error: err.message };
                }
              },
              args: [rawJs],
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          } else {
            const results = await chrome.scripting.executeScript({
              target: { tabId: target },
              func: (cmdCode) => {
                const chips = Array.from(document.querySelectorAll('button.empty-chip, button.chip'));
                const startBtn = chips.find(c => c.innerText.trim() === 'Start');
                const endBtn = chips.find(c => c.innerText.trim() === 'End');
                
                if (cmdCode === 'click_first_image') {
                  const imgTiles = Array.from(document.querySelectorAll('img[alt*="user\'s image"]'));
                  if (!imgTiles.length) return { error: 'No image tiles found' };
                  const tile = imgTiles[0].closest('div.card, div[role="button"], div.container, [tabindex]') || imgTiles[0];
                  tile.click();
                  const chips = Array.from(document.querySelectorAll('.ingredient-bar-container *')).map(c => ({
                    tag: c.tagName,
                    class: c.className,
                    text: (c.innerText || '').trim(),
                    src: c.src?.slice(0, 100),
                    html: c.outerHTML.slice(0, 200)
                  }));
                  return { success: true, tileClicked: tile.tagName, chips };
                }
                
                if (cmdCode === 'click_start') {
                  if (!startBtn) return { error: 'Start button not found' };
                  startBtn.click();
                  startBtn.focus();
                  return {
                    success: true,
                    clicked: 'Start',
                    activeElement: document.activeElement ? { tag: document.activeElement.tagName, class: document.activeElement.className } : null,
                    overlayCount: document.querySelectorAll('.cdk-overlay-container, .cdk-overlay-pane').length,
                    overlayHtml: document.querySelector('.cdk-overlay-container')?.innerHTML?.slice(0, 1000)
                  };
                }

                return {
                  startFound: !!startBtn,
                  endFound: !!endBtn,
                  chips: chips.map(c => ({ class: c.className, text: c.innerText.trim(), html: c.outerHTML }))
                };
              },
              args: [code]
            });
            sendToAgent({ id: msg.id, result: results[0]?.result });
          }
        } catch (e) {
          sendToAgent({ id: msg.id, error: e.message });
        }
      } else if (msg.type === 'callback_secret') {
        callbackSecret = msg.secret;
        chrome.storage.local.set({ callbackSecret: msg.secret });
        console.log('[FlowAgent] Received callback secret');
      } else if (msg.type === 'pong') {
        // keepalive response
      } else if (msg.type === 'ping') {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'pong' }));
        }
      } else if (msg.type === 'reload_extension' || msg.method === 'reload_extension') {
        console.log('[FlowAgent] Reloading extension background worker');
        setTimeout(() => chrome.runtime.reload(), 300);
      } else if (msg.type === 'update_request_log') {
        let updated = false;
        if (msg.id) {
          const entry = requestLog.find((e) => e.id === msg.id);
          if (entry) {
            if (msg.status) entry.status = msg.status;
            if (msg.outputUrl) entry.outputUrl = msg.outputUrl;
            updated = true;
          }
        }
        if (!updated && msg.mediaId) {
          const entry = requestLog.find(
            (e) =>
              (e.payloadSummary && e.payloadSummary.includes(msg.mediaId)) ||
              (e.responseSummary && e.responseSummary.includes(msg.mediaId)),
          );
          if (entry) {
            if (msg.status) entry.status = msg.status;
            if (msg.outputUrl) entry.outputUrl = msg.outputUrl;
            updated = true;
          }
        }
        if (!updated) {
          const vidEntry = requestLog.find(
            (e) =>
              ['GEN_VID', 'GEN_VID_REF', 'UPSCALE'].includes(e.type) &&
              (!e.outputUrl || e.status !== 'COMPLETED'),
          );
          if (vidEntry) {
            if (msg.status) vidEntry.status = msg.status;
            if (msg.outputUrl) vidEntry.outputUrl = msg.outputUrl;
            updated = true;
          }
        }
        if (updated) broadcastRequestLog();
      }
    } catch (e) {
      console.error('[FlowAgent] Message error:', e);
    }
  };

  ws.onclose = () => {
    setState('off');
    if (_heartbeatTimer) {
      clearInterval(_heartbeatTimer);
      _heartbeatTimer = null;
    }
    chrome.alarms.clear('token-refresh');
    if (!manualDisconnect) scheduleReconnect();
  };

  ws.onerror = (e) => {
    console.error('[FlowAgent] WS error:', e);
    metrics.lastError = 'WS_ERROR';
    chrome.storage.local.set({ metrics });
  };
}

function scheduleReconnect() {
  chrome.alarms.create('reconnect', { delayInMinutes: 0.083 }); // ~5s
}

function keepAlive() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  } else {
    connectToAgent();
  }
}

function sendToAgent(msg) {
  if (ws?.readyState === WebSocket.OPEN) {
    try { ws.send(JSON.stringify(msg)); } catch (e) {}
  }
  if (msg.id) {
    fetch('http://127.0.0.1:8100/api/ext/callback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msg),
    }).catch(() => {});
  }
}

// ─── reCAPTCHA Solving ──────────────────────────────────────

async function requestCaptchaFromTab(tabId, requestId, pageAction) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab || !tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
      return { error: 'INVALID_TAB_URL' };
    }
  } catch (e) {}

  // 1. Direct MAIN world execution (fastest and most reliable)
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: async (siteKey, action) => {
        const getGre = () => window.grecaptcha?.enterprise || window.grecaptcha;
        let gre = getGre();
        if (!gre) {
          // Wait briefly if tab is still completing initialization
          for (let i = 0; i < 6; i++) {
            await new Promise((r) => setTimeout(r, 500));
            gre = getGre();
            if (gre) break;
          }
        }
        if (!gre) return { error: 'NO_GRECAPTCHA' };
        return await new Promise((resolve) => {
          const timer = setTimeout(() => resolve({ error: 'EXECUTE_TIMEOUT' }), 12000);
          const execute = () => {
            try {
              if (gre.execute) {
                gre.execute(siteKey, { action })
                  .then(tok => { clearTimeout(timer); resolve({ token: tok }); })
                  .catch(err => { clearTimeout(timer); resolve({ error: err?.message || 'EXEC_REJECT' }); });
              } else {
                clearTimeout(timer);
                resolve({ error: 'NO_EXECUTE_FN' });
              }
            } catch (e) {
              clearTimeout(timer);
              resolve({ error: e?.message || 'EXEC_FAIL' });
            }
          };

          if (gre.ready) {
            gre.ready(execute);
          } else {
            execute();
          }
        });
      },
      args: [RECAPTCHA_SITE_KEY, pageAction],
    });

    const res = results[0]?.result;
    if (res?.token) return res;
    console.warn('[FlowAgent] Direct MAIN world captcha result:', res);
  } catch (e) {
    console.warn('[FlowAgent] Direct MAIN world captcha exception:', e);
  }

  // 2. Fallback: message bridge to content script
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const resp = await chrome.tabs.sendMessage(tabId, {
        type: 'GET_CAPTCHA',
        requestId,
        pageAction,
      });
      if (resp) {
        if (resp.token) return resp;
        if (resp.error && resp.error !== 'CONTENT_TIMEOUT') {
          console.warn(`[FlowAgent] Tab returned captcha error: ${resp.error}`);
          return resp;
        }
      }
    } catch (error) {
      const msg = error?.message || '';
      const shouldInject =
        msg.includes('Receiving end does not exist') ||
        msg.includes('Could not establish connection');
      if (shouldInject && attempt === 0) {
        try {
          await chrome.scripting.executeScript({
            target: { tabId },
            files: ['content.js'],
});
          await chrome.scripting.executeScript({
            target: { tabId },
            files: ['injected.js'],
            world: 'MAIN',
          });
        } catch (e) {}
      }
      await sleep(1000);
    }
  }
  return { error: 'NO_CAPTCHA_LISTENER' };
}



async function reviveTabIfNeeded(tab) {
  if (!tab) return null;
  if (tab.discarded) {
    try {
      await chrome.tabs.reload(tab.id);
      await sleep(3000);
      return await chrome.tabs.get(tab.id);
    } catch (e) {
      return null;
    }
  }
  return tab;
}

function captchaFromTab(tabId, requestId, captchaAction, timeoutMs = 60000) {
  return Promise.race([
    requestCaptchaFromTab(tabId, requestId, captchaAction),
    new Promise((_, rej) => setTimeout(() => rej(new Error('CAPTCHA_TIMEOUT')), timeoutMs)),
  ]);
}

async function solveCaptcha(requestId, captchaAction) {
  let tabs = await chrome.tabs.query({ url: flowUrls });

  // No Flow tab at all — spawn one and let it settle.
  if (!tabs.length) {
    try {
      await chrome.tabs.create({ url: FLOW_TAB_URL, active: false });
      await sleep(3500);
      tabs = await chrome.tabs.query({ url: flowUrls });
    } catch (e) {
      return { error: e.message || 'NO_FLOW_TAB' };
    }
    if (!tabs.length) return { error: 'NO_FLOW_TAB' };
  }

  // Try each Flow tab in turn with self-healing recovery.
  const errors = [];
  for (const candidate of tabs) {
    const tab = await reviveTabIfNeeded(candidate);
    if (!tab) continue;
    try {
      let resp = await captchaFromTab(tab.id, requestId, captchaAction, 45000);
      if (!resp?.token) {
        // Tab response lacked token — reload tab once to revive grecaptcha
        try {
          console.warn('[Flow Extension] No token returned, reloading tab to revive grecaptcha...', tab.id);
          await chrome.tabs.reload(tab.id);
          await sleep(4000);
          resp = await captchaFromTab(tab.id, requestId, captchaAction, 45000);
        } catch {}
      }
      if (resp?.token) return resp;
      errors.push(resp?.error || 'NO_TOKEN');
      continue;
    } catch (e) {
      const msg = e?.message || '';
      errors.push(msg);
      if (msg.includes('CAPTCHA_TIMEOUT')) {
        try {
          console.warn('[Flow Extension] Captcha timeout detected. Reloading tab for self-healing...', tab.id);
          await chrome.tabs.reload(tab.id);
          await sleep(4000);
          const retryResp = await captchaFromTab(tab.id, requestId, captchaAction, 45000);
          if (retryResp?.token) return retryResp;
        } catch (reErr) {
          console.error('[Flow Extension] Captcha retry failed:', reErr);
        }
      }
      continue;
    }
  }

  // Every candidate failed — last-ditch, spawn a fresh tab and try it once.
  try {
    console.info('[Flow Extension] Spawning fresh Flow tab to solve captcha...');
    const freshTab = await chrome.tabs.create({ url: FLOW_TAB_URL, active: false });
    await sleep(4500);
    return await captchaFromTab(freshTab.id, requestId, captchaAction, 60000);
  } catch (e) {
    return { error: e?.message || errors[0] || 'NO_FLOW_TAB' };
  }
}

async function handleSolveCaptcha(msg) {
  const { id, params } = msg;
  const result = await solveCaptcha(id, params?.captchaAction || 'VIDEO_GENERATION');

  // Standalone captcha solve counts as captcha-consuming
  metrics.requestCount++;
  if (result?.token) {
    metrics.successCount++;
  } else {
    metrics.failedCount++;
    metrics.lastError = result?.error || 'NO_TOKEN';
  }
  chrome.storage.local.set({ metrics });

  sendToAgent({ id, result });
}

// ─── Page-context RPC runner (the current path) ─────────────
//
// Flow's frontend signs its calls with cookies and a per-page `at` token, and
// every generate carries a single-use reCAPTCHA. None of that can be replayed
// from the service worker, so the request has to be issued by the Flow page
// itself: mint a fresh captcha through the grecaptcha bridge, then run the
// batchexecute POST in the page's MAIN world, where at / f.sid / bl live.

const CAPTCHA_SLOT = '__CAPTCHA__';
const MAX_RPC_TEXT = 32000000; // the project listing alone is past 17 MB

async function runBatchRpc(cmd) {
  const tabs = await chrome.tabs.query({ url: flowUrls });
  let candidate = tabs.find((t) => !t.discarded) || tabs[0];
  if (!candidate) {
    // No Flow tab — open one and give the app a moment to boot, otherwise
    // WIZ_global_data is not on the page yet and `at` comes back empty.
    try {
      await chrome.tabs.create({ url: FLOW_TAB_URL, active: false });
      await sleep(5000);
      const fresh = await chrome.tabs.query({ url: flowUrls });
      candidate = fresh.find((t) => !t.discarded) || fresh[0];
    } catch (e) {
      return { error: e?.message || 'NO_FLOW_TAB' };
    }
    if (!candidate) return { error: 'NO_FLOW_TAB' };
  }
  // Chrome discards backgrounded tabs; executeScript throws on a dead one.
  const tab = await reviveTabIfNeeded(candidate);
  if (!tab) return { error: 'FLOW_TAB_DISCARDED' };

  let freq = cmd.freq;
  if (cmd.captchaAction) {
    const solved = await solveCaptcha(cmd.id, cmd.captchaAction);
    if (!solved?.token) return { error: `CAPTCHA_FAILED: ${solved?.error || 'no token'}` };
    freq = freq.split(CAPTCHA_SLOT).join(solved.token);
  }

  let injected = null;
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: 'MAIN',
      args: [cmd.rpcid, freq, MAX_RPC_TEXT, cmd.match || null],
      func: async (rpcid, freqStr, maxText, match) => {
        try {
          const wiz = globalThis.WIZ_global_data || {};
          const at = wiz.SNlM0e;
          const sid = wiz.FdrFJe;
          const bl = wiz.cfb2h;
          if (!at) return { error: 'NO_AT_TOKEN' };
          const reqid = Math.floor(Math.random() * 900000) + 100000;
          const url =
            `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=${encodeURIComponent(rpcid)}` +
            `&f.sid=${encodeURIComponent(sid || '')}&bl=${encodeURIComponent(bl || '')}` +
            `&hl=en-AU&_reqid=${reqid}&rt=c`;
          const resp = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: {
              'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
              'x-same-domain': '1',
            },
            body: new URLSearchParams({ 'f.req': freqStr, at }),
          });
          const text = await resp.text();
          if (match) {
            const found = text.indexOf(match);
            return {
              status: resp.status,
              matched: found !== -1,
              text: found === -1 ? '' : text.slice(found, found + 800),
            };
          }
          return { status: resp.status, text: text.slice(0, maxText) };
        } catch (fetchErr) {
          return { error: 'FETCH_ERROR: ' + fetchErr.message };
        }
      },
    });
    injected = results?.[0];
  } catch (execErr) {
    return { error: 'EXEC_SCRIPT_ERROR: ' + execErr.message };
  }

  return injected?.result || { error: 'NO_INJECTION_RESULT' };
}

async function handleBatchRpc(msg) {
  const { id, params } = msg;
  const { rpcid, freq, captchaAction, match } = params || {};
  if (!rpcid || !freq) {
    sendToAgent({ id, status: 400, error: 'INVALID_BATCH_RPC' });
    return;
  }

  setState('running');
  const hasCaptcha = !!captchaAction;
  if (hasCaptcha) metrics.requestCount++;
  // Hiển thị các thao tác quan trọng: tạo ảnh, tạo video, nội suy frame to frame, up ảnh, đổi tên, tạo dự án
  const importantRpcs = ['ogiZ0b', 'eb1hJf', 'nprQif', 'maseQ', 'mYWVGd', 'jHPbke', 'o8DA4'];
  const visible = hasCaptcha || importantRpcs.includes(rpcid);
  const logType = _classifyRpc(rpcid);
  if (visible) {
    addRequestLog({
      id, type: logType, time: new Date().toISOString(),
      status: 'processing', error: null, outputUrl: null, url: rpcid,
      payloadSummary: freq.slice(0, 200),
    });
  }

  try {
    const out = await runBatchRpc({ id, rpcid, freq, captchaAction, match });
    if (out.error) {
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = out.error; }
      if (visible) updateRequestLog(id, { status: 'failed', error: out.error });
      sendToAgent({ id, status: 502, error: out.error });
    } else {
      if (hasCaptcha) { metrics.successCount++; metrics.lastError = null; }
      if (visible) {
        updateRequestLog(id, {
          status: 'success', httpStatus: out.status,
          responseSummary: (out.text || '').slice(0, 300),
        });
      }
      sendToAgent({ id, status: out.status, data: out.text });
    }
  } catch (e) {
    const err = e?.message || 'BATCH_RPC_FAILED';
    if (hasCaptcha) { metrics.failedCount++; metrics.lastError = err; }
    if (visible) updateRequestLog(id, { status: 'failed', error: err });
    sendToAgent({ id, status: 500, error: err });
  }

  chrome.storage.local.set({ metrics });
  setState('idle');
}

// ─── API Request Proxy ──────────────────────────────────────

async function handleTrpcRequest(msg) {
  const { id, params } = msg;
  const { url, method = 'POST', headers = {}, body, responseMode } = params;

  if (!url || (!url.startsWith('https://labs.google/') && !url.startsWith('https://flow.google.com/'))) {
    sendToAgent({ id, error: 'INVALID_TRPC_URL' });
    return;
  }

  setState('running');
  // TRPC calls don't consume captcha — don't count in metrics

  const logId = id;
  const logType = url.includes('createProject') ? 'CREATE_PROJECT' : 'TRPC';
  // TRPC calls are silent — don't show in request log

  const fetchHeaders = { 'Content-Type': 'application/json', ...headers };
  if (flowKey) {
    fetchHeaders['authorization'] = `Bearer ${flowKey}`;
  }

  try {
    const resp = await fetch(url, {
      method,
      headers: fetchHeaders,
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'include',
    });
    let data;
    if (responseMode === 'url') {
      // fetch() has already followed the authenticated Flow redirect. Return
      // only the final signed URL and cancel the body so large videos are not
      // buffered in the extension or copied through the WebSocket bridge.
      data = {
        url: resp.url,
        contentType: resp.headers.get('content-type'),
      };
      await resp.body?.cancel();
    } else {
      data = await resp.json();
    }
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, { status: 'success' });
    sendToAgent({ id, status: resp.status, data });
  } catch (e) {
    console.error('[FlowAgent] tRPC request failed:', e);
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, { status: 'failed', error: e.message || 'TRPC_FETCH_FAILED' });
    sendToAgent({ id, error: e.message || 'TRPC_FETCH_FAILED' });
  } finally {
    setState('idle');
  }
}

async function handleApiRequest(msg) {
  const { id, params } = msg;
  const { url, method, headers, body, captchaAction } = params;

  if (!url) {
    sendToAgent({ id, error: 'MISSING_URL' });
    return;
  }

  if (!url.startsWith('https://aisandbox-pa.googleapis.com/')) {
    sendToAgent({ id, error: 'INVALID_URL' });
    return;
  }

  setState('running');
  const hasCaptcha = !!captchaAction;
  if (hasCaptcha) metrics.requestCount++;

  const logId = id;
  const logType = _classifyApiUrl(url);
  if (_VISIBLE_TYPES.has(logType)) {
    const payloadSummary = body ? JSON.stringify(body).slice(0, 200) : null;
    addRequestLog({ id: logId, type: logType, time: new Date().toISOString(), status: 'processing', error: null, outputUrl: null, url, payloadSummary });
  }

  try {
    // Step 1: Solve captcha if needed
    let captchaToken = null;
    if (captchaAction) {
      const captchaResult = await solveCaptcha(id, captchaAction);
      captchaToken = captchaResult?.token || null;
      if (!captchaToken) {
        // Cannot proceed without captcha — API will 403
        const err = captchaResult?.error || 'CAPTCHA_FAILED';
        console.error(`[FlowAgent] Captcha failed for ${captchaAction}: ${err}`);
        sendToAgent({ id, status: 403, error: `CAPTCHA_FAILED: ${err}` });
        if (hasCaptcha) { metrics.failedCount++; metrics.lastError = `CAPTCHA_FAILED: ${err}`; }
        chrome.storage.local.set({ metrics });
        updateRequestLog(logId, { status: 'failed', error: `CAPTCHA_FAILED: ${err}` });
        setState('idle');
        return;
      }
    }

    // Step 2: Inject captcha token into body
    let finalBody = body;
    if (captchaToken && finalBody) {
      finalBody = JSON.parse(JSON.stringify(finalBody)); // deep clone
      if (finalBody.clientContext?.recaptchaContext) {
        finalBody.clientContext.recaptchaContext.token = captchaToken;
      }
      if (finalBody.requests && Array.isArray(finalBody.requests)) {
        for (const req of finalBody.requests) {
          if (req.clientContext?.recaptchaContext) {
            req.clientContext.recaptchaContext.token = captchaToken;
          }
        }
      }
    }

    // Step 3: Use flowKey for auth
    const activeFlowKey = flowKey;
    if (!activeFlowKey) {
      sendToAgent({ id, status: 503, error: 'NO_FLOW_KEY' });
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = 'NO_FLOW_KEY'; }
      chrome.storage.local.set({ metrics });
      updateRequestLog(logId, { status: 'failed', error: 'NO_FLOW_KEY' });
      setState('idle');
      return;
    }

    const fetchHeaders = { ...(headers || {}) };
    fetchHeaders['authorization'] = `Bearer ${activeFlowKey}`;

    // Step 4: Make the API call from browser context
    const response = await fetch(url, {
      method: method || 'POST',
      headers: fetchHeaders,
      credentials: 'include',
      body: method === 'GET' ? undefined : JSON.stringify(finalBody),
    });

    let responseData;
    const responseText = await response.text();
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }

    sendToAgent({
      id,
      status: response.status,
      data: responseData,
    });

    const responseSummary = responseText ? responseText.slice(0, 300) : null;
    if (response.ok) {
      if (hasCaptcha) { metrics.successCount++; metrics.lastError = null; }
      updateRequestLog(logId, { status: 'success', httpStatus: response.status, responseSummary });
    } else {
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = `API_${response.status}`; }
      updateRequestLog(logId, { status: 'failed', error: `API_${response.status}`, httpStatus: response.status, responseSummary });
    }
  } catch (e) {
    sendToAgent({
      id,
      status: 500,
      error: e.message || 'API_REQUEST_FAILED',
    });
    if (hasCaptcha) { metrics.failedCount++; metrics.lastError = e.message; }
    updateRequestLog(logId, { status: 'failed', error: e.message || 'API_REQUEST_FAILED' });
  }

  chrome.storage.local.set({ metrics });
  setState('idle');
}

// ─── State & Popup ──────────────────────────────────────────

function setState(newState) {
  state = newState;
  const badges = { idle: '●', running: '▶', off: '○' };
  const colors = { idle: '#22c55e', running: '#f59e0b', off: '#6b7280' };
  chrome.action.setBadgeText({ text: badges[state] || '' });
  chrome.action.setBadgeBackgroundColor({ color: colors[state] || '#000' });
  broadcastStatus();
}

function broadcastStatus() {
  chrome.runtime.sendMessage({ type: 'STATUS_PUSH' }).catch(() => {});
}

chrome.runtime.onMessage.addListener((msg, _, reply) => {
  if (msg.type === 'TOKEN_CAPTURED') {
    flowKey = msg.token;
    metrics.tokenCapturedAt = Date.now();
    chrome.storage.local.set({ flowKey, metrics });
    console.log('[FlowAgent] Bearer token captured from page fetch');
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'STATUS') {
    reply({
      connected: ws?.readyState === WebSocket.OPEN,
      agentConnected: ws?.readyState === WebSocket.OPEN,
      flowKeyPresent: !!flowKey,
      manualDisconnect,
      tokenAge: metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
      metrics: {
        requestCount: metrics.requestCount,
        successCount: metrics.successCount,
        failedCount: metrics.failedCount,
        lastError: metrics.lastError,
      },
      state,
    });
  }

  if (msg.type === 'DISCONNECT') {
    manualDisconnect = true;
    if (ws) ws.close();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'RECONNECT') {
    manualDisconnect = false;
    connectToAgent();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'REQUEST_LOG') {
    reply({ log: requestLog });
    return true;
  }

  if (msg.type === 'CLEAR_REQUEST_LOG') {
    requestLog = [];
    broadcastRequestLog();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'RELOAD_EXTENSION') {
    chrome.runtime.reload();
    return;
  }

  if (msg.type === 'OPEN_FLOW_TAB') {
    chrome.tabs.query({ url: flowUrls }).then((tabs) => {
      if (tabs.length) {
        chrome.tabs.update(tabs[0].id, { active: true });
        reply({ ok: true, tabId: tabs[0].id });
      } else {
        chrome.tabs.create({ url: FLOW_TAB_URL })
          .then((tab) => reply({ ok: true, tabId: tab.id }))
          .catch((e) => reply({ error: e.message }));
      }
    }).catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'REFRESH_TOKEN') {
    captureTokenFromFlowTab()
      .then(() => reply({ ok: true }))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'TEST_CAPTCHA') {
    solveCaptcha(`test-${Date.now()}`, msg.pageAction || 'IMAGE_GENERATION')
      .then((r) => reply(r))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'TRPC_MEDIA_URLS') {
    handleTrpcMediaUrls(msg.trpcUrl, msg.body);
    reply({ ok: true });
    return true;
  }

  // ─── API Sniffer Handlers ──────────────────────────────────
  if (msg.type === 'API_SNIFFED_RECORD' && msg.record) {
    addSnifferLog(msg.record);
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'SYNC_SNIFFER_CONFIG') {
    chrome.tabs.query({}).then((allTabs) => {
      const flowTabs = allTabs.filter(t => t.url && (t.url.includes('flow.google.com') || t.url.includes('labs.google')));
      for (const tab of flowTabs) {
        chrome.tabs.sendMessage(tab.id, msg).catch(() => {});
      }
    }).catch(() => {});
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'GET_SNIFFER_LOGS') {
    reply({ logs: snifferLogs });
    return true;
  }

  if (msg.type === 'CLEAR_SNIFFER_LOGS') {
    snifferLogs = [];
    chrome.storage.local.set({ sniffer_logs: [] }).catch(() => {});
    chrome.runtime.sendMessage({ type: 'SNIFFER_LOG_UPDATED', logs: [] }).catch(() => {});
    reply({ ok: true });
    return true;
  }

  return true;
});

// ─── TRPC Media URL Extractor ──────────────────────────────

function handleTrpcMediaUrls(trpcUrl, bodyText) {
  try {
    // Extract all fresh signed URLs (flow-content.google or legacy GCS)
    const urlRegex = /https:\/\/(?:flow-content\.google|storage\.googleapis\.com\/ai-sandbox-videofx)\/(?:image|video)\/[0-9a-f-]{36}\?[^"'\s]+/g;
    const matches = bodyText.match(urlRegex) || [];
    if (!matches.length) return;

    // Deduplicate and parse
    const urlMap = {};
    for (const rawUrl of matches) {
      // Unescape JSON-escaped URLs
      const url = rawUrl.replace(/\\u0026/g, '&').replace(/\\/g, '');
      const mediaMatch = url.match(/\/(image|video)\/([0-9a-f-]{36})\?/);
      if (mediaMatch) {
        const [, mediaType, mediaId] = mediaMatch;
        // Keep last occurrence (freshest)
        urlMap[mediaId] = { mediaType, url, mediaId };
      }
    }

    const entries = Object.values(urlMap);
    if (!entries.length) return;

    console.log(`[FlowAgent] Captured ${entries.length} fresh media URLs from TRPC`);
    // URL refresh is silent — don't show in request log

    // Update matching video/upscale entries in requestLog if done
    for (const item of entries) {
      if (item.mediaType === 'video') {
        _latestVideoUrls.push({ url: item.url, time: Date.now(), method: 'TRPC', mediaId: item.mediaId });
        if (_latestVideoUrls.length > 50) _latestVideoUrls.shift();
        const vidEntry = requestLog.find(e => ['GEN_VID', 'GEN_VID_REF', 'UPSCALE'].includes(e.type) && (!e.outputUrl || e.status !== 'COMPLETED'));
        if (vidEntry) {
          vidEntry.outputUrl = item.url;
          vidEntry.status = 'COMPLETED';
          broadcastRequestLog();
        }
      }
    }

    // Forward to agent for DB update
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'media_urls_refresh',
        urls: entries,
      }));
    }
  } catch (e) {
    console.error('[FlowAgent] Failed to extract TRPC media URLs:', e);
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Human-like Telemetry ──────────────────────────────────
// Periodically send tracking events to Google's analytics endpoints
const _UA = navigator.userAgent;
let _telemetrySessionId = `;${Date.now()}`;
function _rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

function _buildBatchLogPayload() {
  const types = ['FLOW_IMAGE_LATENCY', 'FLOW_VIDEO_LATENCY'];
  return {
    appEvents: Array.from({ length: _rand(1, 3) }, () => ({
      event: types[_rand(0, types.length - 1)],
      eventProperties: [
        { key: 'CURRENT_TIME_MS', doubleValue: Date.now() },
        { key: 'DURATION_MS', doubleValue: _rand(150, 800) },
        { key: 'USER_AGENT', stringValue: _UA },
        { key: 'IS_DESKTOP', booleanValue: true },
      ],
      eventMetadata: { sessionId: _telemetrySessionId },
      eventTime: new Date().toISOString(),
    })),
  };
}

function _buildFrontendEventsPayload() {
  const eventTypes = ['FLOW_IMAGE_LATENCY', 'FLOW_VIDEO_LATENCY', 'GRID_SCROLL_DEPTH', 'FLOW_PROJECT_OPEN', 'FLOW_SCENE_VIEW'];
  return {
    events: Array.from({ length: _rand(1, 4) }, () => {
      const et = eventTypes[_rand(0, eventTypes.length - 1)];
      const params = {
        USER_AGENT: { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: _UA },
        IS_DESKTOP: { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: 'true' },
      };
      if (et.includes('LATENCY')) {
        params.CURRENT_TIME_MS = { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: String(Date.now()) };
        params.DURATION_MS = { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: String(_rand(100, 600)) };
      }
      if (et === 'GRID_SCROLL_DEPTH') params.MEDIA_GENERATION_PAYGATE_TIER = { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: 'PAYGATE_TIER_TWO' };
      return { eventType: et, metadata: { sessionId: _telemetrySessionId, createTime: new Date().toISOString(), additionalParams: params } };
    }),
  };
}

async function sendTelemetry() {
  if (!flowKey || state === 'off') return;
  const headers = { 'Content-Type': 'text/plain;charset=UTF-8', authorization: `Bearer ${flowKey}` };
  try {
    const url = Math.random() < 0.5 ? 'https://aisandbox-pa.googleapis.com/v1:batchLog' : 'https://aisandbox-pa.googleapis.com/v1/flow:batchLogFrontendEvents';
    const body = Math.random() < 0.5 ? _buildBatchLogPayload() : _buildFrontendEventsPayload();
    await fetch(url, { method: 'POST', headers, credentials: 'include', body: JSON.stringify(body) });
  } catch {}
}

function scheduleTelemetry() {
  setTimeout(async () => { await sendTelemetry(); scheduleTelemetry(); }, _rand(45, 120) * 1000);
}

setInterval(() => { _telemetrySessionId = `;${Date.now()}`; }, _rand(25, 35) * 60 * 1000);
scheduleTelemetry();
console.log('[FlowAgent] Extension loaded');
