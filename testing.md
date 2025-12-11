# Testing

## How to Use This Document
- Environment: local dev (`DEBUG=True`) with Stripe test keys; logged-in user unless stated.
- Record outcomes as Pass/Fail; note browser/device used for UI checks.

## User Stories Coverage
- US-Auth-01: As a visitor, I can register and log in so I can manage purchases.
- US-Services-01: As a customer, I can browse and search services so I can find what I need.
- US-Cart-01: As a customer, I can add/remove items in a cart so I can review my order.
- US-Pay-01: As a customer, I can complete checkout via Stripe so I can pay securely.
- US-Order-01: As a customer, I receive vouchers after payment so I can redeem later.
- US-Wallet-01: As a customer, I can view active/redeemed/expired vouchers in my wallet.
- US-Voucher-01: As staff, I can scan/redeem vouchers so I can validate them on-site.
- US-Admin-01: As an admin, I can manage services so I can keep offerings current.

## Linting & Checks
- Python: `python manage.py check`, `ruff check orders services project_core` (pass).
- Templates: `djlint templates orders/templates --check` (formatting suggestions only).
- CSS: `npx stylelint "static/**/*.css"` (pass with project config).
- JS: `npx jshint static/js` (no custom JS present to lint).

## Frontend & Navigation
- Home load: Page renders hero, nav, footer, toasts hidden until messages.
- Navigation links: Home, Services, Cart, Dashboard dropdown, footer Reviews/Contact all navigate correctly.
- Responsive nav: Mobile toggle expands/collapses menu; links remain tappable.
- Toasts: Trigger an action (e.g., add to cart) and confirm toast appears and autohides.

## Authentication (AllAuth)
- Register: Create account; redirected with success message; user shown as signed in.
- Login: Existing user can sign in; dashboard dropdown shows authenticated options.
- Logout: Sign out clears session; nav switches to guest options.
- Password reset: Request reset email (console backend in dev) and complete flow.

## Services
- List view: Categories Passes/Packages/Offers render; active services display name/price/button.
- Search: Query (e.g., "groom") returns matching services; empty query shows all.
- Detail view: Service detail page shows description, price, image, and add-to-cart button.

## Cart & Checkout
- Add to cart: From list/detail adds item; quantity increments on repeat add; totals update.
- Remove from cart: Remove button deletes item; cart total updates; empty cart message shown.
- Checkout session: Clicking checkout redirects to Stripe Checkout; correct line items/amounts displayed.
- Cancel checkout: Cancel returns to cart page with items intact.

## Stripe Success & Orders
- Success return: After test payment, user is redirected to success page with confirmation.
- Cart cleared: Cart session emptied after successful payment.
- Order created: Order and order items created for user with is_paid=True.

## Vouchers & Wallet
- Voucher creation: Vouchers generated per quantity with unique codes and QR images.
- Wallet view: Active/ Redeemed/ Expired sections populate correctly for the signed-in user only.
- Voucher detail: Accessible to owner or staff; others are blocked and redirected.
- Invoice: Voucher invoice displays service, price, QR code, and issue/expiry dates.

## Redemption (Staff)
- Staff access: `scan_voucher` and `redeem_voucher` only accessible to staff/superuser.
- Status check: Redeeming an ISSUED voucher marks it REDEEMED and sets redeemed_at.
- Prevent re-use: Redeemed/Expired vouchers cannot be redeemed again; message shown.

## Admin (Superuser)
- Admin login: /admin accessible to superuser.
- Service CRUD: Create/edit/delete services and categories; validation enforces unique slug and main image constraint.
- Voucher view: Vouchers list with status and timestamps visible.

## Media & Assets
- Images load: Logo, icons, service images, and QR codes render without broken links.
- Social links: Footer Instagram and Facebook links open in new tab to correct pages.

## Accessibility
- Alt text: Images have meaningful alt attributes (logo, services, QR codes, social icons).
- Keyboard: Links/buttons focusable; nav toggle reachable via keyboard.
- Forms: Labels associated, required fields marked; error states readable.
- Contrast: Buttons/text meet contrast on primary backgrounds.

## Responsiveness
- Mobile (≤576px): Navbar collapses; cards stack; spacing remains readable.
- Tablet (~768px): Grid aligns; footer columns wrap neatly.
- Desktop (≥1200px): Content centered; cards align in rows; no overflow.
- Orientation: Rotate phone/tablet to ensure layout adapts.

## Search Engine / Meta
- Meta tags: Title, description present; favicon loads.
- Open Graph: Check if logo/hero loads when sharing (optional if configured).
- URLs: Canonical pages load without console errors; trailing slashes consistent.

## Known Constraints
- Stripe: Use test mode; webhook signing secret must be configured for voucher creation on payment success.
- Email: Default console backend in dev; production SMTP required for real emails.
