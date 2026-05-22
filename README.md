# Recycle-IT!

A Django-based middleware system for [Recycle-IT! CIC](https://www.recycle-it.org.uk), a Bolton-based circular economy organisation. This platform replaces manual workflows (PDF forms, spreadsheets, Google Maps routing, manual CO₂ calculations) with an integrated digital system for managing IT equipment donations and collections.

> **Note — Viva/Demo Branch:** This branch (`viva`) is configured with SQLite and includes a pre-seeded database (`db.sqlite3`) with realistic sample data for demonstration purposes. No database setup is required — just install dependencies, configure the `.env` file, and run the server. The production branch (`dev`) uses MySQL.

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
| Database | SQLite (viva branch) / MySQL via `mysqlclient` (dev branch) |
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
├── .env                    # Pre-configured for viva demo (SQLite, ORS key included)
├── db.sqlite3              # Pre-seeded SQLite database with demo data
├── requirements.txt
├── manage.py
└── PopulateData.py         # Script to reset and re-seed the database with sample data
```

---

## Quick Start (Viva Branch)

### Prerequisites

- Python 3.11+
- An [OpenRouteService API key](https://openrouteservice.org/) (already configured in `.env`)

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

### 3. Start the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

The pre-seeded database is already included — no migrations or setup required.

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

---

## Key Design Decisions

**Email-based authentication** — Django's auth machinery expects a `username` field, but this system authenticates via email. The custom `EmailBackend` in `core/backends.py` handles this by accepting `username` in the signature and looking it up as an email in the database. `AuthService.create_user()` sets both `username` and `email` to the same value to keep the system consistent.

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
| `viva` | Demo branch — SQLite, pre-seeded database |

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `ORS_API_KEY` | OpenRouteService API key |
| `EMAIL_HOST_USER` | Gmail address for outbound email |
| `GMAIL_APP_PASSWORD` | Gmail app password |
| `DEFAULT_FROM_EMAIL` | From address used in sent emails |

> **Note:** Database variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) are not required on the viva branch as SQLite is used. These are required on the `dev` branch for MySQL.