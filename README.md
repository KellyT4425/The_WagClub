![Business Logo](static\images\business.png)

# The_WagClub
> "Pampering Pups, One Wag at a Time"

Live Site & Repo

Deployed URL

GitHub repo

Screenshots (Desktop & Mobile)
Three or four images that show home, services, cart/checkout, and a mobile navbar.

## Description
The Wag Club is a Django-powered web application built to make life easier for both dog parents and the people who care for their pups. Instead of dealing with scribbled notes, lost paper passes, or “did I use that voucher already?” moments, everything is handled digitally — clean, simple, and secure.

Customers can browse daycare passes, grooming packages, and special offers, then buy them through a smooth checkout experience. Every purchase instantly generates a unique voucher with its own expiry date and QR code, so owners can redeem their passes on-site with a quick scan. Their personal wallet keeps everything neatly organised in one place, making it easy to see what’s active, what’s expiring soon, and what’s already been used.

Behind the scenes, the platform gives staff all the tools they need to run the business smoothly: managing services and prices, issuing and redeeming vouchers, checking histories, and keeping everything consistent without spreadsheets or guesswork. It’s powered by Django, PostgreSQL, and Stripe, with a responsive front-end that stays true to the soft, friendly Wag Club brand.

The end result feels like a modern companion for a real dog-care business — something that cuts down admin, keeps customers informed, and brings a bit of joy into the process with clean design and puppy energy.

## Tech Stack

| Layer               | Technologies Used                                                                 |
|---------------------|------------------------------------------------------------------------------------|
| 🎨 **Frontend**      | HTML5, CSS3, Bootstrap 5, JavaScript                                               |
| 🐍 **Backend**        | Python 3.12, Django 5                                                              |
| 🗄️ **Database**        | PostgreSQL                                                                         |
| 🔐 **Authentication** | Django AllAuth (user accounts, login, registration)                                |
| 💳 **Payments**       | Stripe API (Checkout Sessions)                                                    |
| ☁️ **Media Storage**  | Cloudinary via `django-cloudinary-storage`                                        |
| 📦 **Static Files**   | WhiteNoise (compressed & cached static file serving)                              |
| 🔲 **QR Generation**  | Segno / qrcode library (for voucher QR codes)                                     |
| ⚙️ **Environment**    | Virtualenv / venv, Python-dotenv                                                   |
| 🚀 **Deployment**     | Heroku (Python buildpack, Postgres add-on, config vars)                          |
| 🐙 **Version Control**| Git & GitHub                                                                       |

## Minimum Viable Product (MVP)
The Wag Club MVP is a focused, practical web application that delivers the essential digital tools a dog daycare & grooming business needs to operate smoothly — without unnecessary complexity. It replaces manual tracking with a streamlined system where customers can purchase passes, view their vouchers, and redeem them using auto-generated QR codes.

At its core, the MVP does three things exceptionally well:

1. Sell services and passes
Users can browse daycare passes, grooming options, and special offers, then complete purchases through a Stripe-ready checkout flow.

2. Generate and manage vouchers
Every purchase creates a unique, secure voucher with an expiry date, QR code, and a clear status (active, redeemed, or expired). Customers can view all their vouchers from a simple “My Wallet” dashboard.

3. Support smooth in-store redemption
Staff can scan or manually check voucher codes to validate them instantly, reducing mistakes and removing the need for paper tracking.

The MVP focuses on real business value: clarity, automation, and reliability. With Django, PostgreSQL, and a clean branded UI, The Wag Club delivers the minimum lovable product a real dog-care service could use today — offering customers a modern digital experience while keeping operations effortless for the staff.

## Key Features (MVP)

Customers can browse all daycare passes, grooming packages, and seasonal offers with clear pricing, durations, and images.

### 🎟️ Digital Voucher Generation

When a customer “purchases” a service:

- A unique voucher code is generated

- An expiry date is automatically applied

- A QR code is created and stored

- A digital invoice is available to view and print

### 📱 Customer Wallet

A personalised My Wallet dashboard shows:

- All active vouchers

- QR code previews

- Voucher status (Active / Redeemed / Expired)

- Quick access to view details or print

### 🔒 QR Code Verification

Each voucher includes a scannable QR code for fast verification at the daycare or grooming salon.

### 🧾 Styled Invoice Generator

Each voucher includes a clean, responsive invoice containing:

- Customer information

- Service details and price

- QR code

- Terms & conditions

- Issue and expiry dates

🛒 Basic Cart System

Users can add services to their cart and review totals.
(Stripe keys included — ready to plug in live payment.)

### 👤 User Authentication

Integrated with Django Allauth:

- Register

- Log in/out

- Password reset

### 🔐 Admin Tools

Staff/admin users can:

- Create and manage services

- View voucher details

- Track expiry and redemption status

- Access all orders

### 🎨 Fully Responsive Brand UI

Custom branding (“The Wag Club” aesthetic):

- Handwritten-style headings

- Soft colour palette

- Clean card layout

- Mobile-friendly hero banner

- Consistent footer + navigation

### ☁️ Cloudinary Media Handling

All images (services, QR codes) are stored and served via Cloudinary.

### 📦 Deployment-Ready

Configured for:

- Static file handling with Whitenoise

- Cloudinary media

- Environment variables

- PostgreSQL

- Django 5


## Entity Relationship Diagram (ERD)

### Core Entities

#### 1. ServiceCategory
Represents a high-level grouping of services (e.g. passes, grooming packages, offers).

- `id` (PK)
- `name` – choice of: Passes, Packages, Offers
- `slug` – unique identifier for URLs
- `is_active` – soft toggle for showing/hiding a category

**Relationships**

- One `ServiceCategory` has many `Service` records.


#### 2. Service
A specific daycare pass, grooming package, or special offer that can be purchased.

- `id` (PK)
- `category` (FK → ServiceCategory)
- `name`
- `slug` – unique
- `description`
- `price`
- `duration_hours` – optional, e.g. length of service/pass
- `img_path` – main display image
- `alt_text` – accessibility text
- `is_bundle` – whether this is a package/bundle
- `is_active` – whether the service is currently available

**Relationships**

- One `Service` belongs to one `ServiceCategory`.
- One `Service` has many `ServiceImage` records.
- One `Service` can appear in many `OrderItem` records.
- One `Service` can be referenced by many `Voucher` records.


#### 3. ServiceImage
Stores one or more images for each service.

- `id` (PK)
- `service` (FK → Service)
- `image_url`
- `alt_text`
- `is_main` – whether this is the main/primary image
- `sort_order` – controls ordering in galleries/lists

**Constraints**

- Exactly one `ServiceImage` per `Service` may have `is_main = True` (enforced via a unique constraint).


#### 4. User
Django’s built-in user model (via `get_user_model()`).

- Standard auth fields (email/username, password, etc.)

**Relationships**

- One `User` has many `Order` records.
- One `User` has many `Voucher` records.


#### 5. Order
Represents a single checkout event / purchase.

- `id` (PK)
- `user` (FK → User)
- `is_paid` – whether payment was completed
- `created_at` – timestamp of order creation

**Relationships**

- One `Order` belongs to one `User`.
- One `Order` has many `OrderItem` records.


#### 6. OrderItem
A line item inside an order (e.g. “5-Day Pass × 2”).

- `id` (PK)
- `order` (FK → Order)
- `service` (FK → Service)
- `quantity`
- `price` – price at time of purchase

**Relationships**

- One `OrderItem` belongs to one `Order`.
- One `OrderItem` references one `Service`.
- One `OrderItem` has exactly one `Voucher` (via OneToOne).


#### 7. Voucher
A digital voucher generated from an `OrderItem`.

- `id` (PK)
- `service` (FK → Service)
- `order_item` (OneToOne → OrderItem)
- `user` (FK → User)
- `code` – unique voucher code
- `qr_img_path` – QR image file
- `status` – choice: ISSUED, REDEEMED, EXPIRED
- `issued_at`
- `redeemed_at` – nullable
- `expires_at` – default 18 months from issue

**Relationships**

- One `Voucher` belongs to one `User`.
- One `Voucher` belongs to one `Service`.
- One `Voucher` is generated from exactly one `OrderItem` (1–1).

## ERD Diagram (Mermaid.js)

    User ||--o{ Order : "places"
    Order ||--o{ OrderItem : "contains"
    OrderItem ||--|| Voucher : "generates"
    User ||--o{ Voucher : "owns"

    ServiceCategory ||--o{ Service : "groups"
    Service ||--o{ ServiceImage : "has"
    Service ||--o{ OrderItem : "purchased_as"
    Service ||--o{ Voucher : "redeemed_for"

    User {
        int id
        string username
        string email
        string password
    }

    ServiceCategory {
        int id
        string name
        string slug
        bool is_active
    }

    Service {
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

    ServiceImage {
        int id
        int service_id
        string image_url
        string alt_text
        bool is_main
        int sort_order
    }

    Order {
        int id
        int user_id
        bool is_paid
        datetime created_at
    }

    OrderItem {
        int id
        int order_id
        int service_id
        int quantity
        decimal price
    }

    Voucher {
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

## Design

### Typography
| Use Case          | Font Family          | Style & Purpose                                           |
|-------------------|----------------------|-------------------------------------------------------------|
| Headings / Logo   | Patrick Hand SC       | Playful, handwritten feel that adds personality to the brand |
| Body Text         | Lato                  | Clean, modern sans-serif for readability and consistency     |


### Colour Palette
| Colour Name     | Hex Code   | Usage                                  |
|-----------------|------------|-----------------------------------------|
| 🐾 Beige        | `#e3dad2`  | Main background (warm, welcoming tone)  |
| 🐶 Charcoal     | `#1a1a1a`  | Primary text & button colour            |
| 🏅 Gold Accent  | `#c7a77b`  | Highlight colour for active states, hover, CTAs |

### Imagery
| Type of Image        | Purpose                                           |
|----------------------|----------------------------------------------------|
| Hero Images          | Establish warm, welcoming first impression         |
| Service Cards        | Visual cues for passes, grooming, and offers       |
| [**QR Code**](https://qr.io/)             | Used in the digital voucher system                 |
| Icons (Cart, Paw)    | Lightweight branding and clarity for navigation    |

- **Unsplash** (royalty-free, no attribution required)
- **Pexels** (royalty-free, no attribution required)

_________________________________

Browse services with search/filter

Auth (signup/login/logout)

Cart & Stripe checkout

Wallet/Vouchers (if live)

Responsive layout, toasts, accessible forms

Information Architecture

Global nav: Home, Services, Cart, Account

Footer: Reviews, Contact, Socials

Design System (tiny)

Fonts: Heading / Body

Colors: hex list (primary, background, text, accent)

Spacing: e.g., 0.5rem / 1rem / 2rem

Components: buttons, cards, forms, toasts

Tech Stack

Django 5, Bootstrap 5, Stripe

Crispy Forms (if used), PostgreSQL (if prod)

Data Model (brief)

Service, Category, Order, OrderItem, Voucher (whatever you actually used)

One line per model explaining purpose & key fields

How to Run Locally

Clone

Create venv & install requirements

Set env vars (STRIPE_PUBLIC_KEY, etc.)

python manage.py migrate

python manage.py runserver

Environment Variables
List each with a one-liner: what it’s for and an example value.

Testing

Manual testing: link to section below (in README or separate TESTING.md)

Automated tests: how to run (see below)

Coverage result (screenshot or percentage)

Known Issues / Future Work

What’s intentionally left out

What you’d do next (1–3 bullets)

Credits

Images (Unsplash links), icons, libraries

License (optional)