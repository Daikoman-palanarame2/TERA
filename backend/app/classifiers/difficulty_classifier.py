import re
from typing import Dict, Any, Optional

class TERAOriginalDifficultyClassifier:
    """
    TERA-original risk-based difficulty classifier.
    Analyzes prompts for fragile or complex characteristics and maps them to:
    - safe_fast: For low-risk, simple tasks.
    - medium_consensus: For reasoning or consensus-friendly tasks.
    - direct_power: For fragile or high-risk tasks requiring strong capabilities.
    """

    def __init__(self) -> None:
        # Define common regexes or keywords
        self.factual_patterns = [
            r"\bcapital\s+of\b", r"\bwho\s+(?:wrote|authored|discovered|invented|created)\b",
            r"\bwhat\s+is\s+the\s+(?:speed|distance|mass|formula|scientific\s+name)\b",
            r"\bbirth\s+date\b", r"\bbiography\s+of\b", r"\bwhere\s+was\b", r"\bwhen\s+was\b",
            r"\bwho\s+is\b", r"\bdefine\b", r"\bexplain\s+the\s+theory\b", r"\bscientific\s+fact\b",
            r"\bhistorical\b"
        ]
        
        self.ner_patterns = [
            r"\bextract\s+all\s+(?:named\s+entities|entities|people|organizations|locations|places|dates)\b",
            r"\bnamed\s+entity\s+recognition\b", r"\bner\b", r"\blist\s+all\s+(?:names|places|organizations|entities)\b"
        ]
        
        self.sentiment_patterns = [
            r"\bmixed\s+sentiment\b", r"\bambiguous\s+sentiment\b", r"\btone\s+analysis\b",
            r"\bnuanced\s+sentiment\b", r"\bneutral\s+or\s+mixed\b"
        ]

    def _is_safe_translation(self, prompt: str) -> bool:
        """
        Translation is safe_fast only if:
        - short (<= 150 chars)
        - literal (no formatting, tone, style, or idiom complexity)
        - mentions exactly source and target languages clearly
        """
        prompt_lower = prompt.lower()
        if "translate" not in prompt_lower:
            return False
            
        # Check length
        if len(prompt) > 150:
            return False
            
        # Check complexity keywords
        complexity_keywords = [
            "idiom", "tone", "localize", "format", "style", "polite", "formal", 
            "informal", "slang", "bullet", "sentence", "meaning", "cultural"
        ]
        if any(kw in prompt_lower for kw in complexity_keywords):
            return False
            
        # Check languages (must find exactly source and target language hints)
        languages = ["english", "french", "spanish", "german", "italian", "chinese", "japanese", "russian", "portuguese"]
        detected_langs = [lang for lang in languages if lang in prompt_lower]
        
        # Must have exactly 1 or 2 detected languages to be clear
        if not (1 <= len(detected_langs) <= 2):
            return False
            
        return True

    def classify(self, prompt: str) -> str:
        """
        Classifies the prompt into safe_fast, medium_consensus, or direct_power.
        """
        prompt_lower = prompt.lower()

        # 1. Fragile characteristic: Factual knowledge (accuracy-first policy)
        for pattern in self.factual_patterns:
            if re.search(pattern, prompt_lower):
                return "direct_power"

        # 2. Fragile characteristic: NER with completeness requirements
        for pattern in self.ner_patterns:
            if re.search(pattern, prompt_lower):
                return "direct_power"

        # 3. Fragile characteristic: Ambiguous or mixed sentiment
        for pattern in self.sentiment_patterns:
            if re.search(pattern, prompt_lower):
                return "direct_power"

        # 4. Fragile characteristic: Multiple semantic requirements + strict formatting
        # Count formatting constraint terms
        constraint_count = 0
        if "sentence" in prompt_lower:
            constraint_count += 1
        if "bullet" in prompt_lower:
            constraint_count += 1
        if "word" in prompt_lower:
            constraint_count += 1
        if "must include" in prompt_lower or "must contain" in prompt_lower:
            constraint_count += 1
            
        if constraint_count >= 2:
            return "direct_power"

        # 5. Fragile characteristic: Complex JSON or nested schema
        if "json" in prompt_lower or "schema" in prompt_lower or "nested" in prompt_lower:
            return "direct_power"

        # 6. Fragile characteristic: Many dependent constraints
        if "must satisfy" in prompt_lower or "following rules" in prompt_lower or "dependent" in prompt_lower:
            return "direct_power"

        # 7. Fragile characteristic: Unsupported multi-step word problems
        # Check if math keywords are present but we don't have a simple task
        has_math = any(kw in prompt_lower for kw in ["solve", "calculate", "equation", "math", "derivative", "integral"])
        if has_math:
            # If it's a longer math prompt or mentions "word problem" or "step by step"
            if len(prompt_lower) > 100 or "step" in prompt_lower or "word problem" in prompt_lower:
                return "direct_power"

        # 8. Check for safe_fast criteria (low-risk tasks)
        is_classification = any(kw in prompt_lower for kw in ["classify", "categorize", "label", "spam", "sentiment", "true or false", "yes or no"])
        is_short_transform = self._is_safe_translation(prompt) or any(kw in prompt_lower for kw in ["uppercase", "lowercase", "reverse", "correct spelling", "format date"])
        is_simple_extract = any(kw in prompt_lower for kw in ["extract email", "extract phone number", "extract date"])
        
        # If it is simple classification/transformation/extraction and not long
        if (is_classification or is_short_transform or is_simple_extract) and len(prompt) < 250:
            return "safe_fast"

        # 9. Medium consensus candidates (multiple generations can establish agreement)
        # e.g., standard short summaries, intermediate reasoning tasks, multiple-choice QA
        is_reasoning = any(kw in prompt_lower for kw in ["reason", "think", "choice", "correct option", "select the best", "summarize"])
        if is_reasoning:
            return "medium_consensus"

        # 10. Default to direct_power for unknown/ambiguous
        return "direct_power"
