# Web Platform — User Guide

**Version:** 1.4.0
**Supported browsers:** Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Logging In](#logging-in)
3. [Registration](#registration)
4. [Two-Factor Authentication (TOTP)](#two-factor-authentication-totp)
5. [My Profile](#my-profile)
6. [API Keys](#api-keys)
7. [Dashboard](#dashboard)
8. [Session Management](#session-management)
9. [Notifications](#notifications)
10. [Admin Portal](#admin-portal)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Deployment

On the very first visit the application launches a **setup wizard** automatically:

1. Enter your desired **application name** (shown throughout the UI)
2. Create the **admin account** (username, email, password)
3. Click **Create Account** — you will be redirected to the admin login page

After initial setup the wizard is disabled and regular users access the app at the root URL.

### Accessing the App

```
http://localhost:8080          # Development (default)
https://yourdomain.com         # Production (HTTPS via Caddy)
```

---

## Logging In

1. Enter your **username** and **password**
2. Click **Login**
3. If your account has TOTP enabled, you will be prompted for a 6-digit code from your authenticator app

On successful login you are taken to your dashboard.

### Forgot Password

1. Click **Forgot password?** below the login form
2. Enter your registered email address
3. Click **Send Reset Link**
4. Open the email and click the reset link (link expires after a short window)
5. Enter and confirm your new password

> In development (no SMTP configured) the reset link is printed to the application log instead of emailed.

---

## Registration

1. Click **Register here** on the login page
2. Enter a **username**, **email address**, and **password**
3. If invite-only mode is active, paste your **invitation code** into the invite field
4. Click **Register** — you will be automatically logged in

Password requirements: minimum 8 characters, at least one uppercase letter, one lowercase letter, one digit, and one special character.

### Email Verification

After registering you will receive a verification email. Click the link to confirm your address. If `FORCE_EMAIL_VERIFICATION` is enabled on the server, your account will be restricted until verified.

Click **Resend verification email** from the banner shown in the app if you did not receive the email.

### Invitation Links

When invite-only mode is enabled, admins generate invitation links of the form:

```
https://yourdomain.com/static/index.html?invite=<token>
```

Clicking this link opens the registration form with the invitation code pre-filled.

---

## Two-Factor Authentication (TOTP)

### Enable 2FA

1. Log in and go to your dashboard
2. In the **Account Security** card, click **Set up 2FA**
3. Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)
4. Enter the 6-digit code shown in your app to confirm
5. Click **Enable**

### Disable 2FA

1. In the **Account Security** card, click **Disable 2FA**
2. Enter your current 6-digit TOTP code
3. Click **Disable**

---

## My Profile

Click your **username** (or display name) in the top-right header to open the profile panel.

| Field | Description |
|---|---|
| Display Name | Shown in the header instead of your username |
| Bio | Short description shown on your profile |
| Timezone | Used for date/time display |
| Language | UI language preference |
| Avatar | Upload a JPEG, PNG, or WebP image (max 2 MB); stored as 90×90 JPEG |

Click **Save Profile** to apply changes.

### Changing Your Avatar

Click **Change Avatar** and select an image file. The image is automatically cropped to 200×200 pixels and stored securely on the server.

---

## API Keys

API keys let scripts and services authenticate to the API without using your password or JWT token. Keys are sent via the `X-API-Key` request header.

### Create a Key

1. In the **API Keys** dashboard card, click **New Key**
2. Enter a descriptive **name** (e.g. `CI/CD Pipeline`)
3. Optionally set an **expiry** (30 days, 90 days, 1 year, or never)
4. Click **Create Key**
5. **Copy the key immediately** — it is shown only once

Key format: `mpk_` followed by 40 hex characters (44 chars total).

### Using a Key

```bash
curl -H "X-API-Key: mpk_<your-key>" https://yourdomain.com/api/auth/me
```

### Revoke a Key

Click the trash icon next to any key in the API Keys card. The key stops working immediately.

---

## Dashboard

The dashboard is fully customizable.

### Built-in Cards

| Card | Description |
|---|---|
| Welcome | Introduction banner |
| Account Security | TOTP status and setup; Active Sessions button |
| API Keys | List and manage your API keys |

### Customizing

Click **Customize** (top-right of dashboard) to:

- **Show/hide** built-in cards using the toggle checkboxes
- **Add custom cards** with a title, optional body text, icon, and an optional link button
- **Edit or delete** custom cards

Custom card settings are stored in your browser's `localStorage` — they persist across sessions on the same device.

---

## Session Management

Each browser login creates a tracked session. You can view and revoke sessions from the **Active Sessions** button in the Account Security card.

- **Revoke** a single session to log out that device
- **Revoke All** to log out everywhere (including your current session)

---

## Notifications

When logged in, a real-time notification channel is opened automatically. Incoming notifications appear as a toast message in the corner of the screen and increment a badge counter in the header.

- The badge resets when you log out
- Notifications are sent by the server via WebSocket — no polling required
- No browser extension or manual refresh is needed

---

## Admin Portal

The admin portal is available to administrators and users who have been granted permission scopes by their role.

Access it via the **Admin** button in the top-right header (visible only when you have admin access or at least one permission scope).

Direct URL: `/static/admin.html`

### Sections

#### Users

List all users with their username, display name, email, role, admin status, and last login time.

Actions:
- **Create** a new user (with optional admin flag and role assignment)
- **Edit** a user — update username, email, password, role, admin status, and active flag
- **Delete** a user (cannot delete your own account)

#### Roles *(admin only)*

Manage named roles and their permission scopes.

| Scope | Description |
|---|---|
| `users:read` | View user list in admin portal |
| `logs:read` | View activity logs |
| `system:read` | View system info and resource stats |
| `backups:read` | View backups list |
| `backups:write` | Create new backups |
| `invitations:manage` | Create and revoke invitations |
| `roles:manage` | View role list |
| `feature_flags:manage` | View and toggle feature flags |

Seeded roles at install time: `viewer`, `editor`, `manager`.

#### Invitations

Create single-use invitation tokens to allow new users to register when invite-only mode is active.

1. Click **Create Invitation**
2. Optionally restrict to a specific email address and set an expiry
3. Copy the invitation link and share it with the intended recipient

Used invitations show the date and the account that consumed them. Unused invitations can be revoked.

#### Logs

View the system activity log, filterable by level (INFO, WARNING, ERROR). Includes timestamps, user, IP address, and action.

#### Backups

Create and download database backups. Backups are stored in the `backups/` directory inside the container.

#### System

View real-time system resource stats: CPU, memory, disk, and service statuses. When the admin dashboard is open, stats update live every 5 seconds via a WebSocket connection — no page refresh needed.

#### Config

View and update application-level settings: app name, invite-only mode toggle.

#### Feature Flags *(admin or `feature_flags:manage` scope)*

Database-backed on/off switches that control platform features without a code deployment.

| Flag | Description |
|---|---|
| `registration` | Allow new user self-registration |
| `oauth_login` | Allow OAuth2 social login |
| `api_keys` | Allow users to generate API keys |
| `invitations` | Allow admins to create invitations |

- Toggle any flag using the switch in the admin portal
- Create custom flags for your own features via **Add Flag**
- The four built-in flags above cannot be deleted (toggle only)
- Any service can read a flag via `GET /api/feature-flags/{name}` — returns `{"name": "...", "enabled": true/false}`

#### Developer Tools *(admin only)*

- **Export TypeScript Client** — Downloads a fully-typed `client.ts` file containing TypeScript interfaces for all API schemas and `fetch` wrappers for all endpoints. Ideal for building frontend applications.
- **Export OpenAPI JSON** — Downloads the raw OpenAPI 3.x specification.
- **Scaffold CLI** — Run `python -m scaffold router <name>` from the project root to generate a boilerplate router, schema stubs, and a migration SQL stub for a new resource.

---

## Troubleshooting

### Cannot log in

- Check username and password (case-sensitive)
- Clear browser cookies/localStorage and try again
- Use **Forgot password?** to reset via email
- Confirm your email is verified if `FORCE_EMAIL_VERIFICATION` is enabled

### Login form fields are unresponsive

Hard-refresh the page (`Ctrl+Shift+R` / `Cmd+Shift+R`) to clear cached JavaScript. If the issue persists, open the browser console (F12) and look for JavaScript errors.

### Invite code not accepted

- Confirm the token has not expired
- Confirm the token has not already been used (each token is single-use)
- Ask an admin to generate a new invitation

### Avatar not updating

- Ensure the image is ≤ 2 MB and is JPEG, PNG, or WebP
- Hard-refresh the page after uploading to clear the browser image cache

### API key returns 401

- Verify the key has not been revoked
- Check that the `X-API-Key` header is present and correctly formatted
- Confirm the key has not passed its expiry date

### Admin link not visible

The Admin link appears only if you are an admin (`is_admin = true`) or your assigned role grants at least one permission scope. Contact an admin to adjust your role or permissions.

---

**Need help?** Open an issue at the project repository or contact your system administrator.
