import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

def setup_logger(name, log_dir, log_filename, level=logging.INFO):
    """
    Sets up a logger with:
    1. TimedRotatingFileHandler (Daily rotation, keeps 30 days)
    2. StreamHandler (Console output)
    """
    # 1. Ensure Log Directory Exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_path = os.path.join(log_dir, log_filename)
    
    # 2. Configure Logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Avoid duplicates
    
    # Clean up existing handlers to avoid duplicates on re-import
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # 3. Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 4. File Handler (Daily Rotation + Compression)
    # writes to 'filename', rotates to 'filename.YYYY-MM-DD.gz' at midnight
    file_handler = TimedRotatingFileHandler(
        log_path, when='midnight', interval=1, backupCount=90, encoding='utf-8'
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    
    # ✅ GZIP Compression Logic
    import gzip
    import shutil
    
    def namer(name):
        return name + ".gz"
    
    def rotator(source, dest):
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)
        
    file_handler.namer = namer
    file_handler.rotator = rotator

    logger.addHandler(file_handler)
    
    # 5. Stream Handler (Console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    return logger
