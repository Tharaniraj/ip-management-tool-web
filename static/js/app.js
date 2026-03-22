// IP Management Tool - Web Edition - Frontend JavaScript

// ━━ STATE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

let records         = [];
let deletedRecords  = [];
let previewedRecords = [];         // Holds import preview until confirmed
let editingIndex    = null;        // _index of record being edited; null = adding
let selectedRows    = new Set();   // Set of _index values
let currentSort     = { column: 'ip', reverse: false };

// ━━ INITIALIZATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

document.addEventListener('DOMContentLoaded', () => {
    loadRecords();

    // Hide write-action buttons for read-only users
    if (USER_ROLE !== 'admin') {
        ['btnAdd', 'btnEdit', 'btnDelete', 'btnImport', 'btnExport', 'btnBackup', 'btnRecover'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        // Hide select-all checkbox — no point selecting without actions
        const selectAll = document.getElementById('selectAll');
        if (selectAll) selectAll.style.display = 'none';
    }

    document.getElementById('searchInput').addEventListener('keyup', () => loadRecords());
    document.getElementById('statusFilter').addEventListener('change', () => loadRecords());

    document.getElementById('selectAll').addEventListener('change', (e) => {
        selectAllRows(e.target.checked);
    });

    document.getElementById('btnAdd').addEventListener('click', openAddDialog);
    document.getElementById('btnEdit').addEventListener('click', openEditDialog);
    document.getElementById('btnDelete').addEventListener('click', deleteSelected);
    document.getElementById('btnImport').addEventListener('click', openImportDialog);
    document.getElementById('btnExport').addEventListener('click', exportRecords);
    document.getElementById('btnRecover').addEventListener('click', openRecoveryDialog);
    document.getElementById('btnBackup').addEventListener('click', triggerBackup);
    document.getElementById('btnRefresh').addEventListener('click', () => {
        loadRecords();
        showToast('Data refreshed', 'success');
    });
    document.getElementById('btnSettings').addEventListener('click', openSettingsDialog);

    document.getElementById('recordForm').addEventListener('submit', (e) => {
        e.preventDefault();
        saveRecord();
    });

    document.querySelectorAll('.records-table th.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.column;
            if (currentSort.column === column) {
                currentSort.reverse = !currentSort.reverse;
            } else {
                currentSort.column = column;
                currentSort.reverse = false;
            }
            loadRecords();
        });
    });
});

// ━━ LOAD RECORDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function loadRecords() {
    try {
        const q      = document.getElementById('searchInput').value;
        const status = document.getElementById('statusFilter').value;
        const url    = `/api/records?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}&sort=${currentSort.column}&rev=${currentSort.reverse}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load');

        const data = await response.json();
        records = data.data || [];

        updateSummary(data.summary);
        renderTable();
    } catch (error) {
        console.error('Error loading records:', error);
        showToast('Error loading records', 'error');
    }
}

// ━━ RENDER TABLE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function renderTable() {
    const tbody       = document.getElementById('tableBody');
    const emptyState  = document.getElementById('emptyState');
    const tableWrapper = tbody.closest('.table-wrapper');

    if (records.length === 0) {
        tbody.innerHTML = '';
        tableWrapper.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    tableWrapper.style.display = 'block';
    emptyState.style.display   = 'none';

    tbody.innerHTML = records.map(record => {
        const idx         = record._index;
        const isSelected  = selectedRows.has(idx);
        const statusClass = `status-${(record.status || 'unknown').toLowerCase()}`;
        const added       = record.added_on ? new Date(record.added_on).toLocaleDateString() : '-';
        const checkboxCell = USER_ROLE === 'admin'
            ? `<td><input type="checkbox" class="checkbox row-checkbox" data-index="${idx}" ${isSelected ? 'checked' : ''}></td>`
            : '<td></td>';

        return `
            <tr class="${isSelected ? 'selected' : ''}" data-index="${idx}">
                ${checkboxCell}
                <td><code>${record.ip}</code></td>
                <td>${record.subnet || '-'}</td>
                <td>${record.hostname || '-'}</td>
                <td>${record.description || '-'}</td>
                <td><span class="status-badge ${statusClass}">${record.status || ''}</span></td>
                <td>${added}</td>
            </tr>
        `;
    }).join('');

    document.querySelectorAll('.row-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.index, 10);
            if (e.target.checked) {
                selectedRows.add(idx);
            } else {
                selectedRows.delete(idx);
                document.getElementById('selectAll').checked = false;
            }
            updateRowSelection();
        });
    });

    if (USER_ROLE === 'admin') {
        document.querySelectorAll('#tableBody tr').forEach(row => {
            row.addEventListener('click', (e) => {
                if (e.target.tagName === 'INPUT') return;
                const checkbox = row.querySelector('.row-checkbox');
                if (!checkbox) return;
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            });
        });
    }
}

function updateRowSelection() {
    document.querySelectorAll('#tableBody tr').forEach(row => {
        const idx = parseInt(row.dataset.index, 10);
        row.classList.toggle('selected', selectedRows.has(idx));
    });
}

function selectAllRows(select) {
    if (select) {
        records.forEach(r => selectedRows.add(r._index));
    } else {
        selectedRows.clear();
    }
    renderTable();
}

// ━━ CRUD OPERATIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function openAddDialog() {
    editingIndex = null;
    document.getElementById('dialogTitle').textContent = 'Add IP Record';
    document.getElementById('recordForm').reset();
    document.getElementById('ipInput').disabled = false;
    document.getElementById('ipError').textContent   = '';
    document.getElementById('formError').textContent = '';
    openDialog('recordDialog');
}

function openEditDialog() {
    if (selectedRows.size === 0) { showToast('Select a record to edit', 'warning'); return; }
    if (selectedRows.size > 1)   { showToast('Select only one record to edit', 'warning'); return; }

    const idx    = Array.from(selectedRows)[0];
    const record = records.find(r => r._index === idx);
    if (!record) return;

    editingIndex = idx;
    document.getElementById('dialogTitle').textContent         = 'Edit IP Record';
    document.getElementById('ipInput').value                   = record.ip;
    document.getElementById('ipInput').disabled                = true;
    document.getElementById('subnetInput').value               = record.subnet || '24';
    document.getElementById('hostnameInput').value             = record.hostname || '';
    document.getElementById('descriptionInput').value          = record.description || '';
    document.getElementById('statusSelect').value              = record.status;
    document.getElementById('ipError').textContent             = '';
    document.getElementById('formError').textContent           = '';
    openDialog('recordDialog');
}

async function saveRecord() {
    const ip          = document.getElementById('ipInput').value.trim();
    const subnet      = document.getElementById('subnetInput').value.trim();
    const hostname    = document.getElementById('hostnameInput').value.trim();
    const description = document.getElementById('descriptionInput').value.trim();
    const status      = document.getElementById('statusSelect').value;

    document.getElementById('ipError').textContent   = '';
    document.getElementById('formError').textContent = '';

    if (!isValidIP(ip)) {
        document.getElementById('ipError').textContent = 'Invalid IP address format';
        return;
    }

    try {
        let response;
        if (editingIndex !== null) {
            response = await fetch(`/api/records/${editingIndex}`, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ ip, subnet, hostname, description, status }),
            });
        } else {
            response = await fetch('/api/records', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ ip, subnet, hostname, description, status }),
            });
        }

        const data = await response.json();

        if (!data.success) {
            document.getElementById('formError').textContent = data.error || 'Failed to save';
            return;
        }

        showToast(editingIndex !== null ? 'Record updated' : 'Record added', 'success');
        closeDialog('recordDialog');
        selectedRows.clear();
        loadRecords();
    } catch (error) {
        console.error('Error saving record:', error);
        showToast('Failed to save record', 'error');
    }
}

async function deleteSelected() {
    if (selectedRows.size === 0) { showToast('Select records to delete', 'warning'); return; }
    if (!confirm(`Delete ${selectedRows.size} record(s)?`)) return;

    try {
        const indices  = Array.from(selectedRows);
        const response = await fetch('/api/records/delete', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ indices }),
        });

        const data = await response.json();

        if (!data.success) { showToast('Failed to delete', 'error'); return; }

        showToast(`Deleted ${data.deleted} record(s)`, 'success');
        selectedRows.clear();
        loadRecords();
    } catch (error) {
        console.error('Error deleting:', error);
        showToast('Failed to delete records', 'error');
    }
}

// ━━ BACKUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function triggerBackup() {
    try {
        const response = await fetch('/api/backup', { method: 'POST' });
        const data     = await response.json();
        showToast(
            data.success ? 'Backup created' : (data.error || 'Backup failed'),
            data.success ? 'success' : 'error'
        );
    } catch {
        showToast('Backup failed', 'error');
    }
}

// ━━ IMPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function openImportDialog() {
    document.getElementById('importFile').value        = '';
    document.getElementById('importStatus').textContent = '';
    document.getElementById('importStatus').className  = 'import-status';
    document.getElementById('confirmImportBtn').style.display = 'none';
    previewedRecords = [];
    openDialog('importDialog');
}

async function previewImport() {
    const fileInput = document.getElementById('importFile');
    if (!fileInput.files.length) { showToast('Select a file', 'warning'); return; }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        showImportStatus('Analysing file…', 'info');
        const response = await fetch('/api/import', { method: 'POST', body: formData });
        const data     = await response.json();

        if (!data.success) { showImportStatus(`Error: ${data.error}`, 'error'); return; }

        previewedRecords = data.records || [];

        const conflictMsg = data.conflicts && data.conflicts.length
            ? ` ⚠ ${data.conflicts.length} conflict(s) will be skipped.` : '';
        const errMsg = data.errors && data.errors.length
            ? ` ${data.errors.length} row error(s) ignored.` : '';

        showImportStatus(
            `Found ${data.count} record(s).${conflictMsg}${errMsg} Click Import to confirm.`,
            data.conflicts && data.conflicts.length ? 'warning' : 'success'
        );
        document.getElementById('confirmImportBtn').style.display = 'inline-block';
    } catch {
        showImportStatus('Failed to read file', 'error');
    }
}

async function confirmImport() {
    if (!previewedRecords.length) { showToast('Nothing to import', 'warning'); return; }

    try {
        const response = await fetch('/api/import/confirm', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ records: previewedRecords, skip_conflicts: true }),
        });
        const data = await response.json();

        if (!data.success) { showImportStatus(`Error: ${data.error}`, 'error'); return; }

        showImportStatus(`Imported ${data.imported} record(s)`, 'success');
        document.getElementById('confirmImportBtn').style.display = 'none';
        previewedRecords = [];

        setTimeout(() => { closeDialog('importDialog'); loadRecords(); }, 1500);
    } catch {
        showImportStatus('Import failed', 'error');
    }
}

function showImportStatus(message, type) {
    const el       = document.getElementById('importStatus');
    el.textContent = message;
    el.className   = `import-status active ${type}`;
}

// ━━ EXPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function exportRecords() {
    const format = prompt('Export as:\n1. CSV\n2. JSON\n\nEnter 1 or 2:', '1');
    if (format === null) return;

    const q      = document.getElementById('searchInput').value;
    const status = document.getElementById('statusFilter').value;
    const type   = format.trim() === '2' ? 'json' : 'csv';
    window.location.href = `/api/export?format=${type}&q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}`;
    showToast(`Exporting as ${type.toUpperCase()}…`, 'success');
}

// ━━ RECOVERY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function openRecoveryDialog() {
    openDialog('deletedDialog');
    loadDeletedRecords();
}

async function loadDeletedRecords() {
    try {
        const response = await fetch('/api/deleted');
        if (!response.ok) throw new Error();
        const data     = await response.json();
        deletedRecords = data.data || [];
        renderDeletedList();
    } catch {
        showToast('Error loading deleted records', 'error');
    }
}

function renderDeletedList() {
    const list = document.getElementById('deletedList');

    if (deletedRecords.length === 0) {
        list.innerHTML = '<p style="padding:20px;text-align:center;">No deleted records</p>';
        return;
    }

    list.innerHTML = deletedRecords.map((record, i) => `
        <div class="deleted-item">
            <div class="deleted-item-info">
                <div class="deleted-item-ip">${record.ip}</div>
                <div class="deleted-item-hostname">${record.hostname || ''}</div>
            </div>
            <button class="btn btn-add deleted-item-btn"
                    onclick="recoverDeleted(${i})">Recover</button>
        </div>
    `).join('');
}

async function recoverDeleted(index) {
    try {
        const response = await fetch(`/api/deleted/${index}/recover`, { method: 'POST' });
        const data     = await response.json();

        if (!data.success) { showToast(data.error || 'Failed to recover', 'error'); return; }

        showToast('Record recovered', 'success');
        loadDeletedRecords();
        loadRecords();
    } catch {
        showToast('Failed to recover record', 'error');
    }
}

async function clearAllDeleted() {
    if (!confirm('Clear all deleted records permanently?')) return;

    try {
        const response = await fetch('/api/deleted/clear', { method: 'POST' });
        const data     = await response.json();

        if (!data.success) { showToast('Failed to clear', 'error'); return; }

        showToast('Deleted records cleared', 'success');
        loadDeletedRecords();
    } catch {
        showToast('Failed to clear deleted records', 'error');
    }
}

// ━━ SETTINGS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function openSettingsDialog() {
    const el = document.getElementById('settingsRecordCount');
    try {
        const response = await fetch('/api/summary');
        const data     = await response.json();
        el.textContent = `Total records: ${data.data.total}`;
    } catch {
        el.textContent = `Total records: ${records.length}`;
    }
    // Clear password fields
    ['oldPassword', 'newPassword', 'confirmPassword'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    loadUserList();
    openDialog('settingsDialog');
}

// ━━ SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function updateSummary(summary) {
    if (!summary) return;
    document.getElementById('badge-total').textContent    = `${summary.total} total`;
    document.getElementById('badge-active').textContent   = `${summary.active} active`;
    document.getElementById('badge-inactive').textContent = `${summary.inactive} inactive`;
    document.getElementById('badge-reserved').textContent = `${summary.reserved} reserved`;
}

// ━━ DIALOGS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function openDialog(dialogId) {
    document.getElementById(dialogId).classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeDialog(dialogId) {
    document.getElementById(dialogId).classList.remove('active');
    document.body.style.overflow = 'auto';
}

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
});

// ━━ TOAST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon  = document.getElementById('toastIcon');
    const msg   = document.getElementById('toastMsg');

    const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
    icon.className = `fa-solid ${icons[type] || icons.info} toast-icon`;
    msg.textContent = message;
    toast.className = `toast active ${type}`;
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('active'), 3200);
}

// ━━ UTILITIES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function isValidIP(ip) {
    const parts = ip.split('.');
    if (parts.length !== 4) return false;
    return parts.every(p => {
        const n = Number(p);
        return p !== '' && Number.isInteger(n) && n >= 0 && n <= 255;
    });
}

window.addEventListener('focus', () => loadRecords());

// ━━ CHANGE PASSWORD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function changePassword() {
    const oldPw = document.getElementById('oldPassword').value;
    const newPw = document.getElementById('newPassword').value;
    const cfmPw = document.getElementById('confirmPassword').value;

    if (!oldPw || !newPw || !cfmPw) { showToast('Fill in all password fields', 'warning'); return; }
    if (newPw !== cfmPw)            { showToast('New passwords do not match', 'error');    return; }
    if (newPw.length < 6)           { showToast('Password must be at least 6 characters', 'error'); return; }

    try {
        const response = await fetch('/api/users/password', {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ old_password: oldPw, new_password: newPw }),
        });
        const data = await response.json();
        if (!data.success) { showToast(data.error || 'Failed to change password', 'error'); return; }
        showToast('Password changed successfully', 'success');
        ['oldPassword', 'newPassword', 'confirmPassword'].forEach(id => {
            document.getElementById(id).value = '';
        });
    } catch {
        showToast('Failed to change password', 'error');
    }
}

// ━━ USER MANAGEMENT (admin) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function loadUserList() {
    const container = document.getElementById('userList');
    if (!container) return;
    try {
        const response = await fetch('/api/users');
        if (!response.ok) return;                   // Not admin — silently skip
        const data = await response.json();
        renderUserList(data.data || []);
    } catch { /* silently ignore */ }
}

function renderUserList(users) {
    const container = document.getElementById('userList');
    if (!container) return;

    if (users.length === 0) {
        container.innerHTML = '<p style="padding:12px;color:var(--text-secondary);font-size:13px;">No users found</p>';
        return;
    }

    container.innerHTML = users.map(u => {
        const isSelf           = u.username === CURRENT_USER;
        const safeUsername     = u.username.replace(/'/g, "\\'");
        const actionHtml       = isSelf
            ? '<span style="color:var(--text-secondary);font-size:12px;">(you)</span>'
            : `<button class="btn btn-delete deleted-item-btn" onclick="deleteUserAccount('${safeUsername}')">Delete</button>`;
        return `
            <div class="deleted-item">
                <div class="deleted-item-info">
                    <div class="deleted-item-ip">${u.username}</div>
                    <div class="deleted-item-hostname">${u.role}</div>
                </div>
                ${actionHtml}
            </div>`;
    }).join('');
}

async function createNewUser() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newUserPassword').value;
    const role     = document.getElementById('newUserRole').value;

    if (!username || !password) { showToast('Username and password required', 'warning'); return; }

    try {
        const response = await fetch('/api/users', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ username, password, role }),
        });
        const data = await response.json();
        if (!data.success) { showToast(data.error || 'Failed to create user', 'error'); return; }
        showToast(`User '${username}' created`, 'success');
        document.getElementById('newUsername').value      = '';
        document.getElementById('newUserPassword').value  = '';
        loadUserList();
    } catch {
        showToast('Failed to create user', 'error');
    }
}

async function deleteUserAccount(username) {
    if (!confirm(`Delete user '${username}'?`)) return;
    try {
        const response = await fetch(`/api/users/${encodeURIComponent(username)}`, { method: 'DELETE' });
        const data     = await response.json();
        if (!data.success) { showToast(data.error || 'Failed to delete user', 'error'); return; }
        showToast(`User '${username}' deleted`, 'success');
        loadUserList();
    } catch {
        showToast('Failed to delete user', 'error');
    }
}
