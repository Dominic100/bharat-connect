"""
learning_agent.py - Continuous Learning & Optimization Agent
=============================================================

Analyzes discovery patterns and suggests optimizations.
Learns from every iteration to improve future discovery strategies.

This agent is responsible for:
1. Pattern analysis and trend detection
2. Strategy optimization recommendations
3. Coverage estimation
4. Success rate tracking
5. Discovery insights
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningAgent:
    """
    Continuous learning agent that analyzes discovery patterns.
    
    Purpose: Learn from discovery results to optimize future iterations
    
    Analyzes:
    - Success/failure patterns
    - Parameter effectiveness
    - Coverage trends
    - Optimal strategies
    - Domain-specific insights
    """
    
    def __init__(self):
        """Initialize learning agent."""
        self.iteration_history = []
        self.domain_patterns = defaultdict(list)
        self.parameter_effectiveness = defaultdict(lambda: {"success": 0, "failures": 0})
        self.strategy_performance = defaultdict(list)
        self.insights = []
        
        logger.info("LearningAgent initialized")
    
    def analyze_iteration(self, 
                         iteration_num: int,
                         domain: str,
                         candidates_generated: int,
                         candidates_validated: int,
                         new_feeds_found: int,
                         patterns: Dict,
                         strategy: str,
                         validated_reports: Optional[List[Dict]] = None,
                         rejected_reports: Optional[List[Dict]] = None) -> Dict:
        """
        Analyze single iteration results.
        
        Args:
            iteration_num: Iteration number
            domain: Domain being discovered
            candidates_generated: Number of candidates generated
            candidates_validated: Number of candidates validated
            new_feeds_found: Number of new valid feeds found
            patterns: Learned patterns from RAG agent
            strategy: Generation strategy used
            
        Returns:
            Analysis report
        """
        
        logger.info(f"Analyzing Iteration {iteration_num}...")
        
        # If the caller provided rich validated report lists, use them to update counts
        if validated_reports is not None:
            candidates_validated = len(validated_reports)

        # Calculate metrics
        success_rate = new_feeds_found / max(1, candidates_validated)
        generation_efficiency = new_feeds_found / max(1, candidates_generated)
        
        # Record iteration
        iteration_record = {
            "iteration": iteration_num,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "candidates_generated": candidates_generated,
            "candidates_validated": candidates_validated,
            "new_feeds_found": new_feeds_found,
            "success_rate": success_rate,
            "generation_efficiency": generation_efficiency,
            "strategy": strategy,
            "patterns": patterns,
            "validated_reports": validated_reports or [],
            "rejected_reports": rejected_reports or []
        }
        
        self.iteration_history.append(iteration_record)
        
        # Track strategy performance
        self.strategy_performance[strategy].append({
            "iteration": iteration_num,
            "success_rate": success_rate,
            "efficiency": generation_efficiency
        })
        
        # Analyze patterns
        analysis = self._analyze_patterns(patterns)
        
        # Generate insights
        insights = self._generate_insights(iteration_num, iteration_record, analysis)
        self.insights.extend(insights)
        
        logger.info(f"   Iteration {iteration_num} analyzed")
        logger.info(f"      Success rate: {success_rate:.1%}")
        logger.info(f"      Efficiency: {generation_efficiency:.1%}")
        
        return {
            "iteration": iteration_num,
            "metrics": iteration_record,
            "analysis": analysis,
            "insights": insights
        }
    
    def _analyze_patterns(self, patterns: Dict) -> Dict:
        """Analyze discovered patterns."""
        
        analysis = {
            "parameters": {},
            "parameter_count": 0,
            "dependencies": 0,
            "coverage_estimate": 0,
            "key_insights": []
        }
        
        if not patterns:
            return analysis
        
        # Analyze parameters
        params = patterns.get("parameters", {})
        analysis["parameter_count"] = len(params)
        
        for param_name, param_info in params.items():
            param_analysis = {
                "name": param_name,
                "type": param_info.get("type"),
                "observed_values": len(param_info.get("observed_values", [])),
                "confidence": param_info.get("confidence", 0),
                "interpretation": param_info.get("interpretation", "")
            }
            analysis["parameters"][param_name] = param_analysis
        
        # Analyze dependencies
        deps = patterns.get("dependencies", [])
        analysis["dependencies"] = len(deps)
        
        for dep in deps:
            insight = f"{dep.get('parameter')} depends on {dep.get('depends_on')}"
            analysis["key_insights"].append(insight)
        
        # Coverage estimate
        coverage = patterns.get("coverage", {})
        analysis["coverage_estimate"] = coverage.get("coverage_percent", 0)
        
        return analysis
    
    def _generate_insights(self, 
                          iteration_num: int,
                          iteration_record: Dict,
                          analysis: Dict) -> List[str]:
        """Generate actionable insights from iteration."""
        
        insights = []
        success_rate = iteration_record.get("success_rate", 0)
        strategy = iteration_record.get("strategy", "unknown")
        
        # Success rate insights
        if success_rate > 0.2:
            insights.append(f"Iteration {iteration_num}: High success rate ({success_rate:.1%})")
        elif success_rate > 0.1:
            insights.append(f"Iteration {iteration_num}: Moderate success rate ({success_rate:.1%})")
        elif success_rate == 0:
            insights.append(f"Iteration {iteration_num}: No new feeds (possible convergence)")
        else:
            insights.append(f"Iteration {iteration_num}: Low success rate ({success_rate:.1%})")
        
        # Strategy performance
        if strategy == "hybrid":
            insights.append(f"Strategy '{strategy}' provides balanced exploration")
        elif strategy == "suggested":
            insights.append(f"Strategy '{strategy}' focuses on high-confidence candidates")
        elif strategy == "systematic":
            insights.append(f"Strategy '{strategy}' explores comprehensively")
        
        # Coverage insights
        coverage = analysis.get("coverage_estimate", 0)
        if coverage > 80:
            insights.append(f"Coverage high ({coverage}%) - near saturation")
        elif coverage > 50:
            insights.append(f"Coverage moderate ({coverage}%) - keep exploring")
        else:
            insights.append(f"Coverage low ({coverage}%) - significant potential remains")
        
        # Parameter complexity
        param_count = analysis.get("parameter_count", 0)
        if param_count > 5:
            insights.append(f"High parameter complexity ({param_count} params) - focus on dependencies")
        elif param_count <= 2:
            insights.append(f"Low parameter complexity ({param_count} params) - exhaustive search recommended")
        
        # Dependencies
        dep_count = analysis.get("dependencies", 0)
        if dep_count > 0:
            insights.append(f"Identified {dep_count} parameter dependencies - refine generation strategy")
        
        return insights
    
    def get_convergence_assessment(self, recent_iterations: int = 3) -> Dict:
        """
        Assess if discovery is converging.
        
        Args:
            recent_iterations: Number of recent iterations to analyze
            
        Returns:
            Convergence assessment
        """
        
        if len(self.iteration_history) < recent_iterations:
            return {
                "converging": False,
                "reason": "Not enough iterations",
                "confidence": 0,
                "recommendation": "Continue iterations"
            }
        
        recent = self.iteration_history[-recent_iterations:]
        recent_feeds = [it.get("new_feeds_found", 0) for it in recent]
        
        # Check convergence indicators
        all_zero = all(count == 0 for count in recent_feeds)
        avg_recent = sum(recent_feeds) / len(recent_feeds)
        
        if all_zero:
            return {
                "converging": True,
                "reason": "No new feeds found in recent iterations",
                "confidence": 0.95,
                "recommendation": "Stop discovery"
            }
        
        if avg_recent < 1:
            return {
                "converging": True,
                "reason": "Diminishing returns detected",
                "confidence": 0.80,
                "recommendation": "1-2 more iterations then stop"
            }
        
        if avg_recent < 3:
            return {
                "converging": True,
                "reason": "Gradual reduction in new feeds",
                "confidence": 0.60,
                "recommendation": "Continue 2-3 more iterations"
            }
        
        return {
            "converging": False,
            "reason": "Good discovery rate maintained",
            "confidence": 0.70,
            "recommendation": "Continue iterations"
        }
    
    def get_strategy_recommendation(self) -> Dict:
        """
        Recommend optimal strategy based on history.
        
        Returns:
            Strategy recommendation
        """
        
        if not self.strategy_performance:
            return {
                "recommended": "hybrid",
                "reason": "No history available",
                "confidence": 0.5
            }
        
        # Calculate average success rate per strategy
        strategy_scores = {}
        for strategy, results in self.strategy_performance.items():
            avg_success = sum(r["success_rate"] for r in results) / len(results)
            avg_efficiency = sum(r["efficiency"] for r in results) / len(results)
            
            # Weighted score (60% success, 40% efficiency)
            score = (avg_success * 0.6) + (avg_efficiency * 0.4)
            strategy_scores[strategy] = {
                "score": score,
                "avg_success": avg_success,
                "avg_efficiency": avg_efficiency,
                "uses": len(results)
            }
        
        # Find best strategy
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1]["score"])
        
        return {
            "recommended": best_strategy[0],
            "score": best_strategy[1]["score"],
            "avg_success_rate": best_strategy[1]["avg_success"],
            "avg_efficiency": best_strategy[1]["avg_efficiency"],
            "times_used": best_strategy[1]["uses"],
            "all_strategies": strategy_scores,
            "confidence": min(0.95, best_strategy[1]["score"])
        }
    
    def get_domain_insights(self, domain: str) -> Dict:
        """
        Get insights specific to a domain.
        
        Args:
            domain: Domain to analyze
            
        Returns:
            Domain-specific insights
        """
        
        domain_iterations = [
            it for it in self.iteration_history 
            if it.get("domain") == domain
        ]
        
        if not domain_iterations:
            return {"domain": domain, "iterations": 0, "insights": []}
        
        total_generated = sum(it.get("candidates_generated", 0) for it in domain_iterations)
        total_validated = sum(it.get("candidates_validated", 0) for it in domain_iterations)
        total_found = sum(it.get("new_feeds_found", 0) for it in domain_iterations)
        
        avg_success = sum(it.get("success_rate", 0) for it in domain_iterations) / len(domain_iterations)
        
        insights = [
            f"Iterations: {len(domain_iterations)}",
            f"Total feeds found: {total_found}",
            f"Total candidates tested: {total_validated}",
            f"Average success rate: {avg_success:.1%}",
            f"Generation efficiency: {(total_found / max(1, total_generated)):.1%}"
        ]
        
        # Best iteration
        best_iter = max(domain_iterations, key=lambda x: x.get("new_feeds_found", 0))
        insights.append(f"Best iteration: #{best_iter['iteration']} with {best_iter['new_feeds_found']} new feeds")
        
        return {
            "domain": domain,
            "iterations": len(domain_iterations),
            "total_found": total_found,
            "avg_success_rate": avg_success,
            "insights": insights
        }
    
    def get_parameter_effectiveness(self) -> Dict:
        """
        Analyze which parameters are most effective.
        
        Returns:
            Parameter effectiveness analysis
        """
        
        effectiveness = {}
        
        for param, stats in self.parameter_effectiveness.items():
            total = stats["success"] + stats["failures"]
            if total == 0:
                success_rate = 0
            else:
                success_rate = stats["success"] / total
            
            effectiveness[param] = {
                "success": stats["success"],
                "failures": stats["failures"],
                "total": total,
                "success_rate": success_rate,
                "effectiveness_score": success_rate * 100
            }
        
        # Sort by effectiveness
        sorted_params = sorted(
            effectiveness.items(),
            key=lambda x: x[1]["effectiveness_score"],
            reverse=True
        )
        
        return dict(sorted_params)
    
    def get_learning_report(self) -> Dict:
        """
        Get comprehensive learning report.
        
        Returns:
            Complete learning analysis
        """
        
        convergence = self.get_convergence_assessment()
        strategy_rec = self.get_strategy_recommendation()
        
        total_iterations = len(self.iteration_history)
        total_feeds = sum(
            it.get("new_feeds_found", 0) 
            for it in self.iteration_history
        )
        total_tested = sum(
            it.get("candidates_validated", 0) 
            for it in self.iteration_history
        )
        
        return {
            "summary": {
                "total_iterations": total_iterations,
                "total_feeds_found": total_feeds,
                "total_urls_tested": total_tested,
                "average_success_rate": total_feeds / max(1, total_tested) if total_tested > 0 else 0
            },
            "convergence_assessment": convergence,
            "strategy_recommendation": strategy_rec,
            "parameter_effectiveness": self.get_parameter_effectiveness(),
            "insights": self.insights,
            "iteration_history": self.iteration_history
        }
    
    def print_insights(self):
        """Print all insights in human-readable format."""
        logger.info("\n" + "="*80)
        logger.info("LEARNING INSIGHTS")
        logger.info("="*80)

        for insight in self.insights:
            logger.info(f"  - {insight}")

        # Convergence assessment
        convergence = self.get_convergence_assessment()
        logger.info("\nConvergence Assessment:")
        logger.info(f"   Status: {'Converging' if convergence['converging'] else 'Not converged'}")
        logger.info(f"   Reason: {convergence['reason']}")
        logger.info(f"   Confidence: {convergence['confidence']:.0%}")
        logger.info(f"   Recommendation: {convergence['recommendation']}")

        # Strategy recommendation
        strategy = self.get_strategy_recommendation()
        logger.info("\nStrategy Recommendation:")
        logger.info(f"   Recommended: {strategy['recommended']}")
        logger.info(f"   Success Rate: {strategy.get('avg_success_rate', 0):.1%}")
        logger.info(f"   Confidence: {strategy['confidence']:.0%}")


# Example usage
if __name__ == "__main__":
    learner = LearningAgent()
    
    # Simulate iterations
    patterns_1 = {
        "parameters": {
            "ModId": {"type": "numeric", "observed_values": ["1", "2", "3"]},
            "Lang": {"type": "numeric", "observed_values": ["8", "18"]}
        },
        "coverage": {"coverage_percent": 40}
    }
    
    result = learner.analyze_iteration(
        iteration_num=1,
        domain="pib.gov.in",
        candidates_generated=50,
        candidates_validated=48,
        new_feeds_found=7,
        patterns=patterns_1,
        strategy="hybrid"
    )
    
    print(json.dumps(result, indent=2, default=str))
    
    # Get report
    report = learner.get_learning_report()
    learner.print_insights()
