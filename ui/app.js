const modules = [
  { id: 'backend-status', title: 'Backend status / health' },
  { id: 'routing-policy', title: 'Routing policy preview' },
  { id: 'relay-diagnostics', title: 'Relay diagnostics / logs' },
  { id: 'config-validation', title: 'Config validation' },
];

function renderState(el, type, msg, details = '') {
  el.innerHTML = `<h3>${el.dataset.title}</h3><div class="state ${type}"><strong>${msg}</strong>${details ? `<pre>${details}</pre>` : ''}</div>`;
}

async function loadDashboard() {
  modules.forEach(m => {
    const el = document.getElementById(m.id);
    el.dataset.title = m.title;
    renderState(el, 'loading', 'Loading module data...', 'Please wait while we query local proxy APIs.');
  });

  try {
    const res = await fetch('/__mhr/api/dashboard');
    if (!res.ok) throw new Error(`API returned ${res.status}`);
    const data = await res.json();

    const backend = document.getElementById('backend-status');
    const rows = Object.keys(data.backends || {}).map(k => `${k}: health=${data.backends[k].health}, errors=${data.backends[k].errors}, circuit_open_until=${data.backends[k].circuit_open_until}`).join('\n');
    renderState(backend, rows ? 'success' : 'empty', rows ? 'Backend telemetry available.' : 'No backend telemetry yet.', rows || 'Action: generate traffic then click Refresh.');

    const routing = document.getElementById('routing-policy');
    const routingDetails = JSON.stringify(data.routing_policy || {}, null, 2);
    renderState(routing, data.routing_policy ? 'success' : 'empty', data.routing_policy ? 'Routing policy loaded.' : 'No routing policy found.', data.routing_policy ? routingDetails : 'Action: verify config mode and restart proxy.');

    const diag = document.getElementById('relay-diagnostics');
    const diagLines = (data.relay_diagnostics || []).join('\n');
    renderState(diag, diagLines ? 'success' : 'empty', diagLines ? 'Recent diagnostics fetched.' : 'No relay diagnostics yet.', diagLines || 'Action: make at least one request through proxy.');

    const cfg = document.getElementById('config-validation');
    if (data.config_validation?.valid) {
      renderState(cfg, 'success', 'Config validation passed.', JSON.stringify(data.config_validation, null, 2));
    } else {
      renderState(cfg, 'error', 'Config validation failed.', JSON.stringify(data.config_validation || { errors: ['Unknown validation error'] }, null, 2));
    }
  } catch (err) {
    modules.forEach(m => {
      const el = document.getElementById(m.id);
      renderState(el, 'error', 'Failed to load dashboard data.', `${err.message}\nAction: ensure proxy is running and open http://127.0.0.1:<port>/__mhr/ui/ .`);
    });
  }
}

document.getElementById('refreshBtn').addEventListener('click', loadDashboard);
window.addEventListener('DOMContentLoaded', loadDashboard);
