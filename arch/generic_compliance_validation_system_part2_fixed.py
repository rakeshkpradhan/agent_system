
"""
Generic Multi-Policy Compliance Validation System - Part 2 (Fixed)
Completing the universal implementation with remaining agents and orchestration

This file continues from generic_compliance_validation_system_part1.py
"""

# Continue imports from Part 1
from generic_compliance_validation_system_part1 import *

# ====== CONTINUED AGENT IMPLEMENTATIONS ======

class ComplianceRetrievalAgent:
    """Universal agent for hybrid compliance context retrieval across all policies"""

    def __init__(self, config: GenericComplianceConfig):
        self.config = config
        self.spanner_client = spanner.Client(project=config.project_id)
        self.embeddings = VertexAIEmbeddings(
            model_name=config.embedding_model,
            project=config.project_id
        )

    async def process(self, state: GenericValidationState) -> GenericValidationState:
        """Execute hybrid retrieval for any compliance policy"""

        state.timestamps["compliance_retrieval_start"] = datetime.now().isoformat()

        try:
            if not state.active_policy:
                state.warnings.append("No active policy found, using generic retrieval")
                return state

            # Step 1: Execute hybrid retrieval strategy
            retrieval_results = await self._execute_hybrid_retrieval(
                state.evidence_components,
                state.active_policy,
                state.applicable_rules
            )

            # Step 2: Extract similar evidence examples
            state.similar_evidence_examples = retrieval_results["vector_results"]

            # Step 3: Build comprehensive RAG context
            state.rag_context = await self._build_comprehensive_rag_context(
                state.active_policy,
                state.applicable_rules,
                state.similar_evidence_examples,
                state.evidence_analysis
            )

            # Step 4: Handle cross-policy context if applicable
            if state.cross_policy_references and self.config.cross_policy_validation:
                cross_policy_context = await self._build_cross_policy_context(
                    state.cross_policy_references
                )
                state.rag_context += "\n\n=== CROSS-POLICY CONTEXT ===\n" + cross_policy_context

            # Step 5: Store processing trace
            state.agent_traces["compliance_retrieval"] = {
                "policy_id": state.active_policy.policy_id,
                "rules_processed": len(state.applicable_rules),
                "similar_examples_found": len(state.similar_evidence_examples),
                "retrieval_strategy": "hybrid_graph_vector",
                "cross_policy_enabled": bool(state.cross_policy_references),
                "rag_context_length": len(state.rag_context),
                "execution_time": datetime.now().isoformat()
            }

            state.timestamps["compliance_retrieval_complete"] = datetime.now().isoformat()

        except Exception as e:
            error_msg = f"Compliance retrieval failed: {str(e)}"
            state.error_messages.append(error_msg)
            logger.error(error_msg)

        return state

    async def _execute_hybrid_retrieval(self, evidence_components: Dict[str, str],
                                       policy: CompliancePolicyModel,
                                       rules: List[ComplianceRuleModel]) -> Dict[str, Any]:
        """Execute hybrid retrieval combining graph and vector approaches"""

        # Parallel execution of graph and vector retrieval
        graph_task = self._graph_retrieval(policy.policy_id, rules)
        vector_task = self._vector_retrieval(evidence_components, policy.policy_category)

        # Execute both strategies concurrently
        graph_results, vector_results = await asyncio.gather(graph_task, vector_task)

        return {
            "graph_results": graph_results,
            "vector_results": vector_results,
            "hybrid_strategy": "parallel_execution",
            "retrieval_timestamp": datetime.now().isoformat()
        }

    async def _graph_retrieval(self, policy_id: str, 
                              rules: List[ComplianceRuleModel]) -> Dict[str, Any]:
        """Structured retrieval from Spanner Graph for policy-specific rules"""

        try:
            instance = self.spanner_client.instance(self.config.spanner_instance_id)
            database = instance.database(self.config.spanner_database_id)

            # Complex GQL query for comprehensive rule context
            gql_query = """
            GRAPH ComplianceGraph
            MATCH (policy:CompliancePolicy {policy_id: $policy_id})-[:CONTAINS]->(rule:ComplianceRule)
            OPTIONAL MATCH (rule)-[:HAS_CRITERIA]->(criteria:ValidationCriteria)
            OPTIONAL MATCH (rule)-[:REQUIRES_EVIDENCE]->(evidence:EvidenceType)
            OPTIONAL MATCH (policy)-[:REFERENCES]->(ref_policy:CompliancePolicy)
            OPTIONAL MATCH (rule)-[:DEPENDS_ON]->(dep_rule:ComplianceRule)

            RETURN 
                rule.rule_id,
                rule.rule_name,
                rule.description,
                rule.validation_criteria,
                rule.severity_level,
                ARRAY_AGG(DISTINCT criteria.criteria_name) as validation_criteria_list,
                ARRAY_AGG(DISTINCT evidence.evidence_type) as required_evidence_types,
                ARRAY_AGG(DISTINCT ref_policy.policy_name) as referenced_policies,
                ARRAY_AGG(DISTINCT dep_rule.rule_name) as dependent_rules
            ORDER BY rule.rule_number
            """

            with database.snapshot() as snapshot:
                results = snapshot.execute_sql(gql_query, params={"policy_id": policy_id})

                structured_rules = []
                for row in results:
                    rule_context = {
                        "rule_id": row[0],
                        "rule_name": row[1],
                        "description": row[2],
                        "validation_criteria": json.loads(row[3]) if row[3] else {},
                        "severity_level": row[4],
                        "validation_criteria_list": [c for c in row[5] if c] if row[5] else [],
                        "required_evidence_types": [e for e in row[6] if e] if row[6] else [],
                        "referenced_policies": [p for p in row[7] if p] if row[7] else [],
                        "dependent_rules": [r for r in row[8] if r] if row[8] else []
                    }
                    structured_rules.append(rule_context)

                return {
                    "retrieval_type": "knowledge_graph",
                    "source": "spanner_graph",
                    "policy_id": policy_id,
                    "rules_retrieved": len(structured_rules),
                    "structured_rules": structured_rules,
                    "graph_traversal_depth": 2,
                    "retrieval_timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.warning(f"Graph retrieval failed: {str(e)}, using rule list fallback")
            return {
                "retrieval_type": "fallback_rules",
                "source": "local_rules",
                "structured_rules": [
                    {
                        "rule_id": rule.rule_id,
                        "rule_name": rule.rule_name,
                        "description": rule.description,
                        "validation_criteria": rule.validation_criteria,
                        "severity_level": rule.severity_level
                    }
                    for rule in rules
                ]
            }

    async def _vector_retrieval(self, evidence_components: Dict[str, str],
                               policy_category: str) -> List[Dict[str, Any]]:
        """Semantic retrieval from AlloyDB vector store for similar evidence"""

        try:
            # Combine evidence components for embedding
            combined_evidence = " ".join([
                f"{component}: {content}" 
                for component, content in evidence_components.items() 
                if content and content.upper() not in ['NOT_FOUND', 'MISSING']
            ])

            if not combined_evidence.strip():
                return []

            # Generate query embedding
            query_embedding = self.embeddings.embed_query(combined_evidence)

            # Connect to AlloyDB
            connector = Connector()

            def getconn():
                return connector.connect(
                    self.config.alloydb_instance,
                    "pg8000",
                    user=self.config.alloydb_user,
                    password=self.config.alloydb_password,
                    db=self.config.alloydb_database
                )

            # Multi-domain vector similarity search
            with getconn() as conn:
                cursor = conn.cursor()

                # Enhanced similarity query with policy category filtering
                similarity_query = """
                SELECT 
                    id,
                    evidence_text,
                    evidence_type,
                    policy_context,
                    domain_category,
                    compliance_outcome,
                    evidence_metadata,
                    policy_mappings,
                    source_url,
                    (embedding <=> %s::vector) as similarity_distance
                FROM multi_domain_evidence_embeddings 
                WHERE domain_category = %s OR policy_context LIKE %s
                    AND (embedding <=> %s::vector) < %s
                ORDER BY similarity_distance
                LIMIT %s
                """

                cursor.execute(similarity_query, [
                    str(query_embedding),
                    policy_category,
                    f"%{policy_category}%",
                    str(query_embedding),
                    1.0 - self.config.similarity_threshold,
                    self.config.max_retrieved_examples
                ])

                results = cursor.fetchall()
                similar_examples = []

                for row in results:
                    example = {
                        "id": row[0],
                        "evidence_text": row[1][:800] + "..." if len(row[1]) > 800 else row[1],
                        "evidence_type": row[2],
                        "policy_context": row[3],
                        "domain_category": row[4],
                        "compliance_outcome": row[5],
                        "evidence_metadata": row[6] if row[6] else {},
                        "policy_mappings": row[7] if row[7] else {},
                        "source_url": row[8],
                        "similarity_score": 1.0 - row[9]  # Convert distance to similarity
                    }
                    similar_examples.append(example)

                return similar_examples

        except Exception as e:
            logger.warning(f"Vector retrieval failed: {str(e)}")
            return []

    async def _build_comprehensive_rag_context(self, policy: CompliancePolicyModel,
                                             rules: List[ComplianceRuleModel],
                                             similar_examples: List[Dict[str, Any]],
                                             evidence_analysis: Dict[str, Dict[str, Any]]) -> str:
        """Build comprehensive RAG context for any policy type"""

        context_sections = []

        # Section 1: Policy Context
        context_sections.append(f"=== COMPLIANCE POLICY CONTEXT ===")
        context_sections.append(f"Policy ID: {policy.policy_id}")
        context_sections.append(f"Policy Name: {policy.policy_name}")
        context_sections.append(f"Policy Category: {policy.policy_category}")
        context_sections.append(f"Description: {policy.description}")
        context_sections.append(f"Version: {policy.version}")
        context_sections.append(f"Status: {policy.status}")

        # Section 2: Evidence Analysis Summary
        context_sections.append("\n=== CURRENT EVIDENCE ANALYSIS ===")
        for component, analysis in evidence_analysis.items():
            present = "✓ PRESENT" if analysis.get("present", False) else "✗ MISSING"
            quality = analysis.get("quality_score", 0.0)
            relevance = analysis.get("relevance_score", 0.0)

            context_sections.append(f"""
Component: {component.upper()}
Status: {present}
Quality Score: {quality:.2f}
Relevance Score: {relevance:.2f}
Issues: {'; '.join(analysis.get('issues', [])[:2])}
Summary: {analysis.get('content_summary', 'No summary')[:200]}
""")

        # Section 3: Applicable Compliance Rules
        context_sections.append("\n=== APPLICABLE COMPLIANCE RULES ===")
        for rule in rules:
            context_sections.append(f"""
Rule {rule.rule_number}: {rule.rule_name}
Description: {rule.description}
Category: {rule.rule_category}
Severity: {rule.severity_level}
Validation Criteria: {json.dumps(rule.validation_criteria, indent=2)}
""")

        # Section 4: Similar Evidence Examples
        if similar_examples:
            context_sections.append("\n=== SIMILAR EVIDENCE EXAMPLES ===")
            for i, example in enumerate(similar_examples[:4], 1):  # Limit to top 4
                context_sections.append(f"""
Example {i} (Similarity: {example.get('similarity_score', 0.0):.2f}):
Policy Context: {example.get('policy_context', 'Unknown')}
Evidence Type: {example.get('evidence_type', 'General')}
Compliance Outcome: {example.get('compliance_outcome', 'UNKNOWN')}
Domain Category: {example.get('domain_category', 'General')}
Content: {example.get('evidence_text', 'No content')}
""")

        return "\n".join(context_sections)

    async def _build_cross_policy_context(self, cross_references: List[Dict[str, Any]]) -> str:
        """Build context for cross-policy relationships"""

        if not cross_references:
            return ""

        context_sections = []
        context_sections.append("Cross-Policy Relationships:")

        for ref in cross_references:
            context_sections.append(f"""
Source Policy: {ref.get('source_policy', 'Unknown')}
Target Policy: {ref.get('target_policy', 'Unknown')}
Relationship Type: {ref.get('reference_type', 'Unknown')}
Relationship: {ref.get('relationship', 'Unknown')}
""")

        return "\n".join(context_sections)


class GenericEvaluationAgent:
    """Universal agent for policy-agnostic compliance evaluation using Gemini 2.5 Pro"""

    def __init__(self, config: GenericComplianceConfig):
        self.config = config
        self.llm = GenerativeModel(config.llm_model)

    async def process(self, state: GenericValidationState) -> GenericValidationState:
        """Execute generic compliance evaluation for any policy type"""

        state.timestamps["generic_evaluation_start"] = datetime.now().isoformat()

        try:
            if not state.active_policy:
                state.error_messages.append("No active policy for evaluation")
                return state

            # Step 1: Create policy-specific evaluation prompt
            state.enhanced_prompt = await self._build_generic_evaluation_prompt(
                state.active_policy,
                state.applicable_rules,
                state.rag_context,
                state.evidence_components
            )

            # Step 2: Execute LLM evaluation
            response = await self.llm.generate_content_async(state.enhanced_prompt)
            state.llm_response = response.text

            # Step 3: Parse generic compliance decision
            state.compliance_decision = await self._parse_generic_compliance_decision(
                state.llm_response, state.active_policy
            )

            # Step 4: Process individual rule assessments
            state.rule_assessments = await self._process_rule_assessments(
                state.compliance_decision, state.applicable_rules
            )

            # Step 5: Determine final status and confidence
            state.final_status = ComplianceStatus(
                state.compliance_decision.get("overall_status", "REQUIRES_REVIEW")
            )
            state.confidence_score = state.compliance_decision.get("confidence_score", 0.0)

            # Step 6: Handle multi-policy results if applicable
            if len(state.detected_policies) > 1:
                state.multi_policy_results[state.active_policy.policy_id] = {
                    "status": state.final_status.value,
                    "confidence": state.confidence_score,
                    "rule_count": len(state.rule_assessments)
                }

            # Step 7: Store processing trace
            state.agent_traces["generic_evaluation"] = {
                "policy_id": state.active_policy.policy_id,
                "policy_category": state.active_policy.policy_category,
                "rules_evaluated": len(state.rule_assessments),
                "final_status": state.final_status.value,
                "confidence_score": state.confidence_score,
                "prompt_length": len(state.enhanced_prompt),
                "response_length": len(state.llm_response),
                "evaluation_method": "policy_agnostic_llm",
                "execution_time": datetime.now().isoformat()
            }

            state.timestamps["generic_evaluation_complete"] = datetime.now().isoformat()

        except Exception as e:
            error_msg = f"Generic evaluation failed: {str(e)}"
            state.error_messages.append(error_msg)
            state.final_status = ComplianceStatus.ERROR
            logger.error(error_msg)

        return state

    async def _build_generic_evaluation_prompt(self, policy: CompliancePolicyModel,
                                             rules: List[ComplianceRuleModel],
                                             rag_context: str,
                                             evidence_components: Dict[str, str]) -> str:
        """Build universal evaluation prompt adaptable to any policy type"""

        # Create rule summary for prompt
        rules_summary = "\n".join([
            f"Rule {rule.rule_number}: {rule.rule_name} - {rule.description} (Severity: {rule.severity_level})"
            for rule in rules
        ])

        # Create individual rule analysis template
        rule_analysis_template = "\n".join([
            f"Rule {rule.rule_number} - {rule.rule_name}: [COMPLIANT/NON_COMPLIANT/REQUIRES_REVIEW]\n"
            f"Assessment: [Specific analysis based on evidence and rule requirements]\n"
            f"Evidence_Reference: [Reference specific evidence components that support or contradict compliance]\n"
            f"Confidence: [0.0-1.0]\n"
            f"Severity_Impact: [How rule severity affects overall compliance]\n"
            for rule in rules
        ])

        return f"""
You are a Universal Compliance Expert capable of evaluating evidence against any compliance policy. 
Your task is to assess evidence compliance for the specified policy using comprehensive analysis.

**COMPLIANCE POLICY INFORMATION:**
Policy ID: {policy.policy_id}
Policy Name: {policy.policy_name}
Policy Category: {policy.policy_category}
Policy Description: {policy.description}
Policy Version: {policy.version}

**COMPLIANCE RULES TO EVALUATE:**
{rules_summary}

**COMPREHENSIVE CONTEXT FOR EVALUATION:**
{rag_context}

**CURRENT EVIDENCE TO EVALUATE:**
{json.dumps(evidence_components, indent=2)}

**UNIVERSAL EVALUATION REQUIREMENTS:**
1. Evaluate each rule individually based on the evidence provided
2. Consider policy-specific context and requirements
3. Use similar evidence examples as benchmarks for assessment
4. Provide specific evidence-based reasoning for each decision
5. Account for rule severity levels in overall assessment
6. Consider cross-policy implications if applicable

**REQUIRED RESPONSE FORMAT:**

OVERALL_STATUS: [COMPLIANT/NON_COMPLIANT/REQUIRES_REVIEW/PARTIAL_COMPLIANT]
CONFIDENCE_SCORE: [0.0-1.0]

RULE_BY_RULE_ANALYSIS:

{rule_analysis_template}

POLICY_SPECIFIC_FINDINGS:
- [List key findings specific to this policy category with evidence references]

EVIDENCE_QUALITY_ASSESSMENT:
- [Assess the quality and completeness of evidence for this policy type]

COMPLIANCE_GAPS:
- [List specific gaps or missing elements that prevent full compliance]

RECOMMENDATIONS:
- [Provide actionable recommendations to achieve full compliance for this policy]

OVERALL_RATIONALE:
[Comprehensive explanation of the overall compliance decision, considering:
- Policy-specific requirements and context
- Evidence quality and completeness relative to policy expectations
- Rule severity levels and their cumulative impact
- Similar case patterns and benchmarking
- Domain-specific compliance standards
- Cross-policy implications if applicable]

**CRITICAL INSTRUCTIONS:**
- Base all assessments strictly on the provided evidence and policy rules
- Be specific about what evidence supports or contradicts each rule
- Consider the policy category context in your evaluation approach
- Reference similar examples when they provide relevant benchmarks
- Explain confidence scores based on evidence quality and completeness
- Provide policy-specific recommendations that are actionable and relevant
"""

    async def _parse_generic_compliance_decision(self, llm_response: str, 
                                               policy: CompliancePolicyModel) -> Dict[str, Any]:
        """Parse compliance decision from LLM response for any policy type"""

        decision = {
            "policy_id": policy.policy_id,
            "policy_name": policy.policy_name,
            "policy_category": policy.policy_category,
            "overall_status": "REQUIRES_REVIEW",
            "confidence_score": 0.5,
            "rule_evaluations": {},
            "policy_specific_findings": [],
            "evidence_quality_assessment": [],
            "compliance_gaps": [],
            "recommendations": [],
            "overall_rationale": "",
            "raw_response": llm_response
        }

        lines = llm_response.split('\n')
        current_section = None
        current_rule = None

        for line in lines:
            line = line.strip()

            # Parse overall status and confidence
            if line.startswith("OVERALL_STATUS:"):
                status = line.split(":", 1)[1].strip()
                decision["overall_status"] = status

            elif line.startswith("CONFIDENCE_SCORE:"):
                try:
                    score = float(line.split(":", 1)[1].strip())
                    decision["confidence_score"] = score
                except (ValueError, IndexError):
                    decision["confidence_score"] = 0.5

            # Parse rule evaluations
            elif line.startswith("Rule ") and (" - " in line and ":" in line):
                rule_match = re.match(r'Rule (\d+) - ([^:]+): (.+)', line)
                if rule_match:
                    rule_number = rule_match.group(1)
                    rule_name = rule_match.group(2).strip()
                    rule_status = rule_match.group(3).strip()

                    current_rule = f"rule_{rule_number}"
                    decision["rule_evaluations"][current_rule] = {
                        "rule_number": rule_number,
                        "rule_name": rule_name,
                        "status": rule_status,
                        "assessment": "",
                        "evidence_reference": "",
                        "confidence": 0.5,
                        "severity_impact": ""
                    }

            # Parse rule details
            elif line.startswith("Assessment:") and current_rule:
                decision["rule_evaluations"][current_rule]["assessment"] = line.split(":", 1)[1].strip()

            elif line.startswith("Evidence_Reference:") and current_rule:
                decision["rule_evaluations"][current_rule]["evidence_reference"] = line.split(":", 1)[1].strip()

            elif line.startswith("Confidence:") and current_rule:
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                    decision["rule_evaluations"][current_rule]["confidence"] = confidence
                except (ValueError, IndexError):
                    decision["rule_evaluations"][current_rule]["confidence"] = 0.5

            elif line.startswith("Severity_Impact:") and current_rule:
                decision["rule_evaluations"][current_rule]["severity_impact"] = line.split(":", 1)[1].strip()

            # Parse sections
            elif line.startswith("POLICY_SPECIFIC_FINDINGS:"):
                current_section = "policy_specific_findings"
                current_rule = None

            elif line.startswith("EVIDENCE_QUALITY_ASSESSMENT:"):
                current_section = "evidence_quality_assessment"
                current_rule = None

            elif line.startswith("COMPLIANCE_GAPS:"):
                current_section = "compliance_gaps"
                current_rule = None

            elif line.startswith("RECOMMENDATIONS:"):
                current_section = "recommendations"
                current_rule = None

            elif line.startswith("OVERALL_RATIONALE:"):
                current_section = "overall_rationale"
                current_rule = None

            # Collect section content
            elif line.startswith("- ") and current_section in ["policy_specific_findings", "evidence_quality_assessment", "compliance_gaps", "recommendations"]:
                decision[current_section].append(line[2:].strip())

            elif current_section == "overall_rationale" and line:
                if decision["overall_rationale"]:
                    decision["overall_rationale"] += " " + line
                else:
                    decision["overall_rationale"] = line

        return decision

    async def _process_rule_assessments(self, compliance_decision: Dict[str, Any],
                                      rules: List[ComplianceRuleModel]) -> Dict[str, Dict[str, Any]]:
        """Process individual rule assessments with policy context"""

        assessments = {}

        for rule in rules:
            rule_key = f"rule_{rule.rule_number}"
            rule_evaluation = compliance_decision.get("rule_evaluations", {}).get(rule_key, {})

            assessment = {
                "rule_info": {
                    "rule_id": rule.rule_id,
                    "rule_number": rule.rule_number,
                    "rule_name": rule.rule_name,
                    "rule_category": rule.rule_category,
                    "description": rule.description,
                    "severity_level": rule.severity_level
                },
                "evaluation_results": {
                    "status": rule_evaluation.get("status", "REQUIRES_REVIEW"),
                    "assessment": rule_evaluation.get("assessment", "No assessment available"),
                    "evidence_reference": rule_evaluation.get("evidence_reference", "No evidence reference"),
                    "confidence": rule_evaluation.get("confidence", 0.5),
                    "severity_impact": rule_evaluation.get("severity_impact", "Not specified")
                },
                "validation_criteria": rule.validation_criteria,
                "rule_parameters": rule.rule_parameters
            }

            assessments[rule.rule_id] = assessment

        return assessments


# ====== GENERIC WORKFLOW ORCHESTRATION ======

class GenericComplianceValidationWorkflow:
    """Universal LangGraph workflow for multi-policy compliance validation"""

    def __init__(self, config: GenericComplianceConfig):
        self.config = config

        # Initialize generic agents
        self.evidence_agent = EvidenceSummarizerAgent(config)
        self.policy_agent = PolicyDiscoveryAgent(config)
        self.retrieval_agent = ComplianceRetrievalAgent(config)
        self.evaluation_agent = GenericEvaluationAgent(config)

        # Create workflow with memory
        self.memory = MemorySaver()
        self.workflow = self._build_generic_workflow()

    def _build_generic_workflow(self) -> StateGraph:
        """Build universal workflow supporting any compliance policy"""

        workflow = StateGraph(GenericValidationState)

        # Add generic agent nodes
        workflow.add_node("summarize_evidence", self._evidence_summarizer_node)
        workflow.add_node("discover_policies", self._policy_discovery_node)
        workflow.add_node("retrieve_compliance_context", self._compliance_retrieval_node)
        workflow.add_node("evaluate_generic_compliance", self._generic_evaluation_node)

        # Define universal workflow edges
        workflow.add_edge(START, "summarize_evidence")
        workflow.add_edge("summarize_evidence", "discover_policies")
        workflow.add_edge("discover_policies", "retrieve_compliance_context")
        workflow.add_edge("retrieve_compliance_context", "evaluate_generic_compliance")
        workflow.add_edge("evaluate_generic_compliance", END)

        # Add conditional error handling for each stage
        workflow.add_conditional_edges(
            "summarize_evidence",
            self._check_for_errors,
            {"continue": "discover_policies", "error": END}
        )

        workflow.add_conditional_edges(
            "discover_policies",
            self._check_policy_discovery,
            {"continue": "retrieve_compliance_context", "no_policy": END}
        )

        workflow.add_conditional_edges(
            "retrieve_compliance_context",
            self._check_for_errors,
            {"continue": "evaluate_generic_compliance", "error": END}
        )

        return workflow.compile(checkpointer=self.memory)

    # Node implementations
    async def _evidence_summarizer_node(self, state: GenericValidationState) -> GenericValidationState:
        return await self.evidence_agent.process(state)

    async def _policy_discovery_node(self, state: GenericValidationState) -> GenericValidationState:
        return await self.policy_agent.process(state)

    async def _compliance_retrieval_node(self, state: GenericValidationState) -> GenericValidationState:
        return await self.retrieval_agent.process(state)

    async def _generic_evaluation_node(self, state: GenericValidationState) -> GenericValidationState:
        return await self.evaluation_agent.process(state)

    # Conditional routing functions
    def _check_for_errors(self, state: GenericValidationState) -> str:
        return "error" if state.error_messages else "continue"

    def _check_policy_discovery(self, state: GenericValidationState) -> str:
        if state.error_messages:
            return "error"
        elif not state.detected_policies and not state.active_policy:
            return "no_policy"
        else:
            return "continue"

    async def validate_generic_compliance(self, confluence_url: str,
                                        change_request_id: str = None,
                                        requested_policies: List[str] = None) -> GenericValidationState:
        """Execute generic compliance validation for any policy type"""

        # Initialize state
        initial_state = GenericValidationState()
        initial_state.confluence_url = confluence_url
        initial_state.change_request_id = change_request_id or f"generic-compliance-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        initial_state.requested_policies = requested_policies or []
        initial_state.timestamps["workflow_start"] = datetime.now().isoformat()

        logger.info(f"Starting generic validation workflow for: {confluence_url}")
        if requested_policies:
            logger.info(f"Requested policies: {requested_policies}")

        # Execute workflow
        try:
            config_dict = {"configurable": {"thread_id": initial_state.change_request_id}}
            result = await self.workflow.ainvoke(initial_state, config=config_dict)

            result.timestamps["workflow_complete"] = datetime.now().isoformat()

            policy_info = f"Policy: {result.active_policy.policy_name}" if result.active_policy else "No policy"
            logger.info(f"Generic validation completed: {result.final_status.value} - {policy_info} (Confidence: {result.confidence_score:.2f})")

            return result

        except Exception as e:
            logger.error(f"Generic workflow execution failed: {str(e)}")
            initial_state.error_messages.append(f"Workflow execution failed: {str(e)}")
            initial_state.final_status = ComplianceStatus.ERROR
            return initial_state


# ====== MAIN EXECUTION EXAMPLE ======

async def main():
    """Example execution demonstrating multi-policy support"""

    # Initialize generic configuration and workflow
    config = GenericComplianceConfig()
    workflow = GenericComplianceValidationWorkflow(config)

    # Example test cases for different policy types
    test_cases = [
        {
            "confluence_url": "https://confluence.company.com/display/PROJECT/Test-Execution-Evidence",
            "change_request_id": "CHG-2024-MULTIPL-001",
            "description": "Test execution evidence - should detect Policy 101",
            "requested_policies": []  # Auto-detection
        },
        {
            "confluence_url": "https://confluence.company.com/display/SECURITY/Security-Assessment-Report",
            "change_request_id": "CHG-2024-MULTIPL-002", 
            "description": "Security assessment report - should detect Policy 201",
            "requested_policies": []  # Auto-detection
        },
        {
            "confluence_url": "https://confluence.company.com/display/PROJECT/Mixed-Compliance-Evidence",
            "change_request_id": "CHG-2024-MULTIPL-003",
            "description": "Mixed evidence - test multi-policy validation",
            "requested_policies": ["POL-101", "POL-201"]  # Specific policies requested
        }
    ]

    print("🌟 Generic Multi-Policy Compliance Validation System")
    print("="*80)
    print("Universal system supporting unlimited policy types:")
    print("  • Policy 101: Test Execution")
    print("  • Policy 201: Security Compliance") 
    print("  • Policy 301: Deployment Validation")
    print("  • Policy 401: Code Review")
    print("  • Policy 501: Documentation")
    print("  • ...Future policies automatically supported")
    print("="*80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['change_request_id']}")
        print(f"📄 Description: {test_case['description']}")
        print(f"🔗 Evidence URL: {test_case['confluence_url']}")
        if test_case['requested_policies']:
            print(f"🎯 Requested Policies: {', '.join(test_case['requested_policies'])}")
        else:
            print(f"🔍 Policy Detection: Auto-detect from evidence")

        try:
            # Execute generic validation workflow
            result = await workflow.validate_generic_compliance(
                confluence_url=test_case["confluence_url"],
                change_request_id=test_case["change_request_id"],
                requested_policies=test_case.get("requested_policies")
            )

            # Display results
            print(f"\n✅ GENERIC COMPLIANCE VALIDATION RESULTS:")
            print(f"Final Status: {result.final_status.value}")
            print(f"Overall Confidence: {result.confidence_score:.2f}")

            # Policy information
            if result.active_policy:
                print(f"\n🎯 Active Policy:")
                print(f"  Policy ID: {result.active_policy.policy_id}")
                print(f"  Policy Name: {result.active_policy.policy_name}")
                print(f"  Policy Category: {result.active_policy.policy_category}")

            # Evidence analysis summary
            print(f"\n📊 Evidence Analysis:")
            print(f"  Evidence Type: {result.evidence_type.value}")
            for component, analysis in list(result.evidence_analysis.items())[:3]:
                status = "✓" if analysis.get("present", False) else "✗"
                quality = analysis.get("quality_score", 0.0)
                print(f"  {status} {component}: Quality {quality:.2f}")

        except Exception as e:
            print(f"\n❌ Generic validation failed: {str(e)}")

        print("-" * 60)

    print("\n🎯 Generic Multi-Policy System completed successfully!")


if __name__ == "__main__":
    # Execute the generic multi-policy validation workflow
    asyncio.run(main())
