"""
Enhanced Security Settings for Multi-Tenant E-Commerce Platform
Add these settings to your main settings.py file
"""
from datetime import timedelta
import os

# ============================================================================
# AUTHENTICATION SETTINGS
# ============================================================================

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'api.authentication.SecureAuthenticationBackend',
    'api.authentication.EmailAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Custom User Model (already set in main settings)
# AUTH_USER_MODEL = 'customers.Customer'

# ============================================================================
# JWT (JSON Web Token) SETTINGS
# ============================================================================

SIMPLE_JWT = {
    # Token Lifetime
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Short-lived access tokens
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),      # Longer refresh tokens

    # Token Rotation
    'ROTATE_REFRESH_TOKENS': True,                   # Generate new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,                # Blacklist old refresh tokens

    # Security
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SIGNING_KEY', 'your-secret-key-change-in-production'),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'multi-tenant-store',

    # Token Claims
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Token Validation
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    # Sliding Tokens (Alternative to Refresh Tokens)
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),

    # Update Last Login
    'UPDATE_LAST_LOGIN': True,
}

# ============================================================================
# REST FRAMEWORK SETTINGS
# ============================================================================

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'api.throttles.BurstRateThrottle',
        'api.throttles.SustainedRateThrottle',
        'api.throttles.TenantRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'burst': '60/minute',
        'sustained': '1000/day',
        'login': '5/minute',
        'register': '3/hour',
        'password_reset': '3/hour',
        'payment': '10/hour',
        'checkout': '10/hour',
        'search': '100/hour',
        'email': '5/hour',
        'vip': '10000/day',
        'tenant': '10000/day',
        'ip': '1000/hour',
        'admin': '100000/day',
    },

    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # Renderers
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],

    # Exception Handling
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',

    # Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Require strong passwords
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================================
# SESSION SECURITY
# ============================================================================

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'  # Use cache for sessions
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_SECURE = True  # Only send over HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request

# Cookie Security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = True
CSRF_COOKIE_AGE = 31449600  # 1 year

# ============================================================================
# CORS (Cross-Origin Resource Sharing)
# ============================================================================

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    # Add your frontend URLs here
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================================================
# SECURITY HEADERS
# ============================================================================

# Security Middleware Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = False  # Set to True in production with HTTPS

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security Headers
SECURE_REFERRER_POLICY = 'same-origin'

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join('logs', 'django.log'),
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join('logs', 'security.log'),
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'api.authentication': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'api.views': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

# Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@yourstore.com')

# ============================================================================
# CACHE CONFIGURATION (For Rate Limiting and Sessions)
# ============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.getenv('REDIS_PASSWORD', None),
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'MAX_CONNECTIONS': 50,
        },
        'KEY_PREFIX': 'multitenant',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# ============================================================================
# TWO-FACTOR AUTHENTICATION
# ============================================================================

TWO_FACTOR_ENABLED = True
TWO_FACTOR_BACKUP_CODES_COUNT = 10
TWO_FACTOR_ISSUER_NAME = 'Multi-Tenant Store'

# ============================================================================
# ACCOUNT SECURITY
# ============================================================================

# Account Lockout Settings
ACCOUNT_LOCKOUT_ENABLED = True
ACCOUNT_LOCKOUT_ATTEMPTS = 5
ACCOUNT_LOCKOUT_DURATION = 30  # minutes

# Password Reset
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour
PASSWORD_RESET_MAX_ATTEMPTS = 3

# Email Verification
EMAIL_VERIFICATION_REQUIRED = True
EMAIL_VERIFICATION_TIMEOUT = 86400  # 24 hours

# Session Security
INACTIVE_SESSION_TIMEOUT = 1800  # 30 minutes

# ============================================================================
# API DOCUMENTATION (drf-spectacular)
# ============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Multi-Tenant E-Commerce API',
    'DESCRIPTION': 'Comprehensive API for multi-tenant e-commerce platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SECURITY': [
        {
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    ],
}

# ============================================================================
# PRODUCTION SECURITY CHECKLIST
# ============================================================================

# Remember to update these in production:
# 1. Change SECRET_KEY and JWT_SIGNING_KEY
# 2. Set DEBUG = False
# 3. Configure ALLOWED_HOSTS properly
# 4. Set SECURE_SSL_REDIRECT = True
# 5. Configure proper email settings
# 6. Set up Redis for caching
# 7. Configure CORS_ALLOWED_ORIGINS for your frontend
# 8. Set up proper database backups
# 9. Enable database SSL connections
# 10. Set up monitoring and alerting

