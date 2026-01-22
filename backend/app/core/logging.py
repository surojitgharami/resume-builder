# app/core/logging.py
import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')


class StructuredFormatter(logging.Formatter):
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'api_key', 'authorization',
        'access_token', 'refresh_token', 'jwt', 'cookie', 'session'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        request_id = request_id_ctx.get()
        if request_id:
            log_data['request_id'] = request_id
        
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }
        
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            for key, value in record.extra.items():
                if key.lower() not in self.SENSITIVE_FIELDS:
                    log_data[key] = value
                else:
                    log_data[key] = '[REDACTED]'
        
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", enable_sentry: bool = False, sentry_dsn: str = None) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
    
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('motor').setLevel(logging.WARNING)
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # Guard against empty or malformed Sentry DSN
    if enable_sentry and sentry_dsn and sentry_dsn.strip():
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            
            sentry_logging = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[sentry_logging],
                traces_sample_rate=0.1,
                environment="production",
                before_send=filter_sensitive_data,
            )
            
            logging.info("Sentry error tracking initialized")
        
        except ImportError:
            logging.warning("Sentry SDK not installed")
        except Exception as e:
            logging.error(f"Failed to initialize Sentry: {str(e)}")


def filter_sensitive_data(event: Dict[str, Any], hint: Dict[str, Any]) -> Dict[str, Any]:
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        if isinstance(headers, dict):
            for key in list(headers.keys()):
                if key.lower() in ['authorization', 'cookie', 'x-api-key']:
                    headers[key] = '[REDACTED]'
    
    if 'request' in event and 'query_string' in event['request']:
        query = event['request'].get('query_string', '')
        if 'token' in query.lower() or 'key' in query.lower():
            event['request']['query_string'] = '[REDACTED]'
    
    return event


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def get_request_id() -> str:
    return request_id_ctx.get()
