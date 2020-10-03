import logging.config
import os

from dotenv import load_dotenv

DEBUG = False

if DEBUG:
    load_dotenv('.env_local')
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
else:
    load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET')
PASS_SALT = os.getenv('PASS_SALT')

DATABASE = {
    'database': os.getenv('DB'),
    'password': os.getenv('DB_PASSWORD'),
    'user': os.getenv('DB_USER'),
    'host': os.getenv('DB_HOST'),
}

logger_config = {
    'version': 1,
    'disable_exsisting_logger': False,
    'formatters': {
        'std_format': {
            'format': '{asctime} - {levelname} - {name} - {message}',
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'std_format',
        },

    },
    'loggers': {
        'app': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}

logging.config.dictConfig(logger_config)
logger = logging.getLogger('app')
