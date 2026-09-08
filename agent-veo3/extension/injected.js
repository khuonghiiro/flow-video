/**
 * Injected into MAIN world on labs.google — has access to window.grecaptcha
 * Also intercepts TRPC fetch responses to capture fresh signed media URLs.
 */
(function () {
  if (window.__FLOW_INJECTED__) {
    console.log('[FlowAgent] injected.js already initialized');
    return;
  }
  window.__FLOW_INJECTED__ = true;

  const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

  // ─── TRPC Response Monitor ─────────────────────────────────
  if (!window._flowOriginalFetch) {
    window._flowOriginalFetch = window.fetch;
    window.fetch = async function (...args) {
      const response = await window._flowOriginalFetch.apply(this, args);
      try {
        const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
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
        const opts = args[1];
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
