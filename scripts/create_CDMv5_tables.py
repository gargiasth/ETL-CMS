"""
Create the OMOP CDM v5 tables on Databricks.

Thin wrapper around the reusable sql_translation module. Reads a Postgres
DDL file, translates via `sql_translation.translate_postgres_to_databricks`,
and executes each statement against the target catalog and schema.

Usage (via Databricks Job):
    python create_omop_tables_databricks.py <catalog> <schema> <sql_path>
"""
import os
import sys

# Ensure our sibling module is importable regardless of cwd
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.path.insert(0, _repo_root)


from utils.sql_translation import (
    append_using_delta,
    is_unsupported,
    translate_postgres_to_databricks,
)


def parse_args():
    if len(sys.argv) != 4:
        print("Usage: create_omop_tables_databricks.py <catalog> <schema> <sql_path>")
        sys.exit(1)
    return sys.argv[1], sys.argv[2], sys.argv[3]


def read_sql_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def execute_statements(spark, statements, catalog, schema):
    """Set SQL context and execute each translated statement.

    Statements identified as unsupported (see sql_translation.is_unsupported)
    are still attempted — they'll fail explicitly and be logged, which is
    intentional. This surfaces the known-gap issues so they're visible
    rather than silently swallowed.
    """
    spark.sql(f"USE CATALOG {catalog}")
    spark.sql(f"USE SCHEMA {schema}")

    executed = 0
    failed = 0

    for i, stmt in enumerate(statements, 1):
        stmt = append_using_delta(stmt)

        # Log statements we already know are unsupported, but still attempt
        # them so the failure surfaces in logs rather than being hidden.
        reason = is_unsupported(stmt)
        if reason:
            print(f"Statement {i} known-unsupported ({reason}) — attempting anyway")

        try:
            spark.sql(stmt)
            executed += 1
        except Exception as e:
            failed += 1
            print(f"Statement {i} failed: {stmt.splitlines()[0][:80]}")
            print(f"   Error: {e}")

    print(f"\n{executed} succeeded, {failed} failed, {len(statements)} total")


def main():
    catalog, schema, sql_path = parse_args()

    print(f"Catalog:    {catalog}")
    print(f"Schema:     {schema}")
    print(f"SQL source: {sql_path}")

    postgres_sql = read_sql_file(sql_path)
    statements = translate_postgres_to_databricks(postgres_sql)
    print(f"Translated {len(statements)} statements from Postgres to Databricks SQL")

    # Spark is available in Databricks job runtime context
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    execute_statements(spark, statements, catalog, schema)

    # Exit 0 even with failures — some are expected (sequences)
    # and we don't want to block downstream tasks
    sys.exit(0)


if __name__ == "__main__":
    main()