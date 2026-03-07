import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../App';
import { api } from '../api/client';

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState('login'); // 'login' | 'register' | 'forgot'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Already logged in → go to dashboard
  if (user) {
    navigate('/', { replace: true });
    return null;
  }

  async function handleLogin(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const data = await api.auth.login(username, password);
      const me = await api.auth.me();
      // Persist language preference from profile
      if (me.language) {
        localStorage.setItem('pref_lang', me.language);
        i18n.changeLanguage(me.language);
      }
      login(data.access_token, me);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await api.auth.register(username, email, password);
      setTab('login');
      setInfo('Registration successful — please log in.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleForgot(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await api.auth.forgotPassword(email);
      setInfo('Reset link sent — check your email.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '20px',
      }}
    >
      <div
        style={{
          background: '#fff',
          borderRadius: '12px',
          boxShadow: '0 20px 60px rgba(0,0,0,.3)',
          padding: '40px',
          width: '100%',
          maxWidth: '420px',
        }}
      >
        <h1 style={{ textAlign: 'center', color: '#667eea', marginBottom: '8px' }}>
          Web Platform
        </h1>

        {/* Tab switcher */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
          {['login', 'register'].map((t_) => (
            <button
              key={t_}
              onClick={() => { setTab(t_); setError(''); setInfo(''); }}
              style={{
                flex: 1,
                padding: '8px',
                border: '2px solid',
                borderColor: tab === t_ ? '#667eea' : '#e0e0e0',
                background: tab === t_ ? '#667eea' : '#fff',
                color: tab === t_ ? '#fff' : '#333',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600,
                textTransform: 'capitalize',
              }}
            >
              {t(t_)}
            </button>
          ))}
        </div>

        {info && (
          <p role="status" style={{ color: 'green', marginBottom: '12px', fontSize: '14px' }}>
            {info}
          </p>
        )}
        {error && (
          <p role="alert" style={{ color: '#c33', background: '#fee', padding: '10px', borderRadius: '6px', marginBottom: '12px', fontSize: '14px' }}>
            {error}
          </p>
        )}

        {tab === 'login' && (
          <form onSubmit={handleLogin} noValidate>
            <Field label={t('username')} htmlFor="sp-username">
              <input id="sp-username" type="text" value={username} onChange={e => setUsername(e.target.value)}
                required autoComplete="username" aria-required="true" style={inputStyle} />
            </Field>
            <Field label={t('password')} htmlFor="sp-password">
              <input id="sp-password" type="password" value={password} onChange={e => setPassword(e.target.value)}
                required autoComplete="current-password" aria-required="true" style={inputStyle} />
            </Field>
            <button type="submit" disabled={submitting} style={btnStyle}>
              {submitting ? '…' : t('login')}
            </button>
            <p style={{ textAlign: 'center', marginTop: '12px', fontSize: '13px' }}>
              <button type="button" onClick={() => { setTab('forgot'); setError(''); }}
                style={{ background: 'none', border: 'none', color: '#667eea', cursor: 'pointer', textDecoration: 'underline', fontSize: '13px' }}>
                {t('forgot_password')}
              </button>
            </p>
          </form>
        )}

        {tab === 'register' && (
          <form onSubmit={handleRegister} noValidate>
            <Field label={t('username')} htmlFor="sp-reg-username">
              <input id="sp-reg-username" type="text" value={username} onChange={e => setUsername(e.target.value)}
                required autoComplete="username" aria-required="true" style={inputStyle} />
            </Field>
            <Field label={t('email')} htmlFor="sp-reg-email">
              <input id="sp-reg-email" type="email" value={email} onChange={e => setEmail(e.target.value)}
                required autoComplete="email" aria-required="true" style={inputStyle} />
            </Field>
            <Field label={t('password')} htmlFor="sp-reg-password">
              <input id="sp-reg-password" type="password" value={password} onChange={e => setPassword(e.target.value)}
                required autoComplete="new-password" aria-required="true" style={inputStyle} />
            </Field>
            <button type="submit" disabled={submitting} style={btnStyle}>
              {submitting ? '…' : t('register')}
            </button>
          </form>
        )}

        {tab === 'forgot' && (
          <form onSubmit={handleForgot} noValidate>
            <Field label={t('email')} htmlFor="sp-forgot-email">
              <input id="sp-forgot-email" type="email" value={email} onChange={e => setEmail(e.target.value)}
                required autoComplete="email" aria-required="true" style={inputStyle} />
            </Field>
            <button type="submit" disabled={submitting} style={btnStyle}>
              {submitting ? '…' : t('send_reset_link')}
            </button>
            <p style={{ textAlign: 'center', marginTop: '12px', fontSize: '13px' }}>
              <button type="button" onClick={() => { setTab('login'); setError(''); }}
                style={{ background: 'none', border: 'none', color: '#667eea', cursor: 'pointer', textDecoration: 'underline', fontSize: '13px' }}>
                {t('back_to_login')}
              </button>
            </p>
          </form>
        )}

        {/* Language switcher */}
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <select
            value={i18n.language}
            onChange={e => { i18n.changeLanguage(e.target.value); localStorage.setItem('pref_lang', e.target.value); }}
            style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px', border: '1px solid #ddd', cursor: 'pointer' }}
            aria-label={t('language')}
          >
            <option value="en">English</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
          </select>
        </div>
      </div>
    </main>
  );
}

function Field({ label, htmlFor, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <label htmlFor={htmlFor} style={{ display: 'block', marginBottom: '6px', fontWeight: 500, fontSize: '14px', color: '#333' }}>
        {label}
      </label>
      {children}
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '10px 14px',
  border: '2px solid #e0e0e0',
  borderRadius: '8px',
  fontSize: '15px',
  boxSizing: 'border-box',
  outline: 'none',
};

const btnStyle = {
  width: '100%',
  padding: '12px',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: '#fff',
  border: 'none',
  borderRadius: '8px',
  fontSize: '15px',
  fontWeight: 600,
  cursor: 'pointer',
};
