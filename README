# Recycle-IT!

A Django-based middleware system for [Recycle-IT! CIC](https://www.recycle-it.org.uk), a Bolton-based circular economy organisation. This platform replaces manual workflows (PDF forms, spreadsheets, Google Maps routing, manual CO₂ calculations) with an integrated digital system for managing IT equipment donations and collections.

---

## Overview

Recycle-IT! serves two user types:

- **Public donors** — submit IT equipment collection requests via an online form
- **Internal staff** — review, approve, and schedule collections through a dedicated dashboard

Core capabilities include donation intake, staff review workflows, optimised route planning via the OpenRouteService API, CO₂ emissions tracking, and a KPI dashboard.

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend framework | Django 6.x |
| REST API | Django REST Framework |
| Database | MySQL (via `mysqlclient`) |
| Route optimisation | OpenRouteService (VROOM + Directions API) |
| Environment config | `python-decouple` |
| Python | 3.14 |

---

## Project Structure

```
recycle_it/
├── core/
│   ├── models.py           # User, Donor, Donation, Item, Collection, EmissionRecord, SystemSettings
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── backends.py         # Custom email-based authentication backend
│   ├── tests.py
│   ├── test_runner.py      # Custom timed test runner with per-test stats
│   └── services/
│       ├── auth_service.py
│       ├── donation_service.py
│       ├── collection_service.py
│       ├── route_service.py        # ORS VROOM + Directions API integration
│       └── emissions_service.py
├── templates/
│   └── core/               # HTML templates for all views
├── static/
│   └── css/                # Stylesheets (base, staff, donor)
├── recycle_it/             # Django project settings, URLs, WSGI/ASGI
├── .env_example            # Environment variable template
├── requirements.txt
├── manage.py
└── PopulateData.py         # Script to seed the database with sample data
```

---

## Setup

### Prerequisites

- Python 3.11+
- MySQL server running locally
- An [OpenRouteService API key](https://openrouteservice.org/)

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd recycle_it
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `mysqlclient` requires MySQL development headers. On Ubuntu/Debian: `sudo apt-get install libmysqlclient-dev`. The `requirements.txt` lists `PyMySQL` as an alternative if needed.

### 3. Configure environment variables

Copy `.env_example` to `.env` and fill in your values:

```bash
cp .env_example .env
```

```ini
SECRET_KEY=your_secret_key_here
DEBUG=True

DB_NAME=recycle_it
DB_USER=recycle_it_user
DB_PASSWORD=your_db_password_here
DB_HOST=localhost
DB_PORT=3306

ORS_API_KEY=your_ors_api_key_here

EMAIL_HOST_USER=your_email@example.com
GMAIL_APP_PASSWORD=your_gmail_app_password_here
DEFAULT_FROM_EMAIL=your_email@example.com
```

### 4. Set up the MySQL database

```sql
CREATE DATABASE recycle_it CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'recycle_it_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON recycle_it.* TO 'recycle_it_user'@'localhost';

-- Required for running tests:
GRANT ALL PRIVILEGES ON test_recycle_it.* TO 'recycle_it_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a staff user

Always create users through `AuthService` to ensure email-based login is set up correctly:

```bash
python manage.py shell
```

```python
from core.services.auth_service import AuthService
AuthService.create_user(email="admin@example.com", password="yourpassword", is_admin=True)
```

> **Important:** Do not use `createsuperuser` directly — it bypasses `AuthService` and will result in a login that does not work with the custom email authentication backend.

### 7. (Optional) Seed sample data

```bash
python PopulateData.py
```

### 8. Start the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

---

## Running Tests

The project uses a custom `TimedTestRunner` that reports per-test timing, pass/fail rates, and aggregate stats.

```bash
python manage.py test
```

---

## Key Design Decisions

**Email-based authentication** — Django's auth machinery expects a `username` field, but this system authenticates via email. The custom `EmailBackend` in `core/backends.py` handles this by accepting `username` in the signature and looking it up as an email in the database.

**Geocoding at submission time** — Donor addresses (`street_address`, `city`, `postcode`) are geocoded when the donation form is submitted, with coordinates persisted on the `Donation` model. This avoids re-geocoding at route optimisation time.

**ORS route optimisation** — The VROOM endpoint is used for stop ordering. Because VROOM responses do not include road distances, a separate Directions API call retrieves actual road distances, with a duration-based fallback at 50 km/h.

**Service layer** — Business logic is encapsulated in `core/services/` rather than in views, keeping views thin and making the logic independently testable.

---

## Git Branches

| Branch | Purpose |
|---|---|
| `master` | Original baseline, preserved as submitted |
| `dev` | Active development |

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `DB_NAME` | MySQL database name |
| `DB_USER` | MySQL username |
| `DB_PASSWORD` | MySQL password |
| `DB_HOST` | Database host (default: `localhost`) |
| `DB_PORT` | Database port (default: `3306`) |
| `ORS_API_KEY` | OpenRouteService API key |
| `EMAIL_HOST_USER` | Gmail address for outbound email |
| `GMAIL_APP_PASSWORD` | Gmail app password |
| `DEFAULT_FROM_EMAIL` | From address used in sent emails |