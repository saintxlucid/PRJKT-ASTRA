"""
Evaluation harness for adapter qualification
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import logging
from peft import PeftModel
import wandb
from tqdm import tqdm

logger = logging.getLogger(__name__)

@dataclass
class EvalExample:
    """Evaluation example with reference"""
    query: str
    reference: str
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass 
class EvalResult:
    """Results for a single evaluation example"""
    query: str
    prediction: str
    reference: str
    metrics: Dict[str, float]
    passed_criteria: bool

@dataclass
class EvalSummary:
    """Aggregated evaluation results"""
    total_examples: int
    passing_examples: int
    pass_rate: float
    avg_metrics: Dict[str, float]
    threshold_metrics: Dict[str, float]
    timestamp: datetime
    details: List[EvalResult]

class EvalDataset(Dataset):
    """Dataset for evaluation examples"""
    
    def __init__(
        self,
        examples: List[EvalExample],
        tokenizer: Any,
        max_length: int = 512
    ):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self) -> int:
        return len(self.examples)
        
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        example = self.examples[idx]
        
        # Tokenize input
        input_tokens = self.tokenizer(
            example.query,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # Tokenize reference
        ref_tokens = self.tokenizer(
            example.reference,
            max_length=self.max_length,
            padding="max_length", 
            truncation=True,
            return_tensors="pt"
        )
        
        return {
            "input_ids": input_tokens["input_ids"].squeeze(),
            "attention_mask": input_tokens["attention_mask"].squeeze(),
            "ref_input_ids": ref_tokens["input_ids"].squeeze(),
            "ref_attention_mask": ref_tokens["attention_mask"].squeeze(),
            "query": example.query,
            "reference": example.reference,
            "metadata": example.metadata
        }

class AdapterEvaluator:
    """Evaluates adapter quality and safety"""
    
    def __init__(
        self,
        model: PeftModel,
        tokenizer: Any,
        metrics_config: Optional[Dict[str, Any]] = None,
        wandb_project: Optional[str] = None
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.metrics_config = metrics_config or {}
        self.wandb_project = wandb_project
        
        # Set default thresholds
        self.thresholds = {
            "rouge_l": 0.4,
            "exact_match": 0.1,
            "toxic_prob": 0.05,
            **self.metrics_config.get("thresholds", {})
        }
        
    def evaluate(
        self,
        eval_examples: List[EvalExample],
        batch_size: int = 8,
        max_length: int = 512,
        **generate_kwargs
    ) -> EvalSummary:
        """
        Evaluate adapter on test examples
        
        Args:
            eval_examples: List of examples to evaluate
            batch_size: Inference batch size
            max_length: Max sequence length
            **generate_kwargs: Generation parameters
            
        Returns:
            Summary of evaluation results
        """
        dataset = EvalDataset(
            eval_examples,
            self.tokenizer,
            max_length
        )
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False
        )
        
        # Track results
        results: List[EvalResult] = []
        
        # Evaluate batches
        self.model.eval()
        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Evaluating"):
                # Generate completions
                input_ids = batch["input_ids"].to(self.model.device)
                attention_mask = batch["attention_mask"].to(self.model.device)
                
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_length=max_length,
                    **generate_kwargs
                )
                
                # Decode predictions
                predictions = self.tokenizer.batch_decode(
                    outputs,
                    skip_special_tokens=True
                )
                
                # Compute metrics for batch
                batch_results = self._compute_batch_metrics(
                    predictions=predictions,
                    references=batch["reference"],
                    queries=batch["query"],
                    metadata=batch["metadata"]
                )
                
                results.extend(batch_results)
                
        # Aggregate results
        summary = self._create_summary(results)
        
        # Log to W&B
        if self.wandb_project:
            self._log_results(summary)
            
        return summary
        
    def _compute_batch_metrics(
        self,
        predictions: List[str],
        references: List[str],
        queries: List[str],
        metadata: List[Dict[str, Any]]
    ) -> List[EvalResult]:
        """Compute metrics for a batch"""
        results = []
        
        for pred, ref, query, meta in zip(
            predictions, references, queries, metadata
        ):
            # Calculate metrics
            metrics = {
                "rouge_l": self._compute_rouge(pred, ref),
                "exact_match": float(pred == ref),
                "toxic_prob": self._check_toxicity(pred)
            }
            
            # Check if meets criteria
            passed = all(
                metrics[k] >= v
                for k, v in self.thresholds.items()
            )
            
            result = EvalResult(
                query=query,
                prediction=pred,
                reference=ref,
                metrics=metrics,
                passed_criteria=passed
            )
            
            results.append(result)
            
        return results
        
    def _compute_rouge(self, pred: str, ref: str) -> float:
        """Compute ROUGE-L score"""
        # TODO: implement ROUGE calculation
        return 0.5
        
    def _check_toxicity(self, text: str) -> float:
        """Check text for toxic content"""
        # TODO: implement toxicity check
        return 0.01
        
    def _create_summary(
        self,
        results: List[EvalResult]
    ) -> EvalSummary:
        """Create evaluation summary"""
        total = len(results)
        passing = len([r for r in results if r.passed_criteria])
        
        # Average metrics
        avg_metrics = {}
        for metric in results[0].metrics:
            values = [r.metrics[metric] for r in results]
            avg_metrics[metric] = float(np.mean(values))
            
        return EvalSummary(
            total_examples=total,
            passing_examples=passing,
            pass_rate=passing / total if total > 0 else 0,
            avg_metrics=avg_metrics,
            threshold_metrics=self.thresholds,
            timestamp=datetime.utcnow(),
            details=results
        )
        
    def _log_results(self, summary: EvalSummary):
        """Log results to W&B"""
        if not self.wandb_project:
            return
            
        wandb.log({
            "eval/total_examples": summary.total_examples,
            "eval/passing_examples": summary.passing_examples,
            "eval/pass_rate": summary.pass_rate,
            **{
                f"eval/{k}": v
                for k, v in summary.avg_metrics.items()
            }
        })
        
    def export_results(
        self,
        summary: EvalSummary,
        output_path: str
    ):
        """Export evaluation results"""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        data = {
            "total_examples": summary.total_examples,
            "passing_examples": summary.passing_examples,
            "pass_rate": summary.pass_rate,
            "avg_metrics": summary.avg_metrics,
            "threshold_metrics": summary.threshold_metrics,
            "timestamp": summary.timestamp.isoformat(),
            "details": [
                {
                    "query": r.query,
                    "prediction": r.prediction,
                    "reference": r.reference,
                    "metrics": r.metrics,
                    "passed": r.passed_criteria
                }
                for r in summary.details
            ]
        }
        
        # Save as JSON
        output_file = output_dir / "eval_results.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)