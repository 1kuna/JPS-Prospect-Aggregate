#!/usr/bin/env python3
"""
Unit test for the pull source functionality.
This script tests the API endpoint for pulling a data source.
"""

import os
import sys
import json
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_pull_source(source_id):
    """Test the pull source API endpoint."""
    # Get the API URL from environment variables or use default
    api_url = os.getenv("API_URL", "http://localhost:5001/api")
    
    # Construct the endpoint URL
    endpoint = f"{api_url}/data-sources/{source_id}/pull"
    
    logger.info(f"Testing pull source API endpoint: {endpoint}")
    
    try:
        # Make the API request
        response = requests.post(endpoint, timeout=300)  # 5-minute timeout
        
        # Log the response status code
        logger.info(f"Response status code: {response.status_code}")
        
        # Try to parse the response as JSON
        try:
            response_data = response.json()
            logger.info(f"Response data: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse response as JSON: {response.text}")
            return False
        
        # Check if the request was successful
        if response.status_code == 200 and response_data.get("status") == "success":
            logger.info("Pull source test passed!")
            return True
        else:
            logger.error(f"Pull source test failed: {response_data.get('message', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return False

def get_data_sources():
    """Get all data sources from the API."""
    # Get the API URL from environment variables or use default
    api_url = os.getenv("API_URL", "http://localhost:5001/api")
    
    # Construct the endpoint URL
    endpoint = f"{api_url}/data-sources"
    
    logger.info(f"Getting data sources from API: {endpoint}")
    
    try:
        # Make the API request
        response = requests.get(endpoint)
        
        # Log the response status code
        logger.info(f"Response status code: {response.status_code}")
        
        # Try to parse the response as JSON
        try:
            response_data = response.json()
            return response_data.get("data", [])
        except json.JSONDecodeError:
            logger.error(f"Failed to parse response as JSON: {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return []

if __name__ == "__main__":
    # Get all data sources
    data_sources = get_data_sources()
    
    if not data_sources:
        logger.error("No data sources found!")
        sys.exit(1)
    
    # Print all data sources
    logger.info(f"Found {len(data_sources)} data sources:")
    for source in data_sources:
        logger.info(f"  - ID: {source['id']}, Name: {source['name']}")
    
    # Test pull source for each data source
    for source in data_sources:
        logger.info(f"Testing pull source for {source['name']} (ID: {source['id']})")
        success = test_pull_source(source['id'])
        logger.info(f"Pull source test for {source['name']} {'passed' if success else 'failed'}") 