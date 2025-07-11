import requests # Or potentially use 'import ollama' if using the official client
import json
import os
from typing import Optional, Dict, Any
from app.utils.logger import logger

# --- Configuration ---
# Default Ollama API endpoint. Use environment variable if available.
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate" 
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
# Default timeout for the API request in seconds
DEFAULT_TIMEOUT = 240 # Adjust as needed, inference can be slow (Increased from 120)

# --- Main Ollama Interaction Function ---

def call_ollama(prompt: str, model_name: str, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Calls the Ollama /api/generate endpoint to get a completion for the given prompt.

    Args:
        prompt: The input prompt for the LLM.
        model_name: The name of the Ollama model to use (e.g., 'llama3:8b').
        options: Optional dictionary of Ollama parameters (e.g., temperature, top_p).

    Returns:
        The generated text content as a string, or None if an error occurs.
    """
    
    logger.debug(f"Attempting to call Ollama model '{model_name}'...")
    
    # 1. Construct the request payload
    # Ensure 'stream' is set to False to get the full response at once.
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False, 
        "options": options if options else {} # Add any custom options if provided
    }
    
    # 2. Make the HTTP POST request
    try:
        # --- Replace with actual API call ---
        # Example using 'requests' library:
        response = requests.post(
            OLLAMA_BASE_URL, 
            headers={'Content-Type': 'application/json'},
            json=payload, 
            timeout=DEFAULT_TIMEOUT 
        )
        
        # Example using 'ollama' library:
        # client = ollama.Client() # Consider initializing the client outside if calling repeatedly
        # response_data = client.generate(model=model_name, prompt=prompt, stream=False, options=options)
        # --- End API call example ---

        # 3. Check HTTP status code (if using requests)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # 4. Parse the JSON response
        response_data = response.json()
        
        # 5. Extract the generated text
        # The actual generated text is usually in the 'response' key for stream=False
        generated_text = response_data.get('response')
        
        if generated_text:
            logger.debug(f"Ollama response received successfully for model '{model_name}'.")
            return generated_text.strip()
        else:
            logger.warning(f"Ollama response for model '{model_name}' did not contain expected 'response' field. Full response: {response_data}")
            return None

    # 6. Handle Potential Errors
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error: Could not connect to Ollama at {OLLAMA_BASE_URL}. Is Ollama running? Error: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error: Request to Ollama timed out after {DEFAULT_TIMEOUT} seconds. Error: {e}")
        return None
    except requests.exceptions.RequestException as e: # Catch other requests errors (like HTTPError)
        logger.error(f"Request Error: Ollama API request failed. Status: {e.response.status_code if e.response else 'N/A'}. Response: {e.response.text if e.response else 'N/A'}. Error: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: Failed to parse Ollama response. Response text: {response.text}. Error: {e}")
        return None
    # Add error handling specific to the 'ollama' library if using that
    # except ollama.ResponseError as e: ... 
    except Exception as e:
        logger.error(f"Unexpected Error during Ollama call: {e}", exc_info=True)
        return None