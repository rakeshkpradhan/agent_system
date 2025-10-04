"""
Agent 3: Policy Evaluation Agent (Decision Making)

This agent uses Gemini 2.5 Pro LLM to perform core compliance analysis by:
1. Building detailed evaluation prompt with role, rules, evidence, and context
2. Querying LLM with JSON mode enabled for structured output
3. Parsing and validating the compliance decision response
"""

import logging
import json
from typing import Dict, Any
from datetime import datetime

from ..models.data_models import WorkflowState, PolicyRule, ComplianceDecision
from ..services.external_services import VertexAIService
from ..core.config import config

logger = logging.getLogger(__name__)


class PolicyEvaluationAgent:
    """
    Agent responsible for LLM-based compliance evaluation using Gemini 2.5 Pro.

    This agent performs three main tasks:
    1. Build Evaluation Prompt: Create structured zero-shot prompt for LLM
    2. Query LLM: Send prompt to Gemini 2.5 Pro with JSON mode enabled
    3. Parse and Validate: Process and validate JSON response structure
    """

    def __init__(self):
        """Initialize the Policy Evaluation Agent."""
        self.vertex_service = VertexAIService()

        logger.info("Initialized Policy Evaluation Agent")

    async def process(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main processing method for Policy Evaluation Agent.

        Args:
            state: Current workflow state

        Returns:
            Dictionary with processing results and updated state
        """
        try:
            policy_rules = state.policy_rules
            evidence_documents = state.evidence_documents
            rag_context = state.rag_context

            logger.info("Starting LLM-based compliance evaluation")
            state.add_message("Starting policy evaluation with Gemini 2.5 Pro")

            # Task 1: Build Evaluation Prompt
            prompt = self._build_evaluation_prompt(policy_rules, evidence_documents, rag_context)
            state.add_message(f"Built evaluation prompt ({len(prompt)} characters)")

            # Task 2: Query LLM
            llm_response = self._query_llm(prompt)
            state.add_message(f"Received LLM response: {llm_response.get('decision', 'unknown')}")

            # Task 3: Parse and Validate
            validated_response = self._parse_and_validate(llm_response)
            state.add_message(f"Validated response with {len(validated_response.get('rule_assessments', []))} rule assessments")

            return {
                'llm_evaluation': validated_response,
                'success': True
            }

        except Exception as e:
            error_msg = f"PolicyEvaluationAgent failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return {
                'error': error_msg,
                'success': False
            }

    def _build_evaluation_prompt(self, policy_rules: List[PolicyRule], 
                                evidence_documents: List[Any], rag_context: str) -> str:
        """
        Task 1: Build Evaluation Prompt for LLM.

        Constructs a detailed, structured zero-shot prompt including role definition,
        policy rules, evidence content, context, and output format specification.

        Args:
            policy_rules: List of policy rules to evaluate against
            evidence_documents: Evidence documents to analyze
            rag_context: Assembled RAG context from previous agent

        Returns:
            Structured prompt string for LLM
        """
        try:
            logger.info("Building comprehensive evaluation prompt for LLM")

            # Combine evidence content
            evidence_content = self._format_evidence_content(evidence_documents)

            # Define JSON output schema
            output_schema = self._get_output_schema()

            # Build comprehensive prompt
            prompt = f"""You are an expert compliance auditor with deep knowledge of organizational policies and regulatory requirements. Your task is to determine if the provided evidence complies with the given policy rules.

ROLE AND GOAL:
You are conducting a thorough compliance audit. Analyze the evidence document against each specific policy rule. For each rule, determine compliance status and provide supporting evidence quotes. Make an overall compliance decision based on all rule assessments with appropriate confidence scoring.

POLICY RULES TO EVALUATE:
{self._format_policy_rules_for_prompt(policy_rules)}

EVIDENCE TO ANALYZE:
{evidence_content}

CONTEXTUAL INFORMATION:
{rag_context}

EVALUATION INSTRUCTIONS:
1. Review each policy rule carefully and understand its specific requirements
2. Search through the evidence for information relevant to each rule
3. For each rule, determine one of the following statuses:
   - "Compliant": Evidence clearly demonstrates rule satisfaction with supporting quotes
   - "Non-Compliant": Evidence shows rule violation or clearly insufficient compliance
   - "Indeterminate": Insufficient evidence to make a determination
4. Provide direct quotes from evidence supporting your assessment for each rule
5. Calculate an overall confidence score (0.0-1.0) based on:
   - Evidence quality and completeness
   - Clarity of compliance indicators
   - Number of rules with clear determinations
6. Write a comprehensive analysis summary explaining your overall decision
7. Consider rule severity and type when making overall compliance determination

CRITICAL REQUIREMENTS:
- Use ONLY information explicitly present in the provided evidence
- Quote exact text from evidence to support each rule assessment
- If evidence is missing for a rule, mark as "Indeterminate" with explanation
- Be objective, thorough, and conservative in your analysis
- Consider the severity and criticality of different rules in overall decision
- Ensure confidence score reflects evidence quality and assessment certainty

OUTPUT FORMAT:
Your response MUST be a valid JSON object matching this exact schema:
{json.dumps(output_schema, indent=2)}

Begin your detailed compliance analysis now:"""

            logger.info(f"Built evaluation prompt with {len(prompt)} characters")
            return prompt

        except Exception as e:
            logger.error(f"Failed to build evaluation prompt: {str(e)}")
            raise

    def _format_evidence_content(self, evidence_documents: List[Any]) -> str:
        """Format evidence documents for prompt inclusion."""
        if not evidence_documents:
            return "No evidence documents provided for analysis."

        evidence_parts = []
        for i, doc in enumerate(evidence_documents[:20], 1):  # Limit to prevent prompt overflow
            content = doc.content if hasattr(doc, 'content') else str(doc)

            # Add document metadata if available
            metadata_info = ""
            if hasattr(doc, 'metadata'):
                section = doc.metadata.section_header
                content_type = doc.metadata.content_type
                if section:
                    metadata_info = f" (Section: {section})"
                elif content_type:
                    metadata_info = f" (Type: {content_type})"

            evidence_parts.append(f"Document {i}{metadata_info}:\n{content}")

        return '\n\n'.join(evidence_parts)

    def _format_policy_rules_for_prompt(self, policy_rules: List[PolicyRule]) -> str:
        """Format policy rules for prompt inclusion."""
        if not policy_rules:
            return """No specific policy rules found. Evaluate based on general compliance best practices:
- Documentation completeness and accuracy
- Process adherence and quality standards  
- Risk management and security considerations
- Regulatory and industry standard compliance"""

        formatted_rules = []
        for i, rule in enumerate(policy_rules, 1):
            rule_text = f"""Rule {i}:
Rule ID: {rule.rule_id}
Description: {rule.rule_description}
Type: {rule.rule_type}
Severity: {rule.severity}
Validation Criteria: {rule.validation_criteria or 'General compliance assessment required'}
Policy Source: {rule.policy_name}"""

            formatted_rules.append(rule_text)

        return '\n\n'.join(formatted_rules)

    def _get_output_schema(self) -> Dict[str, Any]:
        """Get JSON output schema for LLM response validation."""
        return {
            "type": "object",
            "properties": {
                "policy_name": {
                    "type": "string",
                    "description": "Name of the policy being evaluated"
                },
                "decision": {
                    "type": "string",
                    "enum": ["Compliant", "Non-Compliant", "Indeterminate"],
                    "description": "Overall compliance decision"
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Confidence in the decision (0.0-1.0)"
                },
                "analysis_summary": {
                    "type": "string",
                    "description": "Comprehensive summary of the compliance analysis"
                },
                "rule_assessments": {
                    "type": "array",
                    "description": "Individual assessments for each policy rule",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {
                                "type": "string",
                                "description": "Identifier of the rule being assessed"
                            },
                            "rule_description": {
                                "type": "string", 
                                "description": "Description of the rule requirements"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["Compliant", "Non-Compliant", "Indeterminate"],
                                "description": "Compliance status for this specific rule"
                            },
                            "evidence_quote": {
                                "type": "string",
                                "description": "Direct quote from evidence supporting the assessment"
                            },
                            "confidence_score": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence in this rule assessment"
                            }
                        },
                        "required": ["rule_id", "rule_description", "status", "evidence_quote"]
                    }
                }
            },
            "required": ["policy_name", "decision", "confidence_score", "analysis_summary", "rule_assessments"]
        }

    def _query_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Task 2: Query LLM (Gemini 2.5 Pro) with JSON mode enabled.

        Sends the constructed prompt to Gemini 2.5 Pro and awaits structured response.

        Args:
            prompt: Structured evaluation prompt

        Returns:
            Parsed JSON response from LLM
        """
        try:
            logger.info("Querying Gemini 2.5 Pro for compliance evaluation")

            # Use Vertex AI service to query LLM
            llm_response = self.vertex_service.evaluate_compliance(prompt)

            # Log response summary
            decision = llm_response.get('decision', 'unknown')
            confidence = llm_response.get('confidence_score', 0.0)
            num_assessments = len(llm_response.get('rule_assessments', []))

            logger.info(f"LLM evaluation completed: {decision} (confidence: {confidence:.2f}, "
                       f"{num_assessments} rule assessments)")

            return llm_response

        except Exception as e:
            logger.error(f"LLM query failed: {str(e)}")
            raise

    def _parse_and_validate(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task 3: Parse and Validate LLM response structure.

        Validates the JSON response against expected schema and ensures data quality.

        Args:
            llm_response: Raw response from LLM

        Returns:
            Validated and cleaned response
        """
        try:
            logger.info("Parsing and validating LLM response")

            # Validate response structure
            validation_errors = self._validate_response_structure(llm_response)

            if validation_errors:
                logger.error(f"Response validation failed: {', '.join(validation_errors)}")
                raise ValueError(f"LLM response validation failed: {', '.join(validation_errors)}")

            # Clean and normalize response
            cleaned_response = self._clean_response(llm_response)

            logger.info("Response validation completed successfully")
            return cleaned_response

        except Exception as e:
            logger.error(f"Response validation failed: {str(e)}")
            raise

    def _validate_response_structure(self, response: Dict[str, Any]) -> List[str]:
        """Validate LLM response structure and return list of errors."""
        errors = []

        # Check required top-level fields
        required_fields = ['policy_name', 'decision', 'confidence_score', 'analysis_summary', 'rule_assessments']
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")

        # Validate decision values
        valid_decisions = [d.value for d in ComplianceDecision]
        if response.get('decision') not in valid_decisions:
            errors.append(f"Invalid decision value: {response.get('decision')}")

        # Validate confidence score
        try:
            score = float(response.get('confidence_score', -1))
            if not (0.0 <= score <= 1.0):
                errors.append(f"Confidence score out of range: {score}")
        except (ValueError, TypeError):
            errors.append("Invalid confidence score format")

        # Validate rule assessments
        rule_assessments = response.get('rule_assessments', [])
        if not isinstance(rule_assessments, list):
            errors.append("rule_assessments must be a list")
        else:
            for i, assessment in enumerate(rule_assessments):
                if not isinstance(assessment, dict):
                    errors.append(f"Rule assessment {i} must be an object")
                    continue

                required_rule_fields = ['rule_id', 'rule_description', 'status', 'evidence_quote']
                for field in required_rule_fields:
                    if field not in assessment:
                        errors.append(f"Rule assessment {i} missing field: {field}")

                if assessment.get('status') not in valid_decisions:
                    errors.append(f"Rule assessment {i} has invalid status: {assessment.get('status')}")

        return errors

    def _clean_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize LLM response."""
        cleaned = response.copy()

        # Ensure confidence score is float
        try:
            cleaned['confidence_score'] = float(cleaned['confidence_score'])
        except (ValueError, TypeError):
            cleaned['confidence_score'] = 0.0

        # Clean rule assessments
        if 'rule_assessments' in cleaned:
            for assessment in cleaned['rule_assessments']:
                # Ensure confidence score exists for each rule
                if 'confidence_score' not in assessment:
                    assessment['confidence_score'] = cleaned['confidence_score']
                else:
                    try:
                        assessment['confidence_score'] = float(assessment['confidence_score'])
                    except (ValueError, TypeError):
                        assessment['confidence_score'] = 0.5

                # Trim long evidence quotes
                if len(assessment.get('evidence_quote', '')) > 1000:
                    assessment['evidence_quote'] = assessment['evidence_quote'][:997] + '...'

        return cleaned

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring."""
        return {
            'agent_name': 'PolicyEvaluationAgent',
            'llm_model': config.llm_model_name,
            'json_mode_enabled': True,
            'response_validation': True
        }
