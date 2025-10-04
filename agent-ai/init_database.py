#!/usr/bin/env python3
"""
Database initialization script for Agentic AI Compliance Verification System.

This script initializes:
1. Spanner vector store tables for evidence embeddings
2. Sample SpannerGraph schema for policy rules
3. Sample policy data for testing

Usage:
    python scripts/init_database.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from langchain_google_spanner import SpannerVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_spanner_vector_store():
    """Initialize Spanner vector store tables."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID')
        instance_id = os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
        database_id = os.getenv('SPANNER_DATABASE_ID', 'compliance-db')

        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable must be set")

        logger.info(f"Initializing Spanner vector store: {project_id}/{instance_id}/{database_id}")

        # Initialize vector store table with metadata columns
        SpannerVectorStore.init_vector_store_table(
            instance_id=instance_id,
            database_id=database_id,
            table_name="evidence_embeddings",
            id_column="langchain_id",
            content_column="content", 
            embedding_column="embedding",
            metadata_columns=[
                {"name": "source_url", "type": "STRING(MAX)"},
                {"name": "section_header", "type": "STRING(500)"},
                {"name": "chunk_id", "type": "STRING(100)"},
                {"name": "extraction_method", "type": "STRING(50)"},
                {"name": "content_type", "type": "STRING(50)"},
                {"name": "validation_status", "type": "STRING(50)"},
                {"name": "policy_name", "type": "STRING(200)"},
                {"name": "timestamp", "type": "TIMESTAMP"},
                {"name": "rule_assessments", "type": "JSON"},
                {"name": "analysis_summary", "type": "STRING(MAX)"},
                {"name": "confidence_score", "type": "FLOAT64"},
                {"name": "updated_at", "type": "TIMESTAMP"}
            ],
            vector_size=768  # text-embedding-005 dimensions
        )

        logger.info("✅ Successfully initialized evidence_embeddings table")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize Spanner vector store: {str(e)}")
        return False


def create_spanner_graph_schema():
    """Create SpannerGraph schema for policy rules."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID')
        instance_id = os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
        database_id = os.getenv('SPANNER_DATABASE_ID', 'compliance-db')
        graph_name = os.getenv('SPANNER_GRAPH_NAME', 'PolicyGraph')

        client = spanner.Client(project=project_id)
        instance = client.instance(instance_id)
        database = instance.database(database_id)

        logger.info(f"Creating SpannerGraph schema: {graph_name}")

        # DDL statements for graph schema
        ddl_statements = [
            # Create Policy node table
            """
            CREATE TABLE Policy (
                id STRING(100) NOT NULL,
                name STRING(200) NOT NULL,
                description STRING(MAX),
                version STRING(50),
                effective_date DATE,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                updated_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true)
            ) PRIMARY KEY (id)
            """,

            # Create Rule node table
            """
            CREATE TABLE Rule (
                rule_id STRING(100) NOT NULL,
                description STRING(MAX) NOT NULL,
                type STRING(100),
                severity STRING(50),
                validation_criteria STRING(MAX),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                updated_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true)
            ) PRIMARY KEY (rule_id)
            """,

            # Create Policy-Rule relationship table
            """
            CREATE TABLE PolicyHasRule (
                policy_id STRING(100) NOT NULL,
                rule_id STRING(100) NOT NULL,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                FOREIGN KEY (policy_id) REFERENCES Policy (id),
                FOREIGN KEY (rule_id) REFERENCES Rule (rule_id)
            ) PRIMARY KEY (policy_id, rule_id)
            """,

            # Create Policy-Policy reference table
            """
            CREATE TABLE PolicyReferences (
                policy_id STRING(100) NOT NULL,
                referenced_policy_id STRING(100) NOT NULL,
                reference_type STRING(100),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                FOREIGN KEY (policy_id) REFERENCES Policy (id),
                FOREIGN KEY (referenced_policy_id) REFERENCES Policy (id)
            ) PRIMARY KEY (policy_id, referenced_policy_id)
            """,

            # Create the property graph
            f"""
            CREATE PROPERTY GRAPH {graph_name}
            NODE TABLES (
                Policy,
                Rule
            )
            EDGE TABLES (
                PolicyHasRule 
                    SOURCE KEY (policy_id) REFERENCES Policy (id)
                    DESTINATION KEY (rule_id) REFERENCES Rule (rule_id)
                    LABEL HAS_RULE,
                PolicyReferences
                    SOURCE KEY (policy_id) REFERENCES Policy (id) 
                    DESTINATION KEY (referenced_policy_id) REFERENCES Policy (id)
                    LABEL REFERENCES
            )
            """
        ]

        # Execute DDL statements
        operation = database.update_ddl(ddl_statements)
        operation.result()

        logger.info("✅ Successfully created SpannerGraph schema")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create SpannerGraph schema: {str(e)}")
        return False


def insert_sample_policy_data():
    """Insert sample policy data for testing."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID')
        instance_id = os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
        database_id = os.getenv('SPANNER_DATABASE_ID', 'compliance-db')

        client = spanner.Client(project=project_id)
        instance = client.instance(instance_id)
        database = instance.database(database_id)

        logger.info("Inserting sample policy data")

        with database.batch() as batch:
            # Insert sample policies
            batch.insert(
                table='Policy',
                columns=['id', 'name', 'description', 'version', 'effective_date'],
                values=[
                    ('POL_RT', 'Regression Testing Policy', 
                     'Policy defining requirements for regression testing in software releases', 
                     '1.0', '2024-01-01'),
                    ('POL_PT', 'Performance Testing Policy',
                     'Policy defining requirements for performance testing and benchmarking',
                     '1.0', '2024-01-01'),
                    ('POL_TS', 'Testing Strategy Policy',
                     'Overall testing strategy and methodology requirements',
                     '1.0', '2024-01-01'),
                    ('POL_DS', 'Development Strategy Policy',
                     'Development practices and code quality requirements',
                     '1.0', '2024-01-01')
                ]
            )

            # Insert sample rules
            batch.insert(
                table='Rule',
                columns=['rule_id', 'description', 'type', 'severity', 'validation_criteria'],
                values=[
                    ('RT-001', 'All critical regression tests must be executed for major releases',
                     'Mandatory', 'High', '100% execution of critical test cases with pass rate >= 95%'),
                    ('RT-002', 'Test results must be documented and signed off by QA Lead',
                     'Documentation', 'High', 'Signed approval from designated QA Lead required'),
                    ('RT-003', 'Regression test suite must include database migration testing',
                     'Technical', 'Medium', 'Evidence of database migration test execution and validation'),

                    ('PT-001', 'Performance benchmarks must meet defined SLA requirements',
                     'Performance', 'High', 'All SLA metrics within acceptable thresholds'),
                    ('PT-002', 'Load testing must be performed under realistic user scenarios',
                     'Performance', 'Medium', 'Evidence of realistic load test execution'),

                    ('TS-001', 'Test strategy must be documented and approved before development',
                     'Process', 'High', 'Approved test strategy document exists'),
                    ('TS-002', 'Test coverage must meet minimum threshold requirements',
                     'Quality', 'Medium', 'Code coverage >= 80% for critical components'),

                    ('DS-001', 'Code must pass static analysis with zero high-severity issues',
                     'Quality', 'High', 'Static analysis report shows no high-severity violations'),
                    ('DS-002', 'All code changes must be peer-reviewed before merge',
                     'Process', 'High', 'Evidence of peer review approval in version control')
                ]
            )

            # Insert policy-rule relationships
            batch.insert(
                table='PolicyHasRule',
                columns=['policy_id', 'rule_id'],
                values=[
                    ('POL_RT', 'RT-001'),
                    ('POL_RT', 'RT-002'), 
                    ('POL_RT', 'RT-003'),
                    ('POL_PT', 'PT-001'),
                    ('POL_PT', 'PT-002'),
                    ('POL_TS', 'TS-001'),
                    ('POL_TS', 'TS-002'),
                    ('POL_DS', 'DS-001'),
                    ('POL_DS', 'DS-002')
                ]
            )

            # Insert policy references (cross-references)
            batch.insert(
                table='PolicyReferences',
                columns=['policy_id', 'referenced_policy_id', 'reference_type'],
                values=[
                    ('POL_RT', 'POL_TS', 'dependency'),
                    ('POL_PT', 'POL_TS', 'dependency'),
                    ('POL_TS', 'POL_DS', 'reference')
                ]
            )

        logger.info("✅ Successfully inserted sample policy data")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to insert sample data: {str(e)}")
        return False


def main():
    """Main initialization function."""
    print("🗄️ Initializing Agentic AI Compliance Database Components")
    print("=" * 60)

    success_count = 0

    # Initialize vector store
    print("1. Initializing Spanner vector store...")
    if init_spanner_vector_store():
        success_count += 1

    # Create graph schema  
    print("\n2. Creating SpannerGraph schema...")
    if create_spanner_graph_schema():
        success_count += 1

    # Insert sample data
    print("\n3. Inserting sample policy data...")
    if insert_sample_policy_data():
        success_count += 1

    print("\n" + "=" * 60)
    print(f"✅ Database initialization completed: {success_count}/3 components successful")

    if success_count < 3:
        print("⚠️  Some components failed. Check logs above for details.")
        sys.exit(1)
    else:
        print("🎉 All database components initialized successfully!")


if __name__ == "__main__":
    main()
