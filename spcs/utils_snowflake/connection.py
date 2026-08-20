"""
Shared Snowflake connection helper.

Connects at the account level only (no database/schema) — callers run
their own `USE DATABASE` / `USE SCHEMA` once those exist. This lets the
same connection function serve both "create the database" (which can't
specify a database that doesn't exist yet) and "create tables inside
an existing schema".
"""
import os
from dotenv import load_dotenv
import snowflake.connector


def get_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ["SNOWFLAKE_ROLE"],
    )


if __name__ == "__main__":
    load_dotenv()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_VERSION()")
        print(cur.fetchone())
    finally:
        conn.close()