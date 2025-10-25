"""
automated_pipeline.py - Bharat Connect Automated Pipeline Orchestrator
=======================================================================

This script orchestrates the complete end-to-end pipeline:
1. Discovery (RSS + DIKSHA)
2. Connector generation
3. Fivetran deployment

Runs daily (configurable) with full automation

Author: Bharat Connect Team
Date: 2025-10-25
"""

import subprocess
import time
import os
import sys
from datetime import datetime, timedelta
import logging
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths (adjust to your project structure)
PROJECT_ROOT = Path(__file__).parent
AGENTS_DIR = PROJECT_ROOT / "agents"
RSS_CONNECTOR_DIR = PROJECT_ROOT / "connectors" / "rss-connector"
DIKSHA_CONNECTOR_DIR = PROJECT_ROOT / "connectors" / "diksha-connector"

# Fivetran configuration
FIVETRAN_API_KEY = os.getenv('FIVETRAN_API_KEY', '')  # Use env var in production!
FIVETRAN_DESTINATION = 'bc_bigquery'
RSS_CONNECTION = 'rss_connector'
DIKSHA_CONNECTION = 'diksha_connector'

# Schedule configuration
RUN_INTERVAL_HOURS = 24  # Run once per day
# RUN_INTERVAL_HOURS = 1  # For testing: run every hour

# Logging
LOG_FILE = PROJECT_ROOT / 'pipeline.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_command(cmd, cwd=None, input_text=None):
    """
    Run a shell command with optional auto-responses.
    
    Args:
        cmd: Command to run (string or list)
        cwd: Working directory
        input_text: Text to send to stdin (for automated responses)
    
    Returns:
        (success: bool, output: str)
    """
    try:
        logger.info(f"Running: {cmd}")
        
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info(f"Success")
            return True, result.stdout
        else:
            logger.error(f"Failed with return code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False, str(e)

def run_python_script(script_path, cwd=None):
    """Run a Python script."""
    return run_command(['python', str(script_path)], cwd=cwd)

def deploy_to_fivetran(connector_dir, connection_name, api_key, destination):
    """
    Deploy connector to Fivetran with automated responses.
    
    Automated responses:
    1. "Does this debug run/deploy need configuration (y/N):" → n
    2. "Do you want to proceed with the update? (y/N):" → y
    """
    logger.info(f"Deploying {connection_name} to Fivetran...")
    
    cmd = [
        'fivetran', 'deploy',
        '--api-key', api_key,
        '--destination', destination,
        '--connection', connection_name
    ]
    
    # Auto-responses: first "n" for config, then "y" for update confirmation
    auto_responses = "n\ny\n"
    
    success, output = run_command(cmd, cwd=connector_dir, input_text=auto_responses)
    
    if success:
        logger.info(f"{connection_name} deployed successfully")
    else:
        logger.error(f"{connection_name} deployment failed")
    
    return success

# ============================================================================
# PIPELINE STAGES
# ============================================================================

def stage_1_rss_discovery():
    """Stage 1: RSS Feed Discovery"""
    logger.info("=" * 70)
    logger.info("STAGE 1: RSS FEED DISCOVERY")
    logger.info("=" * 70)
    
    # Run RSS discovery agents
    success, output = run_python_script(
        AGENTS_DIR / 'main.py',
        cwd=AGENTS_DIR
    )
    
    if not success:
        logger.error("RSS discovery failed!")
        return False
    
    # Check if discover_results.json was created
    results_file = AGENTS_DIR / 'discover_results.json'
    if not results_file.exists():
        logger.error("discover_results.json not created!")
        return False
    
    logger.info("RSS discovery completed")
    return True

def stage_2_diksha_discovery():
    """Stage 2: DIKSHA Content Discovery"""
    logger.info("=" * 70)
    logger.info("STAGE 2: DIKSHA CONTENT DISCOVERY")
    logger.info("=" * 70)
    
    # Run DIKSHA discovery agent
    success, output = run_python_script(
        PROJECT_ROOT / 'diksha_discovery_agent.py',
        cwd=PROJECT_ROOT
    )
    
    if not success:
        logger.error("DIKSHA discovery failed!")
        return False
    
    # Check if diksha_content.json was created
    results_file = PROJECT_ROOT / 'diksha_content.json'
    if not results_file.exists():
        logger.error("diksha_content.json not created!")
        return False
    
    logger.info("✅ DIKSHA discovery completed")
    return True

def stage_3_generate_rss_connector():
    """Stage 3: Generate RSS Connector"""
    logger.info("=" * 70)
    logger.info("STAGE 3: GENERATE RSS CONNECTOR")
    logger.info("=" * 70)
    
    # Copy discover_results.json to RSS connector directory
    import shutil
    src = AGENTS_DIR / 'discover_results.json'
    dst = RSS_CONNECTOR_DIR / 'discover_results.json'
    shutil.copy(src, dst)
    logger.info(f"Copied discover_results.json to {RSS_CONNECTOR_DIR}")
    
    # Generate RSS connector
    success, output = run_python_script(
        RSS_CONNECTOR_DIR / 'generate_connector.py',
        cwd=RSS_CONNECTOR_DIR
    )
    
    if not success:
        logger.error("RSS connector generation failed!")
        return False
    
    # Check if connector.py was created
    connector_file = RSS_CONNECTOR_DIR / 'connector.py'
    if not connector_file.exists():
        logger.error("RSS connector.py not created!")
        return False
    
    logger.info("✅ RSS connector generated")
    return True

def stage_4_generate_diksha_connector():
    """Stage 4: Generate DIKSHA Connector"""
    logger.info("=" * 70)
    logger.info("STAGE 4: GENERATE DIKSHA CONNECTOR")
    logger.info("=" * 70)
    
    # Copy diksha_content.json to DIKSHA connector directory
    import shutil
    src = PROJECT_ROOT / 'diksha_content.json'
    dst = DIKSHA_CONNECTOR_DIR / 'diksha_content.json'
    shutil.copy(src, dst)
    logger.info(f"Copied diksha_content.json to {DIKSHA_CONNECTOR_DIR}")
    
    # Generate DIKSHA connector
    success, output = run_python_script(
        DIKSHA_CONNECTOR_DIR / 'generate_diksha_connector.py',
        cwd=DIKSHA_CONNECTOR_DIR
    )
    
    if not success:
        logger.error("DIKSHA connector generation failed!")
        return False
    
    # Check if connector.py was created
    connector_file = DIKSHA_CONNECTOR_DIR / 'connector.py'
    if not connector_file.exists():
        logger.error("DIKSHA connector.py not created!")
        return False
    
    logger.info("DIKSHA connector generated")
    return True

def stage_5_deploy_rss_connector():
    """Stage 5: Deploy RSS Connector to Fivetran"""
    logger.info("=" * 70)
    logger.info("STAGE 5: DEPLOY RSS CONNECTOR")
    logger.info("=" * 70)
    
    success = deploy_to_fivetran(
        RSS_CONNECTOR_DIR,
        RSS_CONNECTION,
        FIVETRAN_API_KEY,
        FIVETRAN_DESTINATION
    )
    
    return success

def stage_6_deploy_diksha_connector():
    """Stage 6: Deploy DIKSHA Connector to Fivetran"""
    logger.info("=" * 70)
    logger.info("STAGE 6: DEPLOY DIKSHA CONNECTOR")
    logger.info("=" * 70)
    
    success = deploy_to_fivetran(
        DIKSHA_CONNECTOR_DIR,
        DIKSHA_CONNECTION,
        FIVETRAN_API_KEY,
        FIVETRAN_DESTINATION
    )
    
    return success

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_pipeline():
    """Run complete pipeline."""
    start_time = datetime.now()
    logger.info("")
    logger.info("=" * 70)
    logger.info(" " * 15 + "BHARAT CONNECT PIPELINE")
    logger.info(f" " * 20 + f"Run started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    stages = [
        ("RSS Discovery", stage_1_rss_discovery),
        ("DIKSHA Discovery", stage_2_diksha_discovery),
        ("Generate RSS Connector", stage_3_generate_rss_connector),
        ("Generate DIKSHA Connector", stage_4_generate_diksha_connector),
        ("Deploy RSS Connector", stage_5_deploy_rss_connector),
        ("Deploy DIKSHA Connector", stage_6_deploy_diksha_connector),
    ]
    
    results = {}
    
    for stage_name, stage_func in stages:
        try:
            logger.info("")
            success = stage_func()
            results[stage_name] = success
            
            if not success:
                logger.error(f"Pipeline halted at stage: {stage_name}")
                break
                
        except Exception as e:
            logger.error(f"Exception in {stage_name}: {e}")
            import traceback
            traceback.print_exc()
            results[stage_name] = False
            break
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(" " * 20 + "PIPELINE SUMMARY")
    logger.info("=" * 70)
    
    for stage_name, success in results.items():
        status = "✅ SUCCESS" if success else "FAILED"
        logger.info(f"  {stage_name}: {status}")
    
    logger.info("")
    logger.info(f"  Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Duration: {duration}")
    logger.info("=" * 70)
    
    all_success = all(results.values())
    
    if all_success:
        logger.info("Pipeline completed successfully!")
    else:
        logger.error("Pipeline completed with errors")
    
    return all_success

# ============================================================================
# SCHEDULER
# ============================================================================

def run_scheduler():
    """Run pipeline on schedule (continuous loop)."""
    logger.info("=" * 70)
    logger.info(" " * 10 + "AUTOMATED PIPELINE SCHEDULER STARTED")
    logger.info(f" " * 15 + f"Interval: Every {RUN_INTERVAL_HOURS} hours")
    logger.info("=" * 70)
    
    run_count = 0
    
    while True:
        run_count += 1
        logger.info(f"\n\n{'#' * 70}")
        logger.info(f"{'#' * 70}")
        logger.info(f"  RUN #{run_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'#' * 70}")
        logger.info(f"{'#' * 70}\n")
        
        try:
            run_pipeline()
        except Exception as e:
            logger.error(f"Pipeline exception: {e}")
            import traceback
            traceback.print_exc()
        
        # Calculate next run time
        next_run = datetime.now() + timedelta(hours=RUN_INTERVAL_HOURS)
        logger.info(f"\nNext run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Sleeping for {RUN_INTERVAL_HOURS} hours...")
        
        # Sleep until next run
        time.sleep(RUN_INTERVAL_HOURS * 3600)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Bharat Connect Automated Pipeline')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run pipeline once and exit (no scheduling)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=RUN_INTERVAL_HOURS,
        help=f'Run interval in hours (default: {RUN_INTERVAL_HOURS})'
    )
    
    args = parser.parse_args()
    
    # Update interval if specified
    if args.interval != RUN_INTERVAL_HOURS:
        RUN_INTERVAL_HOURS = args.interval
        logger.info(f"Custom interval set: {RUN_INTERVAL_HOURS} hours")
    
    try:
        if args.once:
            # Run once and exit
            logger.info("Running pipeline once (--once mode)")
            success = run_pipeline()
            sys.exit(0 if success else 1)
        else:
            # Run continuously
            run_scheduler()
            
    except KeyboardInterrupt:
        logger.info("\n\nPipeline interrupted by user (Ctrl+C)")
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
