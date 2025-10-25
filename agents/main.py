"""
main.py - Entry point with Checkpoint & Resume Functionality
=============================================================

Features:
1. Runs intelligent_feed_agent (Phase 1)
2. Saves checkpoint after Phase 1 completes
3. If error occurs in Phase 2+, can resume from checkpoint
4. Avoids re-running expensive Phase 1 discovery
"""

import os
import json
import logging
from datetime import datetime
from urllib.parse import urljoin
from coordinator import CoordinatorAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoints for recovery and resume capability.
    
    Purpose: Allow discovery to resume from checkpoints if errors occur
    """
    
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = checkpoint_dir
        
        # Create checkpoint directory if it doesn't exist
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
            logger.info(f"Created checkpoint directory: {checkpoint_dir}")
    
    def save_phase_1_checkpoint(self, feeds: list, run_id: str) -> str:
        """
        Save Phase 1 results as checkpoint.
        
        Args:
            feeds: Discovered feeds from Phase 1
            run_id: Unique run identifier
            
        Returns:
            Checkpoint file path
        """
        
        checkpoint_data = {
            "checkpoint_type": "phase_1_complete",
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "feeds_count": len(feeds),
            "feeds": feeds
        }
        
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"phase_1_checkpoint_{run_id}.json"
        )
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Phase 1 checkpoint saved: {checkpoint_file}")
        logger.info(f"   Feeds: {len(feeds)}")
        
        return checkpoint_file
    
    def load_phase_1_checkpoint(self, run_id: str) -> dict:
        """
        Load Phase 1 checkpoint if it exists.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Checkpoint data or None if not found
        """
        
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"phase_1_checkpoint_{run_id}.json"
        )
        
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                logger.info(f"Loaded Phase 1 checkpoint: {checkpoint_file}")
                logger.info(f"   Feeds: {checkpoint_data['feeds_count']}")
                
                return checkpoint_data
            
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
                return None
        
        return None
    
    def save_final_results_checkpoint(self, results: dict, run_id: str) -> str:
        """
        Save final results as checkpoint.
        
        Args:
            results: Final discovery results
            run_id: Unique run identifier
            
        Returns:
            Checkpoint file path
        """
        
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"final_results_checkpoint_{run_id}.json"
        )
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Final results checkpoint saved: {checkpoint_file}")
        
        return checkpoint_file
    
    def list_available_checkpoints(self) -> list:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint files
        """
        
        if not os.path.exists(self.checkpoint_dir):
            return []
        
        checkpoints = []
        for file in os.listdir(self.checkpoint_dir):
            if file.endswith('.json'):
                checkpoints.append(os.path.join(self.checkpoint_dir, file))
        
        return sorted(checkpoints, reverse=True)
    
    def cleanup_old_checkpoints(self, keep_count: int = 5):
        """
        Clean up old checkpoints, keeping only recent ones.
        
        Args:
            keep_count: Number of recent checkpoints to keep
        """
        
        checkpoints = self.list_available_checkpoints()
        
        if len(checkpoints) > keep_count:
            for checkpoint in checkpoints[keep_count:]:
                try:
                    os.remove(checkpoint)
                    logger.info(f"Removed old checkpoint: {checkpoint}")
                except Exception as e:
                    logger.error(f"Error removing checkpoint: {e}")


def main(force_phase1: bool = False):
    """
    Main entry point with checkpoint & resume functionality.
    """
    
    import uuid
    
    # Configuration
    PROJECT_ID = "bharat-connect-000"
    BASE_URL = "https://pib.gov.in/RssMain.aspx"
    START_URL = "https://www.pib.gov.in/ViewRss.aspx"
    MAX_ITERATIONS = 5
    MIN_QUALITY_SCORE = 60
    # RUN_ID = str(uuid.uuid4())[:8]  # Unique run identifier
    RUN_ID = "7f08d392"
    
    # Initialize checkpoint manager
    checkpoint_mgr = CheckpointManager(checkpoint_dir="./checkpoints")

    # Allow forcing Phase 1 even when a checkpoint exists.
    # You can set the environment variable FORCE_PHASE1=1 or pass --force-phase1 on the CLI.
    if not force_phase1:
        env_force = os.environ.get("FORCE_PHASE1", "").lower()
        force_phase1 = env_force in ("1", "true", "yes")
    
    print("\n" + "="*100)
    print("MULTI-AGENT RSS FEED DISCOVERY WITH CHECKPOINTS")
    print("="*100)
    print(f"\nRun ID: {RUN_ID}\n")
    
    # Initialize coordinator
    coordinator = CoordinatorAgent(
        project_id=PROJECT_ID,
        base_url=BASE_URL,
        max_iterations=MAX_ITERATIONS,
        min_quality_score=MIN_QUALITY_SCORE
    )
    # Ensure coordinator has a start_time so final analysis can compute duration
    coordinator.start_time = datetime.now()
    
    phase_1_feeds = None
    
    try:
        # ====================================================================
        # PHASE 1: Initial Heuristic Discovery
        # ====================================================================
        
        logger.info("📍 PHASE 1: Initial Heuristic Discovery")
        logger.info("-" * 100)
        
        # Try to load from checkpoint first (unless force_phase1 is set)
        checkpoint = None
        if not force_phase1:
            checkpoint = checkpoint_mgr.load_phase_1_checkpoint(RUN_ID)
        
        if checkpoint and not force_phase1:
            # Resume from checkpoint
            logger.info("Resuming from Phase 1 checkpoint...")
            phase_1_feeds = checkpoint.get("feeds", [])
            # Use checkpoint timestamp as start_time if available so durations are meaningful
            try:
                ts = checkpoint.get("timestamp")
                if ts:
                    coordinator.start_time = datetime.fromisoformat(ts)
            except Exception:
                coordinator.start_time = datetime.now()
        else:
            # Run Phase 1 from scratch
            logger.info("Running Phase 1 discovery (this may take a while)...")
            phase_1_feeds = coordinator.intelligent_agent.discover(
                START_URL,
                max_pages=500
            )
            
            if not phase_1_feeds:
                logger.error("Phase 1 failed: No feeds discovered")
                return
            
            logger.info(f"Phase 1 complete: {len(phase_1_feeds)} feeds discovered")
            
            # ✅ CHECKPOINT SAVED HERE
            checkpoint_mgr.save_phase_1_checkpoint(phase_1_feeds, RUN_ID)
        
    # ====================================================================
    # PHASE 2+: RAG Learning Iterations with Validation
    # ====================================================================
        
        logger.info("\n📍 PHASE 2+: RAG Learning Iterations")
        logger.info("-" * 100)
        
        # Normalize Phase 1 feed URLs (convert relative -> absolute) before validation
        normalized_feeds = []
        for f in phase_1_feeds:
            if isinstance(f, dict):
                u = f.get("url") or f.get("link") or f.get("href")
                if u and not u.startswith("http"):
                    u = urljoin(BASE_URL, u)
                    f["url"] = u
                normalized_feeds.append(f)
            elif isinstance(f, str):
                u = f
                if not u.startswith("http"):
                    u = urljoin(BASE_URL, u)
                normalized_feeds.append(u)
            else:
                normalized_feeds.append(f)

        logger.info(f"   Validating {len(normalized_feeds)} Phase 1 feeds before continuing...")
        validation_results = coordinator.validator_agent.validate_batch(normalized_feeds)

        validated_count = validation_results.get("valid_count", 0)
        success_rate = validation_results.get("success_rate", 0)
        # Populate coordinator lists (same shape used elsewhere)
        coordinator.all_discovered_feeds = normalized_feeds
        coordinator.validated_feeds = validation_results.get("validated_feeds", [])

        coordinator.phase_results["phase_1"] = {
            "status": "loaded_from_checkpoint" if checkpoint else "completed",
            "feeds_discovered": len(phase_1_feeds),
            "feeds_validated": validated_count,
            "validation_rate": success_rate
        }

        # Run RAG iterations (this is where errors might occur)
        coordinator._phase_2_rag_iterations()

        # ====================================================================
        # PHASE FINAL: Analysis & Results
        # ====================================================================

        logger.info("\n📍 PHASE FINAL: Analysis & Results Compilation")
        logger.info("-" * 100)

        results = coordinator._phase_final_analysis()

        # Print final summary
        coordinator._print_final_summary(results)

    # CHECKPOINT SAVED FOR FINAL RESULTS
        checkpoint_mgr.save_final_results_checkpoint(results, RUN_ID)

        # Save results to main file
        output_file = coordinator.save_results("discovery_results.json")

        print(f"\nDiscovery complete!")
        print(f"   Total feeds: {results['summary']['total_unique_feeds']}")
        print(f"   Results saved to: {output_file}")
        print(f"   Checkpoint saved for recovery\n")

        # Cleanup old checkpoints (keep only 5 most recent)
        checkpoint_mgr.cleanup_old_checkpoints(keep_count=5)
    
    except Exception as e:
        print(f"\nError occurred: {e}")
        print(f"\nGood news: Phase 1 results (if any) were saved as a checkpoint.")
        print(f"   Checkpoint: {RUN_ID}")
        print(f"\nTo recover from this checkpoint:")
        print(f"   1. Fix the error in the subsequent scripts")
        print(f"   2. Run main.py again with the same inputs")
        print(f"   3. The system will load Phase 1 results and continue from Phase 2\n")
        
        logger.error(f"Discovery workflow failed: {e}", exc_info=True)
        
        # List available checkpoints
        available = checkpoint_mgr.list_available_checkpoints()
        if available:
            print(f"Available checkpoints:")
            for checkpoint in available[:5]:
                print(f"   - {os.path.basename(checkpoint)}")
        
        raise


def show_available_checkpoints():
    """
    Show all available checkpoints for manual inspection.
    """
    
    checkpoint_mgr = CheckpointManager()
    available = checkpoint_mgr.list_available_checkpoints()
    
    print("\nAvailable Checkpoints:")
    print("="*100)
    
    if not available:
        print("No checkpoints found")
        return
    
    for checkpoint in available[:10]:
        filename = os.path.basename(checkpoint)
        size = os.path.getsize(checkpoint)
        print(f"   • {filename} ({size:,} bytes)")
    
    if len(available) > 10:
        print(f"   ... and {len(available) - 10} more")


if __name__ == "__main__":
    import sys
    
    # Check for command-line arguments
    # Simple CLI parsing: support --list-checkpoints, --help, and --force-phase1
    args = sys.argv[1:]
    if not args:
        # Run normal discovery
        main()
    else:
        if "--help" in args:
            print("""
Usage: python main.py [options]

Options:
  (no args)              Run discovery with checkpoints
  --list-checkpoints     Show all available checkpoints
  --force-phase1         Force running Phase 1 discovery even if a checkpoint exists
  --help                 Show this help message

Examples:
  python main.py                         # Run normal discovery
  python main.py --list-checkpoints      # Show saved checkpoints
  python main.py --force-phase1          # Force Phase 1 discovery (ignore checkpoint)
            """)
        elif "--list-checkpoints" in args:
            show_available_checkpoints()
        else:
            # If --force-phase1 present, pass it to main
            force_flag = "--force-phase1" in args
            main(force_phase1=force_flag)