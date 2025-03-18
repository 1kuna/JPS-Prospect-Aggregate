"""Common imports used throughout the application."""

# System imports
import os
import sys
import time
import traceback
import glob
import pathlib
import re
import shutil
import sqlite3

# Date and time
import datetime
from datetime import datetime, timedelta

# Data processing
import csv
import json
import pandas as pd
from io import StringIO

# Web and networking
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Logging
import logging
from logging.handlers import RotatingFileHandler

# Group imports for easier access
system = {
    'os': os,
    'sys': sys,
    'time': time,
    'traceback': traceback,
    'glob': glob,
    'pathlib': pathlib,
    're': re,
    'shutil': shutil,
    'sqlite3': sqlite3
}

datetime_utils = {
    'datetime': datetime,
    'timedelta': timedelta
}

data_processing = {
    'csv': csv,
    'json': json,
    'pandas': pd,
    'StringIO': StringIO
}

web = {
    'requests': requests,
    'RequestException': RequestException,
    'Timeout': Timeout,
    'RequestsConnectionError': RequestsConnectionError,
    'BeautifulSoup': BeautifulSoup,
    'sync_playwright': sync_playwright,
    'PlaywrightTimeoutError': PlaywrightTimeoutError
}

logging_utils = {
    'logging': logging,
    'RotatingFileHandler': RotatingFileHandler
}

# Export all modules directly for traditional imports
__all__ = [
    'os', 'sys', 'time', 'traceback', 'glob', 'pathlib', 're', 'shutil', 'sqlite3',
    'datetime', 'timedelta',
    'csv', 'json', 'pd', 'StringIO',
    'requests', 'RequestException', 'Timeout', 'RequestsConnectionError',
    'BeautifulSoup', 'sync_playwright', 'PlaywrightTimeoutError',
    'logging', 'RotatingFileHandler',
    'system', 'datetime_utils', 'data_processing', 'web', 'logging_utils'
] 