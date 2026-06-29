/* ── AI Smart Attendance System – main.js ── */

// ─── CLOCK ───
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  const s = String(now.getSeconds()).padStart(2, '0');
  const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
  const hh = now.getHours() % 12 || 12;
  document.getElementById('liveClock').textContent =
    `${String(hh).padStart(2,'0')}:${m}:${s} ${ampm}`;
}
setInterval(updateClock, 1000);
updateClock();

// ─── TOAST ───
function showToast(msg, color = '#6C63FF') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.borderLeftColor = color;
  t.style.borderLeft = `3px solid ${color}`;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ─── STATUS BADGE ───
function badge(status) {
  const s = (status || '—').toLowerCase();
  if (s === 'present') return `<span class="badge badge-present">✓ Present</span>`;
  if (s === 'late')    return `<span class="badge badge-late">⚠ Late</span>`;
  if (s === 'absent')  return `<span class="badge badge-absent">✗ Absent</span>`;
  return `<span class="badge badge-unmarked">— Unmarked</span>`;
}

// ─── LOAD ATTENDANCE TABLE ───
async function loadAttendance() {
  try {
    const res = await fetch('/api/attendance');
    const rows = await res.json();
    const tbody = document.getElementById('attBody');
    tbody.innerHTML = '';
    rows.forEach((r, i) => {
      const tr = document.createElement('tr');
      tr.setAttribute('data-name', r.name.toLowerCase());
      tr.setAttribute('data-dept', r.department.toLowerCase());
      tr.innerHTML = `
        <td style="color:var(--text-dim);font-size:.78rem">${String(i+1).padStart(2,'0')}</td>
        <td><strong>${r.name}</strong></td>
        <td><span style="background:rgba(108,99,255,.1);color:var(--purple);padding:2px 8px;border-radius:20px;font-size:.75rem;font-weight:600">${r.department}</span></td>
        <td>${badge(r.status)}</td>
        <td style="font-family:monospace;font-size:.8rem;color:var(--text-dim)">${r.time}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch(e) { console.error('Attendance load error:', e); }
}

// ─── LOAD STATS ───
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const d = await res.json();
    document.getElementById('statPresent').textContent = d.present;
    document.getElementById('statLate').textContent    = d.late;
    document.getElementById('statAbsent').textContent  = d.absent;
    document.getElementById('statUnmarked').textContent= d.unmarked;
    const total = d.total || 1;
    document.getElementById('progPresent').style.width = (d.present / total * 100) + '%';
    document.getElementById('progLate').style.width    = (d.late    / total * 100) + '%';
    document.getElementById('progAbsent').style.width  = (d.absent  / total * 100) + '%';
  } catch(e) {}
}

// ─── LOAD DETECTION LOG ───
async function loadDetections() {
  try {
    const res = await fetch('/api/detections');
    const items = await res.json();
    const log = document.getElementById('detectionLog');
    if (!items.length) {
      log.innerHTML = '<div class="log-empty">No detections yet</div>';
      return;
    }
    log.innerHTML = items.map(d => `
      <div class="log-entry">
        <div>
          <div class="log-name">${d.name}</div>
          <div class="log-dept">${d.department}</div>
        </div>
        <div>${badge(d.status)}</div>
        <div class="log-time">${d.time}</div>
      </div>
    `).join('');
  } catch(e) {}
}

// ─── CAMERA CONTROLS ───
async function startCamera() {
  showToast('Starting camera…', '#6C63FF');
  try {
    const res = await fetch('/api/start_camera', { method: 'POST' });
    const d = await res.json();
    if (d.camera_active) {
      document.getElementById('camDot').className = 'dot dot-green';
      document.getElementById('camStatusText').textContent = 'Active';
      document.getElementById('camOverlay').style.display = 'none';
      showToast('Camera started ✓', '#22c55e');
    } else {
      showToast('Camera not found – check device', '#ef4444');
    }
  } catch(e) { showToast('Error starting camera', '#ef4444'); }
}

async function stopCamera() {
  await fetch('/api/stop_camera', { method: 'POST' });
  document.getElementById('camDot').className = 'dot dot-red';
  document.getElementById('camStatusText').textContent = 'Offline';
  showToast('Camera stopped', '#f59e0b');
}

// ─── TRAIN MODEL ───
async function trainModel() {
  showToast('Training face recognition model…', '#6C63FF');
  try {
    const res = await fetch('/api/train', { method: 'POST' });
    const d = await res.json();
    if (d.success) {
      showToast(`Model trained for ${d.people} person(s) ✓`, '#22c55e');
    } else {
      showToast('No face data found. Register faces first.', '#f59e0b');
    }
  } catch(e) { showToast('Training failed', '#ef4444'); }
}

// ─── MARK ABSENT (manual trigger) ───
async function markAbsent() {
  if (!confirm('Mark all unmarked students as Absent?')) return;
  await fetch('/api/mark_absent', { method: 'POST' });
  showToast('Absent marked for all unmarked students', '#ef4444');
  loadAttendance();
  loadStats();
}

// ─── EXPORT CSV ───
async function exportCSV() {
  try {
    const res = await fetch('/export');
    const d = await res.json();
    if (d.success) {
      showToast(`Exported ${d.rows} rows → ${d.file}`, '#00D4B4');
    }
  } catch(e) { showToast('Export failed', '#ef4444'); }
}

// ─── TABLE SEARCH ───
function filterTable() {
  const q = document.getElementById('searchBox').value.toLowerCase();
  document.querySelectorAll('#attBody tr').forEach(tr => {
    const name = tr.getAttribute('data-name') || '';
    const dept = tr.getAttribute('data-dept') || '';
    tr.style.display = (name.includes(q) || dept.includes(q)) ? '' : 'none';
  });
}

// ─── AUTO-REFRESH ───
function refresh() {
  loadAttendance();
  loadStats();
  loadDetections();
}

// Init
refresh();
setInterval(refresh, 4000);   // refresh every 4s
