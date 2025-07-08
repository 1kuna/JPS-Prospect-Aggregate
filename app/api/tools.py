"""
Tools API endpoints for executing system scripts with admin permissions.
"""

import subprocess
import threading
import queue
import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.api.auth import admin_required
from app.utils.logger import logger
from dataclasses import dataclass, asdict
from enum import Enum

tools_bp = Blueprint('tools', __name__, url_prefix='/api/tools')

class ScriptCategory(Enum):
    DATA_COLLECTION = "Data Collection"
    DATA_ENHANCEMENT = "Data Enhancement"
    EXPORT_ANALYSIS = "Export & Analysis"
    MAINTENANCE = "Maintenance & Cleanup"
    DATABASE_SETUP = "Database Setup"

@dataclass
class ScriptParameter:
    name: str
    type: str  # 'string', 'number', 'boolean', 'choice'
    required: bool = False
    default: Optional[str] = None
    description: Optional[str] = None
    choices: Optional[List[str]] = None

@dataclass
class ScriptConfig:
    id: str
    name: str
    description: str
    script_path: str
    category: ScriptCategory
    parameters: List[ScriptParameter] = None
    dangerous: bool = False
    requires_confirmation: bool = False
    timeout: int = 300  # 5 minutes default

    def to_dict(self):
        data = asdict(self)
        data['category'] = self.category.value
        return data

# Script configurations
SCRIPT_CONFIGS = [
    # Data Collection
    ScriptConfig(
        id="run_all_scrapers",
        name="Run All Scrapers",
        description="Execute all configured web scrapers to collect prospect data from government sources",
        script_path="scripts/run_all_scrapers.py",
        category=ScriptCategory.DATA_COLLECTION,
        timeout=1800  # 30 minutes
    ),
    ScriptConfig(
        id="test_individual_scraper",
        name="Test Individual Scraper",
        description="Test a specific scraper or all scrapers without the web server",
        script_path="scripts/test_scraper_individual.py",
        category=ScriptCategory.DATA_COLLECTION,
        parameters=[
            ScriptParameter(
                name="scraper",
                type="choice",
                required=True,
                description="Scraper to test",
                choices=['all', 'dhs', 'treasury', 'state', 'justice', 'labor', 
                        'commerce', 'hhs', 'ssa', 'interior', 'transportation', 
                        'va', 'gsa', 'nrc', 'acquisition_gateway']
            )
        ]
    ),
    ScriptConfig(
        id="run_scraper_tests",
        name="Run Scraper Test Suite",
        description="Run comprehensive test suite for all scrapers",
        script_path="scripts/run_scraper_tests.py",
        category=ScriptCategory.DATA_COLLECTION,
        parameters=[
            ScriptParameter(
                name="verbose",
                type="boolean",
                default="false",
                description="Enable verbose output"
            ),
            ScriptParameter(
                name="scraper",
                type="string",
                required=False,
                description="Test specific scraper only"
            )
        ]
    ),
    ScriptConfig(
        id="validate_file_naming",
        name="Validate File Naming",
        description="Check data file naming conventions for consistency",
        script_path="scripts/validate_file_naming.py",
        category=ScriptCategory.DATA_COLLECTION
    ),
    
    # Data Enhancement
    ScriptConfig(
        id="llm_enhancement",
        name="LLM Enhancement",
        description="Enhance prospect data using AI (requires Ollama with qwen3 model)",
        script_path="scripts/enrichment/enhance_prospects_with_llm.py",
        category=ScriptCategory.DATA_ENHANCEMENT,
        parameters=[
            ScriptParameter(
                name="mode",
                type="choice",
                required=True,
                description="Enhancement mode",
                choices=['values', 'contacts', 'titles', 'naics', 'all', '--check-status'],
                default="--check-status"
            ),
            ScriptParameter(
                name="limit",
                type="number",
                required=False,
                description="Number of prospects to process (empty for all)"
            ),
            ScriptParameter(
                name="dry_run",
                type="boolean",
                default="false",
                description="Preview without saving changes"
            )
        ],
        timeout=3600  # 1 hour for large batches
    ),
    
    # Export & Analysis
    ScriptConfig(
        id="export_decisions",
        name="Export Decisions for LLM",
        description="Export go/no-go decisions for machine learning training",
        script_path="scripts/export_decisions_for_llm.py",
        category=ScriptCategory.EXPORT_ANALYSIS,
        parameters=[
            ScriptParameter(
                name="format",
                type="choice",
                required=False,
                default="jsonl",
                description="Export format",
                choices=['jsonl', 'csv', 'both']
            ),
            ScriptParameter(
                name="reasons_only",
                type="boolean",
                default="false",
                description="Only export decisions with reasons"
            )
        ]
    ),
    ScriptConfig(
        id="export_database_csv",
        name="Export Database to CSV",
        description="Export prospects and inferred data to CSV files",
        script_path="scripts/utils/export_db_to_csv.py",
        category=ScriptCategory.EXPORT_ANALYSIS
    ),
    
    # Maintenance & Cleanup
    ScriptConfig(
        id="data_retention",
        name="Data Retention Cleanup",
        description="Clean up old data files to manage storage (keeps most recent files per source)",
        script_path="app/utils/data_retention.py",
        category=ScriptCategory.MAINTENANCE,
        parameters=[
            ScriptParameter(
                name="execute",
                type="boolean",
                default="false",
                description="Execute cleanup (default is dry-run preview)"
            ),
            ScriptParameter(
                name="retention_count",
                type="number",
                default="3",
                description="Number of recent files to keep per source"
            )
        ],
        dangerous=True,
        requires_confirmation=True
    ),
    ScriptConfig(
        id="health_check",
        name="Database Health Check",
        description="Test database connectivity and scraper functionality",
        script_path="scripts/health_check.py",
        category=ScriptCategory.MAINTENANCE
    ),
    ScriptConfig(
        id="backfill_file_logs",
        name="Backfill File Logs",
        description="Create file processing logs for existing data files",
        script_path="scripts/backfill_file_logs.py",
        category=ScriptCategory.MAINTENANCE
    ),
    
    # Database Setup
    ScriptConfig(
        id="setup_databases",
        name="Complete Database Setup",
        description="Initialize databases, run migrations, and populate initial data",
        script_path="scripts/setup_databases.py",
        category=ScriptCategory.DATABASE_SETUP,
        dangerous=True,
        requires_confirmation=True
    ),
    ScriptConfig(
        id="init_user_database",
        name="Initialize User Database",
        description="Set up user authentication database",
        script_path="scripts/init_user_database.py",
        category=ScriptCategory.DATABASE_SETUP,
        dangerous=True,
        requires_confirmation=True
    ),
    ScriptConfig(
        id="populate_data_sources",
        name="Populate Data Sources",
        description="Add all configured agency data sources to database",
        script_path="scripts/populate_data_sources.py",
        category=ScriptCategory.DATABASE_SETUP
    ),
    ScriptConfig(
        id="migrate_data_directories",
        name="Migrate Data Directories",
        description="Handle data directory structure migrations",
        script_path="scripts/migrate_data_directories.py",
        category=ScriptCategory.DATABASE_SETUP
    ),
    ScriptConfig(
        id="standardize_naics",
        name="Standardize NAICS Codes",
        description="Format all NAICS codes to standard format",
        script_path="scripts/migrations/standardize_naics_formatting.py",
        category=ScriptCategory.DATABASE_SETUP
    )
]

# Create lookup dictionary
SCRIPTS_BY_ID = {script.id: script for script in SCRIPT_CONFIGS}

# Running scripts tracking
running_scripts: Dict[str, dict] = {}
script_lock = threading.Lock()


def build_command(script_config: ScriptConfig, parameters: dict) -> List[str]:
    """Build command line arguments for script execution."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / script_config.script_path
    
    # Start with python and script path
    cmd = [sys.executable, str(script_path)]
    
    # Add parameters
    if script_config.parameters:
        for param in script_config.parameters:
            value = parameters.get(param.name)
            
            # Skip if not provided and not required
            if value is None and not param.required:
                continue
                
            # Handle different parameter types
            if param.type == 'boolean':
                if value in ['true', True, '1', 'yes']:
                    if param.name == 'execute':
                        cmd.append('--execute')
                    elif param.name == 'verbose':
                        cmd.append('--verbose')
                    elif param.name == 'dry_run':
                        cmd.append('--dry-run')
                    elif param.name == 'reasons_only':
                        cmd.append('--reasons-only')
            elif param.name == 'mode' and script_config.id == 'llm_enhancement':
                # Special handling for LLM enhancement mode
                if value == '--check-status':
                    cmd.append('--check-status')
                else:
                    cmd.append(value)
            else:
                # String, number, or choice parameters
                if param.name == 'scraper':
                    cmd.extend(['--scraper', str(value)])
                elif param.name == 'format':
                    cmd.extend(['--format', str(value)])
                elif param.name == 'limit':
                    cmd.extend(['--limit', str(value)])
                elif param.name == 'retention_count':
                    cmd.extend(['--retention-count', str(value)])
    
    return cmd


def execute_script_with_streaming(execution_id: str, script_config: ScriptConfig, 
                                parameters: dict, output_queue: queue.Queue):
    """Execute a script and stream output to queue."""
    try:
        # Build command
        cmd = build_command(script_config, parameters)
        logger.info(f"Executing script {script_config.id}: {' '.join(cmd)}")
        
        # Update status
        with script_lock:
            running_scripts[execution_id]['status'] = 'running'
            running_scripts[execution_id]['command'] = ' '.join(cmd)
        
        # Execute script
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=Path(__file__).parent.parent.parent  # Project root
        )
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            if line:
                output_queue.put(('output', line.rstrip()))
                with script_lock:
                    running_scripts[execution_id]['output'].append(line.rstrip())
        
        # Wait for completion
        return_code = process.wait()
        
        # Update final status
        with script_lock:
            if return_code == 0:
                running_scripts[execution_id]['status'] = 'completed'
                output_queue.put(('status', 'completed'))
            else:
                running_scripts[execution_id]['status'] = 'failed'
                running_scripts[execution_id]['error'] = f'Process exited with code {return_code}'
                output_queue.put(('error', f'Process exited with code {return_code}'))
                
    except Exception as e:
        logger.error(f"Error executing script {script_config.id}: {str(e)}")
        with script_lock:
            running_scripts[execution_id]['status'] = 'error'
            running_scripts[execution_id]['error'] = str(e)
        output_queue.put(('error', str(e)))
    finally:
        output_queue.put(('done', None))


@tools_bp.route('/scripts', methods=['GET'])
@admin_required
def list_scripts():
    """Get list of available scripts organized by category."""
    try:
        # Group scripts by category
        scripts_by_category = {}
        for script in SCRIPT_CONFIGS:
            category = script.category.value
            if category not in scripts_by_category:
                scripts_by_category[category] = []
            scripts_by_category[category].append(script.to_dict())
        
        return jsonify({
            'status': 'success',
            'data': {
                'scripts': scripts_by_category,
                'categories': [cat.value for cat in ScriptCategory]
            }
        })
    except Exception as e:
        logger.error(f"Error listing scripts: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to list scripts'
        }), 500


@tools_bp.route('/scripts/<script_id>', methods=['GET'])
@admin_required
def get_script_details(script_id):
    """Get detailed information about a specific script."""
    try:
        script = SCRIPTS_BY_ID.get(script_id)
        if not script:
            return jsonify({
                'status': 'error',
                'message': 'Script not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': script.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting script details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get script details'
        }), 500


@tools_bp.route('/execute/<script_id>', methods=['POST'])
@admin_required
def execute_script(script_id):
    """Execute a script with provided parameters."""
    try:
        script = SCRIPTS_BY_ID.get(script_id)
        if not script:
            return jsonify({
                'status': 'error',
                'message': 'Script not found'
            }), 404
        
        # Get parameters from request
        data = request.get_json() or {}
        parameters = data.get('parameters', {})
        
        # Generate execution ID
        import uuid
        execution_id = str(uuid.uuid4())
        
        # Initialize tracking
        with script_lock:
            running_scripts[execution_id] = {
                'id': execution_id,
                'script_id': script_id,
                'script_name': script.name,
                'status': 'pending',
                'output': [],
                'started_at': None,
                'parameters': parameters
            }
        
        # Create output queue
        output_queue = queue.Queue()
        
        # Start execution thread
        thread = threading.Thread(
            target=execute_script_with_streaming,
            args=(execution_id, script, parameters, output_queue)
        )
        thread.daemon = True
        thread.start()
        
        # Return execution ID for streaming
        return jsonify({
            'status': 'success',
            'data': {
                'execution_id': execution_id,
                'message': f'Started execution of {script.name}'
            }
        })
        
    except Exception as e:
        logger.error(f"Error executing script: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to execute script: {str(e)}'
        }), 500


@tools_bp.route('/stream/<execution_id>', methods=['GET'])
@admin_required
def stream_output(execution_id):
    """Stream script output using server-sent events."""
    def generate():
        # Check if execution exists
        with script_lock:
            if execution_id not in running_scripts:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Execution not found'})}\n\n"
                return
        
        # Create queue for this stream
        output_queue = queue.Queue()
        
        # Get current output
        with script_lock:
            execution = running_scripts[execution_id]
            for line in execution['output']:
                yield f"data: {json.dumps({'type': 'output', 'line': line})}\n\n"
        
        # Check if already completed
        if execution['status'] in ['completed', 'failed', 'error']:
            yield f"data: {json.dumps({'type': 'status', 'status': execution['status']})}\n\n"
            if 'error' in execution:
                yield f"data: {json.dumps({'type': 'error', 'message': execution['error']})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        
        # Wait for new output
        last_index = len(execution['output'])
        while True:
            try:
                # Check for new output
                with script_lock:
                    execution = running_scripts.get(execution_id)
                    if not execution:
                        break
                    
                    # Send any new lines
                    current_output = execution['output']
                    if len(current_output) > last_index:
                        for line in current_output[last_index:]:
                            yield f"data: {json.dumps({'type': 'output', 'line': line})}\n\n"
                        last_index = len(current_output)
                    
                    # Check if completed
                    if execution['status'] in ['completed', 'failed', 'error']:
                        yield f"data: {json.dumps({'type': 'status', 'status': execution['status']})}\n\n"
                        if 'error' in execution:
                            yield f"data: {json.dumps({'type': 'error', 'message': execution['error']})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        break
                
                # Small delay to prevent busy waiting
                import time
                time.sleep(0.1)
                
            except GeneratorExit:
                break
            except Exception as e:
                logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@tools_bp.route('/executions', methods=['GET'])
@admin_required
def list_executions():
    """List recent script executions."""
    try:
        with script_lock:
            # Get all executions sorted by start time
            executions = list(running_scripts.values())
            # Sort by started_at or status
            executions.sort(key=lambda x: x.get('started_at', ''), reverse=True)
            
            # Limit to recent executions
            recent_executions = executions[:20]
        
        return jsonify({
            'status': 'success',
            'data': {
                'executions': recent_executions,
                'total': len(executions)
            }
        })
    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to list executions'
        }), 500


@tools_bp.route('/executions/<execution_id>', methods=['GET'])
@admin_required
def get_execution_details(execution_id):
    """Get details of a specific execution."""
    try:
        with script_lock:
            execution = running_scripts.get(execution_id)
            if not execution:
                return jsonify({
                    'status': 'error',
                    'message': 'Execution not found'
                }), 404
        
        return jsonify({
            'status': 'success',
            'data': execution
        })
    except Exception as e:
        logger.error(f"Error getting execution details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get execution details'
        }), 500