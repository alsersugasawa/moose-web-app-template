# Release Process Documentation

This document explains the three-tier release process for the Web Platform application.

## Overview

The application uses a **three-tier release strategy**:

1. **Test Branch** - Routine development and testing
2. **Minor Releases** - Bug fixes and security updates (v1.0.X)
3. **Major Releases** - New features and breaking changes (vX.0.0)

---

## 1. Routine Updates (Test Branch)

**Purpose:** Development, testing, and routine changes

**Branch:** `test`

**Workflow File:** `.github/workflows/test-branch.yml`

### When to Use
- Daily development work
- Experimental features
- Code refactoring
- Testing new dependencies
- Documentation updates

### Process

```bash
# Create or switch to test branch
git checkout -b test
# or
git checkout test

# Make your changes
git add .
git commit -m "Your commit message"
git push origin test
```

### What Happens
- ✅ Automated tests run
- ✅ Code linting checks
- ✅ Docker build validation
- ⚠️ **NO release is created**
- ⚠️ **NO version number change**

### GitHub Actions
The workflow automatically:
- Runs Python linting (flake8)
- Executes test suite
- Validates Docker build
- Comments on pull requests

---

## 2. Minor Releases (Bug Fixes & Security)

**Purpose:** Bug fixes, security patches, minor improvements

**Version Format:** `v1.0.X` (increment third number)

**Examples:**
- `v1.0.0` → `v1.0.1` (first bug fix)
- `v1.0.1` → `v1.0.2` (second bug fix)
- `v3.2.4` → `v3.2.5` (patch release)

**Workflow File:** `.github/workflows/minor-release.yml`

### When to Use
- Bug fixes
- Security patches
- Performance improvements
- Documentation fixes
- Dependency updates (no breaking changes)
- Minor UI tweaks

### Process

#### Option 1: Commit and Tag (Recommended)

```bash
# Make sure you're on main branch
git checkout main
git pull origin main

# Make your bug fixes
# ...commit your changes...

# Update version in code
VERSION="1.0.2"
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"$VERSION\"/" app/routers/admin.py

# Commit version change
git add app/routers/admin.py
git commit -m "Fix critical bug in authentication"

# Create and push tag
git tag -a v$VERSION -m "Bug fix release: v$VERSION"
git push origin main
git push origin v$VERSION
```

#### Option 2: GitHub Actions Workflow Dispatch

1. Go to GitHub → Actions → "Minor Release - Security & Bug Fixes"
2. Click "Run workflow"
3. Enter version number (e.g., `1.0.2`)
4. Click "Run workflow"

### What Happens
- ✅ Version updated in `app/routers/admin.py`
- ✅ GitHub release created automatically
- ✅ Changelog generated from commits
- ✅ Docker images built and tagged:
  - `latest`
  - `v1.0.2`
  - `minor-latest`
- ✅ Release notes include installation instructions

### Changelog Generation
The workflow automatically finds commits with:
- Keywords: `fix`, `bug`, `security`
- Generates list for release notes

---

## 3. Major Releases (New Features)

**Purpose:** Major new features, breaking changes, significant updates

**Version Format:** `vX.0.0` (increment first number, reset others to 0)

**Examples:**
- `v1.9.5` → `v2.0.0` (major version bump)
- `v2.0.0` → `v3.0.0` (next major version)

**Workflow File:** `.github/workflows/major-release.yml`

### When to Use
- Major new features
- Breaking API changes
- Database schema changes
- Architecture changes
- Major dependency upgrades
- Complete rewrites or refactors

### Process

#### Option 1: Commit and Tag

```bash
# Make sure you're on main branch
git checkout main
git pull origin main

# Make all your major changes
# ...commit your changes...

# Update version in code
VERSION="2.0.0"
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"$VERSION\"/" app/routers/admin.py

# Commit version change with major release message
git add app/routers/admin.py
git commit -m "🚀 Major release: v$VERSION - New feature set"

# Create and push tag
git tag -a v$VERSION -m "Major release v$VERSION

New Features:
- Feature A
- Feature B

Breaking Changes:
- Changed API endpoint structure
- Updated database schema"

git push origin main
git push origin v$VERSION
```

#### Option 2: GitHub Actions Workflow Dispatch

1. Go to GitHub → Actions → "Major Release - New Features"
2. Click "Run workflow"
3. Enter major version (e.g., `2.0.0`)
4. Optionally add release notes
5. Click "Run workflow"

### What Happens
- ✅ Version validation (must be X.0.0 format)
- ✅ Version updated in code
- ✅ Comprehensive changelog generated:
  - New features
  - Bug fixes
  - Breaking changes
  - Security updates
- ✅ Detailed release notes with:
  - Installation instructions
  - Rollback procedures
  - Breaking changes warning
  - System requirements
- ✅ Docker images built and tagged:
  - `latest`
  - `v2.0.0`
  - `v2` (major version tag)
  - `major-latest`

---

## Version Numbering Rules

### Semantic Versioning Format: `vMAJOR.MINOR.PATCH`

```
v1.0.0
 │ │ └─ PATCH: Bug fixes, security patches
 │ └─── MINOR: New features (backward compatible)
 └───── MAJOR: Breaking changes, major features
```

### Examples

**Patch (Minor Release):**
- `v1.0.0` → `v1.0.1` - Fixed login bug
- `v1.0.1` → `v1.0.2` - Security patch
- `v2.3.4` → `v2.3.5` - Performance fix

**Minor (Use Minor Release workflow):**
- `v1.0.0` → `v1.1.0` - Added new report feature
- `v1.1.0` → `v1.2.0` - Improved UI

**Major (Use Major Release workflow):**
- `v1.9.5` → `v2.0.0` - Complete redesign
- `v2.0.0` → `v3.0.0` - New architecture

---

## Quick Reference

| Action | Branch | Workflow | Version Change | Release Created |
|--------|--------|----------|----------------|-----------------|
| Development | `test` | test-branch.yml | None | No |
| Bug Fix | `main` | minor-release.yml | v1.0.1 → v1.0.2 | Yes |
| Security Patch | `main` | minor-release.yml | v1.0.2 → v1.0.3 | Yes |
| New Feature | `main` | major-release.yml | v1.0.0 → v2.0.0 | Yes |
| Breaking Change | `main` | major-release.yml | v2.0.0 → v3.0.0 | Yes |

---

## Docker Image Tags

### After Minor Release (v1.0.2)
- `web-platform:latest` - Always points to latest stable
- `web-platform:v1.0.2` - Specific version
- `web-platform:minor-latest` - Latest minor release

### After Major Release (v2.0.0)
- `web-platform:latest` - Always points to latest stable
- `web-platform:v2.0.0` - Specific version
- `web-platform:v2` - Major version (gets v2.0.1, v2.0.2, etc.)
- `web-platform:major-latest` - Latest major release

---

## Commit Message Conventions

To ensure proper changelog generation, use these prefixes:

### For Minor Releases
- `fix:` - Bug fixes
- `security:` - Security updates
- `perf:` - Performance improvements

### For Major Releases
- `feat:` - New features
- `add:` - New additions
- `breaking:` - Breaking changes
- `refactor:` - Major refactoring

### Examples

```bash
# Minor release commits
git commit -m "fix: resolve authentication timeout issue"
git commit -m "security: patch XSS vulnerability in user input"
git commit -m "perf: optimize database queries for user inbox"

# Major release commits
git commit -m "feat: add real-time collaboration features"
git commit -m "breaking: change API endpoint structure"
git commit -m "add: implement new dashboard design"
```

---

## Rollback Procedures

### If a Release Fails

**For Minor Releases:**
```bash
# Delete the tag locally and remotely
git tag -d v1.0.2
git push origin :refs/tags/v1.0.2

# Delete the GitHub release manually
# Go to GitHub → Releases → Delete release

# Fix the issue and re-release
```

**For Major Releases:**
1. Use Admin Portal → Backups → Restore snapshot
2. Or manually restore from backup
3. Delete failed release tag
4. Fix issues and re-release

---

## Best Practices

### Before Any Release

1. ✅ Test on test branch first
2. ✅ Review all commits
3. ✅ Update documentation
4. ✅ Check for breaking changes
5. ✅ Ensure tests pass

### Minor Release Best Practices

- Keep changes small and focused
- Only include bug fixes and patches
- Don't introduce new features
- Test thoroughly before tagging

### Major Release Best Practices

- Plan breaking changes carefully
- Update all documentation
- Provide migration guides
- Test extensively in staging
- Schedule maintenance window
- Communicate with users

---

## Automation Details

### GitHub Actions Triggers

**Test Branch:**
- Trigger: Push to `test` branch
- Runs: Tests, linting, build checks

**Minor Release:**
- Trigger: Tag matching `v[0-9]+.[0-9]+.[0-9]+`
- Example: `v1.0.1`, `v2.3.4`
- Validates: Must be patch version

**Major Release:**
- Trigger: Tag matching `v[0-9]+.0.0`
- Example: `v2.0.0`, `v3.0.0`
- Validates: Must be major version (X.0.0)

### Required Secrets (Optional)

Add these to GitHub repository secrets for Docker Hub publishing:

- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_PASSWORD` - Your Docker Hub access token

---

## Troubleshooting

### Workflow Fails

```bash
# View workflow logs
# Go to GitHub → Actions → Select workflow run

# Re-run failed workflow
# Click "Re-run failed jobs"
```

### Wrong Version Tagged

```bash
# Delete tag locally
git tag -d v1.0.2

# Delete tag remotely
git push origin :refs/tags/v1.0.2

# Create correct tag
git tag -a v1.0.3 -m "Correct version"
git push origin v1.0.3
```

### Need to Skip Workflow

```bash
# Add [skip ci] to commit message
git commit -m "docs: update README [skip ci]"
```

---

## Support

For questions or issues with the release process:
- Open an issue on GitHub
- Check workflow logs in Actions tab
- Review this documentation

---

**Last Updated:** 2026-03-05
**Current Version:** 1.6.0
