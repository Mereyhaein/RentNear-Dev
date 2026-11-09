# RentNear — Initial API Structure

## Authentication
POST /api/auth/register — Register a new user  
POST /api/auth/login — Log in  
POST /api/auth/logout — Log out (token required)  
GET /api/auth/me — Current authenticated user

## Users
GET /api/users/{id} — View user profile

## Items
GET /api/items — Get available items  
GET /api/items/{id} — View item details  
POST /api/items — Create an item listing

## Bookings
GET /api/bookings — View user's bookings  
POST /api/bookings — Create a booking  
GET /api/bookings/{id} — View booking details  
Booking status changes use the explicit Sprint 3 actions below; arbitrary PATCH is disabled.

## Sprint 2

- `GET /api/items/`: public available items, newest first. Query: `search`, `category`, `location`, `min_price`, `max_price`, `page`. Each search word matches title/description. Category matches case-insensitively; location is a case-insensitive substring. All filters combine with AND; price bounds are inclusive. Invalid or reversed ranges return 400.
- `GET /api/items/categories/`: public categories from available listings.
- `GET /api/items/mine/`: authenticated user's listings including unavailable items.
- `GET /api/items/{id}/`: public details.
- `POST /api/items/`: authenticated create; title, description, category, price_per_day, location, optional availability and photos. Owner is assigned by the server.
- `PATCH/PUT /api/items/{id}/`: owner-only update.
- `DELETE /api/items/{id}/`: owner-only deletion, 204.

Lists return `{count, next, previous, results}` with 24 items per page. Authentication reuses `Authorization: Token <token>`. Upload multipart data with repeated `photos` fields; edit accepts repeated `remove_image_ids` belonging to this listing. Retained photos plus uploads must not exceed 8. Photos must be valid JPEG/PNG/WebP and at most 5 MB each. Non-upload requests also accept JSON.


## Sprint 3 booking API

Booking endpoints require existing token authentication. List/retrieve/action access is restricted to the renter or item's owner.

- `POST /api/bookings/`: JSON `{item, start_date, end_date}`. Creates a confirmed booking and linked Held mock payment atomically. Dates use ISO `YYYY-MM-DD`, are inclusive, and must begin today or later (UTC). Price is calculated server-side. Rejects unavailable items, self-bookings, overlaps, invalid dates and excessive totals with 400; missing item returns 404.
- `GET /api/bookings/`: paginated bookings made by the user or for their items; includes item title, participant names, dates, total, booking status, dispute flag, and nested payment `{id, amount, state, updated_at}`.
- `GET /api/bookings/{id}/`: participant-only booking details. Unrelated users receive 404.
- `POST /api/bookings/{id}/cancel/`: either participant, only before start; booking/hold become cancelled.
- `POST /api/bookings/{id}/complete/`: owner only, strictly after end; booking becomes completed, hold released.
- `POST /api/bookings/{id}/open-dispute/`: either participant, once started and still active; flag open dispute, keep hold held. Completion/cancellation are blocked until resolution (resolution workflow deferred).
- `GET /api/items/{id}/availability/`: public `{availability, booked_periods: [{start_date, end_date}]}` with current/future active dates, no renter/payment identity.

Transition payloads are empty JSON. Invalid transitions return 400; unauthorized completion returns 403. PATCH/PUT/DELETE bookings and independent payment mutations are unsupported. Payment states in JSON: `held`, `released`, `cancelled`. No card data or real gateway. Database transactions serialize requests on the item row, check inclusive overlaps after acquiring the lock, and update booking and payment together. Item deletion returns 400 when booking history exists.
