# RentNear

Peer-to-peer item rental marketplace. Implements US-01 authentication, US-02 item listings, US-03 search and filters, US-04 bookings, and US-05 mock payment holds.

Stack: React + Vite, Django REST Framework, PostgreSQL.

## Setup

Python 3.9+ and Node.js 18+ are required. PostgreSQL must be running. The app does not fall back to SQLite.

```bash
createdb rentnear
createuser rentnear
psql -c "ALTER USER rentnear WITH PASSWORD 'rentnear';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE rentnear TO rentnear;"
```

Adjust the database name, user, and password in `backend/.env` if yours differ. The database role needs permission to create a test database (`CREATEDB`) so `manage.py test` can run.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The API is http://localhost:8000.

## Auth API

- `POST /api/auth/register` — name, email, password, optional phone
- `POST /api/auth/login` — email, password
- `POST /api/auth/logout` — `Authorization: Token <token>`
- `GET /api/auth/me` — current user

Passwords are hashed by Django. The React app stores the token in `localStorage` and sends it on authenticated requests. `/` is the public marketplace. Creating/editing listings and My Listings require login. `/login` and `/register` are public.

## Sprint 2

Available: public browse/details, authenticated listing creation, My Listings, owner-only editing/deletion, availability controls, multi-photo uploads/previews, and combined keyword/category/location/price filters. Categories are free text with suggestions. Photos are optional: maximum 8 JPEG/PNG/WebP images, 5 MB each, validated by the backend. Payments and booking workflows remain outside this sprint.

For an existing installation, install updated backend requirements and run `python manage.py migrate`; do not recreate the database or overwrite `.env`.

Start in separate terminals:

```bash
cd /Users/mac/Desktop/RentNear-Dev/backend
source .venv/bin/activate
python manage.py runserver
```

```bash
cd /Users/mac/Desktop/RentNear-Dev/frontend
npm run dev
```

Verification:

```bash
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
backend/.venv/bin/python backend/manage.py test accounts marketplace --noinput
cd frontend
npm run build
```

Django tests require permission to create a separate PostgreSQL test database. The existing application role lacks CREATEDB; Sprint 2's 18 tests passed on a temporary isolated PostgreSQL 18 cluster without changing that role or the application database. The existing accounts tests cover registration, login and logout.

Uploads reside in ignored `backend/media/`. Django serves them locally in DEBUG mode; production must serve MEDIA_ROOT at MEDIA_URL through its web server. Removing image records currently leaves files on disk; media cleanup remains an operational limitation.


## Sprint 3: bookings and mock holds

Item details include inclusive start/end dates, an estimated total, and booked-date ranges. `/my-bookings` shows both rentals you made and bookings for your items, with booking and mock-payment statuses. Logging in from an item returns you to that item.

Rules:
- Start must be today or later; end must be on/after start. The end day is charged and reserved (a same-day rental costs one day). Calendar cutoffs use the server's UTC date.
- Only authenticated non-owners can book an available item. Pending/confirmed bookings block overlapping dates. Creation and state transitions lock the item row in a PostgreSQL transaction, protecting concurrent requests. Booking and payment creation either both succeed or both roll back.
- Rental totals are calculated from the stored item price and remain fixed after booking.
- Each new booking is confirmed with a **Held** mock payment. Neither money nor card data is collected.
- Either participant may cancel strictly before the start date: booking and hold become **Cancelled**. After the inclusive end date, the owner can confirm successful completion: booking becomes completed and hold becomes **Released**.
- Either participant may flag an open dispute once a rental starts. The booking remains active and its hold stays **Held**; completion/cancellation are blocked while the dispute is open. Full dispute resolution is deferred to a later sprint; there is no public endpoint to clear the flag.
- Participants alone can read bookings or request transitions. General booking updates/deletion are disabled. Booking/payment admin views are read-only so they cannot bypass the lifecycle. Items with booking history cannot be deleted; mark them unavailable instead.

Migrations `0003_booking_dispute_open_alter_booking_item_and_more` and `0004_backfill_mock_payments` extend the existing schema and add mock payments for any legacy bookings without changing their booking state or amount. Existing users, items and bookings are preserved.

Sprint 3 verification: 36 backend tests passed on isolated PostgreSQL 18, including concurrent overlap/non-overlap requests, invalid dates, permissions, rollback, legacy payment backfill, hold transitions, dispute blocking and all US-01–03 regression tests. Django system/migration checks and the Vite production build passed. Browser smoke checks covered public browse, item details, and the booking login requirement.
