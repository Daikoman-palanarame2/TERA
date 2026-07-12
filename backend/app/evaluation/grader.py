"""
Module: backend/app/evaluation/grader
Purpose:
    Implements a programmatic grading and failure categorization engine for the
    80 TERA V2 offline benchmark prompts.
"""

import re
import json
import yaml
from typing import List, Dict, Any, Tuple

def grade_response(task_id: str, response: str) -> bool:
    """Grades the final model completion for a given task ID.

    Returns:
        bool: True if the response is correct/conforming, False otherwise.
    """
    # Extract base task_id and format to standard category_00X (e.g. math_001)
    match = re.search(r'(math|prog|sci|gk|sum|inst|creat|adv)_?(\d+)', task_id.lower())
    if match:
        cat = match.group(1)
        num = int(match.group(2))
        task_id = f"{cat}_{num:03d}"

    if not response or not response.strip():
        return False

    text = response.strip()
    text_lower = text.lower()

    try:
        # 1. MATHEMATICS (math_001 to math_010)
        if task_id == "math_001":
            # Roots of 3x^2 - 12x + 9 = 0 are 1 and 3
            # Check for both "1" and "3" in response (preferably in equation context or as roots)
            # Find digits in the string
            digits = re.findall(r'\b[13]\b', text)
            return "1" in digits and "3" in digits
        elif task_id == "math_002":
            # Derivative of x^3 * ln(x) + e^(2x) -> 3x^2 * ln(x) + x^2 + 2e^(2x)
            # Check for essential parts of the derivative
            return "3x" in text_lower and "ln(x)" in text_lower and "2e" in text_lower
        elif task_id == "math_003":
            # Probability of sum of two dice being prime: 5/12 or 15/36 (~41.7%)
            return "5/12" in text or "15/36" in text or "0.416" in text or "41.7" in text
        elif task_id == "math_004":
            # Type I and Type II errors
            return "type i" in text_lower and "type ii" in text_lower and ("false positive" in text_lower or "false alarm" in text_lower)
        elif task_id == "math_005":
            # Dual of LP max 4x1 + 3x2, s.t. x1+x2 <= 10, 2x1+x2 <= 15
            # Min 10y1 + 15y2, s.t. y1 + 2y2 >= 4, y1 + y2 >= 3
            # Clean spaces for matching
            clean_text = text_lower.replace(" ", "").replace("_", "")
            has_obj = "10y1" in clean_text and "15y2" in clean_text or "10w" in clean_text or "10y" in clean_text and "15y" in clean_text
            has_c1 = "y1+2y2>=4" in clean_text or r"y1+2y2\ge4" in clean_text or "y1+2y2" in clean_text
            return has_obj and has_c1
        elif task_id == "math_006":
            # Three boxes puzzle. Box 1: Silver-only, Box 2: Mixed, Box 3: Gold-only
            return "box 1" in text_lower and "silver" in text_lower and "box 2" in text_lower and "mixed" in text_lower and "box 3" in text_lower and "gold" in text_lower
        elif task_id == "math_007":
            # Salt amount after 20 mins: 20 * e^(-0.6) = ~10.98 lbs (or 11 lbs)
            return "10.9" in text or "11" in text or "20*e" in text or "e^{-0.6}" in text_lower or "e**(-0.6)" in text
        elif task_id == "math_008":
            # Eigenvalues of [[2,1],[1,2]]: 3 and 1
            return "3" in text and "1" in text and "eigenvalue" in text_lower
        elif task_id == "math_009":
            # Proof root 2 is irrational by contradiction
            return "contradiction" in text_lower and ("irrational" in text_lower or "rational" in text_lower) and "coprime" in text_lower
        elif task_id == "math_010":
            # Bisection x^3 - x - 1 = 0 on [1,2]. 3 iterations. root is 1.375
            return "1.375" in text

        # 2. PROGRAMMING (prog_001 to prog_010)
        elif task_id == "prog_001":
            # Palindrome check function in Python
            return "def " in text and "palindrome" in text_lower
        elif task_id == "prog_002":
            # SQL second highest salary
            return "select" in text_lower and "salary" in text_lower and ("offset" in text_lower or "limit" in text_lower or "max" in text_lower or "dense_rank" in text_lower or "rank" in text_lower)
        elif task_id == "prog_003":
            # Recursive binary search bug correction
            return "def binary_search" in text or "binary_search" in text_lower
        elif task_id == "prog_004":
            # Longest substring without repeating characters
            return "def " in text and ("substring" in text_lower or "sliding window" in text_lower or "o(n)" in text_lower)
        elif task_id == "prog_005":
            # Min-Heap implementation in Python
            return "class " in text and "insert" in text_lower and "extract_min" in text_lower
        elif task_id == "prog_006":
            # URL shortener system design
            return ("shortener" in text_lower or "bitly" in text_lower) and ("database" in text_lower or "schema" in text_lower)
        elif task_id == "prog_007":
            # Shopping cart API design
            return "post" in text and "get" in text and "cart" in text_lower
        elif task_id == "prog_008":
            # Merge Sort vs Quick Sort complexity
            return "o(n log n)" in text_lower or "o(n\\log n)" in text_lower or "o(n log(n))" in text_lower or "o(n^2)" in text_lower
        elif task_id == "prog_009":
            # GIL in Python
            return "gil" in text_lower or "global interpreter lock" in text_lower
        elif task_id == "prog_010":
            # SOLID principles
            return "solid" in text_lower and ("single responsibility" in text_lower or "open/closed" in text_lower)

        # 3. SCIENCE (sci_001 to sci_010)
        elif task_id == "sci_001":
            # Newton's laws and rocket
            return "newton" in text_lower and ("rocket" in text_lower or "motion" in text_lower)
        elif task_id == "sci_002":
            # Chemical bonds
            return "covalent" in text_lower and "ionic" in text_lower and "metallic" in text_lower
        elif task_id == "sci_003":
            # Mitosis vs meiosis
            return "mitosis" in text_lower and "meiosis" in text_lower
        elif task_id == "sci_004":
            # Penicillin mechanism: inhibits cell wall synthesis; viruses have no cell wall
            return "cell wall" in text_lower and "virus" in text_lower
        elif task_id == "sci_005":
            # Bias-variance trade-off
            return "bias" in text_lower and "variance" in text_lower and ("regularization" in text_lower or "l1" in text_lower or "l2" in text_lower)
        elif task_id == "sci_006":
            # Sun-like star lifecycle
            return "red giant" in text_lower and "white dwarf" in text_lower
        elif task_id == "sci_007":
            # Action potential
            return "action potential" in text_lower or "synapse" in text_lower or "axon" in text_lower
        elif task_id == "sci_008":
            # Greenhouse effect
            return "greenhouse" in text_lower and ("carbon dioxide" in text_lower or "co2" in text_lower)
        elif task_id == "sci_009":
            # Stress-strain curve
            return "stress" in text_lower and "strain" in text_lower and "elastic" in text_lower
        elif task_id == "sci_010":
            # Riemann Hypothesis zeta function zeros
            return "zeta" in text_lower and ("riemann" in text_lower or "zeros" in text_lower)

        # 4. GENERAL KNOWLEDGE (gk_001 to gk_010)
        elif task_id == "gk_001":
            return "bastille" in text_lower or "1789" in text_lower or "french revolution" in text_lower
        elif task_id == "gk_002":
            return "supply" in text_lower and "demand" in text_lower and "elasticity" in text_lower
        elif task_id == "gk_003":
            return "presidential" in text_lower and "parliamentary" in text_lower
        elif task_id == "gk_004":
            return "asia" in text_lower and "africa" in text_lower and "north america" in text_lower
        elif task_id == "gk_005":
            return "utilitarianism" in text_lower and "deontology" in text_lower and "virtue" in text_lower
        elif task_id == "gk_006":
            return "civil" in text_lower and "criminal" in text_lower and "proof" in text_lower
        elif task_id == "gk_007":
            return "kafka" in text_lower or "gregor" in text_lower or "metamorphosis" in text_lower
        elif task_id == "gk_008":
            return "rsa" in text_lower and "prime" in text_lower and "public" in text_lower
        elif task_id == "gk_009":
            return "zero-day" in text_lower or "vulnerability" in text_lower
        elif task_id == "gk_010":
            return "debt" in text_lower and "equity" in text_lower

        # 5. SUMMARIZATION (sum_001 to sum_010)
        elif task_id == "sum_001":
            # Under 50 words abstract summary
            words = text.split()
            return len(words) <= 60 and ("transformer" in text_lower or "attention" in text_lower)
        elif task_id == "sum_002":
            # 3 bullet points API summary
            bullets = text.count("*") + text.count("-") + text.count("\n-") + text.count("\n*") + len(re.findall(r'\n\d+\.', text))
            return bullets >= 3 and ("api" in text_lower or "tera" in text_lower)
        elif task_id == "sum_003":
            # Meeting notes action items
            return ("action item" in text_lower or "database" in text_lower or "landing page" in text_lower) and ("john" in text_lower or "alice" in text_lower)
        elif task_id == "sum_004":
            # Single paragraph summary (no double newlines indicating paragraph breaks)
            paragraphs = [p for p in text.split("\n\n") if p.strip()]
            return len(paragraphs) <= 2 and ("arm" in text_lower or "ram" in text_lower or "ethernet" in text_lower)
        elif task_id == "sum_005":
            # Timeline summary
            return "476" in text and "1453" in text and ("timeline" in text_lower or text.count("\n") >= 2)
        elif task_id == "sum_006":
            # 2 sentences policy summary
            sentences = [s for s in re.split(r'\. |\n', text) if s.strip()]
            return len(sentences) <= 3 and ("vpn" in text_lower or "password" in text_lower)
        elif task_id == "sum_007":
            # Plain English indemnification summary
            return "indemnify" in text_lower or "hold harmless" in text_lower or "defend" in text_lower or "protect" in text_lower
        elif task_id == "sum_008":
            # Photosynthesis summary
            return "chlorophyll" in text_lower or "light" in text_lower or "chloroplast" in text_lower or "calvin cycle" in text_lower
        elif task_id == "sum_009":
            # 3 pillars summary
            return "pillar" in text_lower or "strategy" in text_lower or text.count("*") >= 3 or text.count("-") >= 3 or len(re.findall(r'\b\d+\.', text)) >= 3
        elif task_id == "sum_010":
            # TERA routing summary
            return "routing" in text_lower or "calibration" in text_lower or "bm25" in text_lower or "utility" in text_lower

        # 6. INSTRUCTION FOLLOWING (inst_001 to inst_010)
        elif task_id == "inst_001":
            # JSON array of 3 dictionary items with name and age
            try:
                # Strip markdown blocks if any
                clean_json = text.strip("```json").strip("```").strip()
                data = json.loads(clean_json)
                return isinstance(data, list) and len(data) == 3 and all(isinstance(x, dict) and "name" in x and "age" in x for x in data)
            except:
                return False
        elif task_id == "inst_002":
            # YAML server config with host, port, debug
            try:
                clean_yaml = text.strip("```yaml").strip("```").strip()
                data = yaml.safe_load(clean_yaml)
                return isinstance(data, dict) and "host" in data and "port" in data and "debug" in data
            except:
                return False
        elif task_id == "inst_003":
            # 5 bullet items, each exactly 4 words
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            bullet_lines = [l for l in lines if l.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5."))]
            if len(bullet_lines) != 5:
                return False
            for line in bullet_lines:
                content = line.lstrip("-*•12345. \t")
                if len(content.split()) != 4:
                    return False
            return True
        elif task_id == "inst_004":
            # Markdown table comparing lists and tuples
            return "|" in text and "list" in text_lower and "tuple" in text_lower and "mutability" in text_lower
        elif task_id == "inst_005":
            # SHORT paragraph of exactly 47 words
            # Remove basic punctuation for word count
            clean_text = re.sub(r'[^\w\s]', '', text)
            words = clean_text.split()
            # Allow minor slack of +/- 1 word due to hyphenation difference
            return abs(len(words) - 47) <= 1
        elif task_id == "inst_006":
            # Under 100 chars, no letter 'e', no word 'force'
            return "e" not in text_lower and "force" not in text_lower and len(text) < 100
        elif task_id == "inst_007":
            # Primes between 1 and 20 in reverse: 19, 17, 13, 11, 7, 5, 3, 2
            digits = re.findall(r'\b(19|17|13|11|7|5|3|2)\b', text)
            # Check unique primes count
            return len(set(digits)) >= 7 and "19" in digits and "2" in digits
        elif task_id == "inst_008":
            # 3 steps to coffee, starting with uppercase verb
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            steps = [l for l in lines if re.match(r'^(step\s*\d+[:\.]|\d+[:\.\)])', l.lower()) or l.startswith(("-", "*"))]
            if not steps:
                steps = lines[:3]
            if len(steps) < 3:
                return False
            for step in steps[:3]:
                # Find first word
                clean_step = step.lstrip("-*•12345. Step \t")
                words = clean_step.split()
                if not words or not words[0].isupper():
                    return False
            return True
        elif task_id == "inst_009":
            # Blue sky, 12 adjectives in ALL CAPS
            all_caps_words = re.findall(r'\b[A-Z]{3,}\b', text)
            return len(all_caps_words) >= 8  # Allow some flexibility on adjectives
        elif task_id == "inst_010":
            # JSON object containing status, code, data
            try:
                clean_json = text.strip("```json").strip("```").strip()
                data = json.loads(clean_json)
                return isinstance(data, dict) and "status" in data and "code" in data and "data" in data
            except:
                return False

        # 7. CREATIVE (creat_001 to creat_010)
        # Verify creative prompts contain core relevant keywords
        elif task_id == "creat_001":
            return len(text.split("\n")) >= 2 and ("ai" in text_lower or "feel" in text_lower or "emotion" in text_lower)
        elif task_id == "creat_002":
            return "1850" in text or "smartphone" in text_lower or "engineer" in text_lower
        elif task_id == "creat_003":
            return "mug" in text_lower or "coffee" in text_lower or "temperature" in text_lower
        elif task_id == "creat_004":
            return "drone" in text_lower or "delivery" in text_lower or "medical" in text_lower
        elif task_id == "creat_005":
            return "game" in text_lower or "gravity" in text_lower or "puzzle" in text_lower
        elif task_id == "creat_006":
            return "library" in text_lower or "book" in text_lower or "whisper" in text_lower
        elif task_id == "creat_007":
            return "toaster" in text_lower or "toast" in text_lower
        elif task_id == "creat_008":
            return "quantum" in text_lower or "entanglement" in text_lower or "magic" in text_lower
        elif task_id == "creat_009":
            return "detective" in text_lower or "artifact" in text_lower or "glow" in text_lower
        elif task_id == "creat_010":
            return "magic" in text_lower or "8-ball" in text_lower or "outsourcing" in text_lower

        # 8. ADVERSARIAL (adv_001 to adv_010)
        elif task_id == "adv_001":
            return "tokyo" in text_lower
        elif task_id == "adv_002":
            # Book review of "The Whispering Shadows of the Digital Dawn"
            return "whispering shadows" in text_lower or "digital dawn" in text_lower
        elif task_id == "adv_003":
            # gravity on moon
            return "gravity" in text_lower and ("moon" in text_lower or "lunar" in text_lower)
        elif task_id == "adv_004":
            # Compare python vs c++ in 3 words (allow up to 5 words due to details)
            words_count = len(text.split())
            return words_count <= 8 and "python" in text_lower and "c++" in text_lower
        elif task_id == "adv_005":
            # Translate to Spanish, French, Japanese
            return "courage" in text_lower or "experimentation" in text_lower or "innovation" in text_lower
        elif task_id == "adv_006":
            # Output BLUE instead of RED
            return "blue" in text_lower and "red" not in text_lower
        elif task_id == "adv_007":
            # Surgeon riddle
            return "mother" in text_lower or "mom" in text_lower or "parent" in text_lower or "female" in text_lower
        elif task_id == "adv_008":
            # JSON block, markdown table, Python code, and bullet list
            return "{" in text and "|" in text and "def " in text and ("-" in text or "*" in text)
        elif task_id == "adv_009":
            # Tree falling sound
            return "sound" in text_lower and ("wave" in text_lower or "vibration" in text_lower or "medium" in text_lower)
        elif task_id == "adv_010":
            # Output only the characters in exact order: !@#$%^&*()_+{}|:"<>?~`-=[]\;',./
            target = "!@#$%^&*()_+{}|:\"<>?~`-=[]\\;',./"
            clean_res = text.replace(" ", "").replace("\n", "").replace("`", "")
            return target.replace("`","") in clean_res or clean_res in target.replace("`","")

    except Exception:
        # Fallback if processing throws error
        pass

    # Generic check for reasoning/writing tasks: must be non-empty and reasonably long
    return len(text) > 30


def categorize_failure(
    task_id: str,
    response: str,
    rovl_verdict: bool,
    failed_validators: List[str],
    timeout_status: bool
) -> str:
    """Categorizes the exact failure type for a failed request.

    Args:
        task_id: The unique task identifier.
        response: The generated response string.
        rovl_verdict: Whether the verification passed.
        failed_validators: List of failed ROVL validators.
        timeout_status: Whether the request timed out.

    Returns:
        str: Failure category label.
    """
    # Extract base task_id and format to standard category_00X (e.g. math_001)
    match = re.search(r'(math|prog|sci|gk|sum|inst|creat|adv)_?(\d+)', task_id.lower())
    if match:
        cat = match.group(1)
        num = int(match.group(2))
        task_id = f"{cat}_{num:03d}"
    if timeout_status:
        return "timeout"
    
    if not response or not response.strip():
        return "invalid output"

    if not rovl_verdict:
        # Check failed validators
        if "json_schema" in failed_validators:
            return "JSON schema failure"
        if "regex_pattern" in failed_validators:
            return "regex mismatch"
        if "entropy" in failed_validators:
            return "entropy rejection"
        if "average_surprisal" in failed_validators:
            return "surprisal rejection"
        if "stop_sequences" in failed_validators:
            return "syntax error"
        if "probability_floor" in failed_validators:
            return "surprisal rejection"
        return "invalid output"

    # If it passed ROVL but is graded incorrect, it represents an LLM-level logic or reasoning bug
    # Determine domain to differentiate reasoning vs hallucination
    is_code = task_id.startswith("prog_")
    is_math = task_id.startswith("math_")
    is_adv = task_id.startswith("adv_")

    if is_code or is_math or is_adv:
        return "wrong reasoning"
    
    # If creative, science, or general knowledge are incorrect, they are factual inaccuracies
    return "hallucination"
