# Application Update Guide

This guide explains how to update the Web Platform application using different methods.

## Update Methods

### Method 1: Admin Portal Update (Recommended)

The easiest way to update is through the Admin Portal:

1. Log in to the Admin Portal at `http://your-domain:8080/admin-login.html`
2. Navigate to the **Dashboard** section
3. Look for the **Application Updates** card
4. Click **Check for Updates** to see if a new version is available
5. If an update is available, click **Install Update**
6. Confirm the update - a snapshot backup will be created automatically
7. Wait for the application to restart (usually 1-2 minutes)

**Features:**
- ✅ Automatic snapshot backup before update
- ✅ Database migrations run automatically
- ✅ No data loss
- ✅ Rollback capability using snapshot backups
- ✅ Zero-downtime for read operations

### Method 2: Manual Git Pull Update

For manual control or if the admin portal is unavailable:

```bash
# Navigate to the application directory
cd /path/to/my-web-app

# Create a manual backup (recommended)
docker compose exec web python -c "
from app.routers.admin import create_backup
import asyncio
asyncio.run(create_backup())
"

# Pull latest changes
git pull origin main

# Rebuild and restart all services (web, worker, redis, db)
docker compose up -d --build

# Run database migrations manually if needed (see Database Migrations section)
# Migrations are SQL files in migrations/ applied via psql
```

### Method 3: CI/CD Automatic Updates

When you push a new tag to GitHub, the CI/CD pipeline automatically:

1. Creates a GitHub release
2. Builds a new Docker image
3. Pushes to Docker Hub (if configured)

To deploy the update:

```bash
# Pull the latest image
docker compose pull

# Restart with new image
docker compose up -d

# Migrations run automatically on startup
```

## Version Management

### Checking Current Version

**Via Admin Portal:**
- Dashboard → System Information → App Version

**Via Command Line:**
```bash
docker compose exec web python -c "from app.routers.admin import APP_VERSION; print(APP_VERSION)"
```

### Creating a New Release

1. Update the version in `app/routers/admin.py`:
   ```python
   APP_VERSION = "3.1.0"  # Update this
   ```

2. Commit and create a tag:
   ```bash
   git add app/routers/admin.py
   git commit -m "Bump version to 3.1.0"
   git tag -a v3.1.0 -m "Release version 3.1.0"
   git push origin main --tags
   ```

3. GitHub Actions will automatically create a release

## Database Migrations

### Automatic Migrations

Database migrations run automatically when:
- Using the Admin Portal update
- Container starts up (if configured)
- Running the update script

### Manual Migrations

Migrations are plain SQL files in the `migrations/` directory (e.g. `001_initial.sql`, `005_phase3.sql`). Apply them in order:

```bash
# Copy the migration file into the db container and apply it
docker cp migrations/006_example.sql webapp-db:/tmp/
docker exec webapp-db psql -U postgres -d webapp -f /tmp/006_example.sql
```

To check which tables exist:

```bash
docker exec webapp-db psql -U postgres -d webapp -c "\dt"
```

## Backup and Rollback

### Automatic Backups

The update process automatically creates snapshot backups:
- Stored in `/app/backups` (or your configured backup directory)
- Named: `snapshot_before_update_YYYYMMDD_HHMMSS.sql`
- Registered in the backups database table

### Rollback Procedure

If an update causes issues:

1. **Via Admin Portal:**
   - Go to Backups section
   - Find the snapshot backup created before the update
   - Click "Restore" and select the snapshot

2. **Via Command Line:**
   ```bash
   # Find the snapshot file
   ls -lh backups/snapshot_before_update*

   # Restore from snapshot
   docker exec -i webapp-db psql -U postgres -d webapp < backups/snapshot_before_update_TIMESTAMP.sql

   # Restart services
   docker compose restart web worker
   ```

## Troubleshooting

### Update Fails

1. Check the logs:
   ```bash
   docker compose logs web --tail=100
   docker compose logs worker --tail=50
   ```

2. Verify all services are healthy:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

3. Verify database connectivity:
   ```bash
   docker exec webapp-db pg_isready -U postgres
   ```

### Application Won't Start After Update

1. Check for import or startup errors:
   ```bash
   docker compose logs web --tail=50
   ```

2. Rollback to snapshot backup (see Rollback Procedure above)

3. Verify Redis is reachable:
   ```bash
   docker exec webapp-redis redis-cli ping
   ```

### Lost Connection During Update

The application may be briefly unavailable during restart:
- Wait 1-2 minutes and refresh the page
- The update continues in the background
- Check `/tmp/update_app.log` for progress

## Update Safety Features

✅ **Automatic Snapshot Backups** - Created before every update
✅ **Database Migrations** - Run automatically with validation
✅ **Rollback Support** - Easy restoration from any backup
✅ **Zero Data Loss** - All data preserved during updates
✅ **Graceful Restart** - Minimal downtime (typically < 30 seconds)
✅ **Update Logging** - All update actions logged in system logs

## CI/CD Configuration

### Required Secrets

Add these to your GitHub repository secrets (Settings → Secrets):

- `DOCKER_USERNAME` - Docker Hub username (optional)
- `DOCKER_PASSWORD` - Docker Hub password/token (optional)

### Customizing the Workflow

Edit `.github/workflows/release.yml` to customize:
- Build steps
- Deployment targets
- Notification webhooks
- Testing procedures

## Production Deployment Checklist

Before updating in production:

- [ ] Backup configuration verified (local + remote)
- [ ] Database backup tested and verified
- [ ] Maintenance window scheduled (if needed)
- [ ] Rollback procedure tested
- [ ] Team notified of update
- [ ] Monitoring alerts configured
- [ ] Update tested in staging environment

## Support

For issues or questions:
- Create an issue at: https://github.com/YOUR_ORG/web-platform/issues
- Check the system logs in Admin Portal
- Review the backup history in Admin Portal

---

**Last Updated:** 2026-03-03
**Version:** 1.4.0
