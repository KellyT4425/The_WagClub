# The_WagClub
The_Wag Club is a full-stack Django e-commerce application created as my Code Institute PP5 milestone project. It delivers doggy day care and grooming services through a subscription-style platform while highlighting key development skills such as CRUD functionality, Stripe integration, and user authentication.

## Database Design

The database was designed using an entity-relationship diagram (ERD) to map out the core models, relationships, and constraints required to meet the project’s functional requirements. The design balances simplicity for maintainability while also providing scalability for future enhancements.

### Entities and Relationships

- User (Django Auth)
- Built on Django’s default authentication system.
- Extended to store first name, last name, and email for personalized communication.
- Each user can create orders, leave reviews, and receive vouchers.

### ServiceCategory

- Groups services into logical categories (e.g., Day Care, Grooming, Boarding).
- Includes slug for clean URLs and an is_active flag for admin control.

### Service

- Represents individual offerings within the catalog.
- Stores details such as name, description, duration, and price.
- Includes short_text for use in service previews and search results.
- A is_bundle field allows flexibility in creating package deals.
- Indexed by (category, price) for faster filtering and sorting.

### ServiceImage

- Provides support for multiple images per service.
- is_main ensures only one primary image is displayed as the “hero” image.
- alt_text and sort_order improve accessibility and user experience.

### Order and OrderItem

- Order records customer purchases, linked to the user.
- OrderItem stores the specific services purchased, with a snapshot of price to preserve historical accuracy.
- Together, they form the foundation of the shopping cart and checkout system.

### Voucher

- Generated automatically after successful payment.
- Linked to both an order and a user.
- Stores a unique code, file path for download, and issue details for customer confirmation.
- Supports future features such as redemption tracking and expiry.

### Review

- Allows authenticated users to leave service feedback.
- Enforced with a 1–5 rating constraint and an is_approved field for moderation.
- Strengthens trust and social proof within the platform.

### ContactMessage

- Enables customers to submit enquiries directly through the site.
- Messages are linked to a user (where applicable) and flagged when handled by admins.

#### Summary

> This schema ensures all key features of the project are supported: subscriptions, Stripe checkout, voucher generation, reviews, and admin management. The separation of concerns (e.g., services, vouchers, reviews) promotes scalability, while constraints and indexes improve data integrity and performance.

![]()