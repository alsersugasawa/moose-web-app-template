# Profile Picture Database Storage Migration

## Overview

Profile pictures are now stored directly in the PostgreSQL database as base64-encoded data instead of as files in the `/uploads/profile_pictures` directory. This change improves security, simplifies backups, and eliminates file system dependencies.

## Changes Made

### Database Schema
- **New Column**: `profile_picture_data` (TEXT) - Stores base64-encoded image data
- **New Column**: `profile_picture_mime_type` (VARCHAR(50)) - Stores MIME type (e.g., 'image/jpeg', 'image/png')
- **Deprecated**: `photo_url` column kept for backward compatibility but no longer used for new uploads

### Backend Changes

#### Models (`app/models.py`)
```python
profile_picture_data = Column(Text, nullable=True)  # Base64-encoded image data
profile_picture_mime_type = Column(String(50), nullable=True)  # e.g., 'image/jpeg'
```

#### API Endpoint (`app/routers/web_platform.py`)
- `/api/family/members/{member_id}/upload-photo` now:
  1. Validates file type and size (max 5MB)
  2. Converts image to base64
  3. Stores in database
  4. Returns data URL format: `data:{mime_type};base64,{data}`

#### Tree Building (`app/routers/web_platform.py`)
- `GET /api/family/tree` endpoint converts base64 data to data URLs for frontend consumption
- Fallback to `photo_url` for backward compatibility with old data

### Frontend Compatibility
- No changes required - frontend continues to use `photo_url` field
- Data URLs (format: `data:image/jpeg;base64,...`) work seamlessly with `<img>` tags

### Docker Configuration
- Removed `/app/uploads` volume mount from `docker-compose.yml`
- Updated `Dockerfile` to not create uploads directory
- Backups directory still maintained for database backups

## Migration Steps

### For Existing Deployments

1. **Run Database Migration**
   ```bash
   # The migration will add new columns without affecting existing data
   docker-compose exec db psql -U postgres -d webapp -f /app/migrations/008_store_photos_in_database.sql
   ```

2. **Optional: Migrate Existing Photos**
   Existing photos in `/uploads/profile_pictures` can remain in place. New uploads will use database storage. To migrate existing photos:
   ```python
   # Migration script (to be run manually if needed)
   import base64
   from pathlib import Path

   for member in family_members:
       if member.photo_url and not member.profile_picture_data:
           file_path = Path(member.photo_url.lstrip('/'))
           if file_path.exists():
               with open(file_path, 'rb') as f:
                   image_data = f.read()
                   member.profile_picture_data = base64.b64encode(image_data).decode('utf-8')
                   member.profile_picture_mime_type = 'image/jpeg'  # Detect from file
   ```

3. **Rebuild and Restart**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## Benefits

### Security
- Profile pictures stored with user data in database
- No direct file system access required
- Eliminates file path traversal vulnerabilities
- Centralized access control through database permissions

### Backup & Recovery
- Database backups automatically include all profile pictures
- Single backup file contains complete application state
- No need to separately backup uploads directory
- Simplified disaster recovery process

### Scalability
- Eliminates file synchronization issues in multi-instance deployments
- Works seamlessly with read replicas
- No shared file system required
- Easier horizontal scaling

### Deployment
- Simplified Docker configuration
- No volume mounts for user uploads
- Stateless application containers
- Easier to deploy to cloud platforms (AWS, Azure, GCP)

## Technical Details

### Data Format
Images are stored as base64-encoded strings and served as data URLs:
```
data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...
```

### Size Considerations
- Base64 encoding increases size by ~33%
- 5MB file limit remains (before encoding)
- Consider PostgreSQL's `TOAST` for large data
- Average profile picture: 100-500KB encoded

### Performance
- Database retrieval is fast for typical profile picture sizes
- Indexed queries perform well even with base64 data
- Consider caching strategies for high-traffic applications

## Backward Compatibility

- Old `photo_url` field maintained
- Existing file-based photos continue to work
- New uploads use database storage
- Frontend requires no changes

## Future Considerations

### Potential Enhancements
- Image optimization/compression before storage
- Multiple image sizes (thumbnail, full)
- CDN integration for caching
- Migration script for bulk photo conversion

### Database Maintenance
- Monitor database size growth
- Implement cleanup for deleted members
- Consider archiving old photos

## Rollback Procedure

If needed, to rollback to file-based storage:

1. Stop application
2. Restore previous code version
3. Existing photos in `/uploads` will still work
4. Database columns can remain (unused) or be dropped

## Testing

Test the following scenarios:
1. Upload new profile picture
2. View profile picture in tree
3. Edit member with profile picture
4. Delete member with profile picture
5. Export tree (CSV, PDF, JPEG)
6. Database backup and restore

## Support

For issues or questions, refer to:
- [USER_GUIDE.md](../USER_GUIDE.md) - User documentation
- [CHANGELOG.md](../CHANGELOG.md) - Version history
- GitHub Issues - Bug reports
