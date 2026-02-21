# Web Platform - User Guide v4.1.0

Complete user guide for the Web Platform Web Application.

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Authentication](#user-authentication)
3. [Managing Family Members](#managing-family-members)
4. [Working with Web Platforms](#working-with-web-platforms)
5. [Tree Visualization](#tree-visualization)
6. [Theme Customization](#theme-customization)
7. [Export Features](#export-features)
8. [Tree Views](#tree-views)
9. [Profile Pictures](#profile-pictures)
10. [Admin Portal](#admin-portal)
11. [Docker Management](#docker-management)
12. [Project Structure](#project-structure)
13. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Time Setup

**New in v4.0.2**: The application now supports custom branding! You can set your own application name during the initial setup.

1. **Admin Setup (First Deployment)**
   - When you first deploy the application, you'll be redirected to the setup wizard
   - Follow the 3-step wizard to create the admin account (see [Admin Portal](#admin-portal) section)
   - Set your custom application name (e.g., "Smith Family Heritage")
   - This name appears throughout the application (login page, headers, titles)

2. **Access the Application**
   - Open your web browser
   - Navigate to `http://localhost:8080`
   - You'll see the login/registration page with your custom app name

3. **Create Your Account**
   - Click "Register here" on the login page
   - Enter:
     - Username (unique identifier)
     - Email address (for recovery)
     - Password (secure, at least 8 characters recommended)
   - Click "Register"
   - You'll be automatically logged in

4. **Your Default Tree**
   - Upon first login, a default tree "My Web Platform" is created automatically
   - You're ready to start adding family members!

### System Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection
- JavaScript enabled

---

## User Authentication

### Logging In

1. Visit `http://localhost:8080`
2. Enter your username and password
3. Click "Login"
4. You'll be redirected to the main application

### Account Settings

Access account settings by clicking your username in the header.

#### Update Email
1. Click your username → Account Settings
2. Enter new email address
3. Click "Update Email"
4. Confirmation message appears

#### Change Password
1. Click your username → Account Settings
2. Enter new password
3. Confirm new password
4. Click "Change Password"
5. You'll be logged out and need to log in with new password

#### Delete Account
⚠️ **Warning**: This action is irreversible!

1. Click your username → Account Settings
2. Scroll to "Danger Zone"
3. Click "Delete Account"
4. Confirm deletion
5. All your trees and data will be permanently deleted

### Logout

Click the "Logout" button in the top-right corner.

---

## Managing Family Members

### Adding a Family Member

1. Click "Add Family Member" button (top of page)
2. Fill in the form:
   - **Required**: First Name, Last Name
   - **Optional**: Middle Name, Nickname, Gender, Birth Date, Death Date, Birth Place, Occupation, Biography
   - **Parents**: Select father and mother from dropdown (if applicable)
   - **Location**: Current City, State, Country
   - **Social Media**: Facebook, Instagram, Twitter, LinkedIn URLs
   - **Previous Partners**: Text field for relationship history
3. Click "Save"
4. The member appears in your tree

### Editing a Family Member

**Method 1: Context Menu (Right-Click)**
1. Right-click on any node in the tree
2. Select "Edit Member"
3. Update information in the modal
4. Click "Save"

**Method 2: Click Node**
1. Click on a node in the tree
2. Details panel opens on the right
3. Click "Edit" button
4. Update information
5. Click "Save"

### Viewing Member Details

**Method 1: Hover**
- Hover over any node to see a tooltip with:
  - Full name
  - Birth date
  - Death date (or "Living" status)

**Method 2: Click**
- Click on any node
- Detailed panel slides in from right showing:
  - All personal information
  - Biography
  - Social media links
  - Current location
  - Previous partners

**Method 3: Context Menu**
- Right-click on node
- Select "View Details"

### Deleting a Family Member

1. Click on the member's node
2. Details panel opens
3. Click "Delete" button (red)
4. Confirm deletion
5. ⚠️ Warning: This removes the member and their relationships

---

## Working with Web Platforms

### Creating Multiple Trees

You can create unlimited family trees (e.g., maternal side, paternal side, spouse's family).

1. Click the gear icon next to tree selector in header
2. Click "Create New Tree"
3. Enter tree name and description
4. Click "Create"
5. New empty tree is created and activated

### Switching Between Trees

1. Use the dropdown in the header
2. Select the tree you want to view
3. Tree loads immediately
4. All members from selected tree appear

### Copying a Tree

1. Click gear icon → Manage Trees
2. Find the tree you want to copy
3. Click "Copy" button
4. Enter new name for the copy
5. Click "Copy"
6. Entire tree with all members and relationships is duplicated

### Renaming a Tree

1. Click gear icon → Manage Trees
2. Find the tree to rename
3. Click "Rename" button
4. Enter new name and description
5. Click "Update"

### Deleting a Tree

⚠️ **Cannot delete your default tree**

1. Click gear icon → Manage Trees
2. Find tree to delete
3. Click "Delete" button
4. Confirm deletion
5. Tree and all members are permanently removed

### Sharing Trees

Share trees with other users for collaboration.

#### Share a Tree
1. Click gear icon → Manage Trees
2. Find tree to share
3. Click "Share" button
4. Enter recipient's username
5. Select permission:
   - **View**: Read-only access
   - **Edit**: Can add/edit/delete members
6. Click "Share"
7. Recipient receives invitation

#### Accept/Decline Share Invitations
1. Notification badge appears on share icon (if pending invitations)
2. Click share icon in header
3. Review pending invitations
4. Click "Accept" or "Decline"
5. Accepted trees appear in your tree selector

#### View Shared Trees
- Shared trees appear in tree dropdown with "[Shared]" indicator
- You have permissions granted by owner
- View-only means read-only access
- Edit permission allows full editing

---

## Tree Visualization

### Navigation

**Zoom Controls**
- **Zoom In**: Click + button in toolbar
- **Zoom Out**: Click - button in toolbar
- **Reset Zoom**: Click reset button in toolbar
- **Mouse Wheel**: Scroll to zoom in/out

**Pan (Move)**
- Click and drag on empty space
- Move tree around the viewport

### Node Colors

- **Blue Circle**: Male
- **Pink Circle**: Female
- **Gray Circle**: Other/Unknown

With profile pictures:
- Blue border for male
- Pink border for female
- Gray border for other/unknown

### Relationships

**Lines**
- **Solid Lines**: Parent-child relationships
- **Dashed Pink Lines**: Partner relationships
- **Red Highlighted Lines**: Active when highlighting descendants

### Context Menu (Right-Click)

Right-click on any node to access:
- **Highlight Descendants**: Show all descendants of this person
- **View Details**: Open details panel
- **Edit Member**: Open edit form
- **Export as JPEG**: Export tree with this member highlighted
- **Export as PDF**: Export tree with this member highlighted
- **Export as CSV**: Export entire tree data

### Highlight Descendants

Show a specific person and all their descendants.

**Method 1: Toolbar Dropdown**
1. Select person from "Highlight Descendants" dropdown
2. Tree highlights selected person and descendants
3. Other nodes fade out (low opacity)
4. Selected person has gold border
5. Click X button to clear highlight

**Method 2: Context Menu**
1. Right-click on any node
2. Select "Highlight Descendants"
3. Highlighting is applied

### Draggable Nodes

Customize your tree layout:
1. Click and hold any node
2. Drag to new position
3. Release to drop
4. Relationships maintained
5. Positions saved when you save a view

---

## Theme Customization

### Changing Themes

Choose from three theme options:

1. **System Default** (recommended)
   - Automatically matches your OS theme
   - Switches when you change OS settings
   - Dark mode at night, light mode during day

2. **Light Mode**
   - Bright, clean colors
   - High contrast for readability
   - Traditional appearance

3. **Dark Mode**
   - Dark backgrounds
   - Reduced eye strain
   - Low-light comfortable

### How to Change Theme

**Main Application:**
1. Look in header (top-right)
2. Find theme dropdown with moon/sun icon
3. Select: System, Light, or Dark
4. Theme changes instantly

**Admin Portal:**
1. Look in navigation bar
2. Find theme dropdown
3. Select preferred theme
4. Changes instantly

### Theme Persistence

- Your preference is saved automatically
- Persists across browser sessions
- Works on both main app and admin portal
- No login required to maintain preference

### Theme Features

- **Smooth Transitions**: 0.3s fade between themes
- **Complete Coverage**: All components themed
  - Headers and navigation
  - Forms and inputs
  - Tables and cards
  - Modals and dialogs
  - Context menus
  - Buttons and controls
- **Accessibility**: Maintains contrast ratios
- **No Performance Impact**: CSS variables only

---

## Export Features

### Export Tree as JPEG

**Method 1: Toolbar**
1. Click camera icon in diagram toolbar
2. Tree exports as JPEG image
3. File downloads automatically
4. Filename: `web_platform.jpeg`

**Method 2: Context Menu**
1. Right-click on any node
2. Select "Export as JPEG"
3. Tree exports with that person in context

### Export Tree as PDF

**Method 1: Toolbar**
1. Click PDF icon in diagram toolbar
2. Tree exports as PDF document
3. File downloads automatically
4. Filename: `web_platform.pdf`

**Method 2: Context Menu**
1. Right-click on any node
2. Select "Export as PDF"
3. Tree exports with that person in context

### Export Data as CSV

Export all member data for backup or migration.

**Method 1: Toolbar**
1. Click spreadsheet icon in diagram toolbar
2. CSV file downloads
3. Contains all member information
4. Filename: `web_platform.csv`

**Method 2: Context Menu**
1. Right-click on any node
2. Select "Export as CSV"
3. Full tree data exports

**CSV Format:**
- All fields included
- Special characters properly escaped
- Can be opened in Excel, Google Sheets
- Use for backups or data analysis

---

## Tree Views

Save different layouts of your tree.

### Creating a View

1. Arrange tree as desired (drag nodes, zoom, etc.)
2. Click "Manage Views" button
3. Enter view name and description
4. Check "Set as default" (optional)
5. Click "Save View"
6. Current layout is saved

### Loading a View

1. Use "View" dropdown selector (next to tree selector)
2. Select saved view name
3. Tree rearranges to saved layout
4. Zoom and positions restored

### Managing Views

1. Click "Manage Views" button
2. See all saved views with thumbnails
3. **Set Default**: Click radio button
4. **Update View**: Click "Update" to save current layout to existing view
5. **Delete View**: Click "Delete" to remove view

### Default View

- Auto-loads when you open the tree
- Only one default per tree
- Uncheck default to use automatic layout

---

## Profile Pictures

### Uploading Profile Pictures

1. Click on member's node
2. Details panel opens
3. Click "Edit" button
4. Find "Profile Picture" section
5. Click "Choose File"
6. Select image file (JPEG, PNG, GIF, WebP)
7. Max size: 5MB
8. Click "Save"
9. Picture appears on tree node

### Picture Display

- **Circular**: 40x40px on tree nodes
- **Bordered**: Color-coded by gender
  - Blue border: Male
  - Pink border: Female
  - Gray border: Other
- **Fallback**: Colored circle if no picture

### Removing Pictures

1. Edit member
2. Upload a blank/default image
3. Or delete and recreate member without picture

---

## Admin Portal

### Accessing Admin Portal

1. Navigate to `http://localhost:8080/static/admin-login.html`
2. Enter admin username and password
3. Click "Login"

### First-Time Admin Setup

**New in v4.0.2**: Beautiful 3-step setup wizard

If no admin exists, you'll be automatically redirected to the setup wizard:

**Step 1: Welcome**
- Introduction to the Web Platform
- Overview of what you'll configure
- Click "Get Started"

**Step 2: Create Admin Account**
1. **Application Name** (required)
   - Enter your custom application name
   - Examples: "Smith Web Platform", "Johnson Heritage", "Miller Family Archive"
   - This name appears throughout the application
   - 2-50 characters required
   - Default: "Web Platform"

2. **Admin Account Details**
   - Username (3+ characters)
   - Email address (valid format required)
   - Password (8+ characters, mix of letters/numbers/symbols)
   - Confirm Password (must match)
   - Real-time validation with error messages

3. Click "Create Account"

**Step 3: Success**
- Confirmation message
- Admin account created
- Custom app name saved
- Click "Go to Admin Login" to access the portal

### Dashboard

View system statistics:
- Total Users
- Active Users (last 30 days)
- Web Platforms
- Family Members
- Tree Views
- Tree Shares

**System Resources:**
- CPU usage, speed, cores
- Memory usage and availability
- Disk usage and space

**Services Status:**
- Web Application (running/stopped)
- PostgreSQL Database
- File Storage

**Application Updates:**
- Current version display
- Releases table with all available versions
- Update to newer versions
- Rollback to older versions

### User Management

**View Users:**
1. Click "Users" in navigation
2. See all registered users
3. View last login times
4. See admin status

**Create User:**
1. Click "Create New User"
2. Fill in form
3. Set admin privileges (optional)
4. Click "Create"

**Edit User:**
1. Find user in table
2. Click "Edit"
3. Update information
4. Toggle admin status
5. Activate/deactivate account
6. Click "Save"

**Delete User:**
1. Find user in table
2. Click "Delete"
3. Confirm deletion
4. ⚠️ Note: Cannot delete yourself

### Activity Logs

1. Click "Logs" in navigation
2. View all system activities
3. Filter by level: INFO, WARNING, ERROR
4. See timestamps, actions, users, IP addresses
5. Track security events

### Database Backups

**Create Backup:**
1. Click "Backups" in navigation
2. Click "Create Backup"
3. Backup runs immediately
4. See confirmation message
5. Backup stored in backups directory

**View Backups:**
- List all backups
- See filename, size, status
- Creation timestamps
- Backup type

### Application Updates

**New in v4.0.2**: Multi-version update and rollback system

**View Available Releases:**
1. Click "Updates" in the admin dashboard
2. The releases table displays:
   - Version number (e.g., v4.0.2)
   - Release date
   - Status (Current, Newer, Older)
   - Action buttons (Update/Rollback)

**Update to Newer Version:**
1. Find the desired version in the releases table
2. Click the "Update" button (blue, with download icon)
3. System generates an update script
4. Two update modes available:

   **Manual Mode (Default - Recommended):**
   - Download the generated bash script
   - Run script from Docker host: `bash update_to_vX.X.X.sh`
   - Script performs:
     - Stops containers
     - Pulls new Docker image from Docker Hub
     - Updates docker-compose.yml
     - Restarts containers
     - Runs database migrations

   **Automatic Mode (Advanced - Requires Docker Socket):**
   - Uncomment Docker socket mount in docker-compose.yml
   - Click "Install Update" in admin portal
   - Update runs automatically inside container
   - ⚠️ Warning: Gives container access to Docker daemon

5. Wait for update to complete
6. Reload admin portal
7. Verify new version in dashboard

**Rollback to Previous Version:**
1. Find the older version in the releases table
2. Click the "Rollback" button (yellow, with counterclockwise icon)
3. Follow same process as update
4. System installs the older version
5. Database migrations are idempotent (safe to run multiple times)

**Update Safety:**
- Database persists across updates (stored in Docker volume)
- All data remains intact during version changes
- SQL migrations handle schema changes
- No data loss when updating or rolling back

**Troubleshooting Updates:**
- If update fails, containers remain in previous state
- Check Docker logs: `docker-compose logs -f web`
- Verify Docker Hub image exists for target version
- Ensure internet connection for image download
- Manual mode is safer for production environments

---

## Docker Management

### Managing Containers

**View Running Containers**
```bash
docker-compose ps
```

**Rebuild After Code Changes**
```bash
docker-compose up -d --build
```

**View Application Logs**
```bash
# All logs
docker-compose logs -f

# Web application logs only
docker-compose logs -f web

# Database logs only
docker-compose logs -f db
```

**Access Container Shell**
```bash
# Web application container
docker-compose exec web bash

# Database container
docker-compose exec db bash
```

**Access PostgreSQL Database**
```bash
docker-compose exec db psql -U postgres -d webapp
```

**Stop Containers**
```bash
# Stop containers (data persists)
docker-compose down

# Stop and remove all data
docker-compose down -v
```

**Restart Containers**
```bash
# Restart all containers
docker-compose restart

# Restart specific container
docker-compose restart web
docker-compose restart db
```

### Volume Management

**View Volumes**
```bash
docker volume ls
```

**Backup Database Volume**
```bash
# Create backup
docker-compose exec db pg_dump -U postgres webapp > backup.sql

# Restore from backup
docker-compose exec -T db psql -U postgres webapp < backup.sql
```

**Clean Up Docker**
```bash
# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a
```

### Troubleshooting Docker Issues

**Port Already in Use**
```bash
# Check what's using port 8080
lsof -i :8080

# Change port in docker-compose.yml
ports:
  - "8081:8000"  # Changed from 8080
```

**Database Connection Issues**
```bash
# Check database is running
docker-compose ps db

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

**Container Won't Start**
```bash
# View logs for errors
docker-compose logs web

# Rebuild from scratch
docker-compose down
docker-compose up -d --build
```

---

## Project Structure

```
my-web-app/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication utilities
│   └── routers/
│       ├── auth.py          # Authentication endpoints
│       ├── web_platform.py   # Family member endpoints
│       ├── web_platforms.py  # Multi-tree management endpoints
│       ├── tree_views.py    # Tree views endpoints
│       └── admin.py         # Admin portal endpoints
├── static/
│   ├── index.html           # Main application page
│   ├── styles.css           # Main CSS styling with theme variables
│   ├── app.js               # Frontend JavaScript (D3.js visualization)
│   ├── admin-login.html     # Admin login page
│   ├── admin.html           # Admin dashboard
│   ├── admin-styles.css     # Admin portal CSS
│   └── admin.js             # Admin dashboard JavaScript
├── migrations/
│   ├── 001_add_tree_views.sql        # Tree views feature
│   ├── 002_add_additional_fields.sql # Extra member fields
│   ├── 003_add_node_positions.sql    # Draggable nodes
│   ├── 004_add_admin_features.sql    # Admin portal
│   ├── 005_add_view_thumbnails.sql   # View thumbnails
│   ├── 006_add_web_platforms.sql      # Multi-tree support
│   └── 007_fix_multi_tree_data.sql   # Data migration fixes
├── uploads/
│   └── profile_pictures/    # Uploaded profile images
├── backups/                 # Database backups
├── .github/
│   └── workflows/           # GitHub Actions CI/CD workflows
├── Dockerfile               # Docker container configuration
├── docker-compose.yml       # Docker Compose orchestration
├── requirements.txt         # Python dependencies
├── CHANGELOG.md            # Version history
├── USER_GUIDE.md           # This file
└── README.md               # Project overview
```

### Key Files Explained

**Backend (Python/FastAPI)**
- `app/main.py` - Application entry point, API routes registration
- `app/database.py` - PostgreSQL connection and session management
- `app/models.py` - Database models (User, User, SystemLog, AppConfig, etc.)
- `app/schemas.py` - Request/response validation schemas
- `app/auth.py` - JWT token generation and validation

**Frontend (HTML/CSS/JavaScript)**
- `static/index.html` - Main application UI
- `static/styles.css` - Theme system with CSS variables
- `static/app.js` - D3.js tree visualization, API calls
- `static/admin.html` - Admin dashboard UI
- `static/admin.js` - Admin functionality (users, backups, updates)

**Database**
- `migrations/` - SQL migration files for schema changes
- PostgreSQL 14 - Relational database for all data

**Container Configuration**
- `Dockerfile` - Python 3.11-slim with FastAPI dependencies
- `docker-compose.yml` - Multi-container setup (web + database)

---

## Troubleshooting

### Login Issues

**Problem**: Cannot log in
- Check username and password (case-sensitive)
- Clear browser cache and cookies
- Try different browser
- Verify application is running: `docker-compose ps`

**Problem**: Forgot password
- Contact administrator for password reset
- Admin can reset via User Management

### Tree Not Displaying

**Problem**: Tree appears empty
- Check tree selector - ensure correct tree selected
- Verify tree has members
- Try refreshing page (F5)
- Check browser console for errors (F12)

**Problem**: Nodes missing
- Ensure members have valid relationships
- Check if filter is active
- Try resetting view

### Performance Issues

**Problem**: Slow loading
- Large trees (>100 members) may load slower
- Clear browser cache
- Close unnecessary browser tabs
- Reduce zoom level

**Problem**: Lag when dragging
- Large trees can be slow to drag
- Save view after arranging
- Use reset zoom to recenter

### Export Issues

**Problem**: PDF export not working
- Check browser allows pop-ups
- Verify enough disk space
- Try JPEG export instead
- Check browser console for errors

**Problem**: CSV export incomplete
- Verify all members visible
- Check no filters active
- Try exporting from different browser

### Profile Picture Issues

**Problem**: Picture not uploading
- Check file size (<5MB)
- Verify file format (JPEG, PNG, GIF, WebP)
- Try smaller image
- Check internet connection

**Problem**: Picture not displaying
- Hard refresh (Ctrl+Shift+F5)
- Clear browser cache
- Re-upload image
- Check uploads directory permissions

### Theme Issues

**Problem**: Theme not changing
- Hard refresh page (Ctrl+Shift+F5)
- Clear localStorage
- Try different browser
- Check browser JavaScript enabled

**Problem**: Theme not persisting
- Check browser allows localStorage
- Verify not in incognito/private mode
- Check browser settings

### Admin Portal Issues

**Problem**: Cannot access admin portal
- Verify you have admin privileges
- Check login credentials
- Contact another administrator

**Problem**: Updates not working
- Check internet connection
- Verify GitHub repository configured
- Check server logs
- Ensure sufficient disk space

### Docker/Container Issues

**Problem**: Application won't start
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs web
docker-compose logs db

# Restart containers
docker-compose restart

# Full rebuild
docker-compose down
docker-compose up -d --build
```

**Problem**: Database connection error
```bash
# Check database is running
docker-compose ps db

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Getting Help

1. **Check Logs**: View application logs for errors
   ```bash
   docker-compose logs -f web
   ```

2. **Check Documentation**:
   - README.md for setup
   - CHANGELOG.md for version changes
   - RELEASE_PROCESS.md for deployment

3. **GitHub Issues**: Report bugs at repository issues page

4. **Admin Logs**: Check activity logs in admin portal

5. **Browser Console**: Press F12 to see JavaScript errors

---

## Tips and Best Practices

### Data Management
- **Regular Backups**: Export CSV periodically
- **Save Views**: Save different arrangements before experimenting
- **Multiple Trees**: Separate trees for different family branches
- **Test Branch**: Use for experimenting before production changes

### Performance
- **Limit Tree Size**: Very large trees (200+ members) may be slow
- **Use Views**: Save views instead of constant rearranging
- **Close Unused Tabs**: Reduces browser memory usage

### Security
- **Strong Passwords**: Use unique, complex passwords
- **Regular Updates**: Install updates when available
- **Backup Before Updates**: Admin portal does this automatically
- **Limit Admin Access**: Only trusted users should be admins

### Collaboration
- **Share Wisely**: Only share with people you trust
- **Use View-Only**: When possible, use view-only permissions
- **Communicate**: Tell collaborators about changes
- **Tree Per Branch**: Separate trees for better organization

---

## Keyboard Shortcuts

*Note: No built-in keyboard shortcuts at this time. Use mouse/touch for all interactions.*

---

## Version Information

**Current Version**: 4.0.0
**Release Date**: January 22, 2026
**Supported Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

---

## Additional Resources

- **README.md**: Installation and setup
- **CHANGELOG.md**: Version history and changes
- **RELEASE_PROCESS.md**: For administrators managing releases
- **UPDATE_GUIDE.md**: Detailed update instructions
- **ADMIN_ACCESS_GUIDE.md**: Admin portal documentation

---

**Need more help?** Check the GitHub repository or contact your administrator.
