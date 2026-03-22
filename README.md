# IP Management Tool — Web Edition

A Flask-based web application for managing IPv4 network records.
Accessible from any browser on your local network.

## Features

- User authentication (login / logout)
- Add, edit, delete IP records
- Real-time search and status filter
- Multi-column sorting
- Bulk import (CSV, JSON) with conflict detection
- Export visible records (CSV or JSON)
- Deleted-records recovery
- Automatic and manual backups
- Accessible on LAN from any device

## Requirements

- Python 3.8 or later
- Internet connection on first run (to install Flask)

## Quick Start

### Windows

Double-click **`START.bat`**

The script will:
1. Check Python is installed
2. Create a virtual environment (`.venv/`)
3. Install Flask automatically
4. Open your browser to `http://localhost:5000`
5. Start the server

### Manual

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in your browser.

## Default Login

| Username | Password  |
|----------|-----------|
| admin    | admin123  |

> Change your password after the first login.

## Project Structure

```
web/
├── app.py                  # Flask server + REST API
├── modules/
│   ├── auth.py             # User authentication
│   ├── ip_manager.py       # CRUD + JSON persistence
│   ├── validator.py        # IP / subnet validation
│   ├── search.py           # Search, filter, sort
│   ├── backup.py           # Backup + soft-delete recovery
│   ├── import_export.py    # CSV / JSON bulk import/export
│   └── logger.py           # File + console logging
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   ├── index.html          # Main UI
│   └── login.html          # Login page
├── data/                   # Created on first run (gitignored)
│   ├── ip_data.json
│   ├── users.json
│   └── backups/
├── logs/                   # Created on first run (gitignored)
├── requirements.txt
└── START.bat
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/records` | List records (search, filter, sort) |
| POST | `/api/records` | Add record |
| PUT | `/api/records/<index>` | Update record |
| POST | `/api/records/delete` | Delete records by index list |
| GET | `/api/summary` | Count by status |
| POST | `/api/import` | Preview import file |
| POST | `/api/import/confirm` | Commit import |
| GET | `/api/export` | Download CSV or JSON |
| POST | `/api/backup` | Create manual backup |
| GET | `/api/deleted` | List deleted records |
| POST | `/api/deleted/<index>/recover` | Recover deleted record |
| GET | `/api/users` | List users (admin only) |
| POST | `/api/users` | Create user (admin only) |
| DELETE | `/api/users/<username>` | Delete user (admin only) |
| PUT | `/api/users/password` | Change own password |

## Data Storage

Records are stored in `data/ip_data.json`.
Each record has: `ip`, `subnet`, `hostname`, `description`, `status`, `added_on`.

Valid status values: `Active`, `Inactive`, `Reserved`

## LAN Access

The server binds to `0.0.0.0:5000` — accessible from any device on your network.
Check the console output for the network IP address after starting.
