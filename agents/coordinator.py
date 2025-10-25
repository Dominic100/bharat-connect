"""
coordinator.py - Main Orchestration Agent
==========================================

Orchestrates the complete multi-agent RSS discovery workflow.
Coordinates between discovery, learning, validation, and optimization.

This is the main entry point that orchestrates:
1. Initial heuristic discovery (UltimateAIScraper)
2. RAG learning iterations (RAGAgent)
3. Feed validation (ValidatorAgent)
4. Pattern analysis and optimization (LearningAgent)
5. Results compilation and storage
"""

from intelligent_feed_agent import UltimateAIScraper
from rag_agent import RAGAgent
from validator_agent import ValidatorAgent
from learning_agent import LearningAgent
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """
    Main orchestrator for multi-agent RSS feed discovery system.
    
    Purpose: Coordinate all agents to discover RSS feeds efficiently
    
    Workflow:
    Phase 1: Initial heuristic discovery
    Phase 2-N: RAG learning iterations with validation
    Phase Final: Analysis and results compilation
    """
    
    def __init__(self, 
                 project_id: str,
                 base_url: str,
                 max_iterations: int = 5,
                 min_quality_score: int = 60):
        """
        Initialize coordinator agent.
        
        Args:
            project_id: Google Cloud project ID
            base_url: Base RSS feed URL (e.g., https://pib.gov.in/RssMain.aspx)
            max_iterations: Maximum RAG iterations (default: 5)
            min_quality_score: Minimum quality score to accept feeds (0-100)
        """
        self.project_id = project_id
        self.base_url = base_url
        self.max_iterations = max_iterations
        self.min_quality_score = min_quality_score
        self.run_id = str(uuid.uuid4())  # Unique ID for this discovery run
        
        # Initialize all agents
        self.intelligent_agent = UltimateAIScraper(project_id)
        self.rag_agent = RAGAgent(project_id, base_url)
        # AIValidatorAgent requires project_id as first argument; pass through for compatibility
        self.validator_agent = ValidatorAgent(project_id=project_id, min_quality_score=min_quality_score, timeout=10)
        self.learning_agent = LearningAgent()
        
        # State tracking
        self.all_discovered_feeds = []
        self.validated_feeds = []
        self.start_time = None
        self.phase_results = {}
        
        logger.info(f"CoordinatorAgent initialized (run_id: {self.run_id})")
        logger.info(f"   Project: {project_id}")
        logger.info(f"   Base URL: {base_url}")
        logger.info(f"   Max iterations: {max_iterations}")
    
    def execute_discovery(self, start_url: str) -> Dict:
        """
        Execute complete discovery workflow.
        
        Args:
            start_url: Starting URL for initial discovery
                      (e.g., https://www.pib.gov.in/ViewRss.aspx)
            
        Returns:
            Complete discovery results
        """
        
        self.start_time = datetime.now()
        
        print("\n" + "="*100)
        print("STARTING MULTI-AGENT RSS FEED DISCOVERY WORKFLOW")
        print("="*100 + "\n")
        
        try:
            # PHASE 1: Initial Heuristic Discovery
            print("PHASE 1: Initial Heuristic Discovery")
            print("-"*100)
            self._phase_1_initial_discovery(start_url)
            
            # PHASE 2-N: RAG Learning Iterations
            print("\nPHASE 2+: RAG Learning & Validation Iterations")
            print("-"*100)
            self._phase_2_rag_iterations()
            
            # PHASE FINAL: Analysis & Compilation
            print("\nPHASE FINAL: Analysis & Results Compilation")
            print("-"*100)
            results = self._phase_final_analysis()
            
            # Print summary
            self._print_final_summary(results)
            
            return results
        
        except Exception as e:
            logger.error(f"Discovery workflow failed: {e}", exc_info=True)
            raise
    
    def _phase_1_initial_discovery(self, start_url: str):
        """
        Phase 1: Initial heuristic discovery using UltimateAIScraper.
        
        This phase uses Selenium and heuristic methods to discover initial feeds.
        """
        
        logger.info("Phase 1: Running heuristic discovery...")
        
        try:
            # Run intelligent discovery
            initial_feeds = self.intelligent_agent.discover(start_url, max_pages=500)

            logger.info(f"   Found {len(initial_feeds)} feeds via heuristics")
            
            if not initial_feeds:
                logger.warning("No initial feeds discovered!")
                self.phase_results["phase_1"] = {
                    "status": "warning",
                    "feeds_discovered": 0,
                    "feeds_validated": 0
                }
                return
            
            # Validate all initial feeds
            logger.info(f"   Validating {len(initial_feeds)} feeds...")
            validation_results = self.validator_agent.validate_batch(initial_feeds, source='phase1', run_id=self.run_id)
            
            validated_count = validation_results["valid_count"]
            logger.info(f"   {validated_count} feeds passed validation")
            
            # Add to main list
            self.all_discovered_feeds.extend(validation_results["validated_feeds"])
            self.validated_feeds = validation_results["validated_feeds"]
            
            self.phase_results["phase_1"] = {
                "status": "success",
                "feeds_discovered": len(initial_feeds),
                "feeds_validated": validated_count,
                "validation_rate": validation_results["success_rate"]
            }
        
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            raise
    
    def _phase_2_rag_iterations(self):
        """
        Phase 2-N: RAG learning iterations with validation.
        
        Each iteration:
        1. Learns patterns from discovered feeds
        2. Generates new candidate URLs
        3. Validates candidates
        4. Analyzes results
        """
        
        if not self.validated_feeds:
            logger.warning("No feeds to learn from in Phase 2")
            return
        # Tag RAG agent with run id so it can persist validation reports with run context
        try:
            self.rag_agent.run_id = self.run_id
        except Exception:
            pass
        for iteration in range(1, self.max_iterations):
            logger.info(f"\nRAG Iteration {iteration}/{self.max_iterations-1}")
            logger.info("="*80)
            
            try:
                # Run RAG iteration
                result = self.rag_agent.run_iteration(
                    current_feeds=self.validated_feeds,
                    strategy="hybrid",
                    num_candidates=50
                )
                
                new_feeds_found = result.get("new_feeds_found", 0)
                logger.info(f"   Found {new_feeds_found} new feeds")

                # Extract rich validation reports (if provided) and forward to LearningAgent
                validated_reports = result.get("validated_reports", [])
                rejected_reports = result.get("rejected_reports", [])

                # Analyze iteration with learning agent (include per-feed reports)
                if self.rag_agent.learned_patterns:
                    learning_result = self.learning_agent.analyze_iteration(
                        iteration_num=iteration,
                        domain=self._extract_domain(self.base_url),
                        candidates_generated=result.get("candidates_generated", 0),
                        # number of candidates that were validated (tests performed)
                        candidates_validated=len(validated_reports) if validated_reports is not None else 0,
                        new_feeds_found=new_feeds_found,
                        patterns=self.rag_agent.learned_patterns,
                        strategy="hybrid",
                        validated_reports=validated_reports,
                        rejected_reports=rejected_reports
                    )
                    
                    # Log insights
                    for insight in learning_result.get("insights", []):
                        logger.info(f"   {insight}")
                
                # Check convergence
                should_stop, reason = self.rag_agent.should_stop_iteration()
                
                if should_stop:
                    logger.info(f"\nConvergence detected: {reason}")
                    break
                
                if new_feeds_found == 0:
                    logger.info(f"No new feeds in iteration {iteration}, stopping early")
                    break
            
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")
                # Continue to next iteration despite error
                continue
        
        # Update all feeds with latest discoveries
        self.all_discovered_feeds = self.rag_agent.discovered_feeds
    
    def _phase_final_analysis(self) -> Dict:
        """
        Phase Final: Comprehensive analysis and results compilation.
        
        Returns:
            Complete discovery results
        """
        
        logger.info("Compiling final results...")
        
        # Get unique feeds: include validated feeds (seed) + any discovered during RAG
        unique_feeds = {}
        combined_sources = []
        if self.all_discovered_feeds:
            combined_sources.extend(self.all_discovered_feeds)
        if self.validated_feeds:
            combined_sources.extend(self.validated_feeds)

        for feed in combined_sources:
            url = None
            if isinstance(feed, dict):
                url = feed.get("url")
            elif isinstance(feed, str):
                url = feed

            if url:
                if url not in unique_feeds:
                    # Prefer the dict form when available
                    if isinstance(feed, dict):
                        unique_feeds[url] = feed
                    else:
                        unique_feeds[url] = {"url": url}
        
        # Get statistics
        rag_stats = self.rag_agent.get_stats()
        validator_stats = self.validator_agent.get_stats()
        learning_report = self.learning_agent.get_learning_report()
        
        # Get convergence assessment
        convergence = self.learning_agent.get_convergence_assessment()
        strategy_rec = self.learning_agent.get_strategy_recommendation()
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        results = {
            "metadata": {
                "run_id": self.run_id,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "base_url": self.base_url,
                "max_iterations": self.max_iterations,
                "min_quality_score": self.min_quality_score
            },
            "summary": {
                "total_unique_feeds": len(unique_feeds),
                "total_iterations": self.rag_agent.iteration_count,
                "total_urls_tested": rag_stats.get("total_urls_tested", 0),
                "overall_success_rate": rag_stats.get("success_rate", 0),
                "avg_quality_score": validator_stats.get("avg_quality_score", 0)
            },
            "discovered_feeds": list(unique_feeds.values()),
            "statistics": {
                "rag_agent": rag_stats,
                "validator_agent": validator_stats,
                "learning_report": learning_report
            },
            "analysis": {
                "convergence": convergence,
                "strategy_recommendation": strategy_rec,
                "phase_results": self.phase_results
            },
            "insights": self.learning_agent.insights
        }
        
        return results
    
    def _print_final_summary(self, results: Dict):
        """Print final summary in human-readable format."""
        
        print("\n" + "="*100)
        print("DISCOVERY WORKFLOW COMPLETE")
        print("="*100)
        
        metadata = results["metadata"]
        summary = results["summary"]
        analysis = results["analysis"]
        
        print(f"\nMETADATA")
        print(f"   Run ID: {metadata['run_id']}")
        print(f"   Duration: {metadata['duration_seconds']:.1f} seconds")
        print(f"   Start: {metadata['start_time']}")
        
        print(f"\nSUMMARY")
        print(f"   Total Feeds: {summary['total_unique_feeds']}")
        print(f"   Iterations: {summary['total_iterations']}")
        print(f"   URLs Tested: {summary['total_urls_tested']}")
        print(f"   Success Rate: {summary['overall_success_rate']:.1%}")
        print(f"   Avg Quality: {summary['avg_quality_score']:.1f}/100")
        
        print(f"\nCONVERGENCE ANALYSIS")
        convergence = analysis["convergence"]
        print(f"   Status: {'CONVERGED' if convergence['converging'] else 'ACTIVE'}")
        print(f"   Reason: {convergence['reason']}")
        print(f"   Confidence: {convergence['confidence']:.0%}")
        print(f"   Recommendation: {convergence['recommendation']}")
        
        print(f"\nSTRATEGY RECOMMENDATION")
        strategy = analysis["strategy_recommendation"]
        print(f"   Recommended: {strategy['recommended']}")
        print(f"   Success Rate: {strategy.get('avg_success_rate', 0):.1%}")
        print(f"   Efficiency: {strategy.get('avg_efficiency', 0):.1%}")
        print(f"   Confidence: {strategy['confidence']:.0%}")
        
        print(f"\nTOP FEEDS (by quality score)")
        sorted_feeds = sorted(
            results["discovered_feeds"],
            key=lambda x: x.get("quality_score", 0),
            reverse=True
        )
        
        for i, feed in enumerate(sorted_feeds[:10], 1):
            quality = feed.get("quality_score", 0)
            title = feed.get("title", "Untitled")[:50]
            print(f"   {i:2d}. [{quality:>3.0f}/100] {title}")
        
        if len(results["discovered_feeds"]) > 10:
            remaining = len(results["discovered_feeds"]) - 10
            print(f"   ... and {remaining} more feeds")
        
        print(f"\nKEY INSIGHTS")
        for insight in self.learning_agent.insights[:5]:
            print(f"   - {insight}")
        
        print("\n" + "="*100)
    
    def save_results(self, filename: str = "discovery_results.json") -> str:
        """
        Save complete discovery results to JSON file.
        
        Args:
            filename: Output filename
            
        Returns:
            Filename where results were saved
        """
        
        results = self._phase_final_analysis()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Results saved to {filename}")
        return filename
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    def get_results(self) -> Dict:
        """Get current discovery results."""
        return self._phase_final_analysis()


# Example usage
if __name__ == "__main__":
    """
    Example: Complete discovery workflow
    """
    
    # Configuration
    PROJECT_ID = "bharat-connect-000"
    BASE_URL = "https://pib.gov.in/RssMain.aspx"
    START_URL = "https://www.pib.gov.in/ViewRss.aspx"
    MAX_ITERATIONS = 5
    MIN_QUALITY_SCORE = 60
    
    # Initialize coordinator
    coordinator = CoordinatorAgent(
        project_id=PROJECT_ID,
        base_url=BASE_URL,
        max_iterations=MAX_ITERATIONS,
        min_quality_score=MIN_QUALITY_SCORE
    )
    
    # Execute discovery
    results = coordinator.execute_discovery(start_url=START_URL)
    
    # Save results
    coordinator.save_results("discovery_results.json")
    
    print(f"\nDiscovery complete!")
    print(f"   Total feeds: {results['summary']['total_unique_feeds']}")
    print(f"   Results saved to: discovery_results.json")
