# TrackPro Account Page Integration Guide

This guide shows how to integrate the standalone account page into your existing TrackPro application.

## Quick Integration

### 1. Add Account Page to Main Menu

```python
# In your main window or menu bar code
from trackpro.ui.standalone_account_page import AccountPage

def show_account_page(self):
    """Show the account settings page."""
    self.account_page = AccountPage(self)
    self.account_page.show()

# Add menu item
account_action = QAction("Account Settings", self)
account_action.triggered.connect(self.show_account_page)
settings_menu.addAction(account_action)
```

### 2. Add Account Page as Tab

```python
# In a tabbed interface
from trackpro.ui.standalone_account_page import AccountPage

# Add to tab widget
account_page = AccountPage(self)
tab_widget.addTab(account_page, "Account")
```

### 3. Add Account Page to System Tray

```python
# In your system tray menu
from trackpro.ui.standalone_account_page import AccountPage

def show_account_settings(self):
    if not hasattr(self, 'account_window'):
        self.account_window = AccountPage()
    self.account_window.show()
    self.account_window.raise_()
    self.account_window.activateWindow()

# Add to tray menu
account_action = QAction("Account Settings", self)
account_action.triggered.connect(self.show_account_settings)
tray_menu.addAction(account_action)
```

## Features Included

✅ **Profile Management**
- First/Last Name, Display Name (required fields)
- Email management (read-only for existing users)
- Date of Birth and Gender selection
- Bio text area
- Profile picture upload (with file validation)

✅ **Data Sharing Control**
- Checkbox to enable/disable data sharing
- Visual status indicator (🟢 Active / 🔴 Disabled)
- Test button to verify data flow control
- Warning dialog when disabling data sharing

✅ **Account Security**
- Password change for password-based users
- OAuth user detection and handling
- Conditional UI based on authentication method

✅ **Account Actions**
- Secure logout with confirmation
- Account deletion with double confirmation
- Proper data cleanup on deletion

✅ **Database Integration**
- Connects to existing `user_details` and `user_profiles` tables
- Secure data loading with authentication checks
- Prevents cross-user data leakage
- Upsert operations for data consistency

✅ **Security Features**
- Authentication validation before data access
- User ID validation in all database operations
- Error handling and logging
- OAuth user support

## Database Schema Requirements

The account page expects these tables to exist:

```sql
-- user_details table
CREATE TABLE user_details (
    user_id UUID PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    date_of_birth DATE,
    gender TEXT,
    share_data BOOLEAN DEFAULT true
);

-- user_profiles table  
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    bio TEXT,
    share_data BOOLEAN DEFAULT true,
    preferences JSONB
);
```

## Configuration

### Required Dependencies

```python
# These should already be available in TrackPro
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ..database import supabase_client  # Your existing Supabase client
```

### Environment Setup

Make sure your Supabase client is properly configured:

```python
# The account page expects this import to work:
from ..database import supabase_client

# And these methods to be available:
supabase = supabase_client.get_supabase_client()
user = supabase.client.auth.get_user()
```

## Customization

### Styling

The account page uses Nord theme colors by default. You can customize the styling by modifying:

- `get_input_style()` - Input field styling
- `get_button_style()` - Button styling  
- Group box styles in each section

### Data Flow Control

The `update_data_sharing_setting()` method is where you can add your telemetry flow control logic:

```python
def update_data_sharing_setting(self, share_data):
    # Add your telemetry control logic here
    if share_data:
        # Enable telemetry collection
        self.enable_telemetry_collection()
    else:
        # Disable telemetry collection
        self.disable_telemetry_collection()
```

### Profile Picture Upload

Currently the profile picture selection is implemented but upload to storage is marked as TODO. To complete this:

```python
def choose_profile_picture(self):
    # ... existing file selection code ...
    
    if file_path:
        # Add your storage upload logic here
        upload_url = self.upload_to_storage(file_path)
        if upload_url:
            # Save the URL to user profile
            self.save_profile_picture_url(upload_url)
```

## Testing

Run the test script to verify the account page works:

```bash
python test_account_page.py
```

This will show the account page in a standalone window for testing UI and functionality.

## Error Handling

The account page includes comprehensive error handling:

- Database connection failures
- Authentication failures  
- Validation errors
- File upload errors
- Network timeouts

All errors are logged and user-friendly messages are displayed.

## Security Considerations

🔒 **Built-in Security Features:**

- User ID validation in all database operations
- Authentication checks before data access
- Cross-user data leakage prevention
- Secure password handling
- OAuth user support

🛡️ **Additional Recommendations:**

- Enable Row Level Security (RLS) in Supabase
- Use HTTPS for all API calls
- Implement rate limiting for sensitive operations
- Regular security audits of user data access

## Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Verify your Supabase configuration
3. Ensure the database schema matches requirements
4. Test with the standalone test script first

The account page is designed to be robust and will gracefully handle most error conditions while protecting user data. 