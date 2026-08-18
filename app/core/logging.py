import logging
import sys
import re


class SecretMasker(logging.Filter):
    def __init__(self, name=""):
        super().__init__(name)
        # Match common secret patterns (e.g. bearer tokens, passwords)
        self.patterns = [
            (re.compile(r'(?i)(password|secret|token|key|api_key)[\"\'\s]*[:=][\"\'\s]*([^\s\"\'\}]+)'), r'\1="***"'),
            (re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*'), 'Bearer ***')
        ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)
        return True

def setup_logging():
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        logger.addHandler(handler)
        
    # Apply filter to all handlers
    for handler in logger.handlers:
        handler.addFilter(SecretMasker())
        
    return logger

logger = setup_logging()
