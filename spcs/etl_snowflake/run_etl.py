"""
run_etl.py

Pulls synpuf_raw + omop_vocabulary from their Snowflake stages into
local temp folders, runs the OHDSI ETL (CMS_SynPuf_ETL_CDM_v5.py,
untouched) against them, then uploads the results to etl_output.
Testable locally now; the mount-based version (no download/upload
step, stages appear as folders directly) is a separate, later change
once this proves the ETL script itself runs correctly.

Usage:
    python run_etl.py <sample_number>
"""
import os
import shutil
import subprocess
import sys
import tempfile

from dotenv import load_dotenv

_snowflake_root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.path.insert(0, _snowflake_root)

from utils_snowflake.connection import get_connection, get_snowpark_session
from utils_snowflake.upload_to_stage import upload_directory_to_stage

ETL_SCRIPT_PATH = r"C:\Users\GargiAsthana\OneDrive - Axle\Projects\Templates\etl-cms-db\python_etl\CMS_SynPuf_ETL_CDM_v5.py"


def run_etl_for_sample(session, sample_number, database, bronze_schema, silver_schema,
                        synpuf_stage, vocab_stage, output_stage):
    work_dir = tempfile.mkdtemp(prefix="etl_")
    synpuf_dir = os.path.join(work_dir, "synpuf")
    vocab_dir = os.path.join(work_dir, "vocab")
    control_dir = os.path.join(work_dir, "control")
    output_dir = os.path.join(work_dir, "output")
    for d in (synpuf_dir, vocab_dir, control_dir, output_dir):
        os.makedirs(d, exist_ok=True)

    session.sql(f"USE SCHEMA {bronze_schema}").collect()
    synpuf_target = os.path.join(synpuf_dir, f"DE_{sample_number}")
    os.makedirs(synpuf_target, exist_ok=True)
    session.file.get(f"@{synpuf_stage}/DE_{sample_number}", synpuf_target)
    session.file.get(f"@{vocab_stage}", vocab_dir)

    etl_env = os.environ.copy()
    etl_env["BASE_SYNPUF_INPUT_DIRECTORY"] = synpuf_dir
    etl_env["BASE_OMOP_INPUT_DIRECTORY"] = vocab_dir
    etl_env["BASE_ETL_CONTROL_DIRECTORY"] = control_dir
    etl_env["BASE_OUTPUT_DIRECTORY"] = output_dir
    etl_env["SYNPUF_DIR_FORMAT"] = "DE_{0}"

    subprocess.run([sys.executable, ETL_SCRIPT_PATH, sample_number], env=etl_env, cwd=os.path.dirname(ETL_SCRIPT_PATH), check=True)

    session.sql(f"USE SCHEMA {silver_schema}").collect()
    n_control = upload_directory_to_stage(session, silver_schema, output_stage, control_dir, prefix="control")
    n_output = upload_directory_to_stage(session, silver_schema, output_stage, output_dir, prefix="output")

    shutil.rmtree(work_dir, ignore_errors=True)
    return f"Sample {sample_number}: staged {n_control} control file(s), {n_output} output file(s)"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_etl.py <sample_number>")
        sys.exit(1)

    load_dotenv()
    sample_number = sys.argv[1]

    database = os.environ["SNOWFLAKE_DATABASE"]
    bronze_schema = os.environ["SNOWFLAKE_BRONZE_SCHEMA"]
    silver_schema = os.environ["SNOWFLAKE_SILVER_SCHEMA"]
    synpuf_stage = os.environ["SNOWFLAKE_RAW_SYNPUF_STAGE"]
    vocab_stage = os.environ["SNOWFLAKE_VOCAB_STAGE"]
    output_stage = os.environ["SNOWFLAKE_ETL_OUTPUT_STAGE"]

    conn = get_connection()
    try:
        session = get_snowpark_session(conn)
        session.sql(f"USE DATABASE {database}").collect()

        result = run_etl_for_sample(session, sample_number, database, bronze_schema, silver_schema,
                                     synpuf_stage, vocab_stage, output_stage)
        print(result)

        session.close()
    finally:
        conn.close()

    print("Done.")