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
})();
