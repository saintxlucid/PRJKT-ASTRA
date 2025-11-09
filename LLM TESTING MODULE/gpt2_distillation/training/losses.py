"""
Loss Functions Module

Implementation of modular loss functions for knowledge distillation.
"""

import torch
import torch.nn.functional as F
from typing import Dict, Any, Optional

def kd_kl_loss(student_logits: torch.Tensor, 
               teacher_logits: torch.Tensor, 
               temperature: float = 2.0) -> torch.Tensor:
    """
    KL divergence knowledge distillation loss.
    
    L_kd = T^2 * KL( softmax(z_T/T) || softmax(z_S/T) )
    
    Args:
        student_logits: Student model logits [batch_size, seq_len, vocab_size]
        teacher_logits: Teacher model logits [batch_size, seq_len, vocab_size]
        temperature: Temperature for softening probability distributions
        
    Returns:
        KL divergence loss
    """
    # Soften probabilities with temperature
    student_log_probs = F.log_softmax(student_logits / temperature, dim=-1)
    teacher_probs = F.softmax(teacher_logits / temperature, dim=-1)
    
    # Compute KL divergence
    kl_div = F.kl_div(
        student_log_probs, 
        teacher_probs, 
        reduction="batchmean"
    )
    
    # Scale by temperature squared
    return kl_div * (temperature ** 2)

def ce_loss(student_logits: torch.Tensor, 
           labels: torch.Tensor, 
           ignore_index: int = -100) -> torch.Tensor:
    """
    Cross-entropy loss on teacher argmax sequence.
    
    Args:
        student_logits: Student model logits [batch_size, seq_len, vocab_size]
        labels: Ground truth labels [batch_size, seq_len]
        ignore_index: Index to ignore in loss calculation
        
    Returns:
        Cross-entropy loss
    """
    return F.cross_entropy(
        student_logits.view(-1, student_logits.size(-1)),
        labels.view(-1),
        ignore_index=ignore_index
    )

def sequence_level_ce(student_texts: list, 
                     teacher_texts: list) -> torch.Tensor:
    """
    Sequence-level cross-entropy loss using edit distance as proxy.
    
    Args:
        student_texts: List of student-generated texts
        teacher_texts: List of teacher-generated texts
        
    Returns:
        Sequence-level loss (1 - normalized edit distance)
    """
    # Simple proxy: use edit distance as inverse measure of similarity
    total_loss = 0.0
    count = 0
    
    for s_text, t_text in zip(student_texts, teacher_texts):
        # Calculate edit distance (simplified)
        # In practice, you might use a more sophisticated metric like BLEU or ROUGE
        edit_dist = simple_edit_distance(s_text, t_text)
        max_len = max(len(s_text), len(t_text))
        
        # Normalize edit distance to [0, 1] range
        normalized_dist = edit_dist / max_len if max_len > 0 else 0.0
        
        # Convert to similarity (1 - distance) and then to loss
        similarity = 1.0 - normalized_dist
        loss = 1.0 - similarity  # Loss is 1 - similarity
        
        total_loss += loss
        count += 1
    
    return torch.tensor(total_loss / count if count > 0 else 0.0)

def simple_edit_distance(s1: str, s2: str) -> int:
    """
    Simple edit distance calculation (Levenshtein distance).
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Edit distance
    """
    if len(s1) < len(s2):
        return simple_edit_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def hint_loss(student_hidden: torch.Tensor, 
              teacher_hidden: torch.Tensor) -> torch.Tensor:
    """
    Hint/fitnet loss: MSE between teacher and student hidden states.
    
    Args:
        student_hidden: Student model hidden states
        teacher_hidden: Teacher model hidden states (possibly projected)
        
    Returns:
        MSE loss between hidden states
    """
    return F.mse_loss(student_hidden, teacher_hidden)

def cot_loss(student_logits: torch.Tensor, 
            cot_labels: torch.Tensor,
            cot_mask: torch.Tensor,
            ignore_index: int = -100) -> torch.Tensor:
    """
    Chain-of-thought loss: predict hidden rationale segment.
    
    Args:
        student_logits: Student model logits for CoT segment
        cot_labels: Ground truth labels for CoT segment
        cot_mask: Mask indicating CoT segment positions
        ignore_index: Index to ignore in loss calculation
        
    Returns:
        CoT prediction loss
    """
    # Apply mask to focus on CoT segment
    masked_logits = student_logits[cot_mask]
    masked_labels = cot_labels[cot_mask]
    
    if masked_logits.numel() == 0:
        return torch.tensor(0.0)
    
    return F.cross_entropy(
        masked_logits.view(-1, masked_logits.size(-1)),
        masked_labels.view(-1),
        ignore_index=ignore_index
    )

def entropy_weighting(entropy: float, 
                     a: float = 0.5, 
                     b: float = 0.8, 
                     w_min: float = 0.3, 
                     w_max: float = 1.5) -> float:
    """
    Calculate per-example weight based on teacher entropy.
    
    w = clip(a + b * H_teacher, w_min, w_max)
    
    Args:
        entropy: Teacher model entropy
        a: Offset parameter
        b: Scaling parameter
        w_min: Minimum weight
        w_max: Maximum weight
        
    Returns:
        Example weight
    """
    weight = a + b * entropy
    return max(w_min, min(w_max, weight))

def mix_losses(logits_s: torch.Tensor, 
              logits_t: torch.Tensor, 
              labels: torch.Tensor, 
              weights: Dict[str, float], 
              temperature: float = 2.0,
              extras: Optional[Dict[str, Any]] = None) -> torch.Tensor:
    """
    Mix multiple loss components with configurable weights.
    
    Args:
        logits_s: Student model logits
        logits_t: Teacher model logits
        labels: Ground truth labels
        weights: Dictionary of loss weights
        temperature: Temperature for KD loss
        extras: Additional data for specialized losses
        
    Returns:
        Combined loss
    """
    total_loss = torch.tensor(0.0)
    
    # KL divergence knowledge distillation
    if weights.get("kd", 0) > 0:
        kd_loss = kd_kl_loss(logits_s, logits_t, temperature)
        total_loss = total_loss + weights["kd"] * kd_loss
    
    # Cross-entropy on teacher outputs
    if weights.get("ce", 0) > 0:
        ce_loss_val = ce_loss(logits_s, labels)
        total_loss = total_loss + weights["ce"] * ce_loss_val
    
    # Sequence-level KD
    if weights.get("seq", 0) > 0 and extras and "txt_s" in extras and "txt_t" in extras:
        seq_loss = sequence_level_ce(extras["txt_s"], extras["txt_t"])
        total_loss = total_loss + weights["seq"] * seq_loss
    
    # Hint/fitnet loss
    if weights.get("hint", 0) > 0 and extras and "h_s" in extras and "h_t" in extras:
        hint_loss_val = hint_loss(extras["h_s"], extras["h_t"])
        total_loss = total_loss + weights["hint"] * hint_loss_val
    
    # Chain-of-thought loss
    if weights.get("cot", 0) > 0 and extras and "cot_labels" in extras and "cot_mask" in extras:
        cot_loss_val = cot_loss(logits_s, extras["cot_labels"], extras["cot_mask"])
        total_loss = total_loss + weights["cot"] * cot_loss_val
    
    return total_loss

# Example usage
if __name__ == "__main__":
    # Example tensors for testing
    batch_size, seq_len, vocab_size = 2, 10, 1000
    student_logits = torch.randn(batch_size, seq_len, vocab_size)
    teacher_logits = torch.randn(batch_size, seq_len, vocab_size)
    labels = torch.randint(0, vocab_size, (batch_size, seq_len))
    
    # Test KD loss
    kd_loss = kd_kl_loss(student_logits, teacher_logits, temperature=2.0)
    print(f"KD Loss: {kd_loss.item():.4f}")
    
    # Test CE loss
    ce_loss_val = ce_loss(student_logits, labels)
    print(f"CE Loss: {ce_loss_val.item():.4f}")
    
    # Test sequence-level loss
    student_texts = ["This is a test", "Another example"]
    teacher_texts = ["This is a test", "Different example"]
    seq_loss = sequence_level_ce(student_texts, teacher_texts)
    print(f"Sequence Loss: {seq_loss.item():.4f}")