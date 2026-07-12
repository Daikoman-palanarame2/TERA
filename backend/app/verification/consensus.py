import json
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from decimal import Decimal
from fractions import Fraction
from app.schemas.data_contracts import RawModelOutput, VerificationConstraints
from app.verification.rovl import ROVL
from app.verification.output_enforcer import OutputEnforcer

def normalize_numeric(text: str) -> Optional[Decimal]:
    """
    Normalizes commas, currency, percentages, units, and parses Decimal or Fraction.
    """
    clean = text.strip().replace(",", "")
    # Strip common currency symbols
    for sym in ["$", "€", "£", "¥"]:
        clean = clean.replace(sym, "")
    # Strip percentages
    if clean.endswith("%"):
        clean = clean[:-1].strip()
        try:
            return Decimal(clean) / Decimal("100")
        except Exception:
            pass
    # Try parsing Fraction
    if "/" in clean:
        try:
            frac = Fraction(clean)
            return Decimal(frac.numerator) / Decimal(frac.denominator)
        except Exception:
            pass
    # Try parsing Decimal directly
    # Regex to extract the first decimal number
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean)
    if match:
        try:
            return Decimal(match.group(0))
        except Exception:
            pass
    return None

def normalize_classification(text: str, allowed_labels: Optional[List[str]] = None) -> Optional[str]:
    """
    Normalizes allowed labels, lowercase, and matches against text.
    """
    clean = text.strip().lower()
    if allowed_labels:
        allowed_normalized = {lbl.strip().lower(): lbl for lbl in allowed_labels}
        # Direct check
        if clean in allowed_normalized:
            return allowed_normalized[clean]
        # Partial check: check if label is in text
        for lbl_norm, lbl_orig in allowed_normalized.items():
            if lbl_norm in clean:
                return lbl_orig
    return clean

def normalize_ner(text: str) -> Optional[frozenset]:
    """
    Parses entity-label pairs from text and normalizes casing/whitespace.
    Common formats:
    - Entity: Label
    - Entity (Label)
    """
    pairs = []
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Format: Entity: Label
        if ":" in line:
            parts = line.split(":", 1)
            ent = parts[0].strip().lower()
            lbl = parts[1].strip().lower()
            pairs.append((ent, lbl))
        # Format: Entity (Label)
        elif "(" in line and line.endswith(")"):
            idx = line.rfind("(")
            ent = line[:idx].strip().lower()
            lbl = line[idx+1:-1].strip().lower()
            pairs.append((ent, lbl))
        else:
            pairs.append((line.lower(), ""))
    if not pairs:
        return None
    return frozenset(pairs)

def canonicalize_json_dict(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: canonicalize_json_dict(v) for k, v in sorted(d.items())}
    elif isinstance(d, list):
        return [canonicalize_json_dict(x) for x in d]
    return d

def normalize_json(text: str) -> Optional[str]:
    """
    Parses JSON and canonicalizes key ordering and whitespace.
    """
    # Strip markdown fences if present
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines[0].startswith("```json") or lines[0] == "```":
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    try:
        data = json.loads(clean)
        canonical = canonicalize_json_dict(data)
        return json.dumps(canonical, sort_keys=True)
    except Exception:
        return None

def compute_average_logprob(sample: RawModelOutput) -> float:
    if not sample.tokens:
        return -999.0
    logprobs = [t.logprob for t in sample.tokens if t.logprob is not None]
    if not logprobs:
        return -999.0
    return sum(logprobs) / len(logprobs)

def resolve_consensus(
    samples: List[RawModelOutput],
    task_type: str,
    constraints: VerificationConstraints,
    rovl: ROVL,
    enforcer: OutputEnforcer,
    allowed_labels: Optional[List[str]] = None
) -> Tuple[Optional[RawModelOutput], float, str]:
    """
    Resolves consensus among samples.
    Returns: Tuple of (winning_sample, agreement_score, agreement_type)
    agreement_type can be: numeric, classification, ner, json, exact_format, none.
    """
    # Step 1: Filter out malformed/invalid candidates
    valid_samples: List[RawModelOutput] = []
    for sample in samples:
        try:
            ver_res = rovl.verify(sample, constraints)
            format_constraints = enforcer.constraints_from_prompt(sample.text)
            format_result = enforcer.enforce(
                sample.text,
                strip_json_fence=(
                    constraints.json_schema is not None
                    and sample.text.lstrip().startswith("```")
                ),
                **format_constraints,
            )
            # If both pass, it's a valid candidate
            if ver_res.passed and format_result.success:
                # Update text to the enforced normalized text if modified
                if format_result.output != sample.text:
                    sample = sample.model_copy(update={"text": format_result.output})
                valid_samples.append(sample)
        except Exception:
            pass

    if not valid_samples:
        return None, 0.0, "none"

    # Step 2: If task is general prose, consensus is disabled/escalated
    if task_type == "prose" or task_type not in ["numeric", "classification", "ner", "json", "exact_format"]:
        return None, 0.0, "none"

    # Step 3: Normalize and group candidates
    groups: Dict[Any, List[RawModelOutput]] = {}
    for sample in valid_samples:
        norm_val = None
        if task_type == "numeric":
            norm_val = normalize_numeric(sample.text)
        elif task_type == "classification":
            norm_val = normalize_classification(sample.text, allowed_labels)
        elif task_type == "ner":
            norm_val = normalize_ner(sample.text)
        elif task_type == "json":
            norm_val = normalize_json(sample.text)
        elif task_type == "exact_format":
            norm_val = sample.text.strip() # Exact string match for format-focused prose

        if norm_val is not None:
            groups.setdefault(norm_val, []).append(sample)

    if not groups:
        return None, 0.0, "none"

    # Find the group with the highest count (strongest cross-sample support)
    sorted_groups = sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)
    best_norm, group_samples = sorted_groups[0]
    
    agreement_score = len(group_samples) / len(samples)

    # Require majority agreement (e.g. at least 2 agreeing samples for n=3)
    if len(group_samples) < 2:
        return None, agreement_score, task_type

    # If there's a tie in support, sort by average logprob
    best_sample = sorted(group_samples, key=compute_average_logprob, reverse=True)[0]
    return best_sample, agreement_score, task_type
