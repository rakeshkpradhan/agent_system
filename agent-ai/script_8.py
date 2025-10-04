# Create Agent 4: Status Update Agent
agent4_code = '''"""
Agent 4: Status Update Agent (Persistence)

This agent is responsible for persisting final evaluation results by:
1. Updating vector store with validation status and assessment results
2. Creating final compliance result object with all metadata
3. Returning complete JSON output marking end of workflow execution
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..models.data_models import (
    WorkflowState, ComplianceResult, RuleAssessment, 
    ComplianceDecision, ValidationStatus
)
from ..services.external_services import SpannerVectorService
from ..core.config import config

logger = logging.getLogger(__name__)


class StatusUpdateAgent:
    """
    Agent responsible for persisting evaluation results and creating final output.
    
    This agent performs two main tasks:
    1. Update Vector Store: Persist evaluation results to Spanner vector store
    2. Create Final Output: Generate complete compliance result object
    """
    
    def __init__(self):
        """Initialize the Status Update Agent."""
        self.vector_service = SpannerVectorService()
        
        logger.info("Initialized Status Update Agent")
    
    async def process(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main processing method for Status Update Agent.
        
        Args:
            state: Current workflow state with evaluation results
            
        Returns:
            Dictionary with final results and completion status
        """
        try:
            request = state.request
            llm_evaluation = state.llm_evaluation
            evidence_id = state.evidence_id
            
            logger.info("Persisting evaluation results and creating final output")
            state.add_message("Starting result persistence and finalization")
            
            # Task 1: Update Vector Store
            update_success = self._update_vector_store(evidence_id, llm_evaluation)
            if update_success:
                state.add_message("Successfully updated vector store with evaluation results")
            else:
                state.add_message("Warning: Failed to update vector store, but continuing...")
            
            # Task 2: Create Final Output
            final_result = self._create_final_result(request, llm_evaluation, evidence_id, state)
            state.add_message(f"Created final compliance result: {final_result.decision.value}")
            
            return {
                'final_result': final_result,
                'vector_store_updated': update_success,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"StatusUpdateAgent failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            
            # Create error result for graceful failure handling
            error_result = self._create_error_result(state.request, str(e))
            return {
                'final_result': error_result,
                'error': error_msg,
                'success': False
            }
    
    def _update_vector_store(self, evidence_id: str, evaluation_result: Dict[str, Any]) -> bool:
        """
        Task 1: Update Vector Store with final evaluation results.
        
        Updates the evidence document record in Spanner vector store with
        validation status, rule assessments, and analysis summary.
        
        Args:
            evidence_id: Unique ID of the evidence document
            evaluation_result: LLM evaluation results to persist
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            logger.info(f"Updating vector store for evidence ID: {evidence_id}")
            
            if not evidence_id:
                logger.warning("No evidence ID provided, skipping vector store update")
                return False
            
            # Use vector service to update document status
            success = self.vector_service.update_document_status(evidence_id, evaluation_result)
            
            if success:
                logger.info(f"Successfully updated evidence {evidence_id} with validation status: "
                           f"{evaluation_result['decision']}")
            else:
                logger.error(f"Failed to update evidence {evidence_id} in vector store")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update vector store: {str(e)}")
            return False
    
    def _create_final_result(self, request: Any, evaluation_result: Dict[str, Any], 
                           evidence_id: str, state: WorkflowState) -> ComplianceResult:
        """
        Task 2: Create Final Output with complete compliance result.
        
        Converts LLM evaluation results into structured ComplianceResult object
        with all necessary metadata and processing information.
        
        Args:
            request: Original compliance request
            evaluation_result: LLM evaluation results
            evidence_id: Evidence document ID
            state: Current workflow state
            
        Returns:
            Complete ComplianceResult object
        """
        try:
            logger.info("Creating final compliance result object")
            
            # Convert rule assessments to RuleAssessment objects
            rule_assessments = []
            for assessment_data in evaluation_result.get('rule_assessments', []):
                try:
                    rule_assessment = RuleAssessment(
                        rule_id=assessment_data.get('rule_id', 'unknown'),
                        rule_description=assessment_data.get('rule_description', ''),
                        status=ComplianceDecision(assessment_data.get('status', 'Indeterminate')),
                        evidence_quote=assessment_data.get('evidence_quote', ''),
                        confidence_score=float(assessment_data.get('confidence_score', 0.0))
                    )
                    rule_assessments.append(rule_assessment)
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid rule assessment: {str(e)}")
                    continue
            
            # Create final compliance result
            final_result = ComplianceResult(
                policy_name=request.policy_name,
                decision=ComplianceDecision(evaluation_result['decision']),
                confidence_score=float(evaluation_result['confidence_score']),
                analysis_summary=evaluation_result['analysis_summary'],
                rule_assessments=rule_assessments,
                evidence_id=evidence_id,
                request_id=request.request_id,
                processing_time_seconds=state.get_processing_time()
            )
            
            # Log final result summary
            logger.info(f"Final compliance result created: {final_result.decision.value} "
                       f"(confidence: {final_result.confidence_score:.2f}, "
                       f"{len(final_result.rule_assessments)} rule assessments, "
                       f"processing time: {final_result.processing_time_seconds:.2f}s)")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Failed to create final result: {str(e)}")
            raise
    
    def _create_error_result(self, request: Any, error_message: str) -> ComplianceResult:
        """Create error result for graceful failure handling."""
        try:
            logger.info("Creating error compliance result")
            
            error_result = ComplianceResult(
                policy_name=getattr(request, 'policy_name', 'Unknown'),
                decision=ComplianceDecision.INDETERMINATE,
                confidence_score=0.0,
                analysis_summary=f"Compliance verification failed due to system error: {error_message}",
                rule_assessments=[],
                request_id=getattr(request, 'request_id', None),
                processing_time_seconds=0.0
            )
            
            return error_result
            
        except Exception as e:
            logger.error(f"Failed to create error result: {str(e)}")
            
            # Minimal fallback result
            return ComplianceResult(
                policy_name="Unknown",
                decision=ComplianceDecision.INDETERMINATE,
                confidence_score=0.0,
                analysis_summary="System error occurred during compliance verification",
                rule_assessments=[]
            )
    
    def _calculate_overall_compliance(self, rule_assessments: List[RuleAssessment]) -> ComplianceDecision:
        """Calculate overall compliance decision from individual rule assessments."""
        if not rule_assessments:
            return ComplianceDecision.INDETERMINATE
        
        # Count assessment results
        compliant_count = sum(1 for r in rule_assessments if r.status == ComplianceDecision.COMPLIANT)
        non_compliant_count = sum(1 for r in rule_assessments if r.status == ComplianceDecision.NON_COMPLIANT)
        indeterminate_count = sum(1 for r in rule_assessments if r.status == ComplianceDecision.INDETERMINATE)
        
        total_assessments = len(rule_assessments)
        
        # Decision logic
        if non_compliant_count > 0:
            # Any non-compliant rule results in overall non-compliance
            return ComplianceDecision.NON_COMPLIANT
        elif compliant_count == total_assessments:
            # All rules compliant
            return ComplianceDecision.COMPLIANT
        elif indeterminate_count == total_assessments:
            # All rules indeterminate
            return ComplianceDecision.INDETERMINATE
        else:
            # Mixed compliant and indeterminate - conservative approach
            return ComplianceDecision.INDETERMINATE
    
    def _validate_evaluation_result(self, evaluation_result: Dict[str, Any]) -> bool:
        """Validate evaluation result structure before processing."""
        required_fields = ['decision', 'confidence_score', 'analysis_summary', 'rule_assessments']
        
        for field in required_fields:
            if field not in evaluation_result:
                logger.error(f"Missing required field in evaluation result: {field}")
                return False
        
        # Validate decision value
        try:
            ComplianceDecision(evaluation_result['decision'])
        except ValueError:
            logger.error(f"Invalid decision value: {evaluation_result['decision']}")
            return False
        
        # Validate confidence score
        try:
            score = float(evaluation_result['confidence_score'])
            if not (0.0 <= score <= 1.0):
                logger.error(f"Confidence score out of range: {score}")
                return False
        except (ValueError, TypeError):
            logger.error("Invalid confidence score format")
            return False
        
        return True
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring."""
        return {
            'agent_name': 'StatusUpdateAgent',
            'vector_store_service': 'SpannerVectorStore',
            'result_validation': True,
            'error_handling': True
        }
'''

with open("agentic_compliance_system/agents/status_update_agent.py", "w") as f:
    f.write(agent4_code)

print("✅ Created Agent 4: Status Update Agent")