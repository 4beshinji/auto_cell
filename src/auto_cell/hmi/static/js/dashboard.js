const state = {
  runId: null,
  pollInterval: null,
};

const els = {
  runSelect: document.getElementById('run-select'),
  refreshRuns: document.getElementById('refresh-runs'),
  statusTime: document.getElementById('status-time'),
  phase: document.getElementById('phase'),
  pendingCount: document.getElementById('pending-count'),
  cppGrid: document.getElementById('cpp-grid'),
  approvalsList: document.getElementById('approvals-list'),
  eventsList: document.getElementById('events-list'),
  ebrContent: document.getElementById('ebr-content'),
  tabs: document.querySelectorAll('.tab'),
  panels: document.querySelectorAll('.tab-panel'),
};

function init() {
  els.runSelect.addEventListener('change', (e) => selectRun(e.target.value));
  els.refreshRuns.addEventListener('click', loadRuns);
  els.tabs.forEach((tab) => tab.addEventListener('click', () => switchTab(tab.dataset.tab)));
  loadRuns();
}

async function loadRuns() {
  try {
    const res = await fetch('/hmi/runs');
    const runs = await res.json();
    const current = els.runSelect.value;
    els.runSelect.innerHTML = '<option value="">-- select run --</option>';
    runs.forEach((runId) => {
      const opt = document.createElement('option');
      opt.value = runId;
      opt.textContent = runId;
      els.runSelect.appendChild(opt);
    });
    if (current && Array.from(els.runSelect.options).some((o) => o.value === current)) {
      els.runSelect.value = current;
    }
    if (!state.runId && runs.length > 0) {
      selectRun(runs[0]);
    }
  } catch (err) {
    console.error('failed to load runs', err);
  }
}

function selectRun(runId) {
  state.runId = runId;
  els.runSelect.value = runId || '';
  if (state.pollInterval) {
    clearInterval(state.pollInterval);
  }
  if (!runId) {
    clearUi();
    return;
  }
  refreshAll();
  state.pollInterval = setInterval(refreshAll, 5000);
}

function clearUi() {
  els.statusTime.textContent = '-';
  els.phase.textContent = '-';
  els.pendingCount.textContent = '-';
  els.cppGrid.innerHTML = '';
  els.approvalsList.innerHTML = '<div class="empty">no run selected</div>';
  els.eventsList.innerHTML = '<div class="empty">no run selected</div>';
  els.ebrContent.innerHTML = '<div class="empty">no run selected</div>';
}

async function refreshAll() {
  if (!state.runId) return;
  await Promise.all([
    refreshStatus(),
    refreshApprovals(),
    refreshEvents(),
  ]);
  if (document.getElementById('tab-ebr').classList.contains('active')) {
    await refreshEbr();
  }
}

async function refreshStatus() {
  try {
    const res = await fetch(`/hmi/runs/${encodeURIComponent(state.runId)}/status`);
    const data = await res.json();
    els.statusTime.textContent = new Date().toLocaleTimeString();
    els.phase.textContent = data.phase || 'unknown';
    els.pendingCount.textContent = String(data.pending_approvals ?? 0);
    renderCpp(data.cpp || {});
  } catch (err) {
    console.error('failed to load status', err);
  }
}

function renderCpp(cpp) {
  const channels = [
    { key: 'vcd', label: 'VCD', unit: 'cells/mL' },
    { key: 'viability', label: 'Viability', unit: '%' },
    { key: 'glucose', label: 'Glucose', unit: 'mM' },
    { key: 'lactate', label: 'Lactate', unit: 'mM' },
    { key: 'ph', label: 'pH', unit: '' },
    { key: 'do', label: 'DO', unit: '%' },
    { key: 'aggregate_diameter_um', label: 'Aggregate', unit: 'µm' },
  ];
  els.cppGrid.innerHTML = channels.map((ch) => {
    const value = cpp[ch.key];
    const display = value === undefined || value === null ? '-' : value;
    return `
      <div class="cpp-item">
        <div class="label">${ch.label}</div>
        <div class="value">${display} ${ch.unit ? `<small>${ch.unit}</small>` : ''}</div>
      </div>
    `;
  }).join('');
}

async function refreshApprovals() {
  try {
    const res = await fetch('/hmi/approvals/pending');
    const items = await res.json();
    renderApprovals(items);
  } catch (err) {
    console.error('failed to load approvals', err);
  }
}

function renderApprovals(items) {
  if (!items || items.length === 0) {
    els.approvalsList.innerHTML = '<div class="empty">no pending approvals</div>';
    return;
  }
  els.approvalsList.innerHTML = items.map((req) => `
    <div class="list-item">
      <div><strong>${req.tool_name}</strong></div>
      <div class="meta">${req.run_id} · requested by ${req.requested_by}</div>
      <div class="meta">${JSON.stringify(req.params)}</div>
      <div class="actions">
        <button onclick="decideApproval('${req.request_id}', 'approve')">Approve</button>
        <button class="danger" onclick="decideApproval('${req.request_id}', 'reject')">Reject</button>
      </div>
    </div>
  `).join('');
}

window.decideApproval = async function (requestId, action) {
  const actor = window.prompt('Enter your actor ID:');
  if (!actor) return;
  const reason = window.prompt('Enter reason:') || action;
  try {
    const res = await fetch(`/hmi/approvals/${encodeURIComponent(requestId)}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, reason }),
    });
    if (!res.ok) {
      const detail = await res.text();
      alert(`Failed: ${detail}`);
      return;
    }
    await refreshApprovals();
    await refreshStatus();
  } catch (err) {
    console.error(`failed to ${action} approval`, err);
  }
};

async function refreshEvents() {
  try {
    const res = await fetch(`/hmi/runs/${encodeURIComponent(state.runId)}/events?limit=50`);
    const events = await res.json();
    renderEvents(events);
  } catch (err) {
    console.error('failed to load events', err);
  }
}

function renderEvents(events) {
  if (!events || events.length === 0) {
    els.eventsList.innerHTML = '<div class="empty">no events</div>';
    return;
  }
  els.eventsList.innerHTML = events.slice().reverse().map((ev) => `
    <div class="list-item">
      <div><strong>${ev.header.event_type}</strong> · ${ev.header.source}</div>
      <div class="meta">${ev.header.timestamp} · ${ev.header.actor}</div>
      <div class="meta">${JSON.stringify(ev.payload).slice(0, 120)}</div>
    </div>
  `).join('');
}

function switchTab(tabName) {
  els.tabs.forEach((t) => t.classList.toggle('active', t.dataset.tab === tabName));
  els.panels.forEach((p) => p.classList.toggle('active', p.dataset.tab === tabName));
  if (tabName === 'ebr') {
    refreshEbr();
  }
}

async function refreshEbr() {
  if (!state.runId) return;
  try {
    const res = await fetch(`/hmi/runs/${encodeURIComponent(state.runId)}/ebr`);
    const data = await res.json();
    els.ebrContent.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
  } catch (err) {
    console.error('failed to load ebr', err);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
