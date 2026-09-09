/**
 * Injected into MAIN world on labs.google — has access to window.grecaptcha
 * Also intercepts TRPC fetch responses to capture fresh signed media URLs.
 */
(function () {
  try {
    document.documentElement.dataset.flowSnifferReady = 'true';
    document.documentElement.dataset.flowInjectedTime = String(Date.now());
  } catch (e) {}

  window.addEventListener('PING_FLOW_SNIFFER', () => {
    window.dispatchEvent(new CustomEvent('PONG_FLOW_SNIFFER', {
      detail: { ready: true, time: Date.now() }
    }));
  });

  const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

  // ─── API Sniffer Configuration & State ─────────────────────
  let _snifferConfig = {
    enabled: true,
    patterns: ['batchexecute?rpcids=nprQif', 'batchexecute?rpcids=eb1hJf', 'batchAsyncGenerateVideo'],
  };
  try {
    const cached = localStorage.getItem('__flow_sniffer_config__');
    if (cached) _snifferConfig = JSON.parse(cached);
  } catch {}

  window.addEventListener('UPDATE_SNIFFER_CONFIG', (e) => {
    if (e.detail) {
      _snifferConfig = e.detail;
      try {
        localStorage.setItem('__flow_sniffer_config__', JSON.stringify(_snifferConfig));
      } catch {}
      console.log('[FlowSniffer] Updated sniffer config:', _snifferConfig);
    }
  });

  function _normalizePath(str) {
    if (!str) return '';
    try {
      return String(str).replace(/^https?:\/\/[^\/]+/i, '').toLowerCase();
    } catch {
      return String(str).toLowerCase();
    }
  }

  function _findMatchingPattern(url) {
    if (!_snifferConfig || !_snifferConfig.enabled || !_snifferConfig.patterns || !url) return null;
    const rawUrl = String(url).toLowerCase();
    const normUrl = _normalizePath(url);

    for (const item of _snifferConfig.patterns) {
      const patStr = typeof item === 'object' ? item.url : item;
      const desc = typeof item === 'object' ? (item.desc || '') : '';
      const p = String(patStr || '').trim().toLowerCase();
      if (!p) continue;

      const normP = _normalizePath(p);

      if (
        rawUrl.includes(p) ||
        normUrl.includes(normP) ||
        (normP.length > 2 && rawUrl.includes(normP))
      ) {
        return { pattern: patStr, desc };
      }
    }
    return null;
  }

  function _extractHeaders(headers) {
    const out = {};
    if (!headers) return out;
    if (headers instanceof Headers) {
      headers.forEach((v, k) => { out[k] = v; });
    } else if (Array.isArray(headers)) {
      headers.forEach(([k, v]) => { out[k] = v; });
    } else if (typeof headers === 'object') {
      Object.assign(out, headers);
    }
    return out;
  }

  function _dispatchSniffedRecord(record) {
    try {
      console.log('[FlowSniffer] Intercepted API:', record.method, record.url, record.matchedPattern);
      window.dispatchEvent(new CustomEvent('FLOW_API_SNIFFED', {
        detail: record,
      }));
      window.postMessage({
        type: 'FLOW_API_SNIFFED_MSG',
        record,
      }, '*');
    } catch (e) {
      console.warn('[FlowSniffer] dispatch error:', e);
    }
  }

  if (window.__FLOW_INJECTED__) {
    console.log('[FlowAgent] injected.js already active, ready state confirmed');
    return;
  }
  window.__FLOW_INJECTED__ = true;

  // ─── Intercept Fetch (TRPC + API Sniffer) ───────────────────
  if (!window._flowOriginalFetch) {
    window._flowOriginalFetch = window.fetch;
    window.fetch = async function (...args) {
      let reqUrl = '';
      let reqMethod = 'GET';
      let reqHeaders = {};
      const opts = args[1] || {};
      let reqBody = opts.body;

      if (typeof args[0] === 'string') {
        reqUrl = args[0];
        reqMethod = (opts.method || 'GET').toUpperCase();
        reqHeaders = _extractHeaders(opts.headers);
      } else if (args[0] && typeof args[0] === 'object') {
        reqUrl = args[0].url || '';
        reqMethod = (opts.method || args[0].method || 'GET').toUpperCase();
        reqHeaders = _extractHeaders(opts.headers || args[0].headers);
      }

      const fullUrl = reqUrl.startsWith('http')
        ? reqUrl
        : (window.location.origin + (reqUrl.startsWith('/') ? '' : '/') + reqUrl);

      const matched = _findMatchingPattern(reqUrl) || _findMatchingPattern(fullUrl);
      const startTime = Date.now();
      let snifferReq = null;

      if (matched) {
        if (reqBody && typeof reqBody === 'object' && typeof reqBody !== 'string') {
          try { reqBody = JSON.stringify(reqBody); } catch {}
        }
        snifferReq = {
          id: 'sniff_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
          time: new Date().toISOString(),
          method: reqMethod,
          url: fullUrl,
          matchedPattern: matched.pattern,
          matchedDesc: matched.desc || '',
          headers: reqHeaders,
          body: reqBody,
        };
      }

      const response = await window._flowOriginalFetch.apply(this, args);

      // Handle Sniffer Interception
      if (snifferReq) {
        try {
          const duration = Date.now() - startTime;
          const clone = response.clone();
          clone.text().then((respText) => {
            const respHeaders = {};
            try {
              if (response.headers && response.headers.forEach) {
                response.headers.forEach((v, k) => { respHeaders[k] = v; });
              }
            } catch {}

            _dispatchSniffedRecord({
              ...snifferReq,
              status: response.status,
              statusText: response.statusText,
              duration,
              responseHeaders: respHeaders,
              responseBody: respText,
            });
          }).catch(() => {});
        } catch {}
      }

      // TRPC URL pickup & Token capture
      try {
        if (response.ok) {
          const clone = response.clone();
          clone.text().then(text => {
            if (text && (text.includes('flow-content.google') || text.includes('storage.googleapis.com/ai-sandbox-videofx/'))) {
              window.dispatchEvent(new CustomEvent('TRPC_MEDIA_URLS', {
                detail: { url, body: text },
              }));
            }
          }).catch(() => {});
        }
      } catch {}

      try {
        let auth = null;
        if (opts && opts.headers) {
          if (opts.headers instanceof Headers) {
            auth = opts.headers.get('authorization');
          } else if (typeof opts.headers === 'object') {
            auth = opts.headers['authorization'] || opts.headers['Authorization'];
          }
        }
        if (auth && String(auth).includes('Bearer ya29.')) {
          const m = String(auth).match(/ya29\.[a-zA-Z0-9_\-]+/);
          if (m) {
            window.dispatchEvent(new CustomEvent('FLOW_TOKEN_CAPTURED', {
              detail: { token: m[0] },
            }));
          }
        }
      } catch {}

      return response;
    };

    // ─── Intercept XMLHttpRequest (for Google BoQ batchexecute) ─
    try {
      const _origXhrOpen = XMLHttpRequest.prototype.open;
      const _origXhrSetHeader = XMLHttpRequest.prototype.setRequestHeader;
      const _origXhrSend = XMLHttpRequest.prototype.send;

      XMLHttpRequest.prototype.open = function (method, url, ...rest) {
        this._sniff_method = method;
        this._sniff_url = typeof url === 'string' ? url : String(url);
        this._sniff_headers = {};
        return _origXhrOpen.call(this, method, url, ...rest);
      };

      XMLHttpRequest.prototype.setRequestHeader = function (header, value) {
        if (this._sniff_headers) {
          this._sniff_headers[header] = value;
        }
        return _origXhrSetHeader.call(this, header, value);
      };

      XMLHttpRequest.prototype.send = function (body) {
        const fullUrl = this._sniff_url.startsWith('http')
          ? this._sniff_url
          : (window.location.origin + (this._sniff_url.startsWith('/') ? '' : '/') + this._sniff_url);

        const matched = _findMatchingPattern(this._sniff_url) || _findMatchingPattern(fullUrl);
        if (matched) {
          const startTime = Date.now();
          let reqBody = typeof body === 'string' ? body : (body ? String(body) : null);
          if (body instanceof FormData) {
            try {
              const entries = [];
              body.forEach((v, k) => entries.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`));
              reqBody = entries.join('&');
            } catch {}
          }

          const snifferReq = {
            id: 'sniff_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
            time: new Date().toISOString(),
            method: (this._sniff_method || 'GET').toUpperCase(),
            url: fullUrl,
            matchedPattern: matched.pattern,
            matchedDesc: matched.desc || '',
            headers: this._sniff_headers || {},
            body: reqBody,
          };

          this.addEventListener('loadend', () => {
            try {
              const duration = Date.now() - startTime;
              _dispatchSniffedRecord({
                ...snifferReq,
                status: this.status,
                statusText: this.statusText,
                duration,
                responseBody: this.responseText,
              });
            } catch {}
          });
        }
        return _origXhrSend.call(this, body);
      };
    } catch (xhrErr) {
      console.warn('[FlowSniffer] XMLHttpRequest hook failed:', xhrErr);
    }

    function scanDomMediaUrls() {
      try {
        const urls = [];
        document.querySelectorAll('video, img, source, a').forEach(el => {
          const s = el.src || el.currentSrc || el.href;
          if (s && (s.includes('flow-content.google') || s.includes('storage.googleapis.com/ai-sandbox-videofx/'))) {
            urls.push(s);
          }
        });
        if (urls.length) {
          window.dispatchEvent(new CustomEvent('TRPC_MEDIA_URLS', {
            detail: { url: window.location.href, body: urls.join(' ') },
          }));
        }
      } catch {}
    }
    setInterval(scanDomMediaUrls, 2000);
    setTimeout(scanDomMediaUrls, 500);
  }

  window.addEventListener('GET_CAPTCHA', async ({ detail }) => {
    const { requestId, pageAction } = detail;
    try {
      await waitForGrecaptcha();
      const token = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('GRECAPTCHA_EXECUTE_TIMEOUT')), 25000);
        const gre = window.grecaptcha?.enterprise || window.grecaptcha;
        if (gre?.ready) {
          gre.ready(async () => {
            try {
              const tok = await gre.execute(SITE_KEY, {
                action: pageAction,
              });
              clearTimeout(timer);
              resolve(tok);
            } catch (err) {
              clearTimeout(timer);
              reject(err);
            }
          });
        } else if (gre?.execute) {
          gre.execute(SITE_KEY, { action: pageAction }).then(tok => {
            clearTimeout(timer);
            resolve(tok);
          }).catch(err => {
            clearTimeout(timer);
            reject(err);
          });
        } else {
          clearTimeout(timer);
          reject(new Error('grecaptcha execute not found'));
        }
      });

      window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
        detail: { requestId, token },
      }));
    } catch (e) {
      console.error('[FlowAgent] grecaptcha error:', e);
      window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
        detail: { requestId, error: e.message || 'CAPTCHA_EXEC_ERROR' },
      }));
    }
  });

  function setScriptUrl(script, url) {
    if (window.trustedTypes) {
      try {
        if (window.trustedTypes.defaultPolicy?.createScriptURL) {
          script.src = window.trustedTypes.defaultPolicy.createScriptURL(url);
          return true;
        }
      } catch (e) {}
      try {
        const p = window.trustedTypes.createPolicy('flow-recaptcha-' + Date.now(), {
          createScriptURL: u => u,
        });
        script.src = p.createScriptURL(url);
        return true;
      } catch (e) {}
    }
    try {
      script.src = url;
      return true;
    } catch (e) {
      console.warn('[FlowAgent] Could not set script.src due to Trusted Types:', e.message);
      return false;
    }
  }

  function waitForGrecaptcha(timeout = 22000) {   // it loads lazily; 10s/15s was optimistic
    return new Promise((resolve, reject) => {
      const start = Date.now();
      let attemptedInject = false;

      const check = () => {
        const gre = window.grecaptcha?.enterprise || window.grecaptcha;
        if (gre?.execute) {
          if (gre.ready) {
            gre.ready(() => resolve());
          } else {
            resolve();
          }
          return;
        }

        // Only attempt to inject script after waiting 3 seconds if not present
        if (!attemptedInject && Date.now() - start > 3000 && !window.grecaptcha && !document.getElementById('flow-recaptcha-script')) {
          attemptedInject = true;
          console.log('[FlowAgent] grecaptcha not found after 3s, attempting dynamic script load...');
          const s = document.createElement('script');
          s.id = 'flow-recaptcha-script';
          s.async = true;
          if (setScriptUrl(s, `https://www.google.com/recaptcha/enterprise.js?render=${SITE_KEY}`)) {
            (document.head || document.documentElement).appendChild(s);
          }
        }

        if (Date.now() - start > timeout) {
          const scripts = Array.from(document.querySelectorAll('script')).map(s => s.src).filter(Boolean);
          const diag = {
            url: window.location.href,
            hasGrecaptcha: !!window.grecaptcha,
            keys: window.grecaptcha ? Object.keys(window.grecaptcha) : [],
            enterpriseKeys: window.grecaptcha?.enterprise ? Object.keys(window.grecaptcha.enterprise) : null,
            recaptchaScripts: scripts.filter(s => s.includes('recaptcha')),
            totalScripts: scripts.length,
          };
          return reject(new Error('grecaptcha not available: ' + JSON.stringify(diag)));
        }
        setTimeout(check, 200);
      };
      check();
    });
  }
})();
