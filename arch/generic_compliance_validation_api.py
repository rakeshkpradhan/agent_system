
"""
Generic Multi-Policy Compliance Validation API
Flask API supporting unlimited compliance policies dynamically
"""

from flask import Flask, request, jsonify
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
import os

# Import the complete generic validation system
from generic_compliance_validation_system_part1 import *
from generic_compliance_validation_system_part2_fixed import *

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize generic validation system
config = GenericComplianceConfig()
workflow = GenericComplianceValidationWorkflow(config)

def serialize_enum(obj):
    """Helper to serialize enums for JSON response"""
    if hasattr(obj, 'value'):
        return obj.value
    return obj

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "generic_compliance_validation",
        "system_type": "multi_policy_universal",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    try:
        return jsonify({
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "langgraph_workflow": "ready",
                "vertex_ai_embeddings": "ready", 
                "gemini_2_5_pro": "ready",
                "spanner_graph": "ready",
                "alloydb_vector_store": "ready"
            },
            "system_capabilities": {
                "multi_policy_support": True,
                "auto_policy_detection": config.auto_policy_detection,
                "cross_policy_validation": config.cross_policy_validation,
                "supported_evidence_formats": config.supported_evidence_formats
            },
            "policy_categories": [
                "test_execution",
                "security_compliance", 
                "deployment_validation",
                "code_review",
                "documentation",
                "unlimited_extensibility"
            ]
        })
    except Exception as e:
        return jsonify({"status": "not_ready", "error": str(e)}), 503

@app.route('/validate/generic-compliance', methods=['POST'])
def validate_generic_compliance():
    """Universal compliance validation endpoint for any policy type"""
    try:
        data = request.get_json()

        if not data or 'confluence_url' not in data:
            return jsonify({
                "error": "Missing required field: confluence_url",
                "required_fields": ["confluence_url"],
                "optional_fields": ["change_request_id", "requested_policies"]
            }), 400

        confluence_url = data['confluence_url']
        change_request_id = data.get('change_request_id')
        requested_policies = data.get('requested_policies', [])

        logger.info(f"Starting generic validation for: {confluence_url}")
        if requested_policies:
            logger.info(f"Requested policies: {requested_policies}")

        # Execute async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                workflow.validate_generic_compliance(confluence_url, change_request_id, requested_policies)
            )
        finally:
            loop.close()

        # Format comprehensive response
        response = {
            "validation_request": {
                "change_request_id": result.change_request_id,
                "confluence_url": result.confluence_url,
                "requested_policies": result.requested_policies,
                "validation_timestamp": datetime.now().isoformat()
            },

            "generic_compliance_results": {
                "overall_status": serialize_enum(result.final_status),
                "confidence_score": result.confidence_score,

                # Policy discovery results
                "policy_discovery": {
                    "auto_detection_enabled": config.auto_policy_detection,
                    "detected_policies": [
                        {
                            "policy_id": policy.policy_id,
                            "policy_name": policy.policy_name,
                            "policy_category": policy.policy_category,
                            "version": policy.version,
                            "description": policy.description[:100] + "..." if len(policy.description) > 100 else policy.description
                        }
                        for policy in result.detected_policies
                    ],
                    "active_policy": {
                        "policy_id": result.active_policy.policy_id,
                        "policy_name": result.active_policy.policy_name,
                        "policy_category": result.active_policy.policy_category,
                        "version": result.active_policy.version
                    } if result.active_policy else None,
                    "cross_policy_references": result.cross_policy_references
                },

                # Evidence analysis results
                "evidence_analysis": {
                    "evidence_type": serialize_enum(result.evidence_type),
                    "evidence_components": {
                        component: {
                            "present": analysis.get("present", False),
                            "quality_score": analysis.get("quality_score", 0.0),
                            "relevance_score": analysis.get("relevance_score", 0.0),
                            "evidence_type_alignment": analysis.get("evidence_type_alignment", 0.0),
                            "content_length": analysis.get("content_length", 0),
                            "issues": analysis.get("issues", [])[:2],
                            "recommendations": analysis.get("recommendations", [])[:2]
                        }
                        for component, analysis in result.evidence_analysis.items()
                    }
                },

                # Rule assessment results
                "rule_assessments": {
                    rule_id: {
                        "rule_info": {
                            "rule_number": assessment["rule_info"]["rule_number"],
                            "rule_name": assessment["rule_info"]["rule_name"],
                            "rule_category": assessment["rule_info"]["rule_category"],
                            "severity_level": assessment["rule_info"]["severity_level"]
                        },
                        "evaluation_results": {
                            "status": assessment["evaluation_results"]["status"],
                            "confidence": assessment["evaluation_results"]["confidence"],
                            "assessment": assessment["evaluation_results"]["assessment"][:200] + "..." if len(assessment["evaluation_results"]["assessment"]) > 200 else assessment["evaluation_results"]["assessment"]
                        }
                    }
                    for rule_id, assessment in result.rule_assessments.items()
                },

                # Compliance decision
                "compliance_decision": {
                    "policy_specific_findings": result.compliance_decision.get("policy_specific_findings", []),
                    "evidence_quality_assessment": result.compliance_decision.get("evidence_quality_assessment", []),
                    "compliance_gaps": result.compliance_decision.get("compliance_gaps", []),
                    "recommendations": result.compliance_decision.get("recommendations", []),
                    "overall_rationale": result.compliance_decision.get("overall_rationale", "")[:500] + "..." if len(result.compliance_decision.get("overall_rationale", "")) > 500 else result.compliance_decision.get("overall_rationale", "")
                }
            },

            # Multi-policy results if applicable
            "multi_policy_results": result.multi_policy_results,

            # Processing metadata
            "processing_metadata": {
                "workflow_execution": {
                    "agents_executed": list(result.agent_traces.keys()),
                    "total_processing_time": _calculate_processing_time(result.timestamps),
                    "evidence_content_length": len(result.raw_evidence),
                    "similar_examples_retrieved": len(result.similar_evidence_examples),
                    "rag_context_length": len(result.rag_context)
                },
                "agent_traces": {
                    agent: {
                        "execution_time": trace.get("execution_time"),
                        "processing_summary": {k: v for k, v in trace.items() if k != "execution_time"}
                    }
                    for agent, trace in result.agent_traces.items()
                },
                "timestamps": result.timestamps
            }
        }

        # Include errors and warnings
        if result.error_messages:
            response["errors"] = result.error_messages

        if result.warnings:
            response["warnings"] = result.warnings

        logger.info(f"Generic validation completed: {serialize_enum(result.final_status)} (Confidence: {result.confidence_score:.2f})")

        return jsonify(response)

    except Exception as e:
        logger.error(f"Generic validation error: {str(e)}")
        return jsonify({
            "error": f"Generic validation failed: {str(e)}",
            "service": "generic_compliance_validation"
        }), 500

@app.route('/validate/policies/discover', methods=['POST'])
def discover_policies():
    """Policy discovery endpoint - identify applicable policies from evidence"""
    try:
        data = request.get_json()

        if not data or 'confluence_url' not in data:
            return jsonify({
                "error": "Missing required field: confluence_url"
            }), 400

        confluence_url = data['confluence_url']

        # Initialize agents for policy discovery only
        evidence_agent = EvidenceSummarizerAgent(config)
        policy_agent = PolicyDiscoveryAgent(config)

        # Create minimal state for discovery
        state = GenericValidationState()
        state.confluence_url = confluence_url

        # Execute discovery workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Step 1: Summarize evidence
            state = loop.run_until_complete(evidence_agent.process(state))

            # Step 2: Discover policies
            state = loop.run_until_complete(policy_agent.process(state))
        finally:
            loop.close()

        return jsonify({
            "confluence_url": confluence_url,
            "policy_discovery_results": {
                "evidence_type": serialize_enum(state.evidence_type),
                "auto_detection_used": not state.requested_policies,
                "detected_policies": [
                    {
                        "policy_id": policy.policy_id,
                        "policy_name": policy.policy_name,
                        "policy_category": policy.policy_category,
                        "version": policy.version,
                        "description": policy.description,
                        "status": policy.status
                    }
                    for policy in state.detected_policies
                ],
                "applicable_rules_count": len(state.applicable_rules),
                "cross_policy_references": state.cross_policy_references,
                "policy_context": state.policy_context
            },
            "discovery_timestamp": datetime.now().isoformat(),
            "service": "generic_policy_discovery"
        })

    except Exception as e:
        logger.error(f"Policy discovery error: {str(e)}")
        return jsonify({
            "error": f"Policy discovery failed: {str(e)}"
        }), 500

@app.route('/policies/catalog', methods=['GET'])
def get_policies_catalog():
    """Get catalog of all available compliance policies"""
    try:
        # This would typically query Spanner Graph for all available policies
        # For demo purposes, return example policy catalog

        policy_categories = [
            {
                "category": "test_execution",
                "description": "Test execution and quality assurance policies",
                "example_policies": [
                    {
                        "policy_id": "POL-101",
                        "policy_name": "Test_Execution",
                        "description": "Comprehensive test execution compliance including scripts, data, plans, outcomes, and defects",
                        "version": "1.0"
                    }
                ]
            },
            {
                "category": "security_compliance",
                "description": "Security assessment and compliance policies",
                "example_policies": [
                    {
                        "policy_id": "POL-201",
                        "policy_name": "Security_Compliance",
                        "description": "Security scanning, vulnerability assessment, and security review compliance",
                        "version": "1.0"
                    }
                ]
            },
            {
                "category": "deployment_validation", 
                "description": "Deployment procedures and infrastructure policies",
                "example_policies": [
                    {
                        "policy_id": "POL-301",
                        "policy_name": "Deployment_Validation",
                        "description": "Deployment procedures, rollback plans, and infrastructure validation",
                        "version": "1.0"
                    }
                ]
            },
            {
                "category": "code_review",
                "description": "Code review and quality assurance policies",
                "example_policies": [
                    {
                        "policy_id": "POL-401",
                        "policy_name": "Code_Review",
                        "description": "Code review processes, static analysis, and quality gates",
                        "version": "1.0"
                    }
                ]
            },
            {
                "category": "documentation",
                "description": "Technical documentation and knowledge management policies",
                "example_policies": [
                    {
                        "policy_id": "POL-501",
                        "policy_name": "Documentation",
                        "description": "Technical documentation, API documentation, and user guides",
                        "version": "1.0"
                    }
                ]
            }
        ]

        return jsonify({
            "policy_catalog": {
                "total_categories": len(policy_categories),
                "categories": policy_categories,
                "system_features": {
                    "unlimited_extensibility": True,
                    "auto_policy_detection": True,
                    "cross_policy_validation": True,
                    "dynamic_rule_loading": True
                }
            },
            "catalog_retrieved_at": datetime.now().isoformat(),
            "service": "generic_policy_catalog"
        })

    except Exception as e:
        logger.error(f"Policy catalog error: {str(e)}")
        return jsonify({
            "error": f"Failed to retrieve policy catalog: {str(e)}"
        }), 500

def _calculate_processing_time(timestamps: Dict[str, str]) -> str:
    """Calculate processing time"""
    if 'workflow_start' in timestamps and 'workflow_complete' in timestamps:
        try:
            start = datetime.fromisoformat(timestamps['workflow_start'])
            end = datetime.fromisoformat(timestamps['workflow_complete'])
            return str(end - start)
        except ValueError:
            return "unknown"
    return "incomplete"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Generic Multi-Policy Compliance Validation API on port {port}")
    logger.info("System: Universal compliance validation supporting unlimited policies")
    app.run(host='0.0.0.0', port=port, debug=False)
