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
  let title, msg, det;
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
  notify.error(title, msg, det);
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
    if (t.details) {
      // Show key details as compact list
      const skip = new Set(['success', 'message', 'remediation', 'error', 'error_type']);
      const entries = Object.entries(t.details).filter(([k]) => !skip.has(k));
      if (entries.length > 0) {
        h += '<div class="sub-test-details">';
        for (const [k, v] of entries) {
          const display = typeof v === 'object' ? JSON.stringify(v) : String(v);
          h += '<span class="detail-tag"><strong>' + esc(k) + ':</strong> ' + esc(display) + '</span> ';
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

/* ── Test-specific formatters (only where generic isn't enough) */
const FORMATTERS = {
  postgresqlv2: function(result) {
    let h = '<div class="test-result-enhanced">' + buildHeader(result, 'PostgreSQL Database') + buildMessage(result);
    const sub = result.sub_tests || {};

    // Connection info
    if (sub.connection?.success && sub.connection.details) {
      h += '<div class="detail-section"><h5>\uD83D\uDD17 Connection</h5>';
      h += '<p>' + esc(sub.connection.details.version || '') + '</p></div>';
    }

    // Databases table
    if (sub.databases?.databases?.length > 0) {
      h += '<div class="detail-section"><h5>\uD83D\uDDC4\uFE0F Databases (' + sub.databases.databases.length + ')</h5>';
      h += '<table class="data-table"><thead><tr><th>Name</th><th>Size</th></tr></thead><tbody>';
      sub.databases.databases.forEach(db => {
        h += '<tr><td>' + esc(db.name) + '</td><td>' + esc(db.size_human) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    // Extensions with critical check
    if (sub.extensions?.installed_extensions) {
      const installed = sub.extensions.installed_extensions;
      const critical = window.CRITICAL_POSTGRESQL_EXTENSIONS || [];
      h += '<div class="detail-section"><h5>\uD83E\uDDE9 Extensions (' + installed.length + ' installed)</h5>';
      if (critical.length > 0) {
        h += '<div class="critical-ext-check">';
        critical.forEach(ext => {
          const found = installed.some(e => e.name === ext);
          h += '<span class="ext-badge ' + (found ? 'ext-ok' : 'ext-missing') + '">' +
            (found ? '\u2705' : '\u274C') + ' ' + esc(ext) + '</span> ';
        });
        h += '</div>';
      }
      h += '<table class="data-table"><thead><tr><th>Extension</th><th>Version</th></tr></thead><tbody>';
      installed.forEach(e => {
        h += '<tr><td>' + esc(e.name) + '</td><td>' + esc(e.version) + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }

    h += buildRemediation(result) + '</div>';
    return h;
  },

  ssl: function(result) {
    let h = '<div class="test-result-enhanced">' + buildHeader(result, 'SSL Certificates') + buildMessage(result);
    const sub = result.sub_tests || {};

    for (const [name, t] of Object.entries(sub)) {
      const ok = t.success;
      h += '<div class="sub-test-item ' + (ok ? 'sub-test-success' : 'sub-test-error') + '">';
      h += '<div class="sub-test-header">' + (ok ? '\u2705' : '\u274C') + ' <strong>' + esc(name) + '</strong></div>';
      h += '<div class="sub-test-message">' + esc(t.message) + '</div>';

      // Certificate details
      if (t.details) {
        const d = t.details;
        if (d.subject) h += '<div class="cert-detail"><strong>Subject:</strong> ' + esc(d.subject) + '</div>';
        if (d.issuer) h += '<div class="cert-detail"><strong>Issuer:</strong> ' + esc(d.issuer) + '</div>';
        if (d.not_after) h += '<div class="cert-detail"><strong>Expires:</strong> ' + esc(d.not_after) +
          (d.days_remaining != null ? ' (' + d.days_remaining + ' days)' : '') + '</div>';
        if (d.serial_number) h += '<div class="cert-detail"><strong>Serial:</strong> ' + esc(d.serial_number) + '</div>';
        if (d.san && d.san.length > 0) h += '<div class="cert-detail"><strong>SANs:</strong> ' + esc(d.san.join(', ')) + '</div>';
      }
      if (t.remediation) h += '<div class="remediation">\uD83D\uDCA1 <em>' + esc(t.remediation) + '</em></div>';
      h += '</div>';
    }

    h += buildRemediation(result) + '</div>';
    return h;
  },

  gpu: function(result) {
    let h = '<div class="test-result-enhanced">' + buildHeader(result, 'GPU Detection') + buildMessage(result);

    if (result.details) {
      const d = result.details;
      h += '<div class="detail-section">';
      if (d.gpu_available !== undefined) {
        h += '<p><strong>GPU Available:</strong> ' + (d.gpu_available ? '\u2705 Yes' : '\u274C No') + '</p>';
      }
      if (d.gpu_count) h += '<p><strong>GPU Count:</strong> ' + esc(String(d.gpu_count)) + '</p>';
      if (d.driver_version) h += '<p><strong>Driver:</strong> ' + esc(d.driver_version) + '</p>';
      if (d.cuda_version) h += '<p><strong>CUDA:</strong> ' + esc(d.cuda_version) + '</p>';

      if (d.devices && d.devices.length > 0) {
        h += '<table class="data-table"><thead><tr><th>Device</th><th>Memory</th><th>Utilization</th></tr></thead><tbody>';
        d.devices.forEach(dev => {
          h += '<tr><td>' + esc(dev.name) + '</td><td>' + esc(dev.memory_total || '') + '</td><td>' + esc(dev.utilization || '') + '</td></tr>';
        });
        h += '</tbody></table>';
      }
      h += '</div>';
    }

    h += buildSubTests(result) + buildRemediation(result) + '</div>';
    return h;
  },

  documentintelligence: function(result) {
    let h = '<div class="test-result-enhanced">' + buildHeader(result, 'Document Intelligence') + buildMessage(result);
    h += buildSubTests(result) + buildRemediation(result) + '</div>';
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
    if (d.success) {
      resultEl.innerHTML = '<strong>' + esc(hostname) + '</strong>: ' + esc((d.addresses || []).join(', '));
    } else {
      resultEl.innerHTML = '<strong>Failed:</strong> ' + esc(d.message || 'Resolution failed');
    }
  } catch (err) {
    resultEl.innerHTML = '<strong>Error:</strong> ' + esc(err.response?.data?.detail || err.message);
  }
}

/* ── Init ────────────────────────────────────────────────────── */
window.addEventListener('load', function() {
  checkTestStatus();
  loadVersion();
});
