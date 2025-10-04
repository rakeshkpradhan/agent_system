# Create LangGraph Workflow Orchestrator
workflow_code = '''"""
LangGraph Workflow Orchestrator for Agentic AI Compliance Verification System.

This module implements the state machine workflow using LangGraph to orchestrate
collaboration between specialized agents in the compliance verification pipeline.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from ..models.data_models import WorkflowState, ComplianceRequest, ComplianceResult
from ..agents.evidence_summarizer_agent import EvidenceSummarizerAgent
from ..agents.control_retrieval_agent import ControlRetrievalAgent
from ..agents.policy_evaluation_agent import PolicyEvaluationAgent
from ..agents.status_update_agent import StatusUpdateAgent
from ..core.config import config

logger = logging.getLogger(__name__)


class ComplianceWorkflow:
    """
    LangGraph-based workflow orchestrator for compliance verification.
    
    Implements the state machine: Data Ingestion → Context Retrieval → Policy Evaluation → Status Update → END
    """
    
    def __init__(self):
        """Initialize the compliance verification workflow."""
        logger.info("Initializing Compliance Workflow Orchestrator")
        
        # Initialize specialized agents
        self.evidence_agent = EvidenceSummarizerAgent()
        self.retrieval_agent = ControlRetrievalAgent()
        self.evaluation_agent = PolicyEvaluationAgent()
        self.status_agent = StatusUpdateAgent()
        
        # Build and compile the workflow graph
        self.graph = self._build_workflow_graph()
        
        logger.info("Compliance workflow initialized successfully")
    
    def _build_workflow_graph(self) -> StateGraph:
        """
        Build the LangGraph state machine for compliance verification.
        
        Workflow: Data Ingestion → Context Retrieval → Policy Evaluation → Status Update → END
        
        Returns:
            Compiled StateGraph ready for execution
        """
        logger.info("Building LangGraph workflow")
        
        # Create the workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add agent nodes
        workflow.add_node("data_ingestion", self._data_ingestion_node)
        workflow.add_node("context_retrieval", self._context_retrieval_node)
        workflow.add_node("policy_evaluation", self._policy_evaluation_node)
        workflow.add_node("status_update", self._status_update_node)
        
        # Define workflow edges (sequential execution)
        workflow.add_edge(START, "data_ingestion")
        workflow.add_edge("data_ingestion", "context_retrieval")
        workflow.add_edge("context_retrieval", "policy_evaluation")
        workflow.add_edge("policy_evaluation", "status_update")
        workflow.add_edge("status_update", END)
        
        # Compile the graph
        compiled_graph = workflow.compile()
        
        logger.info("LangGraph workflow compiled successfully")
        return compiled_graph
    
    async def _data_ingestion_node(self, state: WorkflowState) -> WorkflowState:
        """
        Data Ingestion node - Evidence Summarizer Agent.
        
        Fetches, parses, and stores evidence from Confluence.
        """
        try:
            logger.info("Executing Data Ingestion node")
            
            # Process with Evidence Summarizer Agent
            result = await self.evidence_agent.process(state)
            
            # Update state with results
            if result.get('success'):
                state.evidence_documents = result['evidence_documents']
                state.evidence_id = result['evidence_id']
                state.add_message("Data ingestion completed successfully")
            else:
                state.set_error(result.get('error', 'Data ingestion failed'))
            
            return state
            
        except Exception as e:
            error_msg = f"Data ingestion node failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return state
    
    async def _context_retrieval_node(self, state: WorkflowState) -> WorkflowState:
        """
        Context Retrieval node - Control Retrieval Agent.
        
        Gathers policy rules and similar evidence for RAG context.
        """
        if state.error:
            return state  # Skip if previous node failed
        
        try:
            logger.info("Executing Context Retrieval node")
            
            # Process with Control Retrieval Agent
            result = await self.retrieval_agent.process(state)
            
            # Update state with results
            if result.get('success'):
                state.policy_rules = result['policy_rules']
                state.similar_evidences = result['similar_evidences']
                state.rag_context = result['rag_context']
                state.add_message("Context retrieval completed successfully")
            else:
                state.set_error(result.get('error', 'Context retrieval failed'))
            
            return state
            
        except Exception as e:
            error_msg = f"Context retrieval node failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return state
    
    async def _policy_evaluation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Policy Evaluation node - Policy Evaluation Agent.
        
        Uses Gemini 2.5 Pro LLM for compliance analysis.
        """
        if state.error:
            return state  # Skip if previous node failed
        
        try:
            logger.info("Executing Policy Evaluation node")
            
            # Process with Policy Evaluation Agent
            result = await self.evaluation_agent.process(state)
            
            # Update state with results
            if result.get('success'):
                state.llm_evaluation = result['llm_evaluation']
                state.add_message("Policy evaluation completed successfully")
            else:
                state.set_error(result.get('error', 'Policy evaluation failed'))
            
            return state
            
        except Exception as e:
            error_msg = f"Policy evaluation node failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return state
    
    async def _status_update_node(self, state: WorkflowState) -> WorkflowState:
        """
        Status Update node - Status Update Agent.
        
        Persists results and creates final compliance output.
        """
        if state.error:
            # Even with errors, try to create a result
            logger.warning("Executing Status Update node with previous errors")
        
        try:
            logger.info("Executing Status Update node")
            
            # Process with Status Update Agent
            result = await self.status_agent.process(state)
            
            # Update state with final results
            state.final_result = result['final_result']
            
            if result.get('success'):
                state.add_message("Status update and result finalization completed successfully")
            else:
                # Error result was created
                state.add_message("Status update completed with errors, error result created")
            
            return state
            
        except Exception as e:
            error_msg = f"Status update node failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            
            # Create minimal error result
            from ..models.data_models import ComplianceResult, ComplianceDecision
            state.final_result = ComplianceResult(
                policy_name=state.request.policy_name,
                decision=ComplianceDecision.INDETERMINATE,
                confidence_score=0.0,
                analysis_summary=f"Workflow execution failed: {error_msg}",
                rule_assessments=[],
                request_id=state.request.request_id
            )
            
            return state
    
    async def execute_compliance_verification(self, request: ComplianceRequest) -> ComplianceResult:
        """
        Execute the complete compliance verification workflow.
        
        Args:
            request: ComplianceRequest with policy name and evidence URL
            
        Returns:
            ComplianceResult with final compliance decision and analysis
        """
        try:
            logger.info(f"Starting compliance verification workflow for request: {request.request_id}")
            
            # Initialize workflow state
            initial_state = WorkflowState(request=request)
            initial_state.add_message(f"Starting compliance verification for policy: {request.policy_name}")
            
            # Execute the workflow graph
            logger.info("Invoking LangGraph workflow execution")
            final_state = await self.graph.ainvoke(initial_state)
            
            # Extract final result
            if final_state.final_result:
                result = final_state.final_result
                
                # Log workflow completion
                logger.info(f"Compliance verification completed: {result.decision.value} "
                           f"(confidence: {result.confidence_score:.2f}, "
                           f"processing time: {result.processing_time_seconds:.2f}s)")
                
                # Log workflow messages for debugging
                if config.enable_debug_logging:
                    logger.debug("Workflow execution messages:")
                    for message in final_state.messages:
                        logger.debug(f"  {message}")
                
                return result
            else:
                # Fallback if no result was created
                logger.error("Workflow completed but no final result was generated")
                raise ValueError("Workflow execution failed to produce result")
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            
            # Create error result for graceful failure
            from ..models.data_models import ComplianceResult, ComplianceDecision
            error_result = ComplianceResult(
                policy_name=request.policy_name,
                decision=ComplianceDecision.INDETERMINATE,
                confidence_score=0.0,
                analysis_summary=f"Compliance verification system error: {str(e)}",
                rule_assessments=[],
                request_id=request.request_id
            )
            
            return error_result
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration."""
        return {
            'workflow_type': 'LangGraph State Machine',
            'agents': [
                'EvidenceSummarizerAgent',
                'ControlRetrievalAgent', 
                'PolicyEvaluationAgent',
                'StatusUpdateAgent'
            ],
            'workflow_sequence': [
                'data_ingestion',
                'context_retrieval',
                'policy_evaluation', 
                'status_update'
            ],
            'error_handling': 'Graceful degradation with error results',
            'state_persistence': 'In-memory during execution'
        }
    
    def get_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all agents."""
        return {
            'evidence_summarizer': self.evidence_agent.get_processing_stats(),
            'control_retrieval': self.retrieval_agent.get_processing_stats(),
            'policy_evaluation': self.evaluation_agent.get_processing_stats(),
            'status_update': self.status_agent.get_processing_stats()
        }
'''

with open("agentic_compliance_system/core/workflow.py", "w") as f:
    f.write(workflow_code)

print("✅ Created LangGraph Workflow Orchestrator")