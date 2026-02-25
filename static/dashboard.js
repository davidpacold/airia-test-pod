/* Airia Test Pod - Dashboard JavaScript */
'use strict';

/* ── Initialization (moved from inline scripts) ───────────── */
axios.defaults.withCredentials = true;
(function() {
  var scriptEl = document.currentScript || document.querySelector('script[data-app-version]');
  if (scriptEl && scriptEl.dataset.appVersion) {
    window.APP_VERSION = scriptEl.dataset.appVersion;
  }
})();

/* ── XSS helper ─────────────────────────────────────────────── */
function esc(str) {
  if (str == null) return '';
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(String(str)));
  return d.innerHTML;
}

/* ── Notification Manager ───────────────────────────────────── */
class NotificationManager {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.items = new Map();
  }
  show(type, title, message, details, duration = 5000) {
    const id = String(Date.now());
    const icons = { success: '\u2705', error: '\u274C', warning: '\u26A0\uFE0F', info: '\u2139\uFE0F' };
    const el = document.createElement('div');
    el.className = 'notification ' + type;
    el.id = 'notification-' + id;
    el.innerHTML =
      '<div class="notification-header">' +
        '<span class="notification-title">' + (icons[type] || '') + ' ' + esc(title) + '</span>' +
        '<button class="notification-close" data-nid="' + id + '">\u00D7</button>' +
      '</div>' +
      '<div class="notification-message">' + esc(message) + '</div>' +
      (details ? '<div class="notification-details">' + esc(details) + '</div>' : '');
    el.querySelector('.notification-close').addEventListener('click', () => this.remove(id));
    this.container.appendChild(el);
    this.items.set(id, el);
    if (type !== 'error' && duration > 0) setTimeout(() => this.remove(id), duration);
    return id;
  }
  remove(id) {
    const el = this.items.get(id);
    if (!el) return;
    el.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => { el.remove(); this.items.delete(id); }, 300);
  }
  success(t, m, d) { return this.show('success', t, m, d); }
  error(t, m, d)   { return this.show('error', t, m, d, 0); }
  warning(t, m, d) { return this.show('warning', t, m, d); }
  info(t, m, d)    { return this.show('info', t, m, d); }
}

const notify = new NotificationManager('notificationContainer');

/* ── API Error Handler ──────────────────────────────────────── */
function handleApiError(error, context) {
  const s = error.response?.status;
  let title, msg;
  if (s === 401 || s === 403) {
    title = 'Authentication Required';
    msg = 'Session expired. Redirecting to login\u2026';
    setTimeout(() => { window.location.href = '/login'; }, 2000);
  } else if (s === 404) {
    title = 'Not Found'; msg = 'Endpoint not found.';
  } else if (s === 422) {
    title = 'Validation Error'; msg = error.response?.data?.detail || 'Invalid input.';
  } else if (s === 500) {
    title = 'Server Error'; msg = error.response?.data?.detail || error.message;
  } else if (!error.response) {
    title = 'Network Error'; msg = 'Unable to reach server.';
  } else {
    title = 'Error'; msg = error.response?.data?.detail || error.message || 'Unknown error';
  }
  notify.error(title, msg);
}

/* ── Shared formatting helpers ──────────────────────────────── */
function statusIcon(s) { return s === 'passed' ? '\u2705' : s === 'skipped' ? '\u26A0\uFE0F' : '\u274C'; }
function statusCls(s)  { return s === 'passed' ? 'success' : s === 'skipped' ? 'warning' : 'error'; }

function buildHeader(result, label) {
  return '<div class="result-header ' + statusCls(result.status) + '">' +
    '<h4>' + statusIcon(result.status) + ' ' + esc(label || result.test_name || 'Test Result') + '</h4>' +
    '<div class="test-meta">' +
      '<span class="duration">\u23F1\uFE0F ' + (result.duration_seconds?.toFixed(2) || 'N/A') + 's</span>' +
      '<span class="status">Status: ' + esc(result.status) + '</span>' +
    '</div></div>';
}

function buildMessage(result) {
  return '<div class="result-message"><p><strong>\uD83D\uDCCA Result:</strong> ' + esc(result.message) + '</p></div>';
}

function buildSubTests(result) {
  if (!result.sub_tests || Object.keys(result.sub_tests).length === 0) return '';
  let h = '<div class="sub-tests-section"><h5>\uD83D\uDD0D Test Details:</h5><div class="sub-tests-grid">';
  for (const [name, t] of Object.entries(result.sub_tests)) {
    const ok = t.success;
    h += '<div class="sub-test-item ' + (ok ? 'sub-test-success' : 'sub-test-error') + '">';
    h += '<div class="sub-test-header">' + (ok ? '\u2705' : '\u274C') + ' <strong>' + esc(name) + '</strong></div>';
    h += '<div class="sub-test-message">' + esc(t.message) + '</div>';
    // Collect displayable details
    var skip = new Set(['success', 'message', 'remediation', 'error', 'error_type']);
    var allDetails = [];
    for (var _k of Object.keys(t)) {
      if (!skip.has(_k) && _k !== 'details') allDetails.push([_k, t[_k]]);
    }
    if (t.details) {
      for (var _e of Object.entries(t.details)) {
        if (!skip.has(_e[0])) allDetails.push(_e);
      }
    }
    if (allDetails.length > 0) {
      // Separate prompt/response from metadata
      var promptVal = null, responseVal = null, inputVal = null, descVal = null;
      var metaDetails = [];
      for (var _i = 0; _i < allDetails.length; _i++) {
        var dk = allDetails[_i][0], dv = allDetails[_i][1];
        if (dk === 'prompt') promptVal = dv;
        else if (dk === 'response') responseVal = dv;
        else if (dk === 'input') inputVal = dv;
        else if (dk === 'description') descVal = dv;
        else metaDetails.push([dk, dv]);
      }

      // Render IO block for prompt/response pairs
      var hasIO = promptVal || inputVal || responseVal || descVal;
      if (hasIO) {
        h += '<div class="io-block">';
        if (promptVal) {
          h += '<div class="io-row io-row-prompt"><span class="io-label">Sent</span><span class="io-value">' + esc(promptVal) + '</span></div>';
        }
        if (inputVal) {
          h += '<div class="io-row io-row-prompt"><span class="io-label">Input</span><span class="io-value">' + esc(inputVal) + '</span></div>';
        }
        if (responseVal) {
          h += '<div class="io-row io-row-response"><span class="io-label">Reply</span><span class="io-value">' + esc(responseVal) + '</span></div>';
        }
        if (descVal) {
          h += '<div class="io-row io-row-response"><span class="io-label">Reply</span><span class="io-value">' + esc(descVal) + '</span></div>';
        }
        h += '</div>';
      }

      // Render metadata as inline tags
      if (metaDetails.length > 0) {
        h += '<div class="detail-meta-row">';
        for (var _j = 0; _j < metaDetails.length; _j++) {
          var mk = metaDetails[_j][0], mv = metaDetails[_j][1];
          var display = typeof mv === 'object' ? JSON.stringify(mv) : String(mv);
          h += '<span class="detail-tag"><strong>' + esc(mk) + ':</strong> ' + esc(display) + '</span>';
        }
        h += '</div>';
      }
    }
    if (t.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(t.remediation) + '</em></div>';
    h += '</div>';
  }
  h += '</div></div>';
  return h;
}

function buildRemediation(result) {
  if (!result.remediation) return '';
  return '<div class="remediation-section"><h5>\uD83D\uDCA1 Remediation:</h5>' +
    '<div class="remediation-content">' + esc(result.remediation) + '</div></div>';
}

function buildLogs(result) {
  if (!result.logs || result.logs.length === 0) return '';
  let h = '<div class="logs-section"><h5>\uD83D\uDCDD Logs:</h5><div class="logs-content">';
  result.logs.forEach(l => {
    h += '<div class="log-entry">[' + esc(l.level) + '] ' + esc(l.message) + '</div>';
  });
  return h + '</div></div>';
}

/* ── Generic formatter (works for all tests) ────────────────── */
function formatGeneric(result) {
  return '<div class="test-result-enhanced">' +
    buildHeader(result) + buildMessage(result) + buildSubTests(result) +
    buildLogs(result) + buildRemediation(result) + '</div>';
}

/* ── Shared step-timeline builder ────────────────────────────── */
function buildStepTimeline(sub, stepKeys, labelMap) {
  var hasSteps = stepKeys.some(function(s) { return sub[s]; });
  if (!hasSteps) return '';
  var h = '<div class="sub-tests-section"><div class="step-timeline">';
  for (var si = 0; si < stepKeys.length; si++) {
    var sn = stepKeys[si], st = sub[sn];
    if (!st) continue;
    var sok = st.success;
    h += '<div class="step-item">';
    h += '<div class="step-icon ' + (sok ? 'step-icon-ok' : 'step-icon-fail') + '">' + (sok ? '\u2713' : '\u2717') + '</div>';
    h += '<div class="step-content">';
    h += '<div class="step-name">' + esc(labelMap && labelMap[sn] ? labelMap[sn] : sn.charAt(0).toUpperCase() + sn.slice(1).replace(/_/g, ' ')) + '</div>';
    h += '<div class="step-message">' + esc(st.message || '') + '</div>';
    // Collect detail tags from st.details
    if (st.details && typeof st.details === 'object') {
      var skip = new Set(['success', 'message', 'remediation', 'error', 'error_type']);
      var tags = [];
      for (var dk in st.details) {
        if (skip.has(dk)) continue;
        var dv = st.details[dk];
        if (dv == null || dv === '') continue;
        var display = typeof dv === 'object' ? JSON.stringify(dv) : String(dv);
        tags.push('<span class="detail-tag"><strong>' + esc(dk) + ':</strong> ' + esc(display) + '</span>');
      }
      if (tags.length > 0) h += '<div class="step-details">' + tags.join('') + '</div>';
    }
    if (st.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(st.remediation) + '</em></div>';
    h += '</div></div>';
  }
  h += '</div></div>';
  return h;
}

/* ── Shared AI provider formatter ───────────────────────────── */
function formatAIProvider(result, label) {
  var h = '<div class="test-result-enhanced">' + buildHeader(result, label) + buildMessage(result);
  var sub = result.sub_tests || {};
  var steps = ['chat', 'embedding', 'vision'];
  var labels = { chat: 'Chat Completion', embedding: 'Embedding', vision: 'Vision' };
  var hasSteps = steps.some(function(s) { return sub[s]; });
  if (hasSteps) {
    h += '<div class="sub-tests-section"><div class="step-timeline">';
    for (var si = 0; si < steps.length; si++) {
      var sn = steps[si], st = sub[sn];
      if (!st) continue;
      var sok = st.success;
      h += '<div class="step-item">';
      h += '<div class="step-icon ' + (sok ? 'step-icon-ok' : 'step-icon-fail') + '">' + (sok ? '\u2713' : '\u2717') + '</div>';
      h += '<div class="step-content">';
      h += '<div class="step-name">' + esc(labels[sn] || sn) + '</div>';
      h += '<div class="step-message">' + esc(st.message || '') + '</div>';
      // IO block for prompt/response
      var hasIO = st.prompt || st.input || st.response || st.description;
      if (hasIO) {
        h += '<div class="io-block">';
        if (st.prompt) h += '<div class="io-row io-row-prompt"><span class="io-label">Sent</span><span class="io-value">' + esc(st.prompt) + '</span></div>';
        if (st.input) h += '<div class="io-row io-row-prompt"><span class="io-label">Input</span><span class="io-value">' + esc(st.input) + '</span></div>';
        if (st.response) h += '<div class="io-row io-row-response"><span class="io-label">Reply</span><span class="io-value">' + esc(st.response) + '</span></div>';
        if (st.description) h += '<div class="io-row io-row-response"><span class="io-label">Reply</span><span class="io-value">' + esc(st.description) + '</span></div>';
        h += '</div>';
      }
      // Metadata tags (model, latency, etc.)
      var skipIO = new Set(['success', 'message', 'remediation', 'error', 'error_type', 'prompt', 'response', 'input', 'description', 'details']);
      var metaTags = [];
      for (var mk in st) {
        if (skipIO.has(mk)) continue;
        var mv = st[mk];
        if (mv == null || mv === '') continue;
        metaTags.push('<span class="detail-tag"><strong>' + esc(mk) + ':</strong> ' + esc(typeof mv === 'object' ? JSON.stringify(mv) : String(mv)) + '</span>');
      }
      if (st.details && typeof st.details === 'object') {
        for (var dk in st.details) {
          if (skipIO.has(dk)) continue;
          var dv = st.details[dk];
          if (dv == null || dv === '') continue;
          metaTags.push('<span class="detail-tag"><strong>' + esc(dk) + ':</strong> ' + esc(typeof dv === 'object' ? JSON.stringify(dv) : String(dv)) + '</span>');
        }
      }
      if (metaTags.length > 0) h += '<div class="detail-meta-row">' + metaTags.join('') + '</div>';
      if (st.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(st.remediation) + '</em></div>';
      h += '</div></div>';
    }
    h += '</div></div>';
  } else {
    // Fallback to generic sub-tests if keys don't match expected pattern
    h += buildSubTests(result);
  }
  h += buildRemediation(result) + '</div>';
  return h;
}

/* ── Test-specific formatters ───────────────────────────────── */
const FORMATTERS = {
  /* ── Databases ─────────────────────────────────────────────── */
  postgresqlv2: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'PostgreSQL Database') + buildMessage(result);
    var sub = result.sub_tests || {};
    h += buildStepTimeline(sub, ['connection', 'databases', 'extensions'], null);

    // Databases table
    if (sub.databases && sub.databases.databases && sub.databases.databases.length > 0) {
      h += '<div class="detail-section"><h5>Databases (' + sub.databases.databases.length + ')</h5>';
      h += '<table class="data-table"><thead><tr><th>Name</th><th>Size</th></tr></thead><tbody>';
      sub.databases.databases.forEach(function(db) {
        h += '<tr><td>' + esc(db.name) + '</td><td>' + esc(db.size_human) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    // Extensions table
    if (sub.extensions && sub.extensions.installed_extensions) {
      var installed = sub.extensions.installed_extensions;
      h += '<div class="detail-section"><h5>Extensions (' + installed.length + ' installed)</h5>';
      h += '<table class="data-table"><thead><tr><th>Extension</th><th>Version</th></tr></thead><tbody>';
      installed.forEach(function(e) {
        h += '<tr><td>' + esc(e.name) + '</td><td>' + esc(e.version) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    h += buildRemediation(result) + '</div>';
    return h;
  },

  cassandra: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'Apache Cassandra') + buildMessage(result);
    var sub = result.sub_tests || {};
    var labels = { connection: 'Connect', cluster_health: 'Cluster Health', keyspaces: 'Keyspaces', query_execution: 'Query', replication: 'Replication' };
    h += buildStepTimeline(sub, ['connection', 'cluster_health', 'keyspaces', 'query_execution', 'replication'], labels);
    h += buildRemediation(result) + '</div>';
    return h;
  },

  /* ── Object Storage ────────────────────────────────────────── */
  blobstorage: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'Azure Blob Storage') + buildMessage(result);
    var sub = result.sub_tests || {};
    var labels = { client_creation: 'Connect', container_operations: 'Container', upload_blob: 'Upload', download_blob: 'Download', list_blobs: 'List Blobs', cleanup: 'Cleanup' };
    h += buildStepTimeline(sub, ['client_creation', 'container_operations', 'upload_blob', 'download_blob', 'list_blobs', 'cleanup'], labels);
    h += buildRemediation(result) + '</div>';
    return h;
  },

  s3: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'Amazon S3 Storage') + buildMessage(result);
    var sub = result.sub_tests || {};
    var labels = { connection: 'Connect', list_buckets: 'List Buckets', bucket_access: 'Bucket Access', file_operations: 'File Ops', versioning_check: 'Versioning' };
    h += buildStepTimeline(sub, ['connection', 'list_buckets', 'bucket_access', 'file_operations', 'versioning_check'], labels);
    h += buildRemediation(result) + '</div>';
    return h;
  },

  s3compatible: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'S3 Compatible Storage') + buildMessage(result);
    var sub = result.sub_tests || {};
    var labels = { connection: 'Connect', list_buckets: 'List Buckets', bucket_access: 'Bucket Access', file_operations: 'File Ops' };
    h += buildStepTimeline(sub, ['connection', 'list_buckets', 'bucket_access', 'file_operations'], labels);
    h += buildRemediation(result) + '</div>';
    return h;
  },

  /* ── AI & ML Providers ─────────────────────────────────────── */
  azure_openai: function(result) { return formatAIProvider(result, 'Azure OpenAI'); },
  openai_direct: function(result) { return formatAIProvider(result, 'OpenAI Direct'); },
  anthropic: function(result) { return formatAIProvider(result, 'Anthropic Claude'); },
  bedrock: function(result) { return formatAIProvider(result, 'AWS Bedrock'); },
  gemini: function(result) { return formatAIProvider(result, 'Google Gemini'); },
  mistral: function(result) { return formatAIProvider(result, 'Mistral AI'); },
  vision_model: function(result) { return formatAIProvider(result, 'Vision Model'); },
  dedicated_embedding: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'Dedicated Embedding') + buildMessage(result);
    var sub = result.sub_tests || {};
    var labels = { connection: 'Connect', embedding: 'Embedding', dimensions: 'Dimensions' };
    h += buildStepTimeline(sub, ['connection', 'embedding', 'dimensions'], labels);
    h += buildRemediation(result) + '</div>';
    return h;
  },

  docintel: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'Document Intelligence') + buildMessage(result);
    var sub = result.sub_tests || {};

    // Step timeline: API Connectivity → Document Analysis → Model Information
    var steps = Object.keys(sub);
    if (steps.length > 0) {
      h += '<div class="sub-tests-section"><div class="step-timeline">';
      for (var i = 0; i < steps.length; i++) {
        var name = steps[i], st = sub[name];
        var sok = st.success;
        h += '<div class="step-item">';
        h += '<div class="step-icon ' + (sok ? 'step-icon-ok' : 'step-icon-fail') + '">' + (sok ? '\u2713' : '\u2717') + '</div>';
        h += '<div class="step-content">';
        h += '<div class="step-name">' + esc(name) + '</div>';
        h += '<div class="step-message">' + esc(st.message || '') + '</div>';

        // Metadata tags
        var tags = [];
        if (st.endpoint) tags.push('<span class="detail-tag"><strong>endpoint:</strong> ' + esc(st.endpoint) + '</span>');
        if (st.model || st.model_id) tags.push('<span class="detail-tag"><strong>model:</strong> ' + esc(st.model || st.model_id) + '</span>');
        if (st.model_type) tags.push('<span class="detail-tag"><strong>type:</strong> ' + esc(st.model_type) + '</span>');
        if (st.response_time_ms != null) tags.push('<span class="detail-tag"><strong>response:</strong> ' + esc(st.response_time_ms.toFixed(0) + 'ms') + '</span>');
        if (st.processing_time_ms != null) tags.push('<span class="detail-tag"><strong>processing:</strong> ' + esc((st.processing_time_ms / 1000).toFixed(2) + 's') + '</span>');
        if (st.page_count != null) tags.push('<span class="detail-tag"><strong>pages:</strong> ' + esc(String(st.page_count)) + '</span>');
        if (st.table_count != null) tags.push('<span class="detail-tag"><strong>tables:</strong> ' + esc(String(st.table_count)) + '</span>');
        if (st.paragraph_count != null) tags.push('<span class="detail-tag"><strong>paragraphs:</strong> ' + esc(String(st.paragraph_count)) + '</span>');
        if (st.content_length != null) tags.push('<span class="detail-tag"><strong>content:</strong> ' + esc(st.content_length + ' chars') + '</span>');
        if (tags.length > 0) h += '<div class="step-details">' + tags.join('') + '</div>';

        // Content preview as IO block
        if (st.content_preview) {
          h += '<div class="io-block" style="margin-top:6px">';
          h += '<div class="io-row io-row-response"><span class="io-label">TEXT</span><span class="io-value">' + esc(st.content_preview) + '</span></div>';
          h += '</div>';
        }

        if (st.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(st.remediation) + '</em></div>';
        h += '</div></div>';
      }
      h += '</div></div>';
    }

    h += buildRemediation(result) + '</div>';
    return h;
  },

  /* ── Infrastructure ────────────────────────────────────────── */
  pvc: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'Kubernetes PVC') + buildMessage(result);
    var sub = result.sub_tests || {};
    var stepKeys = ['List Storage Classes', 'Namespace Access', 'PVC Creation', 'PVC Status', 'PVC Cleanup'];
    var labels = {};
    stepKeys.forEach(function(k) { labels[k] = k; });
    h += buildStepTimeline(sub, stepKeys, labels);
    h += buildRemediation(result) + '</div>';
    return h;
  },

  gpu: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'GPU Detection') + buildMessage(result);
    var sub = result.sub_tests || {};
    var keys = Object.keys(sub);

    if (keys.length > 0) {
      h += '<div class="sub-tests-section"><div class="step-timeline">';
      for (var i = 0; i < keys.length; i++) {
        var name = keys[i], st = sub[name];
        var sok = st.success;
        h += '<div class="step-item">';
        h += '<div class="step-icon ' + (sok ? 'step-icon-ok' : 'step-icon-fail') + '">' + (sok ? '\u2713' : '\u2717') + '</div>';
        h += '<div class="step-content">';
        h += '<div class="step-name">' + esc(name) + '</div>';
        h += '<div class="step-message">' + esc(st.message || '') + '</div>';

        // Metadata tags for GPU details
        var tags = [];
        if (st.gpu_count != null) tags.push('<span class="detail-tag"><strong>count:</strong> ' + esc(String(st.gpu_count)) + '</span>');
        if (st.driver_version) tags.push('<span class="detail-tag"><strong>driver:</strong> ' + esc(st.driver_version) + '</span>');
        if (st.cuda_version) tags.push('<span class="detail-tag"><strong>CUDA:</strong> ' + esc(st.cuda_version) + '</span>');
        if (st.compute_capability) tags.push('<span class="detail-tag"><strong>compute:</strong> ' + esc(st.compute_capability) + '</span>');
        if (st.gpu_name) tags.push('<span class="detail-tag"><strong>model:</strong> ' + esc(st.gpu_name) + '</span>');
        if (st.memory_total_gb != null) tags.push('<span class="detail-tag"><strong>VRAM:</strong> ' + esc(st.memory_total_gb + ' GB') + '</span>');
        if (st.memory_used_gb != null) tags.push('<span class="detail-tag"><strong>used:</strong> ' + esc(st.memory_used_gb + ' GB') + '</span>');
        if (st.utilization_gpu_percent != null && st.utilization_gpu_percent !== 'N/A') tags.push('<span class="detail-tag"><strong>GPU util:</strong> ' + esc(st.utilization_gpu_percent + '%') + '</span>');
        if (st.temperature_celsius != null) tags.push('<span class="detail-tag"><strong>temp:</strong> ' + esc(st.temperature_celsius + '\u00B0C') + '</span>');
        if (st.power_draw_watts && st.power_draw_watts !== 'N/A') tags.push('<span class="detail-tag"><strong>power:</strong> ' + esc(st.power_draw_watts + '/' + (st.power_limit_watts || '?') + 'W') + '</span>');
        if (tags.length > 0) h += '<div class="step-details">' + tags.join('') + '</div>';

        if (st.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(st.remediation) + '</em></div>';
        h += '</div></div>';
      }
      h += '</div></div>';
    }

    h += buildRemediation(result) + '</div>';
    return h;
  },

  dns: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'DNS Resolution') + buildMessage(result);
    var sub = result.sub_tests || {};
    var keys = Object.keys(sub);
    if (keys.length > 0) {
      h += '<div class="sub-tests-section">';
      for (var i = 0; i < keys.length; i++) {
        var hostname = keys[i], st = sub[hostname];
        var sok = st.success;
        h += '<div class="dns-lookup-card ' + (sok ? 'dns-lookup-ok' : 'dns-lookup-fail') + '">';
        h += '<div class="dns-lookup-header">';
        h += '<span class="dns-lookup-icon">' + (sok ? '\u2713' : '\u2717') + '</span>';
        h += '<span class="dns-lookup-host">' + esc(hostname) + '</span>';
        if (st.latency_ms != null) h += '<span class="dns-lookup-latency">' + esc(st.latency_ms.toFixed(1)) + 'ms</span>';
        h += '</div>';

        // IO-block style detail table
        h += '<div class="io-block">';
        h += '<div class="io-row io-row-prompt"><span class="io-label">QUERY</span><span class="io-value">' + esc(hostname) + '</span></div>';
        if (st.resolver) h += '<div class="io-row"><span class="io-label">RSLVR</span><span class="io-value">' + esc(st.resolver) + '</span></div>';
        if (st.record_types && st.record_types.length > 0) {
          h += '<div class="io-row"><span class="io-label">TYPE</span><span class="io-value">' + esc(st.record_types.join(' + ')) + '</span></div>';
        }
        if (sok) {
          if (st.ipv4_addresses && st.ipv4_addresses.length > 0) {
            h += '<div class="io-row io-row-response"><span class="io-label">IPv4</span><span class="io-value">' + esc(st.ipv4_addresses.join(', ')) + '</span></div>';
          }
          if (st.ipv6_addresses && st.ipv6_addresses.length > 0) {
            h += '<div class="io-row io-row-response"><span class="io-label">IPv6</span><span class="io-value">' + esc(st.ipv6_addresses.join(', ')) + '</span></div>';
          }
          if (st.canonical_name) {
            h += '<div class="io-row"><span class="io-label">CNAME</span><span class="io-value">' + esc(st.canonical_name) + '</span></div>';
          }
        } else {
          h += '<div class="io-row io-row-error"><span class="io-label">ERROR</span><span class="io-value">' + esc(st.error_code || st.message || 'Resolution failed') + '</span></div>';
        }
        h += '</div>'; // io-block

        if (st.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(st.remediation) + '</em></div>';
        h += '</div>'; // dns-lookup-card
      }
      h += '</div>'; // sub-tests-section
    }
    h += buildRemediation(result) + '</div>';
    return h;
  },

  ssl: function(result) {
    var h = '<div class="test-result-enhanced">' + buildHeader(result, 'SSL Certificates') + buildMessage(result);
    var sub = result.sub_tests || {};

    for (var name in sub) {
      var t = sub[name];
      var ok = t.success;
      var ci = t.certificate_info || {};
      var checks = t.checks || {};
      var conn = checks.connection || {};

      h += '<div class="dns-lookup-card ' + (ok ? 'dns-lookup-ok' : 'dns-lookup-fail') + '">';
      h += '<div class="dns-lookup-header">';
      h += '<span class="dns-lookup-icon">' + (ok ? '\u2713' : '\u2717') + '</span>';
      h += '<span class="dns-lookup-host">' + esc(t.hostname || name) + (t.port && t.port !== 443 ? ':' + t.port : '') + '</span>';
      h += '</div>';
      h += '<div class="io-block">';

      // Trust / connection status
      if (conn.version) {
        h += '<div class="io-row"><span class="io-label">TLS</span><span class="io-value">' + esc(conn.version);
        if (conn.cipher) h += ' / ' + esc(conn.cipher[0]) + ' (' + conn.cipher[2] + '-bit)';
        h += '</span></div>';
      }

      // Self-signed detection
      var chainCheck = checks.certificate_chain || {};
      var isSelfSigned = (chainCheck.chain_details || []).some(function(c) { return c.position === 0 && c.is_self_signed; });
      var trustLabel = conn.success ? (isSelfSigned ? 'Self-Signed' : 'Trusted') : 'Connection Failed';
      var trustClass = conn.success && !isSelfSigned ? 'io-row-response' : 'io-row-error';
      h += '<div class="io-row ' + trustClass + '"><span class="io-label">TRUST</span><span class="io-value">' + esc(trustLabel) + '</span></div>';

      // Subject and issuer
      if (ci.subject) h += '<div class="io-row"><span class="io-label">SUBJ</span><span class="io-value">' + esc(ci.subject) + '</span></div>';
      if (ci.issuer) h += '<div class="io-row"><span class="io-label">ISSUER</span><span class="io-value">' + esc(ci.issuer) + '</span></div>';

      // Validity
      if (ci.valid_until) {
        var expiryClass = ci.days_until_expiry < 0 ? 'io-row-error' : ci.days_until_expiry < 30 ? 'io-row-prompt' : 'io-row-response';
        var expiryText = ci.days_until_expiry < 0 ? 'EXPIRED' : ci.days_until_expiry + ' days remaining';
        h += '<div class="io-row ' + expiryClass + '"><span class="io-label">VALID</span><span class="io-value">' + esc(ci.valid_from || '') + ' \u2192 ' + esc(ci.valid_until) + ' (' + esc(expiryText) + ')</span></div>';
      }

      // Chain
      if (ci.chain_length != null) h += '<div class="io-row"><span class="io-label">CHAIN</span><span class="io-value">' + esc(ci.chain_length + ' certificate(s)') + '</span></div>';

      // Hostname match
      var hmCheck = checks.hostname_match || {};
      if (hmCheck.message) {
        var hmClass = hmCheck.success ? 'io-row-response' : 'io-row-error';
        h += '<div class="io-row ' + hmClass + '"><span class="io-label">MATCH</span><span class="io-value">' + esc(hmCheck.message) + '</span></div>';
      }

      h += '</div>'; // io-block

      if (t.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(t.remediation) + '</em></div>';
      h += '</div>'; // dns-lookup-card
    }

    h += buildRemediation(result) + '</div>';
    return h;
  }
};

/* ── Main formatting dispatcher ─────────────────────────────── */
function formatTestDetails(result, testId) {
  const formatter = FORMATTERS[testId];
  return formatter ? formatter(result) : formatGeneric(result);
}

/* ── Test Execution ─────────────────────────────────────────── */
async function runTest(testId) {
  const statusEl = document.getElementById(testId + '-status');
  const btn = document.getElementById(testId + '-btn');
  const detailsEl = document.getElementById(testId + '-details');
  if (!statusEl || !btn) return;

  statusEl.textContent = 'Running\u2026';
  statusEl.className = 'test-status running';
  btn.disabled = true;
  btn.innerHTML = 'Running <span class="loading-spinner"></span>';
  detailsEl.classList.remove('show');

  try {
    const resp = await axios.post('/api/tests/' + testId);
    const r = resp.data.result || resp.data;
    statusEl.textContent = r.status === 'passed' ? 'Passed' : r.status === 'skipped' ? 'Skipped' : 'Failed';
    statusEl.className = 'test-status ' + (r.status === 'passed' ? 'passed' : r.status === 'skipped' ? 'pending' : 'failed');
    detailsEl.innerHTML = formatTestDetails(r, testId);
    detailsEl.classList.add('show');
  } catch (err) {
    statusEl.textContent = 'Error';
    statusEl.className = 'test-status failed';
    detailsEl.innerHTML = '<strong>Error:</strong> ' + esc(err.response?.data?.detail || err.message);
    detailsEl.classList.add('show');
    handleApiError(err, testId + ' test');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Run Test';
  }
}

async function runAllTests() {
  const btn = document.getElementById('runAllTestsBtn');
  btn.disabled = true;
  btn.innerHTML = 'Running All Tests <span class="loading-spinner"></span>';

  try {
    const resp = await axios.post('/api/tests/run-all');
    const data = resp.data;
    const results = data.results || {};

    for (const [testId, result] of Object.entries(results)) {
      const statusEl = document.getElementById(testId + '-status');
      const detailsEl = document.getElementById(testId + '-details');
      if (!statusEl) continue;

      statusEl.textContent = result.status === 'passed' ? 'Passed' : result.status === 'skipped' ? 'Skipped' : 'Failed';
      statusEl.className = 'test-status ' + (result.status === 'passed' ? 'passed' : result.status === 'skipped' ? 'skipped' : 'failed');

      if (detailsEl) {
        detailsEl.innerHTML = formatTestDetails(result, testId);
        detailsEl.classList.add('show');
      }
    }

    if (data.overall_status) {
      const msg = (data.passed_count || 0) + ' passed, ' + (data.failed_count || 0) + ' failed, ' + (data.skipped_count || 0) + ' skipped';
      notify.show(data.failed_count > 0 ? 'warning' : 'success', 'All Tests Complete', msg);
    }
  } catch (err) {
    handleApiError(err, 'Running all tests');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Run All Tests';
  }
}

/* ── Status check (page load) ───────────────────────────────── */
async function checkTestStatus() {
  try {
    const resp = await axios.get('/api/tests/status');
    const tests = resp.data.tests || {};
    for (const [id, t] of Object.entries(tests)) {
      const el = document.getElementById(id + '-status');
      if (!el || !t.status) continue;
      const when = t.last_run ? new Date(t.last_run).toLocaleString() : 'Never';
      el.textContent = 'Last: ' + (t.status === 'passed' ? 'Passed' : t.status === 'failed' ? 'Failed' : 'Skipped') + ' (' + when + ')';
      el.className = 'test-status ' + (t.status === 'passed' ? 'passed' : t.status === 'failed' ? 'failed' : 'pending');
    }
  } catch (err) {
    console.warn('Status check failed:', err.message);
  }
}

/* ── Version loader ─────────────────────────────────────────── */
async function loadVersion() {
  try {
    const resp = await fetch('/version');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    document.getElementById('version-display').textContent = 'v' + data.version;
  } catch (err) {
    console.warn('Version load failed:', err.message);
    document.getElementById('version-display').textContent = 'v' + (window.APP_VERSION || '');
  }
}

/* ── DNS ad-hoc resolver ────────────────────────────────────── */
async function resolveDns() {
  const input = document.getElementById('dns-hostname');
  const resultEl = document.getElementById('dns-resolve-result');
  if (!input || !resultEl) return;
  const hostname = input.value.trim();
  if (!hostname) { resultEl.textContent = 'Enter a hostname'; return; }

  resultEl.textContent = 'Resolving\u2026';
  try {
    const resp = await axios.post('/api/tests/dns/resolve', { hostname: hostname });
    const d = resp.data;
    if (d.resolved || d.success) {
      var h = '<div class="dns-lookup-card dns-lookup-ok" style="margin-top:8px">';
      h += '<div class="dns-lookup-header">';
      h += '<span class="dns-lookup-icon">\u2713</span>';
      h += '<span class="dns-lookup-host">' + esc(hostname) + '</span>';
      if (d.latency_ms) h += '<span class="dns-lookup-latency">' + d.latency_ms.toFixed(1) + 'ms</span>';
      h += '</div>';
      h += '<div class="io-block">';
      if (d.resolver) h += '<div class="io-row"><span class="io-label">RSLVR</span><span class="io-value">' + esc(d.resolver) + '</span></div>';
      if (d.record_types && d.record_types.length) h += '<div class="io-row"><span class="io-label">TYPE</span><span class="io-value">' + esc(d.record_types.join(' + ')) + '</span></div>';
      if (d.ipv4_addresses && d.ipv4_addresses.length) h += '<div class="io-row io-row-response"><span class="io-label">IPv4</span><span class="io-value">' + esc(d.ipv4_addresses.join(', ')) + '</span></div>';
      if (d.ipv6_addresses && d.ipv6_addresses.length) h += '<div class="io-row io-row-response"><span class="io-label">IPv6</span><span class="io-value">' + esc(d.ipv6_addresses.join(', ')) + '</span></div>';
      if (d.canonical_name) h += '<div class="io-row"><span class="io-label">CNAME</span><span class="io-value">' + esc(d.canonical_name) + '</span></div>';
      h += '</div></div>';
      resultEl.innerHTML = h;
    } else {
      var h = '<div class="dns-lookup-card dns-lookup-fail" style="margin-top:8px">';
      h += '<div class="dns-lookup-header"><span class="dns-lookup-icon">\u2717</span><span class="dns-lookup-host">' + esc(hostname) + '</span></div>';
      h += '<div class="io-block"><div class="io-row io-row-error"><span class="io-label">ERROR</span><span class="io-value">' + esc(d.error_code || d.message || 'Resolution failed') + '</span></div>';
      if (d.resolver) h += '<div class="io-row"><span class="io-label">RSLVR</span><span class="io-value">' + esc(d.resolver) + '</span></div>';
      h += '</div></div>';
      resultEl.innerHTML = h;
    }
  } catch (err) {
    resultEl.innerHTML = '<strong>Error:</strong> ' + esc(err.response?.data?.detail || err.message);
  }
}

/* ── SSL ad-hoc checker ────────────────────────────────────── */
function formatSslCheckResult(d) {
  var ok = d.success;
  var cls = ok ? 'dns-lookup-ok' : 'dns-lookup-fail';
  var icon = ok ? '\u2713' : '\u2717';
  var h = '<div class="dns-lookup-card ' + cls + '" style="margin-top:8px">';
  h += '<div class="dns-lookup-header">';
  h += '<span class="dns-lookup-icon">' + icon + '</span>';
  h += '<span class="dns-lookup-host">' + esc(d.hostname) + ':' + esc(String(d.port)) + '</span>';
  if (d.latency_ms != null) h += '<span class="dns-lookup-latency">' + d.latency_ms.toFixed(1) + 'ms</span>';
  h += '</div>';
  h += '<div class="io-block">';

  if (ok) {
    // Trust status
    var trustLabel = d.trusted ? 'Trusted' : d.is_self_signed ? 'Self-Signed' : 'Untrusted';
    var trustClass = d.trusted ? 'io-row-response' : 'io-row-error';
    h += '<div class="io-row ' + trustClass + '"><span class="io-label">TRUST</span><span class="io-value">' + esc(trustLabel);
    if (!d.trusted && d.trust_error) h += ' \u2014 ' + esc(d.trust_error);
    h += '</span></div>';

    // TLS version and cipher
    if (d.tls_version) h += '<div class="io-row"><span class="io-label">TLS</span><span class="io-value">' + esc(d.tls_version) + (d.cipher ? ' / ' + esc(d.cipher) : '') + (d.cipher_bits ? ' (' + d.cipher_bits + '-bit)' : '') + '</span></div>';

    // Subject
    h += '<div class="io-row"><span class="io-label">SUBJ</span><span class="io-value">' + esc(d.subject) + '</span></div>';

    // Issuer
    h += '<div class="io-row"><span class="io-label">ISSUER</span><span class="io-value">' + esc(d.issuer) + '</span></div>';

    // Validity
    var expiryClass = d.expired ? 'io-row-error' : d.days_remaining < 30 ? 'io-row-prompt' : 'io-row-response';
    var expiryText = d.expired ? 'EXPIRED' : d.days_remaining + ' days remaining';
    h += '<div class="io-row ' + expiryClass + '"><span class="io-label">VALID</span><span class="io-value">' + esc(d.not_before) + ' \u2192 ' + esc(d.not_after) + ' (' + esc(expiryText) + ')</span></div>';

    // SANs
    if (d.san && d.san.length > 0) {
      h += '<div class="io-row"><span class="io-label">SAN</span><span class="io-value">' + esc(d.san.join(', ')) + '</span></div>';
    }

    // Hostname match
    var matchClass = d.hostname_match ? 'io-row-response' : 'io-row-error';
    var matchText = d.hostname_match ? 'Yes' + (d.matched_name ? ' (' + d.matched_name + ')' : '') : 'No \u2014 hostname not in certificate SANs';
    h += '<div class="io-row ' + matchClass + '"><span class="io-label">MATCH</span><span class="io-value">' + esc(matchText) + '</span></div>';

    // Key and signature
    var keyText = (d.key_type || 'Unknown') + (d.key_size ? ' ' + d.key_size + '-bit' : '');
    h += '<div class="io-row"><span class="io-label">KEY</span><span class="io-value">' + esc(keyText) + '</span></div>';
    if (d.signature_algorithm) h += '<div class="io-row"><span class="io-label">SIG</span><span class="io-value">' + esc(d.signature_algorithm) + '</span></div>';

    // Serial
    if (d.serial) h += '<div class="io-row"><span class="io-label">SN</span><span class="io-value">' + esc(d.serial) + '</span></div>';
  } else {
    h += '<div class="io-row io-row-error"><span class="io-label">ERROR</span><span class="io-value">' + esc(d.message || 'Check failed') + '</span></div>';
  }

  h += '</div></div>';
  return h;
}

async function checkSsl() {
  const input = document.getElementById('ssl-hostname');
  const portInput = document.getElementById('ssl-port');
  const resultEl = document.getElementById('ssl-check-result');
  if (!input || !resultEl) return;
  const hostname = input.value.trim();
  if (!hostname) { resultEl.textContent = 'Enter a hostname'; return; }
  var port = parseInt(portInput && portInput.value ? portInput.value : '443', 10) || 443;

  resultEl.textContent = 'Checking SSL\u2026';
  try {
    const resp = await axios.post('/api/tests/ssl/check', { hostname: hostname, port: port });
    resultEl.innerHTML = formatSslCheckResult(resp.data);
  } catch (err) {
    resultEl.innerHTML = '<strong>Error:</strong> ' + esc(err.response?.data?.detail || err.message);
  }
}

/* ── Pod Diagnostics ────────────────────────────────────────── */
var _diagPollTimer = null;

async function collectDiagnostics() {
  var ns = document.getElementById('diag-namespace').value.trim();
  if (!ns) { notify.warning('Missing Input', 'Please enter a namespace.'); return; }

  var sinceEl = document.getElementById('diag-since');
  var since = sinceEl ? sinceEl.value : '';

  var btn = document.getElementById('diagCollectBtn');
  var dlBtn = document.getElementById('diagDownloadBtn');
  var statusEl = document.getElementById('diagStatus');
  var statusText = document.getElementById('diagStatusText');
  var statusIcon = document.getElementById('diagStatusIcon');

  btn.disabled = true;
  // Use textContent + appendChild for spinner to avoid innerHTML with user content
  btn.textContent = 'Collecting ';
  var spinner = document.createElement('span');
  spinner.className = 'loading-spinner';
  btn.appendChild(spinner);
  dlBtn.style.display = 'none';
  statusEl.style.display = 'flex';
  statusIcon.className = 'diag-status-icon diag-status-collecting';
  statusText.textContent = 'Starting collection for namespace "' + ns + '"...';

  try {
    await axios.post('/api/diagnostics/collect', { namespace: ns, since: since });
    // Start polling for status
    _diagPollTimer = setInterval(pollDiagnosticsStatus, 2000);
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Collect Diagnostics';
    statusIcon.className = 'diag-status-icon diag-status-error';
    statusText.textContent = err.response?.data?.detail || err.message || 'Collection failed';
    handleApiError(err, 'diagnostics');
  }
}

function buildDiagProgress(data) {
  // Pipeline definition: ordered phases with icons and group labels
  var pipeline = [
    { key: 'init',       label: 'Initialize',        icon: '\u2699', group: 'Setup' },
    { key: 'events',     label: 'Namespace Events',   icon: '\ud83d\udcdc', group: 'Namespace' },
    { key: 'services',   label: 'Services',           icon: '\ud83d\udd17', group: 'Namespace' },
    { key: 'configmaps', label: 'ConfigMaps',         icon: '\ud83d\udcc4', group: 'Namespace' },
    { key: 'secrets',    label: 'Secrets',            icon: '\ud83d\udd12', group: 'Namespace' },
    { key: 'discover',   label: 'Discover Pods',      icon: '\ud83d\udd0d', group: 'Pods' },
    { key: 'pod',        label: 'Collect Pod Data',   icon: '\ud83d\udce6', group: 'Pods' },
    { key: 'archive',    label: 'Create Archive',     icon: '\ud83d\uddc3', group: 'Finalize' },
    { key: 'complete',   label: 'Complete',           icon: '\ud83c\udfc1', group: 'Finalize' }
  ];

  var completed = data.completed_steps || [];
  var current = data.current_step || '';
  var detail = data.current_detail || '';

  // Normalize pod-done to pod
  if (current === 'pod-done') current = 'pod';

  // Build lookup for step status
  var completedSet = {};
  for (var c = 0; c < completed.length; c++) {
    completedSet[completed[c]] = true;
    if (completed[c] === 'pod-done') completedSet['pod'] = true;
  }

  // Find current step index
  var currentIdx = -1;
  for (var ci = 0; ci < pipeline.length; ci++) {
    if (pipeline[ci].key === current) { currentIdx = ci; break; }
  }

  var h = '<div class="diag-pipeline">';
  var lastGroup = '';

  for (var i = 0; i < pipeline.length; i++) {
    var step = pipeline[i];
    var isDone = completedSet[step.key] || false;
    var isActive = (step.key === current && current !== 'complete');
    var isComplete = (current === 'complete');
    var isPending = !isDone && !isActive && !isComplete;

    // Group header
    if (step.group !== lastGroup) {
      if (lastGroup) h += '</div>'; // close previous group
      h += '<div class="diag-group">';
      h += '<div class="diag-group-label">' + esc(step.group) + '</div>';
      lastGroup = step.group;
    }

    // Node status class
    var cls = 'diag-node';
    if (isDone || isComplete) cls += ' diag-node-done';
    else if (isActive) cls += ' diag-node-active';
    else cls += ' diag-node-pending';

    // Connector line (not for first step)
    if (i > 0 && step.group === pipeline[i - 1].group) {
      var lineCls = 'diag-connector';
      if (isDone || isComplete) lineCls += ' diag-connector-done';
      else if (isActive) lineCls += ' diag-connector-active';
      h += '<div class="' + lineCls + '"></div>';
    }

    h += '<div class="' + cls + '">';
    h += '<div class="diag-node-indicator">';

    if (isDone || isComplete) {
      h += '<svg class="diag-check-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>';
    } else if (isActive) {
      h += '<span class="diag-node-spinner"></span>';
    } else {
      h += '<span class="diag-node-dot"></span>';
    }

    h += '</div>';
    h += '<div class="diag-node-content">';
    h += '<span class="diag-node-label">' + esc(step.label) + '</span>';

    // Pod progress sub-visualization
    if (step.key === 'pod' && isActive && data.total_pods > 0) {
      var podPct = Math.round((data.pod_count / data.total_pods) * 100);
      var podName = detail.replace(/^\d+\/\d+\s*/, '').replace(/\s*-\s*(status|describe|env vars|logs).*$/i, '');
      h += '<div class="diag-pod-tracker">';
      h += '<div class="diag-pod-meta">';
      h += '<span class="diag-pod-count">' + data.pod_count + ' / ' + data.total_pods + ' pods</span>';
      h += '<span class="diag-pod-pct">' + podPct + '%</span>';
      h += '</div>';
      h += '<div class="diag-pod-bar"><div class="diag-pod-bar-fill" style="width:' + podPct + '%"></div></div>';
      if (podName) {
        h += '<div class="diag-pod-current">';
        h += '<span class="diag-pod-current-icon">\u25b6</span> ';
        h += '<span class="diag-pod-current-name">' + esc(podName) + '</span>';
        // Show sub-step (status, describe, logs, etc.)
        var subStep = '';
        if (/status/i.test(detail)) subStep = 'status';
        else if (/describe/i.test(detail)) subStep = 'describe';
        else if (/env/i.test(detail)) subStep = 'env vars';
        else if (/secrets/i.test(detail)) subStep = 'secrets';
        else if (/configmaps/i.test(detail)) subStep = 'configmaps';
        else if (/logs/i.test(detail)) subStep = 'logs';
        if (subStep) h += ' <span class="diag-pod-substep">' + subStep + '</span>';
        h += '</div>';
      }
      h += '</div>';
    } else if (isActive && detail) {
      h += '<span class="diag-node-detail">' + esc(detail) + '</span>';
    }

    // Duration hint for completed pod step
    if (step.key === 'pod' && isDone && data.pod_count > 0) {
      h += '<span class="diag-node-detail">' + data.pod_count + ' pods processed</span>';
    }

    h += '</div>'; // node-content
    h += '</div>'; // node
  }

  if (lastGroup) h += '</div>'; // close last group
  h += '</div>'; // pipeline
  return h;
}

async function pollDiagnosticsStatus() {
  try {
    var resp = await axios.get('/api/diagnostics/status');
    var data = resp.data;
    var statusEl = document.getElementById('diagStatus');
    var statusText = document.getElementById('diagStatusText');
    var statusIcon = document.getElementById('diagStatusIcon');
    var btn = document.getElementById('diagCollectBtn');
    var dlBtn = document.getElementById('diagDownloadBtn');

    if (data.state === 'collecting') {
      statusIcon.className = 'diag-status-icon diag-status-collecting';
      statusText.textContent = '';
      // Replace status text with rich progress
      var progressEl = document.getElementById('diagProgressDetail');
      if (!progressEl) {
        progressEl = document.createElement('div');
        progressEl.id = 'diagProgressDetail';
        statusEl.appendChild(progressEl);
      }
      progressEl.innerHTML = buildDiagProgress(data);
    } else if (data.state === 'ready') {
      clearInterval(_diagPollTimer);
      _diagPollTimer = null;
      statusIcon.className = 'diag-status-icon diag-status-ready';
      statusText.textContent = '';
      // Show completed pipeline with all steps done
      var pd = document.getElementById('diagProgressDetail');
      if (!pd) {
        pd = document.createElement('div');
        pd.id = 'diagProgressDetail';
        statusEl.appendChild(pd);
      }
      pd.innerHTML = buildDiagProgress(data);
      btn.disabled = false;
      btn.textContent = 'Collect Diagnostics';
      dlBtn.style.display = 'inline-flex';
      notify.success('Diagnostics Ready', data.pod_count + ' pod(s) collected from "' + (data.namespace || '') + '".');
    } else if (data.state === 'error') {
      clearInterval(_diagPollTimer);
      _diagPollTimer = null;
      statusIcon.className = 'diag-status-icon diag-status-error';
      statusText.textContent = 'Error: ' + (data.error || 'Unknown error');
      var pd2 = document.getElementById('diagProgressDetail');
      if (pd2) pd2.remove();
      btn.disabled = false;
      btn.textContent = 'Collect Diagnostics';
      notify.error('Diagnostics Failed', data.error || 'Unknown error');
    }
  } catch (err) {
    clearInterval(_diagPollTimer);
    _diagPollTimer = null;
    document.getElementById('diagCollectBtn').disabled = false;
    document.getElementById('diagCollectBtn').textContent = 'Collect Diagnostics';
  }
}

function downloadDiagnostics() {
  window.location.href = '/api/diagnostics/download';
}

/* ── Init ────────────────────────────────────────────────────── */
window.addEventListener('load', function() {
  // Bind test buttons via data attributes (CSP-safe, no inline onclick)
  document.querySelectorAll('[data-test-id]').forEach(function(btn) {
    btn.addEventListener('click', function() { runTest(this.dataset.testId); });
  });
  var runAllBtn = document.getElementById('runAllTestsBtn');
  if (runAllBtn) runAllBtn.addEventListener('click', runAllTests);
  var dnsBtn = document.getElementById('dns-resolve-btn');
  if (dnsBtn) dnsBtn.addEventListener('click', resolveDns);
  var sslBtn = document.getElementById('ssl-check-btn');
  if (sslBtn) sslBtn.addEventListener('click', checkSsl);

  // Diagnostics buttons
  var diagCollect = document.getElementById('diagCollectBtn');
  if (diagCollect) diagCollect.addEventListener('click', collectDiagnostics);
  var diagDownload = document.getElementById('diagDownloadBtn');
  if (diagDownload) diagDownload.addEventListener('click', downloadDiagnostics);

  checkTestStatus();
  loadVersion();
});
