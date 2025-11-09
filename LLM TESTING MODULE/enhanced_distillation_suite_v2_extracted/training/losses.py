import torch
import torch.nn.functional as F

def kd_kl_loss(student_logits, teacher_logits, T: float = 2.0):
    s = F.log_softmax(student_logits / T, dim=-1)
    t = F.softmax(teacher_logits / T, dim=-1)
    return F.kl_div(s, t, reduction="batchmean") * (T * T)

def ce_loss(student_logits, labels, ignore_index=-100):
    return F.cross_entropy(
        student_logits.view(-1, student_logits.size(-1)),
        labels.view(-1),
        ignore_index=ignore_index
    )

def seq_level_proxy_loss(student_ids, teacher_ids):
    # Simple token-F1 proxy (1 - F1)
    import numpy as np
    s = student_ids.detach().cpu().numpy()
    t = teacher_ids.detach().cpu().numpy()
    f1s = []
    for si, ti in zip(s, t):
        sset = set(int(x) for x in si if x >= 0)
        tset = set(int(x) for x in ti if x >= 0)
        inter = len(sset & tset)
        prec = inter / max(len(sset), 1)
        rec = inter / max(len(tset), 1)
        f1 = 0.0 if (prec+rec)==0 else 2*prec*rec/(prec+rec)
        f1s.append(f1)
    return 1.0 - float(sum(f1s)/max(len(f1s),1))

def hint_loss(h_student, h_teacher):
    return F.mse_loss(h_student, h_teacher)

def mix_losses(logits_s, logits_t, labels, weights, T, extras=None):
    L = 0.0
    if weights.get("kd", 0) > 0 and logits_t is not None:
        L = L + weights["kd"] * kd_kl_loss(logits_s, logits_t, T)
    if weights.get("ce", 0) > 0:
        L = L + weights["ce"] * ce_loss(logits_s, labels)
    if weights.get("seq", 0) > 0 and extras and "student_ids" in extras and "teacher_ids" in extras:
        L = L + weights["seq"] * seq_level_proxy_loss(extras["student_ids"], extras["teacher_ids"])
    if weights.get("hint", 0) > 0 and extras and "h_s" in extras and "h_t" in extras:
        L = L + weights["hint"] * hint_loss(extras["h_s"], extras["h_t"])
    return L