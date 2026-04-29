# Hybrid Cloud Data Deduplication System

## 📌 Project Overview
A cloud storage system that automatically detects and eliminates duplicate files using MD5 hashing. Built with Django and hybrid cloud architecture.

## 🎯 Problem Statement
Organizations waste 60-80% of storage space on duplicate files. When multiple users upload the same file, traditional systems store multiple copies. This project solves that problem.

HOW IT WORKS:

1. User uploads a file

2. System generates MD5 hash (unique fingerprint)

3. System checks if hash exists in database

4. TWO POSSIBILITIES:

   → DUPLICATE file:
      - Create reference only
      - No extra storage used

   → NEW file:
      - Store file in cloud
      - Save hash in database

5. Upload completes successfully

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python Django |
| **Database** | SQLite |
| **Public Cloud** | ownCloud |
| **Frontend** | HTML, CSS, Bootstrap, JavaScript |
| **Hashing Algorithm** | MD5 |

## ✨ Key Features

### For Users
- ✅ **Register/Login** - Secure authentication with session management
- ✅ **File Upload** - Automatic duplicate detection using MD5 hashing
- ✅ **File Download** - Download your files anytime
- ✅ **File Search** - Real-time AJAX search
- ✅ **File Sharing** - Share files with other users via unique tokens
- ✅ **Support Tickets** - Raise issues and track status
- ✅ **Feedback** - Submit feedback to admin
- ✅ **Storage Analytics** - View usage with charts

### For Admin
- ✅ **Dashboard** - View system statistics (users, files, storage, tickets)
- ✅ **User Management** - View and delete users
- ✅ **Feedback Management** - View all user feedback
- ✅ **Ticket Management** - Update ticket status and respond to users


PRIVATE CLOUD
(Django Server + SQLite)

Stores Sensitive Data:
• User credentials and profiles
• MD5 hashes for deduplication
• File ownership mappings (user_file_map)
• Share links and permissions
• Support tickets and notifications

----------------------------------------

Only unique files are sent to Public Cloud

----------------------------------------

PUBLIC CLOUD
(ownCloud)

Stores Encrypted File Data Only:
• No user information
• No MD5 hashes
• No metadata

## 🗄️ Database Schema

| Table | Purpose |
|-------|---------|
| `user_login` | User authentication (username, password, type) |
| `user_details` | User profile information |
| `storage_details` | User storage quota (15GB limit) |
| `file_index` | File metadata and MD5 hashes (DEDUPLICATION CORE) |
| `user_file_map` | Maps users to files (many-to-many relationship) |
| `support_ticket` | User support requests |
| `notification` | User notifications |
| `feedback` | User feedback messages |
| `SharedLink` | File sharing tokens and permissions |

## 👥 User Roles

| Role | Capabilities |
|------|--------------|
| **Admin** | Manage users, view all feedback, handle tickets, dashboard analytics |
| **User** | Upload/download files, share files, raise tickets, give feedback |

## 🔒 Security Features

- Session-based authentication
- CSRF protection (Django default)
- File scanning for malware (PHP webshells, SQL injection, etc.)
- Private cloud for sensitive metadata
- Unique tokens for file sharing

## 📊 Storage Quota

- Each user gets **15GB** storage quota
- Quota is tracked in `storage_details` table
- Files are deduplicated - same file uploaded by multiple users counts once

📸 Screenshots: Check the [`/screenshots`](screenshots/) folder for all website screenshots

Video Demo:[Watch demo](Screen Recording 2026-04-28 211430.mp4)

## 🚀 How to Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/emil0512/Hybrid-cloud-deduplication.git

# 2. Navigate to project directory
cd Hybrid-cloud-deduplication

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations
python manage.py migrate

# 5. Create superuser (admin)
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver

🔮 Future Enhancements
Block-level deduplication (for partial file changes)

End-to-end encryption for files

Mobile app (Android/iOS)

Integration with AWS S3 instead of ownCloud

Password hashing (security improvement)


