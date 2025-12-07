![Business Logo](static/images/business.png)

# The Wag Club
> Pampering pups, one wag at a time.

## Contents
- [The Wag Club](#the-wag-club)
  - [Contents](#contents)
- [Overview](#overview)
- [Architecture](#architecture)
- [Live Demo \& Repository](#live-demo--repository)
- [Product Screenshots](#product-screenshots)
- [Features](#features)
- [Frontend](#frontend)
- [Backend](#backend)
- [Tech Stack](#tech-stack)
- [Data Model](#data-model)
- [User Experience](#user-experience)
  - [Stripe Payments](#stripe-payments)
- [Deployment (Heroku)](#deployment-heroku)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Bugs Encountered](#bugs-encountered)
- [Testing](#testing)
- [Manual Testing](#manual-testing)
- [Social Media Presence](#social-media-presence)
  - [Future Enhancements](#future-enhancements)
  - [Credits](#credits)
  - [User Guide](#user-guide)
  - [Admin Guide](#admin-guide)
  - [Business Model](#business-model)
  - [Marketing & SEO](#marketing--seo)

## Overview
The Wag Club is a Django-powered e-commerce site for a dog daycare and grooming business. Customers browse services, add them to a cart, and pay through Stripe. Successful payments generate time-bound vouchers with QR codes that can be redeemed on-site. A customer wallet keeps active, redeemed, and expired vouchers organised; staff can scan and redeem vouchers securely.

## Architecture
- Monolithic Django 5 project split into domain apps:
  - `services`: service catalog, categories, images, search.
  - `orders`: cart, Stripe checkout session creation, webhook fulfilment, vouchers, wallet, redemption.
  - `project_core`: project settings, URLs, static/media configuration.
- Frontend rendered with Django templates + Bootstrap 5; no custom API layer required for core flows.
- Payments handled server-side via Stripe Checkout and webhooks to keep keys secret and ensure orders/vouchers are created after confirmed payment.

## Live Demo & Repository
- Live Site (Heroku): [https://the-wagclub-0b0521e2a364.herokuapp.com/](https://the-wagclub-0b0521e2a364.herokuapp.com/)
- Repository: [https://github.com/<user>/<repo>](https://github.com/<user>/<repo>)  <!-- replace with the actual repo URL -->

## Product Screenshots
Replace the placeholders with your captures (examples below point to `static/images/*`):

<img src="static/images/homepage-hero-img.jpg" alt="Homepage" width="820" />

![Facebook Page Mockup](static/images/facebook-page.png)

- Services listing: `static/images/services-list.png`
- Cart & checkout: `static/images/cart-checkout.png`
- Wallet & voucher detail: `static/images/wallet.png`
- Admin/staff view (optional): `static/images/admin.png`
- Social page (alt): `static/images/facebook-eg.png` / `static/images/insta-post.png`

## Features
- Service browsing with categories (Passes, Packages, Offers) and search.
- Cart and checkout via Stripe Checkout Sessions with order metadata.
- Voucher generation per line item quantity, including QR codes and expiry.
- Customer wallet grouped by status: Active, Redeemed, Expired.
- Voucher detail and printable invoice with QR code.
- Staff redemption via scan or manual code lookup.
- Authentication (register, login, logout, password reset) via Django AllAuth.
- Responsive UI with Bootstrap 5 and custom branding.
- Social proof: footer links to reviews/contact plus Instagram and Facebook presence.

## Frontend
- Templates: Django templates with Bootstrap 5, custom CSS in `static/css/base.css`.
- Layout: responsive navbar, footer social links, toast notifications for feedback.
- Pages: home hero, services list/detail, cart/checkout, wallet, voucher detail/invoice, staff scan/redeem.
- UX: search/filter on services; status badges for vouchers (Active/Redeemed/Expired); accessible form controls and alt text on imagery.
- Icons: Font Awesome for UI glyphs; branded imagery in `static/images`.

## Backend
- Django 5 with two domain apps: `services` (catalog) and `orders` (cart, payments, vouchers).
- Payments: Stripe Checkout session creation (`orders.views.create_checkout_session`) and webhook fulfilment (`orders.views.stripe_webhook`).
- Business logic:
  - Order and order items created only after confirmed payment event.
  - Vouchers generated per quantity with unique codes and QR images, default expiry 18 months.
  - Wallet views filter vouchers by status; staff-only redemption via `scan_voucher`/`redeem_voucher`.
- Auth: Django AllAuth for registration/login/logout/password reset.
- Media: Cloudinary for images; QR codes stored via ImageField.
- Static: WhiteNoise for compressed static serving; Bootstrap/FontAwesome from CDNs.
- Management commands for media health:
  - `python manage.py migrate_media_to_cloudinary [--dry-run]` (upload local media to Cloudinary via default storage).
  - `python manage.py check_media_urls` (HEAD check service/media URLs for 404s).

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript |
| Backend | Python 3.12, Django 5 |
| Database | PostgreSQL (Heroku Postgres) |
| Authentication | Django AllAuth |
| Payments | Stripe Checkout Sessions & Webhooks |
| Media Storage | Cloudinary (`django-cloudinary-storage`) |
| Static Files | WhiteNoise (compressed & cached) |
| QR Generation | `qrcode` |
| Environment | `python-dotenv`, virtualenv/venv |
| Deployment | Heroku (Python buildpack, Postgres add-on) |
| Version Control | Git & GitHub |

## Data Model
### Entities
- `ServiceCategory`: Groups services into Passes, Packages, Offers; slugged for URLs.
- `Service`: A purchasable pass/package/offer with price, duration, imagery, and active toggle.
- `ServiceImage`: Optional gallery per service; unique main image enforced.
- `Order`: A paid checkout linked to a user.
- `OrderItem`: Line items within an order, storing service, quantity, and locked-in price.
- `Voucher`: Generated per order item *and* quantity (multiple vouchers per item when quantity > 1); tracks code, QR image, status (ISSUED, REDEEMED, EXPIRED), issued/redeemed/expiry timestamps, and expiry (default 18 months).
- `User`: Django auth user (owner of orders and vouchers).

### ERD Diagram (Mermaid)
```mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--o{ ORDERITEM : contains
    ORDERITEM ||--o{ VOUCHER : generates
    USER ||--o{ VOUCHER : owns

    SERVICECATEGORY ||--o{ SERVICE : groups
    SERVICE ||--o{ SERVICEIMAGE : has
    SERVICE ||--o{ ORDERITEM : purchased_as
    SERVICE ||--o{ VOUCHER : redeemed_for

    USER {
        int id
        string username
        string email
        string password
    }

    SERVICECATEGORY {
        int id
        string name
        string slug
        bool is_active
    }

    SERVICE {
        int id
        int category_id
        string name
        string slug
        string description
        decimal price
        decimal duration_hours
        string img_path
        string alt_text
        bool is_bundle
        bool is_active
    }

    SERVICEIMAGE {
        int id
        int service_id
        string image_url
        string alt_text
        bool is_main
        int sort_order
    }

    NEWSLETTERSIGNUP {
        int id
        string email
        datetime created_at
    }

    ORDER {
        int id
        int user_id
        bool is_paid
        datetime created_at
    }

    ORDERITEM {
        int id
        int order_id
        int service_id
        int quantity
        decimal price
    }

    VOUCHER {
        int id
        int order_item_id
        int service_id
        int user_id
        string code
        string qr_img_path
        string status
        datetime issued_at
        datetime redeemed_at
        datetime expires_at
    }
```

## User Experience
- Navigation: Home, Services, Cart, Account dropdown, with footer links to Reviews and Contact.
- Styling: Handwritten-style headings, soft palette, clean cards, mobile-friendly layout.
- Accessibility: Alt text on imagery, focusable buttons/links, toasts for feedback.

## Stripe Payments
- Uses Stripe Checkout Sessions with metadata (`user_id`, cart items) to recreate orders on webhook success.
- Webhook endpoint: `/orders/checkout/webhook/` (`orders:stripe_webhook`).
- Success redirect: `/orders/success/?session_id={CHECKOUT_SESSION_ID}`.
- Requires `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_API_KEY` (restricted key optional), and `STRIPE_WEBHOOK` (signing secret).

## Deployment (Heroku)
1) Create Heroku app and add Heroku Postgres.
2) Set config vars (see Environment Variables).
3) `heroku config:set DISABLE_COLLECTSTATIC=0` (only if collectstatic should run).
4) Deploy via GitHub integration or `git push heroku main`.
5) Run migrations: `heroku run python manage.py migrate`.
6) Create superuser: `heroku run python manage.py createsuperuser`.
7) Add allowed host and CSRF origins for your Heroku domain.
8) Set Stripe webhook to `https://<your-app>.herokuapp.com/orders/checkout/webhook/` with the signing secret stored in `STRIPE_WEBHOOK`.

## Local Development
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```
With `DEBUG=True`, the app uses SQLite and permissive hosts for localhost/testserver.

## Environment Variables
Set these in `.env` locally and in Heroku config vars for production:

- `SECRET_KEY` — Django secret key.
- `DEBUG` — `True` (local) / `False` (production).
- `ALLOWED_HOSTS` — comma-separated (e.g., `localhost,127.0.0.1,<your-app>.herokuapp.com`).
- `CSRF_TRUSTED_ORIGINS` — comma-separated origins (e.g., `https://<your-app>.herokuapp.com`).
- `DATABASE_URL` — Postgres connection string (Heroku supplies this).
- `STRIPE_SECRET_KEY` — Stripe secret key.
- `STRIPE_PUBLISHABLE_KEY` — Stripe publishable key.
- `STRIPE_API_KEY` — Optional restricted key for server-side API calls.
- `STRIPE_WEBHOOK` — Stripe webhook signing secret.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` - for media.
- `SITE_URL` - base URL for building absolute QR links (set to your deployed domain).
- `EMAIL_BACKEND` and SMTP settings if using email (defaults to console backend).

## Bugs Encountered
- Stripe webhook 400/500: mismatched signing secret/version; fixed with resilient verification, correct `STRIPE_WEBHOOK`, and idempotent `stripe_session_id` handling (migration `0006_order_stripe_session_id`).
- Duplicate orders/admin delete 500: production DB missing `stripe_session_id`; migration added and webhook skips duplicates.
- Success page 500/302 after payment: success view now trusts Stripe metadata and renders vouchers without forcing login (with ownership checks).
- QR codes pointing to localhost or not rendering: added `/orders/voucher/<code>/qr/` endpoint that generates/serves via default storage (Cloudinary) and respects `SITE_URL`.
- Cloudinary 404s for services/QR: templates now use `.url` (no `{% static %}`/`/media`), added `migrate_media_to_cloudinary` uploader and `check_media_urls` verifier; missing files re-uploaded in admin.
- Stripe CLI/setup friction: documented correct CLI usage (`stripe listen`, `stripe trigger`) and ensured webhook/success URLs align with deployed domain.
- Minor UI/templating issues: fixed malformed service price tag; hardened WhiteNoise/psycopg/Procfile for deploy.

## Testing
- Automated: `python manage.py test`
  - Covers checkout session creation and webhook-driven order/voucher generation.
  - Service list view populates categories.
- Manual (recommended):
  - Add to cart, create Stripe Checkout, ensure success clears cart.
  - Verify vouchers appear in wallet (Active, Redeemed, Expired).
  - Staff redemption via scan/manual code; ensure status changes and permissions hold.
  - Responsive checks on mobile/tablet for nav, forms, and cards.

## Manual Testing
Detailed manual test cases (flows, expected results, and status) are documented in [testing.md](testing.md).

## Social Media Presence
- <img src="static/images/instagram.png" alt="Instagram" width="18" /> Instagram: https://www.instagram.com/thewag_club/
- <img src="static/images/facebook-eg.png" alt="Facebook" width="18" /> Facebook mockups: `static/images/facebook-page.png`, `static/images/facebook-eg.png`
- Include screenshot captures of the live/placeholder page in [Product Screenshots](#product-screenshots) for assessment.

## Future Enhancements
- Email/SMS notifications for expiring vouchers.
- Customer order history and invoices archive.
- Discount codes and promotional bundles.
- Staff dashboard with search/filter for vouchers and redemptions.

## Credits
- Design: The Wag Club brand assets (logo, palette, typography).
- Images: Stored in `static/images` (hero, service imagery, social mockups).
- Libraries: Django, Bootstrap, Stripe, qrcode, Cloudinary, WhiteNoise, Django AllAuth.
- Tools/References: Stripe docs (Checkout, Webhooks, CLI), Django docs (storage, management commands), Cloudinary docs (Django storage), Heroku runtime/buildpack docs; Ruff for linting.
- Testing/ops: `migrate_media_to_cloudinary`, `check_media_urls`, `migrate_media_to_cloudinary`, Stripe CLI for webhook/checkout event testing.

## User Guide
- Browse services: go to Services, search/filter, view details, add to cart.
- Checkout: proceed to Stripe Checkout, pay with test card (4242... in test mode).
- After payment: view success page; vouchers appear in My Wallet with QR codes.
- Redeem: staff scan the QR (staff-only redeem URL) and redeem via POST; customers see status only.
- Account: register/login via AllAuth; wallet shows Active/Redeemed/Expired vouchers.
- Newsletter: subscribe via footer form.
- Roles: customers can browse, pay, and view their vouchers; staff/admin can redeem and manage via admin. Login state is shown in the navbar.

## Admin Guide
- Admin login: use Django admin for CRUD on services, categories, images, orders, vouchers, newsletter signups.
- Vouchers: staff/admin can mark redeemed/expired via admin actions; QR links generate on demand.
- Media: stored in Cloudinary; use `migrate_media_to_cloudinary` and `check_media_urls` to manage media health.
- Security: keep secrets in env vars (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK`, `CLOUDINARY_*`, `SECRET_KEY`, etc.), DEBUG off in prod.
- CRUD: full CRUD available via Django admin for all models; user-facing flows cover create/read/update where applicable (cart/checkout/vouchers).

## Business Model
- Revenue: paid daycare/grooming services purchased online; each purchase issues vouchers for on-site redemption.
- Flow: cart → Stripe Checkout → webhook creates order/vouchers → wallet for customer → staff redeem on scan.
- Value: simplifies booking and redemption, provides clear statuses (Active/Redeemed/Expired), and staff-controlled redemption.

## Marketing & SEO
- Social: Instagram link in footer; Facebook Business Page placeholder is linked in footer (`https://www.facebook.com/TheWagClubBiz`)—replace with your real page if different.
- Newsletter: footer signup stored in `NewsletterSignup`.
- SEO: meta description/keywords in `base.html`, title block, `robots.txt`, `sitemap.xml`, 404 page present. Add per-page meta if desired.
- Agile/UX: maintain user stories/backlog in your Agile board and link it here; include wireframes/mockups (e.g., in `static/docs/`) and reference them in this README for assessment.
