const API_BASE = window.location.origin;
let adminToken = null;
let adminUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

function checkAuth() {
    adminToken = localStorage.getItem('admin_token');
    const userStr = localStorage.getItem('admin_user');

    if (!adminToken || !userStr) {
        window.location.href = '/static/admin-login.html';
        return;
    }

    adminUser = JSON.parse(userStr);

    if (!adminUser.is_admin) {
        alert('Access denied. Admin privileges required.');
        logout();
        return;
    }

    // Display username
    document.getElementById('admin-username').textContent = adminUser.username;

    // Load initial data
    loadDashboard();
}

function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = '/static/admin-login.html';
}

// Section Navigation
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });

    // Remove active class from all nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // Show selected section
    document.getElementById(`${sectionName}-section`).classList.add('active');

    // Add active class to clicked nav link
    event.target.classList.add('active');

    // Load data for section
    switch(sectionName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'users':
            loadUsers();
            break;
        case 'logs':
            loadLogs();
            break;
        case 'backups':
            loadBackupConfig();
            loadBackups();
            break;
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        // Load dashboard stats
        const response = await fetch(`${API_BASE}/api/admin/dashboard`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                logout();
                return;
            }
            throw new Error('Failed to load dashboard');
        }

        const data = await response.json();

        // Update stats
        document.getElementById('stat-total-users').textContent = data.total_users;
        document.getElementById('stat-active-users').textContent = data.active_users;
        document.getElementById('stat-web-platforms').textContent = data.total_web_platforms;
        document.getElementById('stat-family-members').textContent = data.total_family_members;
        document.getElementById('stat-tree-views').textContent = data.total_tree_views;
        document.getElementById('stat-tree-shares').textContent = data.total_tree_shares;

        // Update system resources with color coding
        updateResourceValue('system-cpu-percent', data.cpu_percent, '%');
        document.getElementById('system-cpu-speed').textContent = data.cpu_speed;
        document.getElementById('system-cpu-cores').textContent = data.cpu_cores;

        updateResourceValue('system-memory-percent', data.memory_percent, '%');
        document.getElementById('system-memory-total').textContent = data.memory_total;
        document.getElementById('system-memory-available').textContent = data.memory_available;

        updateResourceValue('system-disk-percent', data.disk_percent, '%');
        document.getElementById('system-disk-total').textContent = data.disk_total;
        document.getElementById('system-disk-available').textContent = data.disk_available;

        // Update system info
        document.getElementById('system-version').textContent = data.app_version;
        document.getElementById('system-uptime').textContent = data.uptime;
        document.getElementById('system-db-size').textContent = data.database_size || 'N/A';
        document.getElementById('python-version').textContent = data.python_version;
        document.getElementById('system-platform').textContent = data.platform;
        document.getElementById('system-arch').textContent = data.architecture;

        // Update service statuses
        updateServiceStatus('service-web', true); // Assume running if we got response
        checkDatabaseStatus();
        checkFileStorageStatus();

        // Display recent logs
        const logsDiv = document.getElementById('recent-logs');
        logsDiv.innerHTML = data.recent_logs.map(log => `
            <div class="log-entry ${log.level}">
                <div class="log-entry-time">${formatDateTime(log.created_at)}</div>
                <div class="log-entry-message">${log.message}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading dashboard:', error);
        alert('Failed to load dashboard data');
    }
}

async function loadSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/system-info`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('system-cpu').textContent = data.cpu_usage;
            document.getElementById('system-memory').textContent = data.memory_usage;
            document.getElementById('system-disk').textContent = data.disk_usage;
        }
    } catch (error) {
        console.error('Error loading system info:', error);
    }
}

// User Management Functions
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to load users');

        const users = await response.json();
        const tbody = document.getElementById('users-table-body');

        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td><span class="badge ${user.is_admin ? 'badge-success' : 'badge-info'}">${user.is_admin ? 'Yes' : 'No'}</span></td>
                <td><span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>${user.last_login ? formatDateTime(user.last_login) : 'Never'}</td>
                <td>
                    <button class="btn-sm btn-edit" onclick="editUser(${user.id})">Edit</button>
                    ${user.id !== adminUser.id ? `<button class="btn-sm btn-delete" onclick="deleteUser(${user.id}, '${user.username}')">Delete</button>` : ''}
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading users:', error);
        alert('Failed to load users');
    }
}

function showCreateUserModal() {
    document.getElementById('create-user-modal').classList.add('show');
    document.getElementById('create-user-form').reset();
}

function closeCreateUserModal() {
    document.getElementById('create-user-modal').classList.remove('show');
}

async function handleCreateUser(event) {
    event.preventDefault();

    const userData = {
        username: document.getElementById('new-username').value,
        email: document.getElementById('new-email').value,
        password: document.getElementById('new-password').value,
        is_admin: document.getElementById('new-is-admin').checked
    };

    try {
        const response = await fetch(`${API_BASE}/api/admin/users`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create user');
        }

        alert('User created successfully');
        closeCreateUserModal();
        loadUsers();

    } catch (error) {
        alert(error.message);
    }
}

async function editUser(userId) {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to load users');

        const users = await response.json();
        const user = users.find(u => u.id === userId);

        if (!user) {
            alert('User not found');
            return;
        }

        document.getElementById('edit-user-id').value = user.id;
        document.getElementById('edit-username').value = user.username;
        document.getElementById('edit-email').value = user.email;
        document.getElementById('edit-is-admin').checked = user.is_admin;
        document.getElementById('edit-is-active').checked = user.is_active;
        document.getElementById('edit-user-modal').classList.add('show');

    } catch (error) {
        alert('Failed to load user details');
    }
}

function closeEditUserModal() {
    document.getElementById('edit-user-modal').classList.remove('show');
}

async function handleEditUser(event) {
    event.preventDefault();

    const userId = document.getElementById('edit-user-id').value;
    const userData = {
        email: document.getElementById('edit-email').value,
        is_admin: document.getElementById('edit-is-admin').checked,
        is_active: document.getElementById('edit-is-active').checked
    };

    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update user');
        }

        alert('User updated successfully');
        closeEditUserModal();
        loadUsers();

    } catch (error) {
        alert(error.message);
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete user');
        }

        alert('User deleted successfully');
        loadUsers();

    } catch (error) {
        alert(error.message);
    }
}

// Logs Functions
async function loadLogs() {
    const level = document.getElementById('log-level-filter').value;
    const url = level
        ? `${API_BASE}/api/admin/logs?level=${level}`
        : `${API_BASE}/api/admin/logs`;

    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to load logs');

        const logs = await response.json();
        const tbody = document.getElementById('logs-table-body');

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No logs found</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(log => `
            <tr>
                <td>${formatDateTime(log.created_at)}</td>
                <td><span class="badge badge-${getBadgeClass(log.level)}">${log.level}</span></td>
                <td>${log.action || '-'}</td>
                <td>${log.message}</td>
                <td>${log.user_id || '-'}</td>
                <td>${log.ip_address || '-'}</td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading logs:', error);
        alert('Failed to load logs');
    }
}

// Backup Functions
async function loadBackupConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/backup-config`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to load backup configuration');

        const config = await response.json();
        const contentDiv = document.getElementById('backup-destinations-content');

        // Build destination cards HTML
        let html = '';

        // Local Disk Card (Always Active)
        html += `
            <div class="destination-card active">
                <div class="destination-header">
                    <span class="destination-icon">💾</span>
                    <h4 class="destination-title">Local Disk</h4>
                    <span class="destination-status active">Active</span>
                </div>
                <div class="destination-details">
                    <strong>Path:</strong> <code>${config.local.path}</code>
                </div>
            </div>
        `;

        // SMB/CIFS Card
        const smbClass = config.smb.status === 'active' ? 'active' : config.smb.status === 'not_mounted' ? 'warning' : 'disabled';
        const smbStatusText = config.smb.status === 'active' ? 'Active' : config.smb.status === 'not_mounted' ? 'Not Mounted' : 'Disabled';
        const smbStatusClass = config.smb.status === 'active' ? 'active' : config.smb.status === 'not_mounted' ? 'warning' : 'disabled';

        html += `
            <div class="destination-card ${smbClass}">
                <div class="destination-header">
                    <span class="destination-icon">🌐</span>
                    <h4 class="destination-title">SMB/CIFS Share</h4>
                    <span class="destination-status ${smbStatusClass}">${smbStatusText}</span>
                </div>
                <div class="destination-details">
                    ${config.smb.enabled ? `
                        <strong>Host:</strong> <code>${config.smb.host}</code><br>
                        <strong>Share:</strong> <code>${config.smb.share}</code><br>
                        <strong>Mount:</strong> <code>${config.smb.mount_point}</code>
                        ${config.smb.status === 'not_mounted' ? '<br><em style="color: #856404;">⚠️ Enabled but not mounted</em>' : ''}
                    ` : `
                        <em style="color: #999;">Configure in .env file to enable</em>
                    `}
                </div>
            </div>
        `;

        // NFS Card
        const nfsClass = config.nfs.status === 'active' ? 'active' : config.nfs.status === 'not_mounted' ? 'warning' : 'disabled';
        const nfsStatusText = config.nfs.status === 'active' ? 'Active' : config.nfs.status === 'not_mounted' ? 'Not Mounted' : 'Disabled';
        const nfsStatusClass = config.nfs.status === 'active' ? 'active' : config.nfs.status === 'not_mounted' ? 'warning' : 'disabled';

        html += `
            <div class="destination-card ${nfsClass}">
                <div class="destination-header">
                    <span class="destination-icon">📁</span>
                    <h4 class="destination-title">NFS Share</h4>
                    <span class="destination-status ${nfsStatusClass}">${nfsStatusText}</span>
                </div>
                <div class="destination-details">
                    ${config.nfs.enabled ? `
                        <strong>Host:</strong> <code>${config.nfs.host}</code><br>
                        <strong>Export:</strong> <code>${config.nfs.export}</code><br>
                        <strong>Mount:</strong> <code>${config.nfs.mount_point}</code>
                        ${config.nfs.status === 'not_mounted' ? '<br><em style="color: #856404;">⚠️ Enabled but not mounted</em>' : ''}
                    ` : `
                        <em style="color: #999;">Configure in .env file to enable</em>
                    `}
                </div>
            </div>
        `;

        contentDiv.innerHTML = html;

    } catch (error) {
        console.error('Error loading backup configuration:', error);
        const contentDiv = document.getElementById('backup-destinations-content');
        contentDiv.innerHTML = '<div style="color: #dc3545;">Failed to load backup configuration</div>';
    }
}

async function loadBackups() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/backups`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to load backups');

        const backups = await response.json();
        const tbody = document.getElementById('backups-table-body');

        if (backups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No backups found</td></tr>';
            return;
        }

        tbody.innerHTML = backups.map(backup => {
            let typeClass = 'badge-info';
            let typeIcon = '';

            switch(backup.backup_type) {
                case 'snapshot':
                    typeClass = 'badge-warning';
                    typeIcon = '📸 ';
                    break;
                case 'config':
                    typeClass = 'badge-secondary';
                    typeIcon = '⚙️ ';
                    break;
                case 'full':
                    typeClass = 'badge-success';
                    typeIcon = '📦 ';
                    break;
                default:
                    typeClass = 'badge-info';
                    typeIcon = '🗄️ ';
            }

            return `
            <tr>
                <td>${backup.filename}</td>
                <td><span class="badge ${typeClass}">${typeIcon}${backup.backup_type}</span></td>
                <td>${formatFileSize(backup.file_size)}</td>
                <td><span class="badge badge-${backup.status === 'completed' ? 'success' : 'warning'}">${backup.status}</span></td>
                <td>${formatDateTime(backup.created_at)}</td>
                <td>
                    <button class="btn-sm btn-edit" onclick="openDownloadBackupModal(${backup.id}, '${backup.filename}')">
                        <i class="bi bi-download"></i> Download
                    </button>
                </td>
            </tr>
        `;
        }).join('');

    } catch (error) {
        console.error('Error loading backups:', error);
        alert('Failed to load backups');
    }
}

// Create Backup Modal Functions
function createBackup() {
    document.getElementById('backup-type-select').value = 'database';
    updateBackupTypeInfo();
    document.getElementById('create-backup-modal').style.display = 'flex';
}

function closeCreateBackupModal() {
    document.getElementById('create-backup-modal').style.display = 'none';
}

function updateBackupTypeInfo() {
    const backupType = document.getElementById('backup-type-select').value;
    const infoDiv = document.getElementById('backup-type-info');

    const infoContent = {
        'database': `
            <strong>Database Backup includes:</strong>
            <ul style="margin: 5px 0 0 20px;">
                <li>All users and authentication data</li>
                <li>Family trees and members</li>
                <li>Tree shares and permissions</li>
                <li>System logs and backups metadata</li>
            </ul>
        `,
        'config': `
            <strong>Configuration Backup includes:</strong>
            <ul style="margin: 5px 0 0 20px;">
                <li>Backup settings (local, SMB, NFS)</li>
                <li>Docker Compose configuration</li>
                <li>Dockerfile configuration</li>
                <li>Environment template (.env.example)</li>
                <li>App version and metadata</li>
            </ul>
            <em style="color: #856404;">Note: Passwords are redacted for security</em>
        `,
        'full': `
            <strong>Full Backup includes:</strong>
            <ul style="margin: 5px 0 0 20px;">
                <li><strong>Database:</strong> All user data, trees, and system logs</li>
                <li><strong>Configuration:</strong> App settings and Docker config</li>
            </ul>
            <em style="color: #28a745;">Recommended for complete system backup</em>
        `
    };

    infoDiv.innerHTML = infoContent[backupType] || '';
}

async function confirmCreateBackup() {
    const backupType = document.getElementById('backup-type-select').value;

    const typeLabels = {
        'database': 'database',
        'config': 'configuration',
        'full': 'full (database + configuration)'
    };

    if (!confirm(`Create a new ${typeLabels[backupType]} backup? This may take a few moments.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/admin/backups`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ backup_type: backupType })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create backup');
        }

        alert(`${typeLabels[backupType].charAt(0).toUpperCase() + typeLabels[backupType].slice(1)} backup created successfully`);
        closeCreateBackupModal();
        loadBackups();

    } catch (error) {
        alert(error.message);
    }
}

// Add event listener for backup type change
document.addEventListener('DOMContentLoaded', function() {
    const backupTypeSelect = document.getElementById('backup-type-select');
    if (backupTypeSelect) {
        backupTypeSelect.addEventListener('change', updateBackupTypeInfo);
    }
});

// Backup Download Modal Functions
let currentDownloadBackupId = null;

function openDownloadBackupModal(backupId, filename) {
    currentDownloadBackupId = backupId;
    document.getElementById('download-backup-filename').textContent = filename;
    document.getElementById('encrypt-download-checkbox').checked = false;
    document.getElementById('encrypt-password').value = '';
    document.getElementById('encrypt-password-group').style.display = 'none';
    document.getElementById('download-backup-modal').style.display = 'flex';
}

function closeDownloadBackupModal() {
    document.getElementById('download-backup-modal').style.display = 'none';
    currentDownloadBackupId = null;
}

function toggleEncryptPassword() {
    const checkbox = document.getElementById('encrypt-download-checkbox');
    const passwordGroup = document.getElementById('encrypt-password-group');
    passwordGroup.style.display = checkbox.checked ? 'block' : 'none';
}

async function confirmDownloadBackup() {
    const encryptCheckbox = document.getElementById('encrypt-download-checkbox');
    const password = document.getElementById('encrypt-password').value;

    if (encryptCheckbox.checked && !password) {
        alert('Please enter an encryption password');
        return;
    }

    try {
        // Build URL with optional password parameter
        let url = `${API_BASE}/api/admin/backups/${currentDownloadBackupId}/download`;
        if (encryptCheckbox.checked && password) {
            url += `?password=${encodeURIComponent(password)}`;
        }

        // Fetch the file
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to download backup');
        }

        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'backup.sql';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?(.+?)"?$/);
            if (match) filename = match[1];
        }

        // Download the file
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);

        closeDownloadBackupModal();

        if (encryptCheckbox.checked) {
            alert('Encrypted backup downloaded successfully! Remember your password - you will need it to restore this backup.');
        }

    } catch (error) {
        alert(error.message);
    }
}

// Restore Backup Modal Functions
function openRestoreBackupModal() {
    document.getElementById('restore-file').value = '';
    document.getElementById('is-encrypted-checkbox').checked = false;
    document.getElementById('decrypt-password').value = '';
    document.getElementById('decrypt-password-group').style.display = 'none';
    document.getElementById('restore-backup-modal').style.display = 'flex';
}

function closeRestoreBackupModal() {
    document.getElementById('restore-backup-modal').style.display = 'none';
}

function toggleDecryptPassword() {
    const checkbox = document.getElementById('is-encrypted-checkbox');
    const passwordGroup = document.getElementById('decrypt-password-group');
    passwordGroup.style.display = checkbox.checked ? 'block' : 'none';
}

async function confirmRestoreBackup() {
    const fileInput = document.getElementById('restore-file');
    const isEncrypted = document.getElementById('is-encrypted-checkbox').checked;
    const password = document.getElementById('decrypt-password').value;
    const createSnapshot = document.getElementById('create-snapshot-checkbox').checked;

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a backup file');
        return;
    }

    if (isEncrypted && !password) {
        alert('Please enter the decryption password');
        return;
    }

    const warningMsg = createSnapshot
        ? '⚠️ WARNING: This will restore the database and overwrite all current data.\n\nA snapshot of the current database will be created first, allowing you to roll back if needed.\n\nAre you sure you want to continue?'
        : '⚠️ WARNING: This will restore the database and overwrite all current data WITHOUT creating a snapshot.\n\nThis is NOT recommended. You will not be able to roll back.\n\nAre you sure you want to continue?';

    if (!confirm(warningMsg)) {
        return;
    }

    try {
        const formData = new FormData();
        formData.append('backup_file', fileInput.files[0]);
        formData.append('create_snapshot', createSnapshot);
        if (isEncrypted && password) {
            formData.append('password', password);
        }

        const response = await fetch(`${API_BASE}/api/admin/backups/restore`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to restore backup');
        }

        const result = await response.json();

        let successMsg = `Database restored successfully from ${result.filename}`;
        if (result.snapshot) {
            successMsg += `\n\n✓ Snapshot created: ${result.snapshot.filename} (ID: ${result.snapshot.id})`;
            successMsg += `\n${result.snapshot.message}`;
        }

        alert(successMsg);
        closeRestoreBackupModal();

        // Reload dashboard data
        loadDashboard();
        loadBackups();

    } catch (error) {
        alert(error.message);
    }
}

// Utility Functions
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatFileSize(bytes) {
    if (!bytes) return '-';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
}

function getBadgeClass(level) {
    switch(level) {
        case 'INFO': return 'info';
        case 'WARNING': return 'warning';
        case 'ERROR': return 'danger';
        default: return 'info';
    }
}

// Resource value updater with color coding
function updateResourceValue(elementId, value, suffix = '') {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = `${value.toFixed(1)}${suffix}`;

    // Remove existing color classes
    element.classList.remove('good', 'warning', 'danger');

    // Add appropriate color class based on value
    if (value < 60) {
        element.classList.add('good');
    } else if (value < 80) {
        element.classList.add('warning');
    } else {
        element.classList.add('danger');
    }
}

// Service status updater
function updateServiceStatus(serviceId, isRunning) {
    const service = document.getElementById(serviceId);
    if (!service) return;

    const statusDot = service.querySelector('.service-status');
    if (!statusDot) return;

    statusDot.classList.remove('status-running', 'status-stopped', 'status-unknown');
    statusDot.classList.add(isRunning ? 'status-running' : 'status-stopped');
}

// Check database status
async function checkDatabaseStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        updateServiceStatus('service-db', response.ok);
    } catch (error) {
        updateServiceStatus('service-db', false);
    }
}

// Check file storage status
async function checkFileStorageStatus() {
    try {
        // Try to access a static file to verify file storage is working
        const response = await fetch(`${API_BASE}/static/styles.css`, { method: 'HEAD' });
        updateServiceStatus('service-uploads', response.ok);
    } catch (error) {
        updateServiceStatus('service-uploads', false);
    }
}

// Backup Settings Modal Functions
function openBackupSettingsModal() {
    // Load current settings first
    loadCurrentBackupSettings();
    document.getElementById('backup-settings-modal').style.display = 'flex';
}

function closeBackupSettingsModal() {
    document.getElementById('backup-settings-modal').style.display = 'none';
}

async function loadCurrentBackupSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/backup-config`, {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to load backup settings');

        const config = await response.json();

        // Set SMB settings
        document.getElementById('smb-enabled').checked = config.smb.enabled;
        document.getElementById('smb-host').value = config.smb.host || '';
        document.getElementById('smb-share').value = config.smb.share || '';
        document.getElementById('smb-username').value = config.smb.username || '';
        document.getElementById('smb-mount-point').value = config.smb.mount_point || '/mnt/smb_backups';
        document.getElementById('smb-password').value = ''; // Never show existing password

        // Set NFS settings
        document.getElementById('nfs-enabled').checked = config.nfs.enabled;
        document.getElementById('nfs-host').value = config.nfs.host || '';
        document.getElementById('nfs-export').value = config.nfs.export || '';
        document.getElementById('nfs-mount-point').value = config.nfs.mount_point || '/mnt/nfs_backups';

        // Show/hide settings based on enabled state
        toggleSMBSettings();
        toggleNFSSettings();

    } catch (error) {
        console.error('Error loading backup settings:', error);
        alert('Failed to load current backup settings');
    }
}

// Toggle SMB settings visibility
document.addEventListener('DOMContentLoaded', () => {
    const smbToggle = document.getElementById('smb-enabled');
    const nfsToggle = document.getElementById('nfs-enabled');

    if (smbToggle) {
        smbToggle.addEventListener('change', toggleSMBSettings);
    }
    if (nfsToggle) {
        nfsToggle.addEventListener('change', toggleNFSSettings);
    }
});

function toggleSMBSettings() {
    const enabled = document.getElementById('smb-enabled').checked;
    const settingsDiv = document.getElementById('smb-settings');
    settingsDiv.style.display = enabled ? 'block' : 'none';
}

function toggleNFSSettings() {
    const enabled = document.getElementById('nfs-enabled').checked;
    const settingsDiv = document.getElementById('nfs-settings');
    settingsDiv.style.display = enabled ? 'block' : 'none';
}

async function saveBackupSettings() {
    try {
        const smbEnabled = document.getElementById('smb-enabled').checked;
        const nfsEnabled = document.getElementById('nfs-enabled').checked;

        // Validate SMB settings if enabled
        if (smbEnabled) {
            const smbHost = document.getElementById('smb-host').value.trim();
            const smbShare = document.getElementById('smb-share').value.trim();
            const smbUsername = document.getElementById('smb-username').value.trim();

            if (!smbHost || !smbShare || !smbUsername) {
                alert('Please fill in all required SMB fields (Host, Share, Username)');
                return;
            }
        }

        // Validate NFS settings if enabled
        if (nfsEnabled) {
            const nfsHost = document.getElementById('nfs-host').value.trim();
            const nfsExport = document.getElementById('nfs-export').value.trim();

            if (!nfsHost || !nfsExport) {
                alert('Please fill in all required NFS fields (Host, Export Path)');
                return;
            }
        }

        // Build configuration object
        const config = {
            smb: {
                enabled: smbEnabled,
                host: document.getElementById('smb-host').value.trim(),
                share: document.getElementById('smb-share').value.trim(),
                username: document.getElementById('smb-username').value.trim(),
                mount_point: document.getElementById('smb-mount-point').value.trim()
            },
            nfs: {
                enabled: nfsEnabled,
                host: document.getElementById('nfs-host').value.trim(),
                export: document.getElementById('nfs-export').value.trim(),
                mount_point: document.getElementById('nfs-mount-point').value.trim()
            }
        };

        // Include password if provided
        const smbPassword = document.getElementById('smb-password').value;
        if (smbPassword) {
            config.smb.password = smbPassword;
        }

        // Send update request
        const response = await fetch(`${API_BASE}/api/admin/backup-config`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update backup settings');
        }

        const result = await response.json();

        // Close modal
        closeBackupSettingsModal();

        // Show success message with restart instructions
        alert(`${result.message}\n\nTo apply the changes:\n1. Stop containers: docker-compose down\n2. Uncomment volume mounts in docker-compose.yml (if using SMB/NFS)\n3. Start containers: docker-compose up -d`);

        // Reload backup configuration display
        loadBackupConfig();

    } catch (error) {
        console.error('Error saving backup settings:', error);
        alert(`Failed to save backup settings: ${error.message}`);
    }
}

// Application Update Functions
async function loadAllReleases() {
    try {
        const checkBtn = document.getElementById('check-update-btn');
        const statusText = document.getElementById('update-status-text');

        checkBtn.disabled = true;
        checkBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Loading...';
        statusText.textContent = 'Loading releases...';

        const response = await fetch('/api/admin/releases', {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Session expired. Please refresh the page and log in again.');
            }
            const errorText = await response.text();
            throw new Error(`Failed to load releases: ${response.status} ${errorText}`);
        }

        const data = await response.json();

        // Update current version display
        document.getElementById('current-version').textContent = data.current_version;

        // Find latest non-prerelease version
        const latestRelease = data.releases.find(r => !r.prerelease);
        if (latestRelease) {
            document.getElementById('latest-version').textContent = latestRelease.version;

            const updateBanner = document.getElementById('update-available-banner');
            if (latestRelease.version !== data.current_version) {
                updateBanner.style.display = 'block';
                statusText.innerHTML = '<span style="color: #ff9800;">Updates Available</span>';
            } else {
                updateBanner.style.display = 'none';
                statusText.innerHTML = '<span style="color: #4caf50;">Up to Date</span>';
            }
        } else {
            document.getElementById('latest-version').textContent = 'N/A';
            statusText.innerHTML = '<span style="color: #999;">No releases found</span>';
        }

        // Populate releases table
        populateReleasesTable(data.releases, data.current_version);

        // Show releases container
        document.getElementById('releases-container').style.display = 'block';

        checkBtn.disabled = false;
        checkBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Check for Updates';

    } catch (error) {
        console.error('Error loading releases:', error);
        document.getElementById('update-status-text').innerHTML = '<span style="color: #f44336;">Load Failed</span>';

        const checkBtn = document.getElementById('check-update-btn');
        checkBtn.disabled = false;
        checkBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Check for Updates';

        alert(`Failed to load releases: ${error.message}`);
    }
}

function populateReleasesTable(releases, currentVersion) {
    const tbody = document.getElementById('releases-table-body');
    tbody.innerHTML = '';

    if (!releases || releases.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center; color: #999;">No releases found</td></tr>';
        return;
    }

    releases.forEach(release => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid #eee';

        // Version column
        const versionCell = document.createElement('td');
        versionCell.style.padding = '12px';
        versionCell.innerHTML = `
            <strong>${release.version}</strong>
            ${release.prerelease ? '<span style="background: #ff9800; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 6px;">PRE-RELEASE</span>' : ''}
        `;
        row.appendChild(versionCell);

        // Release date column
        const dateCell = document.createElement('td');
        dateCell.style.padding = '12px';
        const date = new Date(release.published_at);
        dateCell.textContent = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
        row.appendChild(dateCell);

        // Status column
        const statusCell = document.createElement('td');
        statusCell.style.padding = '12px';
        if (release.is_current) {
            statusCell.innerHTML = '<span style="color: #4caf50; font-weight: bold;"><i class="bi bi-check-circle"></i> Current</span>';
        } else if (compareVersions(release.version, currentVersion) > 0) {
            statusCell.innerHTML = '<span style="color: #2196f3;"><i class="bi bi-arrow-up"></i> Newer</span>';
        } else {
            statusCell.innerHTML = '<span style="color: #999;"><i class="bi bi-arrow-down"></i> Older</span>';
        }
        row.appendChild(statusCell);

        // Action column
        const actionCell = document.createElement('td');
        actionCell.style.padding = '12px';
        actionCell.style.textAlign = 'center';

        if (release.is_current) {
            actionCell.innerHTML = '<span style="color: #999; font-size: 12px;">Installed</span>';
        } else {
            const actionBtn = document.createElement('button');
            actionBtn.className = 'btn-primary';
            actionBtn.style.padding = '6px 16px';
            actionBtn.style.fontSize = '12px';

            if (compareVersions(release.version, currentVersion) > 0) {
                actionBtn.innerHTML = '<i class="bi bi-download"></i> Update';
                actionBtn.onclick = () => installSpecificVersion(release.version, 'update');
            } else {
                actionBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Rollback';
                actionBtn.className = 'btn-secondary';
                actionBtn.onclick = () => installSpecificVersion(release.version, 'rollback');
            }

            actionCell.appendChild(actionBtn);
        }
        row.appendChild(actionCell);

        tbody.appendChild(row);
    });
}

function compareVersions(v1, v2) {
    const parts1 = v1.split('.').map(Number);
    const parts2 = v2.split('.').map(Number);

    for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        const part1 = parts1[i] || 0;
        const part2 = parts2[i] || 0;

        if (part1 > part2) return 1;
        if (part1 < part2) return -1;
    }

    return 0;
}

async function installSpecificVersion(version, action) {
    const actionText = action === 'update' ? 'update to' : 'rollback to';
    const confirmMsg = `This will ${actionText} version ${version}.\n\nA snapshot backup will be created automatically before the ${action}.\n\nDo you want to proceed?`;

    if (!confirm(confirmMsg)) {
        return;
    }

    try {
        const progressDiv = document.getElementById('update-progress');
        const checkBtn = document.getElementById('check-update-btn');

        progressDiv.style.display = 'block';
        if (checkBtn) checkBtn.disabled = true;

        const response = await fetch('/api/admin/update', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ version: version })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to ${action}: ${errorText}`);
        }

        const result = await response.json();

        if (result.update_mode === 'automatic') {
            // Automatic update - app will restart
            alert(`${result.message}\n\nSnapshot Backup: ${result.snapshot.filename}\n\nThe application will restart automatically. Please wait a moment and refresh the page.`);

            // Poll for update status
            pollUpdateStatus();
        } else {
            // Manual update - show instructions
            progressDiv.style.display = 'none';
            if (checkBtn) checkBtn.disabled = false;

            const instructions = result.instructions.join('\n');
            const message = `${result.message}\n\n${instructions}\n\nSnapshot Backup: ${result.snapshot.filename}`;

            // Show instructions in a better format
            if (confirm(message + '\n\nWould you like to download the update script?')) {
                // Download the script
                window.location.href = `/api/admin/backups/download/${result.update_script}`;
            }
        }

    } catch (error) {
        console.error(`Error during ${action}:`, error);
        document.getElementById('update-progress').style.display = 'none';
        const checkBtn = document.getElementById('check-update-btn');
        if (checkBtn) checkBtn.disabled = false;
        alert(`Failed to ${action} to version ${version}: ${error.message}`);
    }
}

async function pollUpdateStatus() {
    const maxAttempts = 60; // Poll for up to 5 minutes
    let attempts = 0;

    const pollInterval = setInterval(async () => {
        attempts++;

        if (attempts > maxAttempts) {
            clearInterval(pollInterval);
            document.getElementById('update-status-text').innerHTML = '<span style="color: #ff9800;">Update Status Unknown</span>';
            alert('Update status check timed out. Please check the system manually.');
            return;
        }

        try {
            const response = await fetch('/api/admin/update-status', {
                headers: {
                    'Authorization': `Bearer ${adminToken}`
                }
            });

            if (!response.ok) {
                // Application might be restarting
                return;
            }

            const status = await response.json();

            if (!status.is_updating) {
                // Update complete
                clearInterval(pollInterval);
                document.getElementById('update-progress').style.display = 'none';
                document.getElementById('update-status-text').innerHTML = '<span style="color: #4caf50;">Update Complete!</span>';

                alert('Update completed successfully! Reloading dashboard...');

                // Reload the page
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            }

        } catch (error) {
            // Application might be restarting, continue polling
            console.log('Waiting for application to restart...');
        }
    }, 5000); // Poll every 5 seconds
}

// Check for updates on dashboard load (after DOMContentLoaded)
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('update-card')) {
        // Wait a bit to ensure adminToken is initialized
        setTimeout(() => {
            if (adminToken) {
                loadAllReleases();
            }
        }, 100);
    }
});

// ============================================
// Theme Management
// ============================================

/**
 * Initialize theme on page load
 */
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'system';
    const themeSelect = document.getElementById('admin-theme-select');

    if (themeSelect) {
        themeSelect.value = savedTheme;
    }

    applyTheme(savedTheme);

    // Listen for system theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            const currentTheme = localStorage.getItem('theme') || 'system';
            if (currentTheme === 'system') {
                applyTheme('system');
            }
        });
    }
}

/**
 * Change theme based on user selection
 */
function changeTheme(theme) {
    localStorage.setItem('theme', theme);
    applyTheme(theme);
}

/**
 * Apply theme to the document
 */
function applyTheme(theme) {
    const root = document.documentElement;

    if (theme === 'system') {
        // Detect system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }
    } else if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
    } else {
        root.removeAttribute('data-theme');
    }
}

// Initialize theme when DOM loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTheme);
} else {
    initializeTheme();
}
