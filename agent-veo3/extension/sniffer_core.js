/**
 * Flow Kit — API Sniffer Core Engine
 * Handles batchexecute decoding, cURL generation, diff comparison, and AI markdown export.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.SnifferCore = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Safely parse JSON or return null
   */
  function safeJsonParse(str) {
    if (!str || typeof str !== 'string') return null;
    try {
      return JSON.parse(str);
    } catch {
      return null;
    }
  }

  /**
   * Check if a string represents valid serialized JSON object or array
   */
  function isJsonText(str) {
    if (typeof str !== 'string') return false;
    const trimmed = str.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        const parsed = JSON.parse(trimmed);
        return parsed !== null && typeof parsed === 'object';
      } catch {
        return false;
      }
    }
    return false;
  }

  /**
   * Check if a string is structured XML (e.g. Google Flow XML prompt)
   */
  function isXmlPrompt(str) {
    if (typeof str !== 'string') return false;
    const trimmed = str.trim();
    return trimmed.startsWith('<') && trimmed.endsWith('>');
  }

  const RAW_BASE64_REGEX = /^[A-Za-z0-9+/=_-]{50,}$/;

  /**
   * Check if a string is base64 (data URI or raw base64/base64url >= 50 chars)
   */
  function isBase64Text(str) {
    if (typeof str !== 'string') return false;
    if (str.startsWith('data:') && str.includes(';base64,')) return true;
    if (str.length >= 50 && RAW_BASE64_REGEX.test(str.trim())) return true;
    return false;
  }

  /**
   * Recursively sanitize data for AI report:
   * - Truncates base64 to < 50 chars + '...'
   * - Truncates Bearer tokens / long param values to < 100 chars + '...'
   * - Preserves JSON text intact (recursively sanitizing inner values)
   * - Preserves structured XML prompts
   * - Omit duplicate rawPayloadStr and rawChunkStr
   */
  function sanitizeValueForAi(val, depth = 0) {
    if (depth > 12) return val;
    if (val === null || val === undefined) return val;

    if (typeof val === 'string') {
      // 1. JSON text: Do NOT truncate as raw string!
      if (isJsonText(val)) {
        try {
          const parsed = JSON.parse(val.trim());
          const inner = sanitizeValueForAi(parsed, depth + 1);
          return JSON.stringify(inner);
        } catch {
          return val;
        }
      }

      // 2. Structured XML prompt: preserve schema
      if (isXmlPrompt(val)) {
        if (val.length > 500) {
          return val.slice(0, 497) + '...';
        }
        return val;
      }

      // 3. Base64: truncate to < 50 chars + '...'
      if (isBase64Text(val)) {
        return val.slice(0, 47) + '...';
      }

      // 4. Bearer / long token / long param value: truncate to < 100 chars + '...'
      if (val.toLowerCase().startsWith('bearer ') && val.length > 100) {
        return val.slice(0, 97) + '...';
      }

      if (val.length > 100) {
        return val.slice(0, 97) + '...';
      }

      return val;
    }

    if (Array.isArray(val)) {
      return val.map(item => sanitizeValueForAi(item, depth + 1));
    }

    if (typeof val === 'object') {
      const out = {};
      for (const k of Object.keys(val)) {
        // Exclude redundant raw unparsed duplicates when parsed structure is available
        if (k === 'rawPayloadStr' && val.parsedPayload !== undefined) continue;
        if (k === 'rawChunkStr' && val.parsedChunk !== undefined) continue;
        out[k] = sanitizeValueForAi(val[k], depth + 1);
      }
      return out;
    }

    return val;
  }

  /**
   * Sanitize long tokens / base64 inside cURL body string for AI report
   */
  function sanitizeCurlBody(bodyStr) {
    if (!bodyStr || typeof bodyStr !== 'string') return bodyStr;
    return bodyStr.replace(/([A-Za-z0-9+/=_-]{70,})/g, (match) => {
      if (match.length <= 80) return match;
      return match.slice(0, 40) + '...[token_truncated]';
    });
  }

  /**
   * Recursively parse stringified JSON nested inside arrays or objects
   */
  function deepParseJson(val, depth = 0) {
    if (depth > 8) return val;
    if (typeof val === 'string') {
      const trimmed = val.trim();
      if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
          (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
        const parsed = safeJsonParse(trimmed);
        if (parsed !== null) {
          return deepParseJson(parsed, depth + 1);
        }
      }
      return val;
    }
    if (Array.isArray(val)) {
      return val.map(item => deepParseJson(item, depth + 1));
    }
    if (val && typeof val === 'object') {
      const out = {};
      for (const k of Object.keys(val)) {
        out[k] = deepParseJson(val[k], depth + 1);
      }
      return out;
    }
    return val;
  }

  /**
   * Decode Google batchexecute form body (e.g. f.req=[[["rpcid","[payload]",null,"generic"]]])
   */
  function decodeBatchexecuteReq(bodyStr) {
    if (!bodyStr || typeof bodyStr !== 'string') return null;
    try {
      let rawFreq = null;
      if (bodyStr.includes('f.req=')) {
        const parts = bodyStr.split('&');
        for (const part of parts) {
          if (part.startsWith('f.req=')) {
            rawFreq = decodeURIComponent(part.slice(6).replace(/\+/g, ' '));
            break;
          }
        }
      } else if (bodyStr.startsWith('[[[') || bodyStr.startsWith('[')) {
        rawFreq = bodyStr;
      }

      if (!rawFreq) return null;

      const outerParsed = safeJsonParse(rawFreq);
      if (!outerParsed || !Array.isArray(outerParsed)) return null;

      const rpcCalls = [];
      const callsList = Array.isArray(outerParsed[0]) ? outerParsed[0] : outerParsed;

      for (const call of callsList) {
        if (Array.isArray(call) && call.length >= 2) {
          const rpcid = call[0];
          const rawPayloadStr = call[1];
          const parsedPayload = deepParseJson(rawPayloadStr);

          rpcCalls.push({
            rpcid,
            envelopeId: call[3] || 'generic',
            parsedPayload,
            rawPayloadStr: typeof rawPayloadStr === 'string' ? rawPayloadStr : JSON.stringify(rawPayloadStr),
          });
        }
      }

      return {
        isBatchexecute: true,
        calls: rpcCalls,
        rawFreq,
      };
    } catch (e) {
      return null;
    }
  }

  /**
   * Parse Google XSSI-prefixed batchexecute or JSON response
   */
  function parseResponseBody(responseText) {
    if (!responseText || typeof responseText !== 'string') return { raw: responseText };

    let cleaned = responseText.trim();
    // Strip Google XSSI prefix: )]}' or )]}'\n
    if (cleaned.startsWith(")]}'")) {
      cleaned = cleaned.slice(4).trim();
    }

    // Try standard JSON parse
    let directJson = safeJsonParse(cleaned);
    if (!directJson) {
      // Fallback for Google BoQ chunked streams: <length>\n<json>\n<length>\n<json>
      const cleanLines = cleaned.replace(/^\s*\d+\s*$/gm, '').trim();
      directJson = safeJsonParse(cleanLines);
      if (!directJson) {
        // Try finding any array starting with [["wrb.fr"
        const wrbIdx = cleaned.indexOf('[["wrb.fr"');
        if (wrbIdx !== -1) {
          const nextNewline = cleaned.indexOf('\n', wrbIdx);
          const candidate = nextNewline !== -1 ? cleaned.substring(wrbIdx, nextNewline).trim() : cleaned.substring(wrbIdx).trim();
          directJson = safeJsonParse(candidate);
        }
      }
    }
    if (directJson !== null) {
      // In batchexecute responses: array of chunks like [["wrb.fr","rpcid","[\"...\"]",...]]
      if (Array.isArray(directJson)) {
        const chunks = [];
        for (const item of directJson) {
          if (Array.isArray(item) && item[0] === 'wrb.fr') {
            const rpcid = item[1];
            const rawChunkStr = item[2];
            const parsedChunk = deepParseJson(rawChunkStr);
            chunks.push({
              type: 'wrb.fr',
              rpcid,
              parsedChunk,
              rawChunkStr,
            });
          } else {
            chunks.push(deepParseJson(item));
          }
        }
        return {
          isBatchexecuteResponse: true,
          chunks,
          parsed: directJson,
          raw: responseText,
        };
      }

      return {
        isJson: true,
        parsed: deepParseJson(directJson),
        raw: responseText,
      };
    }

    return { isRawText: true, raw: responseText };
  }

  /**
   * Generate an executable bash cURL command
   * @param {Object} record - Sniffer record
   * @param {Object} [options] - Generation options
   * @param {boolean} [options.sanitize] - If true, truncates base64 and ultra-long tokens for AI readability
   */
  function generateCurl(record, options = {}) {
    if (!record || !record.url) return '# No URL provided';

    const method = (record.method || 'GET').toUpperCase();
    let url = record.url;
    const headers = record.headers || {};
    const body = record.body;
    const isSanitize = !!options.sanitize;
    const refs = options.refs || [];

    if (refs.length > 0 && typeof applySharedReferences === 'function') {
      url = applySharedReferences(url, refs);
    }

    const lines = [`curl -X ${method} '${url.replace(/'/g, "'\\''")}'`];

    // Filter out pseudo headers or browser forbidden headers
    const skipHeaders = new Set([':method', ':authority', ':scheme', ':path', 'content-length']);
    if (isSanitize) {
      ['sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform', 'sec-fetch-dest',
       'sec-fetch-mode', 'sec-fetch-site', 'accept-language', 'accept-encoding', 'priority'].forEach(h => skipHeaders.add(h));
    }

    for (const [k, v] of Object.entries(headers)) {
      if (!skipHeaders.has(k.toLowerCase()) && v !== undefined && v !== null) {
        let valStr = String(v);
        if (refs.length > 0 && typeof applySharedReferences === 'function') {
          valStr = applySharedReferences(valStr, refs);
        }
        if (isSanitize) {
          if (k.toLowerCase() === 'authorization' && valStr.toLowerCase().startsWith('bearer ') && valStr.length > 50) {
            valStr = valStr.slice(0, 30) + '...[bearer_truncated]';
          } else if (valStr.length > 100 && !isJsonText(valStr)) {
            valStr = valStr.slice(0, 97) + '...';
          }
        }
        lines.push(`  -H '${k}: ${valStr.replace(/'/g, "'\\''")}'`);
      }
    }

    if (body && method !== 'GET' && method !== 'HEAD') {
      let bodyStr = typeof body === 'object' ? JSON.stringify(body) : String(body);
      if (refs.length > 0 && typeof applySharedReferences === 'function') {
        bodyStr = applySharedReferences(bodyStr, refs);
      }
      if (isSanitize) {
        bodyStr = sanitizeCurlBody(bodyStr);
      }
      lines.push(`  --data-raw '${bodyStr.replace(/'/g, "'\\''")}'`);
    }

    lines.push('  --compressed');
    return lines.join(' \\\n');
  }

  /**
   * Extract query parameters from a URL into an object
   */
  function getQueryParams(urlStr) {
    try {
      const u = new URL(urlStr, 'https://flow.google.com');
      const params = {};
      u.searchParams.forEach((v, k) => {
        params[k] = v;
      });
      return params;
    } catch {
      return {};
    }
  }

  /**
   * Recursively compare two objects or arrays and return differences
   */
  function diffValues(valA, valB, path = '') {
    const diffs = [];
    if (valA === valB) return diffs;
    const typeA = Array.isArray(valA) ? 'array' : typeof valA;
    const typeB = Array.isArray(valB) ? 'array' : typeof valB;

    if (typeA !== typeB || valA === null || valB === null) {
      diffs.push({ path: path || 'root', type: 'changed', from: valA, to: valB });
      return diffs;
    }
    if (typeA === 'object' && valA && valB) {
      const allKeys = new Set([...Object.keys(valA), ...Object.keys(valB)]);
      for (const k of allKeys) {
        const subPath = path ? `${path}.${k}` : k;
        if (!(k in valA)) diffs.push({ path: subPath, type: 'added', from: undefined, to: valB[k] });
        else if (!(k in valB)) diffs.push({ path: subPath, type: 'removed', from: valA[k], to: undefined });
        else diffs.push(...diffValues(valA[k], valB[k], subPath));
      }
      return diffs;
    }
    if (typeA === 'array') {
      const maxLen = Math.max(valA.length, valB.length);
      for (let i = 0; i < maxLen; i++) {
        const subPath = `${path}[${i}]`;
        if (i >= valA.length) diffs.push({ path: subPath, type: 'added', from: undefined, to: valB[i] });
        else if (i >= valB.length) diffs.push({ path: subPath, type: 'removed', from: valA[i], to: undefined });
        else diffs.push(...diffValues(valA[i], valB[i], subPath));
      }
      return diffs;
    }
    diffs.push({ path: path || 'value', type: 'changed', from: valA, to: valB });
    return diffs;
  }

  /**
   * Compare two sniffer records
   */
  function compareApiRecords(recordA, recordB) {
    if (!recordA || !recordB) return null;

    const queryA = getQueryParams(recordA.url);
    const queryB = getQueryParams(recordB.url);
    const queryDiffs = diffValues(queryA, queryB, 'query');

    // Payloads
    const decodedA = decodeBatchexecuteReq(recordA.body);
    const decodedB = decodeBatchexecuteReq(recordB.body);

    let payloadDiffs = [];
    if (decodedA && decodedB) {
      const cleanCallsA = sanitizeValueForAi(decodedA.calls);
      const cleanCallsB = sanitizeValueForAi(decodedB.calls);
      payloadDiffs = diffValues(cleanCallsA, cleanCallsB, 'f.req.calls');
    } else {
      const bodyObjA = safeJsonParse(recordA.body) || recordA.body;
      const bodyObjB = safeJsonParse(recordB.body) || recordB.body;
      const cleanBodyA = sanitizeValueForAi(bodyObjA);
      const cleanBodyB = sanitizeValueForAi(bodyObjB);
      payloadDiffs = diffValues(cleanBodyA, cleanBodyB, 'body');
    }

    // Responses
    const respA = parseResponseBody(recordA.responseBody);
    const respB = parseResponseBody(recordB.responseBody);
    const cleanRespA = sanitizeValueForAi(respA.chunks || respA.parsed || respA.raw);
    const cleanRespB = sanitizeValueForAi(respB.chunks || respB.parsed || respB.raw);
    const responseDiffs = diffValues(
      cleanRespA,
      cleanRespB,
      'response'
    );

    return {
      recordAId: recordA.id,
      recordBId: recordB.id,
      urlA: recordA.url,
      urlB: recordB.url,
      queryDiffs,
      payloadDiffs,
      responseDiffs,
    };
  }

  /**
   * Normalize response body to check for business identicality (ignoring stream markers and session timers)
   */
  function normalizeResponseBody(str) {
    if (!str) return '';
    return String(str)
      .replace(/\)\]\}'/g, '')
      .replace(/^\s*\d+\s*$/gm, '')
      .replace(/\[\s*"di"\s*,\s*\d+\s*\]/g, '')
      .replace(/\[\s*"af\.httprm"\s*,\s*\d+\s*,\s*"[^"]*"\s*,\s*\d+\s*\]/g, '')
      .replace(/\[\s*\[\s*"e"\s*,\s*\d+\s*,\s*null\s*,\s*null\s*,\s*\d+\s*\]\s*\]/g, '')
      .trim();
  }

  function arePayloadsIdentical(recA, recB) {
    if (!recA || !recB) return false;
    if (recA.body === recB.body) return true;
    const decA = decodeBatchexecuteReq(recA.body);
    const decB = decodeBatchexecuteReq(recB.body);
    if (decA && decB) {
      if (decA.rawFreq && decA.rawFreq === decB.rawFreq) return true;
      if (Array.isArray(decA.calls) && Array.isArray(decB.calls) && decA.calls.length === decB.calls.length) {
        return JSON.stringify(decA.calls) === JSON.stringify(decB.calls);
      }
    }
    return false;
  }

  function areResponsesIdentical(recA, recB) {
    if (!recA || !recB) return false;
    if (!recA.responseBody && !recB.responseBody) return true;
    if (recA.responseBody === recB.responseBody) return true;
    return normalizeResponseBody(recA.responseBody) === normalizeResponseBody(recB.responseBody);
  }

  /**
   * Automatically discover recurring entities across captured records to build a Shared References Table.
   * Discovers: Project IDs, Operation IDs, Auth tokens (@at), BoQ build labels, XML prompt templates, and crypto blobs.
   */
  function buildSharedReferences(records) {
    if (!records || !Array.isArray(records) || records.length === 0) return [];
    const candidateMap = new Map();

    function register(val, keyPrefix, label) {
      if (!val || typeof val !== 'string') return;
      const clean = val.trim();
      if (clean.length < 8) return;
      if (!candidateMap.has(clean)) {
        candidateMap.set(clean, { key: keyPrefix, label, count: 0 });
      }
    }

    // 1. Scan URLs for Project ID, @at token, BoQ build label
    for (const rec of records) {
      if (!rec.url) continue;
      const matchProj = rec.url.match(/source-path=[^&]*%2Fproject%2F([0-9a-fA-F-]{36})/i) ||
                        rec.url.match(/\/project\/([0-9a-fA-F-]{36})/i);
      if (matchProj && matchProj[1]) register(matchProj[1], '$PROJ', 'Project UUID');

      const matchAt = rec.url.match(/[?&]at=([^&]+)/) || (rec.body && rec.body.match(/[?&]at=([^&]+)/));
      if (matchAt && matchAt[1]) register(decodeURIComponent(matchAt[1]), '$AT', 'Mã phiên (@at)');

      const matchBl = rec.url.match(/[?&]bl=([^&]+)/);
      if (matchBl && matchBl[1]) register(decodeURIComponent(matchBl[1]), '$BUILD', 'BoQ Build (bl)');
    }

    // 2. Discover Operation ID (UUID in polling query or creation response)
    for (const rec of records) {
      const decodedReq = decodeBatchexecuteReq(rec.body);
      if (decodedReq && decodedReq.calls) {
        for (const call of decodedReq.calls) {
          if (call.rpcid === 'jwpduf' && Array.isArray(call.parsedPayload)) {
            try {
              const inner = call.parsedPayload[2][0][0];
              if (inner && typeof inner === 'string' && /^[0-9a-fA-F-]{36}$/.test(inner)) {
                register(inner, '$OP_ID', 'Operation UUID');
              }
            } catch {}
          }
        }
      }
    }

    // 3. Scan for recurring XML prompt structures, crypto blobs, and reference image UUIDs
    let refAssetIdx = 1;
    for (const rec of records) {
      const parsedResp = parseResponseBody(rec.responseBody);
      if (parsedResp && parsedResp.chunks) {
        const respStr = JSON.stringify(parsedResp.chunks);
        const xmlMatch = respStr.match(/(<root>[\s\S]*?<\/root>)/);
        if (xmlMatch && xmlMatch[1]) register(xmlMatch[1], '$XML', 'XML Prompt Template');
      }

      if (rec.body) {
        const decodedReq = decodeBatchexecuteReq(rec.body);
        if (decodedReq && decodedReq.calls) {
          const bodyStr = JSON.stringify(decodedReq.calls);
          const blobMatches = bodyStr.match(/([A-Za-z0-9+/=_-]{70,})/g) || [];
          for (const b of blobMatches) register(b, '$BLOB', 'Session State Blob');
          const uuidMatches = bodyStr.match(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/g) || [];
          for (const u of uuidMatches) {
            if (!candidateMap.has(u)) register(u, `$REF_${refAssetIdx++}`, 'Media / Asset UUID');
          }
        }
      }
    }

    // 4. Count occurrences across all records
    for (const [val, info] of candidateMap.entries()) {
      let occurrences = 0;
      for (const rec of records) {
        const text = (rec.url || '') + ' ' + (rec.body || '') + ' ' + (rec.responseBody || '');
        let idx = 0;
        while ((idx = text.indexOf(val, idx)) !== -1) { occurrences++; idx += val.length; }
        const encoded = encodeURIComponent(val);
        if (encoded !== val) {
          let encIdx = 0;
          while ((encIdx = text.indexOf(encoded, encIdx)) !== -1) { occurrences++; encIdx += encoded.length; }
        }
      }
      info.count = occurrences;
    }

    const resultRefs = [];
    for (const [value, info] of candidateMap.entries()) {
      // Strictly only keep variables that recur (count >= 2)
      if (info.count >= 2) {
        resultRefs.push({
          key: info.key,
          label: info.label,
          value,
          count: info.count,
        });
      }
    }

    resultRefs.sort((a, b) => b.value.length - a.value.length);
    return resultRefs;
  }

  /**
   * Apply shared reference variable substitutions into any string, array, or object
   */
  function applySharedReferences(target, refs) {
    if (!refs || refs.length === 0 || target === null || target === undefined) return target;

    if (typeof target === 'string') {
      let result = target;
      for (const ref of refs) {
        result = result.split(ref.value).join(ref.key);
        const enc = encodeURIComponent(ref.value);
        if (enc !== ref.value) {
          result = result.split(enc).join(ref.key);
        }
      }
      return result;
    }

    if (Array.isArray(target)) {
      return target.map(item => applySharedReferences(item, refs));
    }

    if (typeof target === 'object') {
      const out = {};
      for (const k of Object.keys(target)) {
        out[k] = applySharedReferences(target[k], refs);
      }
      return out;
    }

    return target;
  }

  /**
   * Format the comprehensive Markdown Report for AI consumption
   * Supports compact mode to eliminate token waste on repetitive polling requests.
   * Supports shared references to replace repeated long tokens/UUIDs with $VARIABLES.
   */
  function compileAiReport({ title, reason, records, configName, compact = true, useSharedRefs = true }) {
    const lines = [];
    const now = new Date().toLocaleString('vi-VN');

    // 1. Build Shared References if enabled
    const sharedRefs = (compact && useSharedRefs) ? buildSharedReferences(records) : [];

    lines.push('# 📋 BÁO CÁO PHÂN TÍCH API NETWORK LOG CHO AI');
    if (title && title.trim()) {
      lines.push(`### 🏷️ Tiêu đề: ${title.trim()}`);
    }
    const compactFlags = [];
    if (compact) compactFlags.push('Tinh gọn lặp');
    if (sharedRefs.length > 0) compactFlags.push('Tham chiếu biến chung');
    const flagNote = compactFlags.length > 0 ? ` *(${compactFlags.join(' + ')})*` : '';
    lines.push(`*Thời gian xuất:* ${now} | *Cấu hình:* ${configName || 'Mặc định'} | *Tổng số request:* ${records.length}${flagNote}`);
    lines.push('');

    if (compact) {
      lines.push('> 💡 **Ghi chú tinh gọn cho AI:** Các request/response lặp lại (như polling kiểm tra trạng thái nhiều lần) đã được tự động phát hiện và rút gọn. Chỉ các request khởi tạo hoặc có sự thay đổi dữ liệu mới hiển thị chi tiết.');
      lines.push('');
    }

    let secIdx = 1;

    // 1. Reason / Context
    lines.push(`## 🎯 ${secIdx++}. Mục Đích & Ngữ Cảnh Phân Tích`);
    if (reason && reason.trim()) {
      lines.push(reason.trim());
    } else {
      lines.push('*Chưa nhập ghi chú lý do. Mục đích: Phân tích cấu trúc request/response của Google Flow để hoàn thiện logic client.*');
    }
    lines.push('');
    lines.push('---');
    lines.push('');

    // 2. Shared References Table (only recurring items count >= 2)
    if (sharedRefs.length > 0) {
      lines.push(`## 📌 ${secIdx++}. Biến Tham Chiếu Chung ($REF)`);
      lines.push('| Biến | Ý Nghĩa / Tần Suất | Giá Trị Thực Tế |');
      lines.push('|---|---|---|');
      sharedRefs.forEach(r => {
        const valPreview = r.value.length > 55 ? `${r.value.slice(0, 35)}...` : r.value;
        lines.push(`| \`${r.key}\` | ${r.label} (${r.count}x) | \`${valPreview}\` |`);
      });
      lines.push('', '---', '');
    }

    // Summary Table
    lines.push(`## 📊 ${secIdx++}. Bảng Tổng Quan Các Request Đã Bắt`);
    lines.push('| # | Thời gian | Method | Status | Duration | Pattern Khớp | Mô Tả API | URL / Endpoint |');
    lines.push('|---|---|---|---|---|---|---|---|');

    records.forEach((rec, idx) => {
      const timeStr = rec.time ? new Date(rec.time).toLocaleTimeString('vi-VN') : '—';
      const statusStr = rec.status ? `${rec.status} ${rec.statusText || ''}`.trim() : 'pending';
      const durStr = rec.duration ? `${rec.duration}ms` : '—';
      const pattern = rec.matchedPattern || '—';
      const desc = rec.matchedDesc || '—';
      let shortUrl = (rec.url || '').split('?')[0].replace('https://flow.google.com', '');
      if (sharedRefs.length > 0) {
        shortUrl = applySharedReferences(shortUrl, sharedRefs);
      }
      lines.push(`| ${idx + 1} | ${timeStr} | \`${rec.method || 'POST'}\` | \`${statusStr}\` | ${durStr} | \`${pattern}\` | **${desc}** | \`${shortUrl}\` |`);
    });
    lines.push('', '---', '');

    // Detail for each record
    lines.push(`## 🔍 ${secIdx++}. Chi Tiết Từng API & cURL Command`);
    lines.push('');

    // Build plan: group consecutive identical polling requests if compact mode
    const renderPlan = [];
    if (compact) {
      let i = 0;
      while (i < records.length) {
        const cur = records[i];
        let j = i + 1;
        while (
          j < records.length &&
          records[j].url.split('?')[0] === cur.url.split('?')[0] &&
          arePayloadsIdentical(cur, records[j]) &&
          areResponsesIdentical(cur, records[j])
        ) {
          j++;
        }

        const count = j - i;
        if (count >= 3) {
          renderPlan.push({ type: 'single', record: cur, index: i });
          renderPlan.push({
            type: 'consecutive_group',
            records: records.slice(i + 1, j),
            startIndex: i + 1,
            endIndex: j - 1,
            refIndex: i,
          });
          i = j;
        } else {
          renderPlan.push({ type: 'single', record: cur, index: i });
          i++;
        }
      }
    } else {
      records.forEach((rec, idx) => {
        renderPlan.push({ type: 'single', record: rec, index: idx });
      });
    }

    renderPlan.forEach((item) => {
      if (item.type === 'consecutive_group') {
        const first = item.records[0];
        const last = item.records[item.records.length - 1];
        const tStart = first.time ? new Date(first.time).toLocaleTimeString('vi-VN') : '—';
        const tEnd = last.time ? new Date(last.time).toLocaleTimeString('vi-VN') : '—';
        let shortUrl = (first.url || '').split('?')[0].replace('https://flow.google.com', '');
        if (sharedRefs.length > 0) {
          shortUrl = applySharedReferences(shortUrl, sharedRefs);
        }
        const rpcid = (first.url.match(/rpcids=([^&]+)/) || [])[1] || '';

        lines.push(`### 📡 Requests #${item.startIndex + 1} — #${item.endIndex + 1}: POST \`${shortUrl}${rpcid ? `?rpcids=${rpcid}` : ''}\` *(🔁 Polling lặp lại ${item.records.length} lần)*`);
        if (first.matchedDesc) {
          lines.push(`- **🎯 Chức năng / Mô tả API:** ${first.matchedDesc} (lặp lại định kỳ)`);
        }
        lines.push(`- **⚡ Tinh gọn:** ${item.records.length} request liên tiếp (${tStart} ➔ ${tEnd}) có **Payload và Response hoàn toàn giống Request #${item.refIndex + 1}** (Hệ thống tiếp tục xử lý tác vụ, trạng thái giữ nguyên).`);
        const durations = item.records.map((r, k) => `#${item.startIndex + 1 + k} (${r.duration || 0}ms)`).join(', ');
        lines.push(`- **Nhật ký thời gian phản hồi:** ${durations}`);
        lines.push('', '---', '');
        return;
      }

      const rec = item.record;
      const idx = item.index;
      const rawTitleUrl = (rec.url || '').split('?')[0];
      const titleUrl = sharedRefs.length > 0 ? applySharedReferences(rawTitleUrl, sharedRefs) : rawTitleUrl;

      // Check if this single record has identical payload or response to any earlier record
      let prevPayloadIdx = -1;
      let prevRespIdx = -1;
      let prevRpcIdx = -1;

      if (compact) {
        for (let k = 0; k < idx; k++) {
          if (arePayloadsIdentical(records[k], rec)) {
            prevPayloadIdx = k;
            break;
          }
        }
        for (let k = 0; k < idx; k++) {
          if (areResponsesIdentical(records[k], rec)) {
            prevRespIdx = k;
            break;
          }
        }
        const myRpc = (rec.url.match(/rpcids=([^&]+)/) || [])[1];
        if (myRpc) {
          for (let k = idx - 1; k >= 0; k--) {
            const otherRpc = (records[k].url.match(/rpcids=([^&]+)/) || [])[1];
            if (otherRpc === myRpc) {
              prevRpcIdx = k;
              break;
            }
          }
        }
      }

      const hasNewResponse = prevRpcIdx !== -1 && prevRespIdx === -1;
      const changeTag = hasNewResponse ? ' *(⚡ CÓ DỮ LIỆU MỚI / THAY ĐỔI TRẠNG THÁI)*' : '';

      lines.push(`### 📡 Request #${idx + 1}: ${rec.method || 'POST'} \`${titleUrl}\`${changeTag}`);
      if (rec.matchedDesc) {
        lines.push(`- **🎯 Chức năng / Mô tả API:** ${rec.matchedDesc}`);
      }
      lines.push(`- **ID:** \`${rec.id}\``);
      const fullUrlDisplay = sharedRefs.length > 0 ? applySharedReferences(rec.url, sharedRefs) : rec.url;
      lines.push(`- **URL Đầy đủ:** \`${fullUrlDisplay}\``);
      lines.push(`- **HTTP Status:** \`${rec.status || 0} ${rec.statusText || ''}\` (Thời gian phản hồi: ${rec.duration || 0}ms)`);
      if (rec.matchedPattern) {
        lines.push(`- **Pattern khớp:** \`${rec.matchedPattern}\``);
      }
      lines.push('');

      // cURL Command
      lines.push('#### 💻 cURL Command:');
      lines.push('```bash');
      lines.push(generateCurl(rec, { sanitize: compact, refs: sharedRefs }));
      lines.push('```');
      lines.push('');

      // Request Payload
      lines.push('#### 📤 Request Payload:');
      if (prevPayloadIdx !== -1 && compact) {
        lines.push(`*🔄 Trùng khớp hoàn toàn với Request #${prevPayloadIdx + 1} (Payload giữ nguyên, không đổi).*`);
      } else {
        const decodedBody = decodeBatchexecuteReq(rec.body);
        if (decodedBody && decodedBody.calls && decodedBody.calls.length > 0) {
          lines.push('*Phân giải Google batchexecute `f.req` (Cấu trúc mảng/JSON lồng nhau đã được giải mã):*');
          lines.push('```json');
          const callsSub = sharedRefs.length > 0 ? applySharedReferences(decodedBody.calls, sharedRefs) : decodedBody.calls;
          const callsToRender = compact ? sanitizeValueForAi(callsSub) : callsSub;
          lines.push(JSON.stringify(callsToRender, null, 2));
          lines.push('```');
        } else {
          const parsedBody = safeJsonParse(rec.body);
          if (parsedBody) {
            lines.push('```json');
            const bodySub = sharedRefs.length > 0 ? applySharedReferences(parsedBody, sharedRefs) : parsedBody;
            const bodyToRender = compact ? sanitizeValueForAi(bodySub) : bodySub;
            lines.push(JSON.stringify(bodyToRender, null, 2));
            lines.push('```');
          } else if (rec.body) {
            lines.push('```text');
            const rawBodyStr = compact ? sanitizeCurlBody(String(rec.body)) : String(rec.body);
            lines.push(applySharedReferences(rawBodyStr.slice(0, 4000), sharedRefs));
            lines.push('```');
          } else {
            lines.push('*Không có request body (GET request hoặc body rỗng)*');
          }
        }
      }
      lines.push('');

      // Response Body
      lines.push(`#### 📥 Response Data:${hasNewResponse ? ' *(⚡ DỮ LIỆU ĐÃ CẬP NHẬT)*' : ''}`);
      if (prevRespIdx !== -1 && compact) {
        lines.push(`*🔄 Kết quả & trạng thái trùng khớp Request #${prevRespIdx + 1} (Chưa có dữ liệu mới).*`);
      } else {
        const parsedResp = parseResponseBody(rec.responseBody);
        if (parsedResp.chunks && parsedResp.chunks.length > 0) {
          lines.push('*Phân giải batchexecute response chunks:*');
          lines.push('```json');
          const chunksSub = sharedRefs.length > 0 ? applySharedReferences(parsedResp.chunks, sharedRefs) : parsedResp.chunks;
          const chunksToRender = compact ? sanitizeValueForAi(chunksSub) : chunksSub;
          lines.push(JSON.stringify(chunksToRender, null, 2));
          lines.push('```');
        } else if (parsedResp.parsed) {
          lines.push('```json');
          const parsedSub = sharedRefs.length > 0 ? applySharedReferences(parsedResp.parsed, sharedRefs) : parsedResp.parsed;
          const parsedToRender = compact ? sanitizeValueForAi(parsedSub) : parsedSub;
          lines.push(JSON.stringify(parsedToRender, null, 2));
          lines.push('```');
        } else if (rec.responseBody) {
          lines.push('```text');
          let rawRespStr = compact ? normalizeResponseBody(String(rec.responseBody)) : String(rec.responseBody);
          if (compact) rawRespStr = sanitizeCurlBody(rawRespStr);
          lines.push(applySharedReferences(rawRespStr.slice(0, 3000), sharedRefs));
          lines.push('```');
        } else {
          lines.push('*Chưa có response hoặc response rỗng*');
        }
      }
      lines.push('', '---', '');
    });

    // Auto-comparison if there are multiple requests
    if (records.length >= 2) {
      lines.push(`## ⚖️ ${secIdx++}. Phân Tích So Sánh Các Trường (Field Diff Analysis)`);

      // Smart selection of pair: find two requests of the same RPC that have different responses or payloads
      let pairA = records[0];
      let pairB = records[1];
      let pairDesc = `So sánh giữa Request đầu tiên (#1) và Request thứ hai (#2)`;

      let foundSameRpc = false;
      for (let i = 0; i < records.length; i++) {
        for (let j = i + 1; j < records.length; j++) {
          const rpcA = (records[i].url.match(/rpcids=([^&]+)/) || [])[1];
          const rpcB = (records[j].url.match(/rpcids=([^&]+)/) || [])[1];
          if (rpcA && rpcB && rpcA === rpcB) {
            if (!areResponsesIdentical(records[i], records[j]) || !arePayloadsIdentical(records[i], records[j])) {
              pairA = records[i];
              pairB = records[j];
              pairDesc = `So sánh giữa Request #${i + 1} và Request #${j + 1} (Cùng endpoint RPC [${rpcA}] nhưng có sự biến thiên dữ liệu/kết quả)`;
              foundSameRpc = true;
              break;
            }
          }
        }
        if (foundSameRpc) break;
      }

      lines.push(`*${pairDesc}:*`);
      lines.push('');

      const comp = compareApiRecords(pairA, pairB);
      if (comp) {
        if (comp.queryDiffs.length > 0) {
          lines.push('### 🔹 URL Query Parameters khác nhau:');
          lines.push('| Tham số URL | Giá trị ở #1 | Giá trị ở #2 |');
          lines.push('|---|---|---|');
          comp.queryDiffs.slice(0, 20).forEach(d => {
            const fVal = d.from !== undefined ? applySharedReferences(String(d.from), sharedRefs) : '(không có)';
            const tVal = d.to !== undefined ? applySharedReferences(String(d.to), sharedRefs) : '(không có)';
            lines.push(`| \`${d.path}\` | \`${fVal}\` | \`${tVal}\` |`);
          });
          lines.push('');
        }

        if (comp.payloadDiffs.length > 0) {
          lines.push('### 🔹 Request Payload / Body khác nhau:');
          lines.push('| Đường dẫn trường (Path) | Request Trước | Request Sau | Trạng thái |');
          lines.push('|---|---|---|---|');
          comp.payloadDiffs.slice(0, 30).forEach(d => {
            const fStr = typeof d.from === 'object' ? JSON.stringify(d.from) : String(d.from ?? '—');
            const tStr = typeof d.to === 'object' ? JSON.stringify(d.to) : String(d.to ?? '—');
            const pathSub = applySharedReferences(d.path, sharedRefs);
            const fromSub = applySharedReferences(fStr.slice(0, 60), sharedRefs);
            const toSub = applySharedReferences(tStr.slice(0, 60), sharedRefs);
            lines.push(`| \`${pathSub}\` | \`${fromSub}\` | \`${toSub}\` | **${d.type}** |`);
          });
          lines.push('');
        } else {
          lines.push('*Không phát hiện sự khác biệt lớn trong Request Payload.*');
          lines.push('');
        }

        if (comp.responseDiffs && comp.responseDiffs.length > 0) {
          lines.push('### 🔹 Response Data khác nhau:');
          lines.push('| Đường dẫn trường (Path) | Giá trị Trước | Giá trị Sau | Trạng thái |');
          lines.push('|---|---|---|---|');
          comp.responseDiffs.slice(0, 30).forEach(d => {
            const fStr = typeof d.from === 'object' ? JSON.stringify(d.from) : String(d.from ?? '—');
            const tStr = typeof d.to === 'object' ? JSON.stringify(d.to) : String(d.to ?? '—');
            const pathSub = applySharedReferences(d.path, sharedRefs);
            const fromSub = applySharedReferences(fStr.slice(0, 60), sharedRefs);
            const toSub = applySharedReferences(tStr.slice(0, 60), sharedRefs);
            lines.push(`| \`${pathSub}\` | \`${fromSub}\` | \`${toSub}\` | **${d.type}** |`);
          });
          lines.push('');
        }
      }
      lines.push('', '---', '');
    }

    lines.push('*Tài liệu được sinh tự động bởi Flow Kit Extension — API Sniffer for AI*');
    return lines.join('\n');
  }

  return {
    safeJsonParse,
    deepParseJson,
    decodeBatchexecuteReq,
    parseResponseBody,
    generateCurl,
    getQueryParams,
    diffValues,
    compareApiRecords,
    compileAiReport,
    isJsonText,
    isBase64Text,
    sanitizeValueForAi,
    sanitizeCurlBody,
    buildSharedReferences,
    applySharedReferences,
  };
});
