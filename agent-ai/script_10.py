# Create Flask API Application
flask_api_code = '''"""
Flask API Application for Agentic AI Compliance Verification System.

Provides REST API endpoints for compliance verification with comprehensive
error handling, validation, and monitoring capabilities.
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, g
from werkzeug.exceptions import BadRequest, InternalServerError

from ..models.data_models import ComplianceRequest, ComplianceResult
from ..core.workflow import ComplianceWorkflow
from ..core.config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.update({
    'JSON_SORT_KEYS': False,
    'JSONIFY_PRETTYPRINT_REGULAR': True,
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024  # 16MB max request size
})

# Global workflow instance
workflow: Optional[ComplianceWorkflow] = None


@app.before_first_request
def initialize_application():
    """Initialize the application on first request."""
    global workflow
    
    try:
        logger.info("Initializing Agentic AI Compliance Verification System")
        
        # Validate configuration
        if not config.validate_config():
            raise ValueError("Configuration validation failed")
        
        # Initialize workflow
        workflow = ComplianceWorkflow()
        
        logger.info("Application initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise


@app.before_request
def before_request():
    """Before request processing."""
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', f"req_{int(time.time())}")
    
    # Log request details
    logger.info(f"Request {g.request_id}: {request.method} {request.endpoint} from {request.remote_addr}")


@app.after_request
def after_request(response):
    """After request processing."""
    # Calculate request duration
    duration = time.time() - g.start_time
    
    # Log response details
    logger.info(f"Request {g.request_id}: {response.status_code} in {duration:.3f}s")
    
    # Add custom headers
    response.headers['X-Request-ID'] = g.request_id
    response.headers['X-Processing-Time'] = f"{duration:.3f}s"
    response.headers['X-Service'] = 'agentic-compliance-system'
    
    return response


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for system monitoring.
    
    Returns:
        JSON response with system health status
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'service': 'agentic-compliance-system',
            'workflow_initialized': workflow is not None
        }
        
        # Add configuration summary (non-sensitive)
        health_status['config'] = {
            'project_id': config.project_id,
            'location': config.vertex_ai_location,
            'embedding_model': config.embedding_model_name,
            'llm_model': config.llm_model_name
        }
        
        # Add workflow info if available
        if workflow:
            health_status['workflow'] = workflow.get_workflow_info()
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/validate', methods=['POST'])
async def validate_compliance():
    """
    Main compliance validation endpoint.
    
    Expected JSON Input:
    {
        "policy_name": "Regression Testing Policy",
        "evidence_url": "https://confluence.example.com/wiki/spaces/PROJ/pages/12345/Evidence"
    }
    
    Returns:
        JSON response with compliance decision and analysis
    """
    try:
        # Validate workflow initialization
        if not workflow:
            logger.error("Workflow not initialized")
            return jsonify({
                'error': 'System not ready',
                'message': 'Compliance verification system is not properly initialized',
                'request_id': g.request_id
            }), 503
        
        # Parse and validate request
        request_data = _parse_and_validate_request()
        
        # Create compliance request object
        compliance_request = ComplianceRequest(
            policy_name=request_data['policy_name'],
            evidence_url=request_data['evidence_url']
        )
        
        logger.info(f"Processing compliance validation request: {compliance_request.request_id}")
        
        # Execute workflow
        result = await workflow.execute_compliance_verification(compliance_request)
        
        # Convert result to API response format
        response_data = _format_api_response(result)
        
        # Log completion
        logger.info(f"Request {g.request_id} completed: {result.decision.value} "
                   f"(confidence: {result.confidence_score:.2f})")
        
        return jsonify(response_data), 200
        
    except BadRequest as e:
        logger.warning(f"Bad request {g.request_id}: {str(e)}")
        return jsonify({
            'error': 'Invalid request',
            'message': str(e),
            'request_id': g.request_id
        }), 400
        
    except Exception as e:
        logger.error(f"Request {g.request_id} failed: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred during compliance verification',
            'request_id': g.request_id
        }), 500


@app.route('/config', methods=['GET'])
def get_configuration():
    """
    Get system configuration (non-sensitive information only).
    
    Returns:
        JSON response with system configuration
    """
    try:
        config_info = config.get_all_config()
        
        # Remove sensitive information
        safe_config = {k: v for k, v in config_info.items() 
                      if not any(sensitive in k.lower() 
                                for sensitive in ['token', 'key', 'secret', 'password'])}
        
        return jsonify({
            'config': safe_config,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': g.request_id
        }), 200
        
    except Exception as e:
        logger.error(f"Configuration request failed: {str(e)}")
        return jsonify({
            'error': 'Configuration retrieval failed',
            'message': str(e),
            'request_id': g.request_id
        }), 500


@app.route('/stats', methods=['GET'])
def get_system_stats():
    """
    Get system statistics and agent information.
    
    Returns:
        JSON response with system statistics
    """
    try:
        stats = {
            'workflow_info': workflow.get_workflow_info() if workflow else None,
            'agent_stats': workflow.get_agent_stats() if workflow else None,
            'system_info': {
                'config_valid': config.validate_config(),
                'workflow_ready': workflow is not None,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats request failed: {str(e)}")
        return jsonify({
            'error': 'Statistics retrieval failed',
            'message': str(e),
            'request_id': g.request_id
        }), 500


def _parse_and_validate_request() -> Dict[str, Any]:
    """Parse and validate incoming request data."""
    # Check content type
    if not request.is_json:
        raise BadRequest("Request must be JSON")
    
    # Parse JSON
    try:
        request_data = request.get_json()
    except Exception:
        raise BadRequest("Invalid JSON format")
    
    if not request_data:
        raise BadRequest("Empty request body")
    
    # Validate required fields
    required_fields = ['policy_name', 'evidence_url']
    missing_fields = [field for field in required_fields if field not in request_data]
    
    if missing_fields:
        raise BadRequest(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate field values
    policy_name = request_data['policy_name'].strip()
    evidence_url = request_data['evidence_url'].strip()
    
    if not policy_name:
        raise BadRequest("policy_name cannot be empty")
    
    if not evidence_url:
        raise BadRequest("evidence_url cannot be empty")
    
    # Basic URL validation
    if not any(evidence_url.startswith(proto) for proto in ['http://', 'https://']):
        raise BadRequest("evidence_url must be a valid HTTP/HTTPS URL")
    
    return {
        'policy_name': policy_name,
        'evidence_url': evidence_url
    }


def _format_api_response(result: ComplianceResult) -> Dict[str, Any]:
    """Format ComplianceResult for API response."""
    return {
        'policy_name': result.policy_name,
        'decision': result.decision.value,
        'confidence_score': result.confidence_score,
        'analysis_summary': result.analysis_summary,
        'rule_assessments': [
            {
                'rule_id': assessment.rule_id,
                'rule_description': assessment.rule_description,
                'status': assessment.status.value,
                'evidence_quote': assessment.evidence_quote,
                'confidence_score': assessment.confidence_score
            }
            for assessment in result.rule_assessments
        ],
        'evidence_id': result.evidence_id,
        'request_id': result.request_id,
        'timestamp': result.timestamp,
        'processing_time_seconds': result.processing_time_seconds
    }


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Endpoint not found',
        'message': f"The requested endpoint {request.endpoint} does not exist",
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        'error': 'Method not allowed',
        'message': f"Method {request.method} not allowed for endpoint {request.endpoint}",
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 405


@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle request size limit errors."""
    return jsonify({
        'error': 'Request too large',
        'message': 'Request exceeds maximum allowed size',
        'request_id': getattr(g, 'request_id', 'unknown')
    }), 413


if __name__ == '__main__':
    # Development server - DO NOT use in production
    print("🚀 Starting Agentic AI Compliance Verification System")
    print("⚠️  This is a development server. Use WSGI server for production.")
    
    app.run(
        host=config.flask_host,
        port=config.flask_port,
        debug=config.flask_debug
    )
'''

with open("agentic_compliance_system/api/flask_app.py", "w") as f:
    f.write(flask_api_code)

print("✅ Created Flask API Application")