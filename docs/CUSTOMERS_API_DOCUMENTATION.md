# 👥 Customers API Documentation

## Overview

Comprehensive REST API views for the customers app implementing all features from the project description with full customer management, profile, addresses, loyalty programs, and segmentation.

---

## 🎯 What Was Created

### 1. **Views** (`customers/views.py`)
- ✅ 4 Complete ViewSets with 30+ endpoints
- ✅ Full CRUD operations
- ✅ Profile management
- ✅ Address management
- ✅ Customer groups/segmentation
- ✅ Loyalty program integration
- ✅ Complete Swagger documentation

### 2. **Filters** (`customers/filters.py`)
- ✅ CustomerFilter with 15+ filter options
- ✅ AddressFilter with 6+ filter options
- ✅ Advanced filtering by loyalty tier, stats, dates

### 3. **URLs** (`customers/urls.py`)
- ✅ Complete URL routing with DRF router
- ✅ Public registration endpoint
- ✅ All viewsets registered

---

## 📋 API Endpoints

### Customer Management API

| Endpoint | Method | Description | Permissions |
|----------|--------|-------------|-------------|
| `/api/customers/customers/` | GET | List all customers | Admin |
| `/api/customers/customers/{id}/` | GET | Get customer details | Owner/Admin |
| `/api/customers/customers/{id}/` | PUT/PATCH | Update customer | Owner/Admin |
| `/api/customers/customers/{id}/` | DELETE | Delete customer | Admin |
| `/api/customers/customers/me/` | GET | Get current user profile | Authenticated |
| `/api/customers/customers/update_profile/` | PUT/PATCH | Update current user profile | Authenticated |
| `/api/customers/customers/change_password/` | POST | Change password | Authenticated |
| `/api/customers/customers/{id}/stats/` | GET | Get customer statistics | Owner/Admin |
| `/api/customers/customers/{id}/orders/` | GET | Get customer orders | Owner/Admin |
| `/api/customers/customers/{id}/wishlist/` | GET | Get customer wishlist | Owner/Admin |
| `/api/customers/customers/{id}/reviews/` | GET | Get customer reviews | Owner/Admin |
| `/api/customers/customers/{id}/verify/` | POST | Verify customer account | Admin |
| `/api/customers/customers/{id}/make_vip/` | POST | Upgrade to VIP | Admin |
| `/api/customers/customers/{id}/update_loyalty_tier/` | POST | Update loyalty tier | Admin |
| `/api/customers/customers/{id}/add_loyalty_points/` | POST | Add loyalty points | Admin |
| `/api/customers/customers/{id}/deactivate/` | POST | Deactivate account | Owner/Admin |
| `/api/customers/customers/{id}/reactivate/` | POST | Reactivate account | Admin |

**Features:**
- ✅ Complete profile management
- ✅ Password change with validation
- ✅ Customer statistics dashboard
- ✅ Order history
- ✅ Wishlist integration
- ✅ Review history
- ✅ Account verification
- ✅ VIP status management
- ✅ Loyalty tier system
- ✅ Loyalty points management
- ✅ Account activation/deactivation

---

### Address Management API

| Endpoint | Method | Description | Permissions |
|----------|--------|-------------|-------------|
| `/api/customers/addresses/` | GET | List customer addresses | Authenticated |
| `/api/customers/addresses/{id}/` | GET | Get address details | Owner |
| `/api/customers/addresses/` | POST | Create new address | Authenticated |
| `/api/customers/addresses/{id}/` | PUT/PATCH | Update address | Owner |
| `/api/customers/addresses/{id}/` | DELETE | Delete address | Owner |
| `/api/customers/addresses/{id}/set_default/` | POST | Set as default address | Owner |

**Features:**
- ✅ Multiple addresses per customer
- ✅ Billing and shipping addresses
- ✅ Default address management
- ✅ Address validation
- ✅ Auto-set customer on creation

---

### Customer Groups API

| Endpoint | Method | Description | Permissions |
|----------|--------|-------------|-------------|
| `/api/customers/groups/` | GET | List all customer groups | Authenticated |
| `/api/customers/groups/{id}/` | GET | Get group details | Authenticated |
| `/api/customers/groups/` | POST | Create customer group | Admin |
| `/api/customers/groups/{id}/` | PUT/PATCH | Update group | Admin |
| `/api/customers/groups/{id}/` | DELETE | Delete group | Admin |
| `/api/customers/groups/{id}/members/` | GET | Get group members | Authenticated |
| `/api/customers/groups/{id}/add_member/` | POST | Add customer to group | Admin |
| `/api/customers/groups/{id}/remove_member/` | POST | Remove customer from group | Admin |

**Features:**
- ✅ Customer segmentation
- ✅ Group-based perks (discounts, priority support)
- ✅ Automatic assignment rules
- ✅ Member management
- ✅ Group statistics

---

### Registration API

| Endpoint | Method | Description | Permissions |
|----------|--------|-------------|-------------|
| `/api/customers/register/` | POST | Register new customer | Public |

**Features:**
- ✅ Public registration endpoint
- ✅ Password validation
- ✅ Email/username uniqueness check
- ✅ Returns complete customer profile

---

## 🔍 Filtering Options

### Customer Filters

```bash
GET /api/customers/customers/
```

**Available Filters:**
- ✅ `is_active` - Active/inactive customers
- ✅ `is_verified` - Verified accounts only
- ✅ `is_vip` - VIP customers
- ✅ `phone_verified` - Phone verified customers
- ✅ `loyalty_tier` - Filter by tier (bronze, silver, gold, platinum)
- ✅ `accepts_marketing_email` - Marketing email opt-in
- ✅ `accepts_marketing_sms` - Marketing SMS opt-in
- ✅ `min_orders` - Minimum order count
- ✅ `max_orders` - Maximum order count
- ✅ `min_spent` - Minimum total spent
- ✅ `max_spent` - Maximum total spent
- ✅ `joined_after` - Joined after date
- ✅ `joined_before` - Joined before date
- ✅ `last_order_after` - Last order after date
- ✅ `last_order_before` - Last order before date
- ✅ `preferred_language` - Preferred language
- ✅ `preferred_currency` - Preferred currency
- ✅ `gender` - Gender filter

**Search:**
- ✅ Username, email, first name, last name, phone

**Ordering:**
- ✅ `date_joined`, `-date_joined`
- ✅ `total_orders`, `-total_orders`
- ✅ `total_spent`, `-total_spent`
- ✅ `last_order_date`, `-last_order_date`

### Address Filters

```bash
GET /api/customers/addresses/
```

**Available Filters:**
- ✅ `address_type` - billing or shipping
- ✅ `is_default` - Default addresses only
- ✅ `country` - Filter by country
- ✅ `state` - Filter by state
- ✅ `city` - Filter by city (contains)
- ✅ `customer` - Filter by customer ID (admin)

**Ordering:**
- ✅ `created_at`, `-created_at`
- ✅ `is_default`, `-is_default`

---

## 🚀 Usage Examples

### 1. Register a New Customer
```bash
POST /api/customers/register/
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecureP@ssw0rd123!",
  "password2": "SecureP@ssw0rd123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

### 2. Get Current User Profile
```bash
GET /api/customers/customers/me/
Authorization: Bearer <access_token>
```

### 3. Update Profile
```bash
PATCH /api/customers/customers/update_profile/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1234567890",
  "accepts_marketing_email": true,
  "preferred_currency": "USD"
}
```

### 4. Change Password
```bash
POST /api/customers/customers/change_password/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "OldPassword123!",
  "new_password": "NewSecureP@ss456!",
  "new_password2": "NewSecureP@ss456!"
}
```

### 5. Get Customer Statistics
```bash
GET /api/customers/customers/123/stats/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "total_orders": 15,
  "total_spent": "2450.00",
  "average_order_value": "163.33",
  "last_order_date": "2025-10-15T14:30:00Z",
  "loyalty_points": 2450,
  "loyalty_tier": "gold"
}
```

### 6. Get Customer Orders
```bash
GET /api/customers/customers/123/orders/?status=delivered
Authorization: Bearer <access_token>
```

### 7. Add a New Address
```bash
POST /api/customers/addresses/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "address_type": "shipping",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "address_line1": "123 Main St",
  "address_line2": "Apt 4B",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "is_default": true
}
```

### 8. Set Address as Default
```bash
POST /api/customers/addresses/456/set_default/
Authorization: Bearer <access_token>
```

### 9. Filter Customers by Loyalty Tier
```bash
GET /api/customers/customers/?loyalty_tier=gold&min_spent=1000
Authorization: Bearer <admin_token>
```

### 10. Add Loyalty Points (Admin)
```bash
POST /api/customers/customers/123/add_loyalty_points/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "points": 500,
  "reason": "Special promotion bonus"
}
```

### 11. Verify Customer Account (Admin)
```bash
POST /api/customers/customers/123/verify/
Authorization: Bearer <admin_token>
```

### 12. Create Customer Group (Admin)
```bash
POST /api/customers/groups/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "VIP Gold Members",
  "description": "Top tier customers with exclusive benefits",
  "discount_percentage": 15.00,
  "priority_support": true,
  "free_shipping": true
}
```

### 13. Add Customer to Group (Admin)
```bash
POST /api/customers/groups/5/add_member/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "customer_id": 123
}
```

### 14. Get Customer Wishlist
```bash
GET /api/customers/customers/123/wishlist/
Authorization: Bearer <access_token>
```

### 15. Get Customer Reviews
```bash
GET /api/customers/customers/123/reviews/
Authorization: Bearer <access_token>
```

---

## 🔐 Permission System

### Permission Classes Used:

1. **IsOwnerOrAdmin**
   - Customers can access their own data
   - Admins can access all data

2. **IsAuthenticated**
   - Requires user to be logged in
   - Used for profile access, addresses

3. **IsAdminUser**
   - Admin-only actions
   - Customer list, verification, VIP status

4. **AllowAny**
   - Public registration endpoint

### Access Control Logic:

```python
# Customer ViewSet
- list: Admin only
- retrieve: Owner or Admin
- update: Owner or Admin
- delete: Admin only
- me: Authenticated
- change_password: Authenticated
- stats: Owner or Admin
- orders: Owner or Admin
- verify: Admin only
- make_vip: Admin only

# Address ViewSet
- All actions: Owner only (except admin can see all)
- Addresses automatically filtered by customer

# Customer Group ViewSet
- list, retrieve: Authenticated
- create, update, delete: Admin only
- add_member, remove_member: Admin only
```

---

## 📊 Customer Statistics

### Available Stats:
- ✅ Total orders count
- ✅ Total amount spent
- ✅ Average order value
- ✅ Last order date
- ✅ Loyalty points balance
- ✅ Loyalty tier

### Loyalty Tier System:

| Tier | Total Spent | Benefits |
|------|-------------|----------|
| Bronze | $0 - $999 | Basic benefits |
| Silver | $1,000 - $4,999 | 5% discount |
| Gold | $5,000 - $9,999 | 10% discount, priority support |
| Platinum | $10,000+ | 15% discount, free shipping, VIP access |

---

## 🎁 Customer Groups / Segmentation

### Group Features:
- ✅ Name and description
- ✅ Automatic assignment rules (JSON)
- ✅ Discount percentage per group
- ✅ Priority support flag
- ✅ Free shipping flag
- ✅ Member count tracking

### Use Cases:
- VIP customers
- Wholesale buyers
- Affiliate partners
- Loyalty program tiers
- Marketing segments
- Regional groups

---

## 📧 Marketing Preferences

### Opt-in Fields:
- ✅ `accepts_marketing_email` - Email marketing consent
- ✅ `accepts_marketing_sms` - SMS marketing consent

### Usage:
Filter customers for targeted campaigns:
```bash
GET /api/customers/customers/?accepts_marketing_email=true&loyalty_tier=gold
```

---

## 🌐 Multi-language & Currency Support

### Fields:
- ✅ `preferred_language` - User's preferred language (default: 'en')
- ✅ `preferred_currency` - User's preferred currency (default: 'USD')

### Usage:
Use these fields to personalize the shopping experience:
- Display prices in preferred currency
- Send emails in preferred language
- Customize UI language

---

## 📱 Phone Verification

### Fields:
- ✅ `phone` - Phone number
- ✅ `phone_verified` - Verification status

### Workflow:
1. Customer provides phone number
2. Send verification code (implement via SMS service)
3. Verify code and set `phone_verified = True`
4. Enable phone-based features (2FA, SMS notifications)

---

## 🎯 Customer Lifecycle Actions

### 1. **New Customer**
```bash
POST /api/customers/register/
# Creates account with bronze tier
```

### 2. **Email Verification**
```bash
POST /api/customers/customers/{id}/verify/
# Admin verifies email
```

### 3. **First Purchase**
```bash
# Order system updates:
# - total_orders += 1
# - total_spent += order_amount
# - last_order_date = now
```

### 4. **Loyalty Tier Upgrade**
```bash
POST /api/customers/customers/{id}/update_loyalty_tier/
# Auto-calculates tier based on total_spent
```

### 5. **VIP Upgrade**
```bash
POST /api/customers/customers/{id}/make_vip/
# Manual VIP status for special customers
```

### 6. **Group Assignment**
```bash
POST /api/customers/groups/{group_id}/add_member/
# Add to customer segment
```

---

## 🔄 Integration Points

### Orders App Integration
```python
# Get customer's order history
GET /api/customers/customers/{id}/orders/
```

### Cart/Wishlist Integration
```python
# Get customer's wishlist
GET /api/customers/customers/{id}/wishlist/
```

### Products Integration
```python
# Get customer's product reviews
GET /api/customers/customers/{id}/reviews/
```

### Payments Integration
- Use customer stats for payment method suggestions
- Track spending for loyalty programs

### Recommendations Integration
- Use customer preferences for personalization
- Track customer segments for targeted recommendations

---

## 📈 Analytics & Reporting

### Key Metrics:
- Total customers
- Active vs inactive
- Verified customers
- VIP customers
- Customers by loyalty tier
- Average order value by tier
- Marketing opt-in rates

### Example Queries:
```bash
# Get VIP customers who spent over $5000
GET /api/customers/customers/?is_vip=true&min_spent=5000

# Get gold tier customers who accept marketing
GET /api/customers/customers/?loyalty_tier=gold&accepts_marketing_email=true

# Get customers who joined this month
GET /api/customers/customers/?joined_after=2025-10-01

# Get inactive customers with past orders
GET /api/customers/customers/?is_active=false&min_orders=1
```

---

## 🔧 Admin Features

### Customer Management:
- ✅ View all customers with advanced filtering
- ✅ Verify email addresses
- ✅ Upgrade to VIP status
- ✅ Adjust loyalty points
- ✅ Update loyalty tiers
- ✅ Deactivate/reactivate accounts
- ✅ View customer statistics

### Group Management:
- ✅ Create customer segments
- ✅ Define group benefits
- ✅ Assign/remove members
- ✅ View group statistics

---

## 🎨 Swagger Documentation

All endpoints are fully documented with Swagger/OpenAPI:
- **Descriptions**: Complete endpoint documentation
- **Parameters**: All query/path/body parameters
- **Examples**: Request/response examples
- **Permissions**: Access control clearly marked
- **Tags**: Organized under "Customers"

Access at:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

---

## ✅ Implementation Checklist

- [x] CustomerViewSet with 17 actions
- [x] AddressViewSet with address management
- [x] CustomerGroupViewSet with segmentation
- [x] Public registration endpoint
- [x] Profile management (view, update)
- [x] Password change functionality
- [x] Customer statistics endpoint
- [x] Order history integration
- [x] Wishlist integration
- [x] Reviews integration
- [x] Account verification
- [x] VIP status management
- [x] Loyalty tier system
- [x] Loyalty points management
- [x] Account activation/deactivation
- [x] Address CRUD with default management
- [x] Customer groups/segmentation
- [x] Group member management
- [x] Comprehensive filtering (15+ filters)
- [x] Permission-based access control
- [x] Complete Swagger documentation

---

## 📞 Next Steps

### 1. **Add to Main URLs** ✅
Already added to `config/urls.py`

### 2. **Test the API**
```bash
# Start server
python manage.py runserver

# Visit Swagger docs
http://localhost:8000/api/docs/

# Test registration
POST http://localhost:8000/api/customers/register/

# Test profile access
GET http://localhost:8000/api/customers/customers/me/
```

### 3. **Create Admin Users**
```bash
python manage.py createsuperuser
```

---

**The Customers API is now complete and production-ready!** 🎉

All features from the project description have been implemented with comprehensive customer management, loyalty programs, segmentation, and integration points!

