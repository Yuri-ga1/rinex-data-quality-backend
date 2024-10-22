# Constants
ELEVATION = 10
FILE_BASE_PATH = f"files"
UPLOAD_RINEX_URL = 'https://services.simurg.space/rinex-to-csv/upload_rinex'
UPLOAD_NAV_URL = 'https://services.simurg.space/rinex-to-csv/upload_nav'
RUN_URL = 'https://services.simurg.space/rinex-to-csv/run'
RESULT_URL = 'https://services.simurg.space/rinex-to-csv/get_result'

from custom_logger import Logger
import logging
import os

logger = Logger(
    filename= os.path.join('tmp', 'rinex_data_quality_logger.log'),
    console_logging=True,
    file_logging_level= logging.DEBUG
)

import redis
try:
    redis_client = redis.Redis(host='redis', port=6379, db=0)
except:
    logger.critical("Redis client is not working")