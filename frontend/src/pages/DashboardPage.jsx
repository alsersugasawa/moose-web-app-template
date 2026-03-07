import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../App';
import { api } from '../api/client';

export default function DashboardPage() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [files, setFiles] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    api.notifications.list().then(setNotifications).catch(() => {});
    api.files.list().then(setFiles).catch(() => {});
  }, []);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div style={{ minHeight: '100vh', background: '#f5f6fa' }}>
      {/* Header */}
      <header role="banner" style={{
        background: '#667eea', color: '#fff', padding: '12px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>Web Platform</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '14px' }}>{user?.display_name || user?.username}</span>
          {unreadCount > 0 && (
            <span style={{
              background: '#e74c3c', color: '#fff', borderRadius: '50%',
              padding: '2px 7px', fontSize: '12px', fontWeight: 700,
            }} aria-label={`${unreadCount} unread notifications`}>
              {unreadCount}
            </span>
          )}
          <select
            value={i18n.language}
            onChange={e => { i18n.changeLanguage(e.target.value); localStorage.setItem('pref_lang', e.target.value); }}
            aria-label={t('language')}
            style={{ fontSize: '12px', padding: '4px', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
          >
            <option value="en">EN</option>
            <option value="es">ES</option>
            <option value="fr">FR</option>
          </select>
          <button
            onClick={logout}
            style={{
              background: 'rgba(255,255,255,.2)', color: '#fff', border: '1px solid rgba(255,255,255,.5)',
              borderRadius: '6px', padding: '6px 14px', cursor: 'pointer', fontSize: '13px',
            }}
          >
            {t('logout')}
          </button>
        </div>
      </header>

      {/* Skip navigation target */}
      <a id="main-content" tabIndex={-1} style={{ position: 'absolute', opacity: 0 }} aria-hidden="true">main content</a>

      {/* Tab navigation */}
      <nav role="navigation" aria-label="Dashboard sections" style={{
        background: '#fff', borderBottom: '1px solid #e0e0e0',
        display: 'flex', padding: '0 24px', gap: '4px',
      }}>
        {[
          { id: 'overview', label: t('dashboard') },
          { id: 'notifications', label: `Notifications${unreadCount ? ` (${unreadCount})` : ''}` },
          { id: 'files', label: t('files') },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            style={{
              padding: '14px 18px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '3px solid #667eea' : '3px solid transparent',
              color: activeTab === tab.id ? '#667eea' : '#666',
              fontWeight: activeTab === tab.id ? 700 : 400,
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Main content */}
      <main id="main-content" role="main" style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>

        {activeTab === 'overview' && (
          <section aria-labelledby="overview-heading">
            <h2 id="overview-heading" style={{ marginBottom: '16px' }}>{t('welcome')}</h2>
            <p style={{ color: '#666', marginBottom: '24px' }}>{t('welcome_subtitle')}</p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <StatCard label="Files uploaded" value={files.length} />
              <StatCard label="Notifications" value={notifications.length} />
              <StatCard label="Unread" value={unreadCount} />
            </div>
          </section>
        )}

        {activeTab === 'notifications' && (
          <section aria-labelledby="notif-heading">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 id="notif-heading" style={{ margin: 0 }}>Notifications</h2>
              {unreadCount > 0 && (
                <button
                  onClick={() => api.notifications.markAllRead().then(() =>
                    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
                  )}
                  style={secondaryBtnStyle}
                >
                  Mark all read
                </button>
              )}
            </div>
            {notifications.length === 0 ? (
              <p style={{ color: '#999' }}>No notifications yet.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {notifications.map(n => (
                  <li key={n.id} style={{
                    background: n.is_read ? '#fff' : '#f0f4ff',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    marginBottom: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}>
                    <span style={{ fontSize: '14px' }}>{n.message}</span>
                    {!n.is_read && (
                      <button
                        onClick={() => api.notifications.markRead(n.id).then(() =>
                          setNotifications(prev => prev.map(x => x.id === n.id ? { ...x, is_read: true } : x))
                        )}
                        style={{ ...secondaryBtnStyle, fontSize: '12px', padding: '4px 10px' }}
                      >
                        Mark read
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {activeTab === 'files' && (
          <section aria-labelledby="files-heading">
            <h2 id="files-heading" style={{ marginBottom: '16px' }}>{t('files')}</h2>
            <FileUploader onUploaded={file => setFiles(prev => [file, ...prev])} />
            {files.length === 0 ? (
              <p style={{ color: '#999', marginTop: '16px' }}>No files uploaded yet.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, marginTop: '16px' }}>
                {files.map(f => (
                  <li key={f.id} style={{
                    background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px',
                    padding: '12px 16px', marginBottom: '8px',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <div>
                      <strong style={{ fontSize: '14px' }}>{f.filename}</strong>
                      <span style={{ color: '#999', fontSize: '12px', marginLeft: '10px' }}>
                        {formatBytes(f.size_bytes)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => api.files.getUrl(f.id).then(d => window.open(d.url, '_blank'))}
                        style={{ ...secondaryBtnStyle, fontSize: '12px', padding: '4px 10px' }}
                      >
                        Download
                      </button>
                      <button
                        onClick={() => api.files.delete(f.id).then(() =>
                          setFiles(prev => prev.filter(x => x.id !== f.id))
                        )}
                        style={{ ...secondaryBtnStyle, fontSize: '12px', padding: '4px 10px', color: '#e74c3c', borderColor: '#e74c3c' }}
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

      </main>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e0e0e0', borderRadius: '10px',
      padding: '20px', textAlign: 'center',
    }}>
      <div style={{ fontSize: '32px', fontWeight: 700, color: '#667eea' }}>{value}</div>
      <div style={{ color: '#666', fontSize: '13px', marginTop: '4px' }}>{label}</div>
    </div>
  );
}

function FileUploader({ onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  async function handleChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const uploaded = await api.files.upload(file);
      onUploaded(uploaded);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  return (
    <div>
      <label htmlFor="file-upload" style={{
        display: 'inline-block', padding: '10px 20px', background: '#667eea', color: '#fff',
        borderRadius: '8px', cursor: 'pointer', fontSize: '14px', fontWeight: 600,
      }}>
        {uploading ? 'Uploading…' : 'Upload file'}
        <input id="file-upload" type="file" onChange={handleChange} disabled={uploading}
          style={{ display: 'none' }} aria-label="Upload a file" />
      </label>
      {error && <p role="alert" style={{ color: '#c33', fontSize: '13px', marginTop: '8px' }}>{error}</p>}
    </div>
  );
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

const secondaryBtnStyle = {
  background: '#fff', color: '#667eea', border: '1px solid #667eea',
  borderRadius: '6px', padding: '6px 14px', cursor: 'pointer', fontSize: '13px',
};
