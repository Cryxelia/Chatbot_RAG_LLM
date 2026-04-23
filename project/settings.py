from pathlib import Path
import  os
from dotenv import load_dotenv

SECRET_KEY = os.getenv("SECRET_KEY")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / 'templates'

# Determines environment: "production" or "development" (default)
ENV = os.getenv("DJANGO_ENV", "development")

# Debug mode on in all environments except production
DEBUG = ENV != "production"
    
# SESSION COOKIE SETTINGS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = ENV == "production"
SESSION_COOKIE_SAMESITE = "None" if ENV == "production" else "Lax"

# CSRF COOKIE SETTINGS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = ENV == "production"
CSRF_COOKIE_SAMESITE = "None" if ENV == "production" else "Lax"


# Load .env in development
if ENV != "production":
    dotenv_path = BASE_DIR / ".env"
    if dotenv_path.exists():
        from dotenv import load_dotenv
        load_dotenv(dotenv_path)
        print(f".env loaded from {dotenv_path}")


ALLOWED_HOSTS = ['*']
# Consider handling more complex frame options with middleware
X_FRAME_OPTIONS = 'ALLOWALL'

CSRF_TRUSTED_ORIGINS = [
    'http://lexiconinteractive.se',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://app.cloud.scorm.com',        'https://cloud.scorm.com',
    'https://novitus-lms.com',
    'https://sandbox.lexicon.cloud',
    'https://lms.mil.se',
    'https://scorm.itslearning.net',
    'https://fm.itslearning.net',        'https://lexiconplay.se',        'https://hosting.lexiconinteractive.se',        'https://www.lexiconplay.se',
    'http://lexiconinteractive.com',
    'https://lexiconinteractive.com', 'https://lexiconinteractive.se',
]

CORS_ALLOWED_ORIGINS = [
    'http://lexiconinteractive.se',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://app.cloud.scorm.com',        'https://cloud.scorm.com',
    'https://novitus-lms.com',
    'https://sandbox.lexicon.cloud',
    'https://lms.mil.se',
    'https://scorm.itslearning.net',
    'https://fm.itslearning.net',        'https://lexiconplay.se',        'https://hosting.lexiconinteractive.se',        'https://www.lexiconplay.se',
    'http://lexiconinteractive.com',
    'https://lexiconinteractive.com', 'https://lexiconinteractive.se',
]
CORS_ALLOW_METHODS = [    'GET',    'POST',    'OPTIONS',]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "Cookie"
)
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'chat',
    'corsheaders',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',


]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


if ENV == "production":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv("DB_NAME"),
            'USER': os.getenv("DB_USER"),
            'PASSWORD': os.getenv("DB_PASSWORD"),
            'HOST': os.getenv("DB_HOST"),
            'PORT': '3306',
            'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'chat_portfolio_db',
            'USER': 'root',
            'PASSWORD': os.getenv("LOCAL_DB_PW"),
            'HOST': 'localhost',
            'PORT': '3306',
        }
    }



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'

# Static files
if ENV == "production":
    # In production
    STATIC_ROOT = '/home/lexiconi/public_html/static'
else:
    # In developmenty
    STATICFILES_DIRS = [BASE_DIR / 'static']

LOGIN_URL = '/login/'      
LOGIN_REDIRECT_URL = '/chat/' 


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_CHARSET = 'utf-8'

LOGGING_CONFIG = None
import logging.config

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'rag_file': {
            'level': 'DEBUG', 
            'class': 'logging.FileHandler',
            'filename': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rag.log'),
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG', 
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'rag': {
            'handlers': ['rag_file', 'console'],
            'level': 'DEBUG', 
            'propagate': False,
        },
    },
    'root': {  
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

logging.config.dictConfig(LOGGING)