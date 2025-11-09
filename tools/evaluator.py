"""
ASTRA Evaluation Framework

Provides performance metrics and evaluation pipelines for ASTRA subsystems.
Supports metrics for NLU, ASR, Safety, Code Generation, and QA subsystems.

Created: October 18, 2025
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Standard evaluation metrics"""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    loss: float = 0.0
    custom_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class Evaluator(ABC):
    """Base evaluator class for all subsystems"""
    
    def __init__(self, subsystem: str):
        """
        Initialize evaluator.
        
        Args:
            subsystem: Name of subsystem (e.g., 'nlu', 'safety')
        """
        self.subsystem = subsystem
        self.metrics_history: List[EvaluationMetrics] = []
    
    @abstractmethod
    def evaluate(self, predictions: List[Any], targets: List[Any]) -> EvaluationMetrics:
        """Evaluate predictions against targets"""
        pass
    
    def save_results(self, metrics: EvaluationMetrics, output_path: Optional[Path] = None) -> None:
        """Save evaluation results to file"""
        if output_path is None:
            output_path = Path(f"evaluation_{self.subsystem}_{datetime.now().isoformat()}.json")
        
        try:
            output_path.write_text(metrics.to_json())
            logger.info(f"Evaluation results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save evaluation results: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all evaluations"""
        if not self.metrics_history:
            return {}
        
        return {
            'num_evaluations': len(self.metrics_history),
            'latest_metrics': self.metrics_history[-1].to_dict(),
            'average_accuracy': sum(m.accuracy for m in self.metrics_history) / len(self.metrics_history),
            'average_f1': sum(m.f1_score for m in self.metrics_history) / len(self.metrics_history),
        }


class NLUEvaluator(Evaluator):
    """Evaluator for Natural Language Understanding"""
    
    def __init__(self):
        super().__init__('nlu')
    
    def evaluate(self, predictions: List[str], targets: List[str]) -> EvaluationMetrics:
        """Evaluate NLU predictions"""
        if len(predictions) != len(targets):
            raise ValueError("Predictions and targets must have same length")
        
        correct = sum(1 for p, t in zip(predictions, targets) if p == t)
        accuracy = correct / len(predictions) if predictions else 0.0
        
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            precision=accuracy,  # Simplified for intent classification
            recall=accuracy,
            f1_score=accuracy,
            custom_metrics={
                'correct_predictions': correct,
                'total_predictions': len(predictions),
            }
        )
        
        self.metrics_history.append(metrics)
        logger.info(f"NLU Evaluation: Accuracy={accuracy:.4f}")
        return metrics


class SafetyEvaluator(Evaluator):
    """Evaluator for Safety & Toxicity Detection"""
    
    def __init__(self, threshold: float = 0.5):
        super().__init__('safety')
        self.threshold = threshold
    
    def evaluate(self, predictions: List[float], targets: List[int]) -> EvaluationMetrics:
        """
        Evaluate safety predictions.
        
        Args:
            predictions: Toxicity scores [0.0-1.0]
            targets: Binary labels [0 or 1]
        """
        if len(predictions) != len(targets):
            raise ValueError("Predictions and targets must have same length")
        
        # Convert scores to binary predictions
        binary_pred = [1 if p >= self.threshold else 0 for p in predictions]
        
        # Calculate metrics
        tp = sum(1 for p, t in zip(binary_pred, targets) if p == 1 and t == 1)
        fp = sum(1 for p, t in zip(binary_pred, targets) if p == 1 and t == 0)
        tn = sum(1 for p, t in zip(binary_pred, targets) if p == 0 and t == 0)
        fn = sum(1 for p, t in zip(binary_pred, targets) if p == 0 and t == 1)
        
        accuracy = (tp + tn) / len(targets) if targets else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            custom_metrics={
                'true_positives': tp,
                'false_positives': fp,
                'true_negatives': tn,
                'false_negatives': fn,
                'threshold': self.threshold,
            }
        )
        
        self.metrics_history.append(metrics)
        logger.info(f"Safety Evaluation: Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}")
        return metrics


class CodeEvaluator(Evaluator):
    """Evaluator for Code Generation"""
    
    def __init__(self):
        super().__init__('code')
    
    def evaluate(self, predictions: List[str], targets: List[str]) -> EvaluationMetrics:
        """
        Evaluate code generation.
        
        Args:
            predictions: Generated code snippets
            targets: Ground truth code snippets
        """
        if len(predictions) != len(targets):
            raise ValueError("Predictions and targets must have same length")
        
        # Exact match accuracy
        exact_matches = sum(1 for p, t in zip(predictions, targets) if p.strip() == t.strip())
        accuracy = exact_matches / len(predictions) if predictions else 0.0
        
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            custom_metrics={
                'exact_matches': exact_matches,
                'total_samples': len(predictions),
            }
        )
        
        self.metrics_history.append(metrics)
        logger.info(f"Code Evaluation: Exact Match={accuracy:.4f}")
        return metrics


class QAEvaluator(Evaluator):
    """Evaluator for Question-Answering"""
    
    def __init__(self):
        super().__init__('qa')
    
    def evaluate(self, predictions: List[str], targets: List[List[str]]) -> EvaluationMetrics:
        """
        Evaluate QA predictions using F1 and EM scores.
        
        Args:
            predictions: Predicted answers
            targets: Ground truth answers (lists for multiple valid answers)
        """
        if len(predictions) != len(targets):
            raise ValueError("Predictions and targets must have same length")
        
        em_score = 0.0  # Exact Match
        f1_scores = []
        
        for pred, target_list in zip(predictions, targets):
            # Check exact match
            if pred in target_list or pred.strip() in [t.strip() for t in target_list]:
                em_score += 1.0
            
            # Calculate F1 for best match
            best_f1 = 0.0
            for target in target_list:
                f1 = self._calculate_f1(pred, target)
                best_f1 = max(best_f1, f1)
            f1_scores.append(best_f1)
        
        em_score = em_score / len(predictions) if predictions else 0.0
        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
        
        metrics = EvaluationMetrics(
            accuracy=em_score,
            f1_score=avg_f1,
            custom_metrics={
                'exact_match': em_score,
                'average_f1': avg_f1,
            }
        )
        
        self.metrics_history.append(metrics)
        logger.info(f"QA Evaluation: EM={em_score:.4f}, F1={avg_f1:.4f}")
        return metrics
    
    @staticmethod
    def _calculate_f1(pred: str, target: str) -> float:
        """Calculate F1 score between two strings"""
        pred_tokens = set(pred.lower().split())
        target_tokens = set(target.lower().split())
        
        common = len(pred_tokens & target_tokens)
        if common == 0:
            return 0.0
        
        precision = common / len(pred_tokens) if pred_tokens else 0.0
        recall = common / len(target_tokens) if target_tokens else 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return f1


class ASREvaluator(Evaluator):
    """Evaluator for Automatic Speech Recognition"""
    
    def __init__(self):
        super().__init__('asr')
    
    def evaluate(self, predictions: List[str], targets: List[str]) -> EvaluationMetrics:
        """
        Evaluate ASR predictions using Word Error Rate (WER).
        
        Args:
            predictions: Predicted transcriptions
            targets: Ground truth transcriptions
        """
        if len(predictions) != len(targets):
            raise ValueError("Predictions and targets must have same length")
        
        wer_scores = []
        for pred, target in zip(predictions, targets):
            wer = self._calculate_wer(pred, target)
            wer_scores.append(wer)
        
        avg_wer = sum(wer_scores) / len(wer_scores) if wer_scores else 0.0
        accuracy = 1.0 - avg_wer  # Inverse of WER
        
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            custom_metrics={
                'word_error_rate': avg_wer,
            }
        )
        
        self.metrics_history.append(metrics)
        logger.info(f"ASR Evaluation: WER={avg_wer:.4f}")
        return metrics
    
    @staticmethod
    def _calculate_wer(pred: str, target: str) -> float:
        """Calculate Word Error Rate"""
        pred_words = pred.lower().split()
        target_words = target.lower().split()
        
        # Simple edit distance calculation
        d = {}
        for i in range(len(pred_words) + 1):
            d[i, 0] = i
        for j in range(len(target_words) + 1):
            d[0, j] = j
        
        for i in range(1, len(pred_words) + 1):
            for j in range(1, len(target_words) + 1):
                cost = 0 if pred_words[i - 1] == target_words[j - 1] else 1
                d[i, j] = min(
                    d[i - 1, j] + 1,
                    d[i, j - 1] + 1,
                    d[i - 1, j - 1] + cost
                )
        
        wer = d[len(pred_words), len(target_words)] / len(target_words) if target_words else 0.0
        return wer


# Evaluator registry
EVALUATOR_REGISTRY: Dict[str, type] = {
    'nlu': NLUEvaluator,
    'safety': SafetyEvaluator,
    'code': CodeEvaluator,
    'qa': QAEvaluator,
    'asr': ASREvaluator,
}


def get_evaluator(subsystem: str) -> Optional[Evaluator]:
    """Get evaluator for subsystem"""
    evaluator_class = EVALUATOR_REGISTRY.get(subsystem.lower())
    if evaluator_class is None:
        logger.warning(f"No evaluator found for subsystem: {subsystem}")
        return None
    
    return evaluator_class()


if __name__ == "__main__":
    # Test evaluators
    logging.basicConfig(level=logging.INFO)
    
    # Test NLU evaluator
    nlu_eval = NLUEvaluator()
    predictions = ['intent1', 'intent2', 'intent1']
    targets = ['intent1', 'intent2', 'intent3']
    metrics = nlu_eval.evaluate(predictions, targets)
    print(f"\nNLU Metrics: {metrics.to_dict()}")
    
    # Test Safety evaluator
    safety_eval = SafetyEvaluator(threshold=0.5)
    pred_scores = [0.1, 0.8, 0.3, 0.9]
    target_labels = [0, 1, 0, 1]
    metrics = safety_eval.evaluate(pred_scores, target_labels)
    print(f"\nSafety Metrics: {metrics.to_dict()}")
