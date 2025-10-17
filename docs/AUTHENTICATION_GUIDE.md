# 🔐 Authentication & Security System - Complete Guide

## Overview

This is a **highly secure, production-ready authentication system** for the multi-tenant e-commerce platform with multiple layers of security, comprehensive logging, and advanced protection mechanisms.

---

## 🛡️ Security Features

### 1. **Multi-Layer Authentication**
- ✅ JWT (JSON Web Token) based authentication
- ✅ Session-based authentication support
- ✅ Two-Factor Authentication (2FA) with TOTP
- ✅ Email and username login support
- ✅ Secure password hashing (PBKDF2)

### 2. **Account Protection**
- ✅ Account lockout after failed login attempts (5 attempts → 30 min lockout)
- ✅ Failed login attempt tracking with IP logging
- ✅ Suspicious activity detection
- ✅ Geolocation tracking (optional)
- ✅ Device/browser fingerprinting

### 3. **Password Security**
- ✅ Strong password requirements:
  - Minimum 12 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 digit
  - At least 1 special character
- ✅ Common password rejection
- ✅ Password similarity validation
- ✅ Secure password reset with time-limited tokens
- ✅ Password history (prevents reuse)

### 4. **Token Management**
- ✅ Short-lived access tokens (15 minutes)
- ✅ Longer refresh tokens (7 days)
- ✅ Automatic token rotation
- ✅ Token blacklisting
- ✅ Token usage tracking
- ✅ Multi-device logout support

### 5. **Rate Limiting**
- ✅ Burst protection (60 requests/minute)
- ✅ Sustained limits (1000 requests/day)
- ✅ Login throttling (5 attempts/minute)
- ✅ Registration limits (3/hour)
- ✅ Password reset limits (3/hour)
- ✅ Payment operation limits (10/hour)
- ✅ Dynamic rate limiting based on user reputation
- ✅ Per-tenant rate limiting
- ✅ VIP customer higher limits

### 6. **Session Management**
- ✅ Active session tracking
- ✅ Multi-device session management
- ✅ Remote session revocation
- ✅ Session expiration (1 hour)
- ✅ Secure session cookies (HttpOnly, Secure, SameSite)

### 7. **Email Verification**
- ✅ Email verification on registration
- ✅ Time-limited verification tokens (24 hours)
- ✅ Resend verification email
- ✅ Verified user badges

### 8. **Security Logging**
- ✅ Comprehensive security event logging
- ✅ Login attempt history
- ✅ Password change tracking
- ✅ 2FA enable/disable logging
- ✅ Suspicious activity alerts
- ✅ Account lockout logging

### 9. **Advanced Protections**
- ✅ CSRF protection
- ✅ XSS protection headers
- ✅ Clickjacking protection
- ✅ CORS configuration
- ✅ HSTS headers
- ✅ Content type sniffing protection
- ✅ SQL injection protection (ORM)
- ✅ Secure referrer policy

---

## 📚 API Endpoints

### Authentication Endpoints

#### 1. **Register**
```http
POST /api/auth/register/
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

Response:
{
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  },
  "message": "Registration successful. Please check your email to verify your account.",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 2. **Login**
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "johndoe",  // or use "email": "john@example.com"
  "password": "SecureP@ssw0rd123!",
  "two_factor_code": "123456"  // Required if 2FA is enabled
}

Response:
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "is_verified": true,
    "is_vip": false
  }
}
```

#### 3. **Logout**
```http
POST /api/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "all_devices": false  // Set to true to logout from all devices
}

Response:
{
  "message": "Logged out successfully"
}
```

#### 4. **Refresh Token**
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  // New refresh token (rotation enabled)
}
```

### Password Management

#### 5. **Change Password**
```http
POST /api/auth/password/change/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "OldP@ssw0rd123!",
  "new_password": "NewP@ssw0rd456!",
  "new_password2": "NewP@ssw0rd456!"
}

Response:
{
  "message": "Password changed successfully. Please login again."
}
```

#### 6. **Request Password Reset**
```http
POST /api/auth/password/reset/
Content-Type: application/json

{
  "email": "john@example.com"
}

Response:
{
  "message": "If an account with that email exists, a password reset link has been sent."
}
```

#### 7. **Confirm Password Reset**
```http
POST /api/auth/password/reset/confirm/
Content-Type: application/json

{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "password": "NewP@ssw0rd789!",
  "password2": "NewP@ssw0rd789!"
}

Response:
{
  "message": "Password reset successfully"
}
```

### Email Verification

#### 8. **Verify Email**
```http
POST /api/auth/verify-email/
Content-Type: application/json

{
  "token": "550e8400-e29b-41d4-a716-446655440000"
}

Response:
{
  "message": "Email verified successfully"
}
```

### Two-Factor Authentication

#### 9. **Setup 2FA**
```http
POST /api/auth/2fa/setup/
Authorization: Bearer <access_token>

Response:
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_uri": "otpauth://totp/Multi-Tenant%20Store:john@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Multi-Tenant%20Store",
  "backup_codes": [
    "12345678",
    "87654321",
    ...
  ]
}
```

#### 10. **Verify and Enable 2FA**
```http
POST /api/auth/2fa/verify/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "123456"
}

Response:
{
  "message": "Two-factor authentication enabled successfully"
}
```

#### 11. **Disable 2FA**
```http
POST /api/auth/2fa/disable/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "SecureP@ssw0rd123!"
}

Response:
{
  "message": "Two-factor authentication disabled"
}
```

### Session Management

#### 12. **List Active Sessions**
```http
GET /api/auth/sessions/
Authorization: Bearer <access_token>

Response:
{
  "results": [
    {
      "id": 1,
      "ip_address": "192.168.1.1",
      "device_type": "Desktop",
      "browser": "Chrome",
      "location": "New York, US",
      "created_at": "2025-10-17T10:00:00Z",
      "last_activity": "2025-10-17T15:30:00Z",
      "is_current": true
    }
  ]
}
```

#### 13. **Revoke Session**
```http
POST /api/auth/sessions/<session_id>/revoke/
Authorization: Bearer <access_token>

Response:
{
  "message": "Session revoked successfully"
}
```

### Security Monitoring

#### 14. **Login History**
```http
GET /api/auth/login-history/
Authorization: Bearer <access_token>

Response:
{
  "results": [
    {
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "success": true,
      "country": "US",
      "city": "New York",
      "timestamp": "2025-10-17T10:00:00Z"
    }
  ]
}
```

#### 15. **Security Activity Log**
```http
GET /api/auth/security-activity/
Authorization: Bearer <access_token>

Response:
{
  "recent_activity": [
    {
      "event_type": "login",
      "description": "User logged in from 192.168.1.1",
      "ip_address": "192.168.1.1",
      "timestamp": "2025-10-17T10:00:00Z"
    }
  ]
}
```

---

## 🔧 Installation & Setup

### 1. **Install Required Packages**

```bash
pip install djangorestframework
pip install djangorestframework-simplejwt
pip install django-filter
pip install django-cors-headers
pip install drf-spectacular
pip install pyotp  # For 2FA
pip install django-redis  # For caching/sessions
pip install python-dotenv
```

### 2. **Update settings.py**

Add to your `settings.py`:

```python
# Import security settings
from .security_settings import *

# Add 'api' to SHARED_APPS
SHARED_APPS = [
    # ... existing apps
    'api',  # Add this
]

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'api.authentication.SecureAuthenticationBackend',
    'api.authentication.EmailAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

### 3. **Update URLs**

In your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other patterns
    path('api/auth/', include('api.auth_urls')),
]
```

### 4. **Create Migrations**

```bash
python manage.py makemigrations api
python manage.py migrate_schemas --shared
```

### 5. **Environment Variables**

Create a `.env` file:

```env
# JWT Settings
JWT_SIGNING_KEY=your-super-secret-jwt-key-change-this

# Email Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourstore.com

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=your-redis-password

# Database
DB_USERNAME=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
```

---

## 🎯 Usage Examples

### Frontend Integration (React/Vue/Angular)

#### 1. **Login**

```javascript
async function login(username, password, twoFactorCode = null) {
  const response = await fetch('http://your-api.com/api/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username,
      password,
      two_factor_code: twoFactorCode
    })
  });

  const data = await response.json();

  if (response.ok) {
    // Store tokens
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user', JSON.stringify(data.user));

    return data;
  } else {
    throw new Error(data.message || 'Login failed');
  }
}
```

#### 2. **Authenticated Request**

```javascript
async function makeAuthenticatedRequest(url) {
  const access_token = localStorage.getItem('access_token');

  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json',
    }
  });

  if (response.status === 401) {
    // Token expired, try refresh
    await refreshToken();
    return makeAuthenticatedRequest(url);
  }

  return response.json();
}
```

#### 3. **Refresh Token**

```javascript
async function refreshToken() {
  const refresh_token = localStorage.getItem('refresh_token');

  const response = await fetch('http://your-api.com/api/auth/token/refresh/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh: refresh_token })
  });

  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
  } else {
    // Refresh failed, logout user
    logout();
  }
}
```

---

## 🔒 Security Best Practices

### 1. **Production Checklist**

- [ ] Change `SECRET_KEY` and `JWT_SIGNING_KEY`
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Enable HTTPS (`SECURE_SSL_REDIRECT = True`)
- [ ] Configure proper CORS origins
- [ ] Set up Redis for caching
- [ ] Configure email service
- [ ] Set up SSL/TLS for database
- [ ] Enable database backups
- [ ] Configure monitoring (Sentry, DataDog, etc.)
- [ ] Set up log aggregation
- [ ] Configure CDN for static files
- [ ] Enable rate limiting in production
- [ ] Set up firewall rules
- [ ] Configure DDoS protection

### 2. **Token Management**

- Access tokens are short-lived (15 minutes)
- Always use HTTPS in production
- Store tokens securely (HttpOnly cookies or secure storage)
- Implement token refresh logic
- Revoke tokens on logout

### 3. **Password Policies**

- Minimum 12 characters
- Require complexity (upper, lower, digit, special char)
- Prevent password reuse
- Force periodic password changes for sensitive accounts
- Implement password history

### 4. **Monitoring**

- Monitor failed login attempts
- Alert on suspicious patterns
- Track token usage
- Log security events
- Monitor rate limit violations

---

## 📊 Database Models

### Security Tables

- **LoginAttempt**: Track all login attempts
- **TwoFactorAuth**: 2FA settings per user
- **PasswordResetToken**: Password reset tokens
- **EmailVerificationToken**: Email verification tokens
- **RefreshTokenHistory**: JWT refresh token tracking
- **SecurityLog**: General security event logging
- **SessionActivity**: Active user sessions

---

## 🚀 Advanced Features

### 1. **Custom Permissions**

```python
from api.permissions import IsVerified, IsVIPCustomer

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsVerified, IsVIPCustomer]
```

### 2. **Custom Rate Limiting**

```python
from api.throttles import PaymentRateThrottle

class PaymentView(APIView):
    throttle_classes = [PaymentRateThrottle]
```

### 3. **Multi-Tenant Isolation**

All authentication respects tenant boundaries through django-tenants middleware.

---

## 📝 Notes

- All passwords are hashed using PBKDF2
- JWT tokens include user metadata
- 2FA uses TOTP (Time-based One-Time Password)
- Sessions are stored in Redis for performance
- All security events are logged
- Rate limiting prevents brute force attacks
- Account lockout prevents credential stuffing

---

## 🐛 Troubleshooting

### Issue: "Account locked"
**Solution**: Wait 30 minutes or contact admin to unlock

### Issue: "Invalid 2FA code"
**Solution**: Ensure device time is synchronized. Use backup codes if needed.

### Issue: "Token expired"
**Solution**: Implement automatic token refresh on frontend

### Issue: Rate limit exceeded
**Solution**: Wait for the rate limit window to reset

---

## 📞 Support

For security vulnerabilities, please email: security@yourstore.com

---

**Status**: ✅ Production Ready
**Last Updated**: October 2025
**Version**: 1.0.0

