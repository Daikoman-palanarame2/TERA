import logging
import sys

def setup_logging() -> None:
    """
    Sets up the logging configuration for the TERA backend.
    Configures standard output streaming and formats logs.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate log messages if run multiple times
    if logger.hasHandlers():
        logger.handlers.clear()
        
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Stream handler for stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # Configure specific library log levels if needed
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
