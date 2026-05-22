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
| Backend framework | Django 6.0.4 |
| Database | MySQL via `mysqlclient` |
| Route optimisation | OpenRouteService (Geocoding + VROOM + Directions API) |
| Environment config | `python-decouple` |
| Python | 3.11+ |

---

## Project Structure

```
recycle_it/
├── core/
│   ├── models.py           # User, Donor, Donation, Item, Collection, EmissionRecord, SystemSettings
│   ├── views.py            # Thin views — request handling and routing only
│   ├── forms.py            # Login, donation submission, collection, user and settings forms
│   ├── urls.py             # URL routing for all app features
│   ├── admin.py
│   ├── backends.py         # Custom email-based authentication backend
│   ├── tests.py            # Unit test suite (service layer)
│   ├── test_runner.py      # Custom timed test runner with per-test stats
│   └── services/
│       ├── auth_service.py         # User creation, editing, deletion, verification
│       ├── donation_service.py     # Donation intake, approval workflow, email notifications
│       ├── collection_service.py   # Collection scheduling and donation assignment
│       ├── route_service.py        # ORS Geocoding + VROOM + Directions API integration
│       └── emissions_service.py    # CO₂ calculation using configurable SystemSettings
├── templates/
│   └── core/               # HTML templates for all views (16 pages, 2 base templates)
├── static/
│   └── css/                # Stylesheets (base, staff portal, donor form)
├── recycle_it/             # Django project settings, URLs, WSGI/ASGI
├── .env_example            # Environment variable template
├── .env                    # Pre-configured environment file
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

### 1. Create and activate a virtual environment

```bash
cd recycle_it
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `mysqlclient` requires MySQL development headers. On Ubuntu/Debian: `sudo apt-get install libmysqlclient-dev`.

### 3. Configure environment variables

The `.env` file is included and pre-configured. If you need to adjust any values, copy `.env_example` as a reference:

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

### 6. Seed sample data

```bash
python PopulateData.py
```

### 7. Start the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

---

## Demo Login Credentials

| Email | Password | Role |
|---|---|---|
| `admin@recycle-it.org.uk` | `Admin1234!` | Admin |
| `sarah.malik@recycle-it.org.uk` | `Staff1234!` | Staff |

---

## Resetting Demo Data

To wipe and re-seed the database with fresh sample data:

```bash
python PopulateData.py --reset
```

To seed without wiping existing data:

```bash
python PopulateData.py
```

---

## Running Tests

The project uses a custom `TimedTestRunner` that reports per-test timing, pass/fail rates, and aggregate stats.

```bash
python manage.py test
```

> **Note:** The test database (`test_recycle_it`) requires the explicit MySQL grant shown in step 4.

---

## Key Design Decisions

**Email-based authentication** — Django's auth machinery expects a `username` field, but this system authenticates via email. The custom `EmailBackend` in `core/backends.py` handles this by accepting `username` in the signature and looking it up as an email in the database. `AuthService.create_user()` sets both `username` and `email` to the same value to keep the system consistent.

> **Important:** Do not use `createsuperuser` directly — it bypasses `AuthService` and will result in a login that does not work with the custom email authentication backend.

**Geocoding at submission time** — Donor addresses (`street_address`, `city`, `postcode`) are geocoded via the ORS Geocoding endpoint when the donation form is submitted, with coordinates persisted on the `Donation` model. This avoids re-geocoding at route optimisation time.

**ORS route optimisation** — Three separate ORS endpoints are used: Geocoding (address → coordinates at submission), VROOM (optimised stop ordering), and Directions (actual road distance in km, since VROOM responses do not include distance). A duration-based fallback at 50 km/h is used if the Directions call fails, and a manual fallback is available if ORS is entirely unavailable.

**Service layer** — All business logic is encapsulated in `core/services/` rather than in views. Views are kept deliberately thin — they receive a request, call the relevant service method, and return a response. This keeps the logic independently testable and the codebase maintainable.

**Configurable emissions formula** — CO₂ per litre and fuel efficiency values are stored in `SystemSettings` rather than hardcoded, allowing staff to update them via the KPI dashboard without touching the codebase.

---

## Git Branches

| Branch | Purpose |
|---|---|
| `master` | Original baseline, preserved as submitted |
| `dev` | Active development — MySQL configuration |
| `viva` | Viva/demo branch |

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