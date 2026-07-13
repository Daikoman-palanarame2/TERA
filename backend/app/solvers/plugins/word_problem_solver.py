"""
Module: backend/app/solvers/plugins/word_problem_solver
Purpose:
    Implements a safe and narrow mathematical word problem solver using Decimal and Fraction.
"""

import re
from decimal import Decimal
from fractions import Fraction
from typing import Optional
from app.solvers.base_solver import BaseSolver
from app.core.exceptions import VerificationError

class WordProblemSolver(BaseSolver):
    """Solver for evaluating high-confidence mathematical word problems (inventory flow & recipe scaling)."""

    @property
    def name(self) -> str:
        return "word_problem_solver"

    @property
    def pattern(self) -> str:
        # Trigger on keywords related to inventory and recipe scaling
        return r"(?i)\b(inventory|recipe|servings|cookies|sugar|warehouse|stock|restock)\b"

    def solve(self, prompt: str) -> str:
        """Parse and solve the word problem using Decimal/Fraction.

        Raises:
            VerificationError: If parsing fails or the problem has any ambiguity.
        """
        # Determine problem type
        is_recipe = any(k in prompt.lower() for k in ["recipe", "sugar", "cookies", "cup"])
        is_inventory = any(k in prompt.lower() for k in ["inventory", "warehouse", "stock", "restock", "remain"])

        if is_recipe and is_inventory:
            raise VerificationError("Ambiguous prompt matches both recipe and inventory types.", task_id=None)

        if is_recipe:
            return self._solve_recipe(prompt)
        elif is_inventory:
            return self._solve_inventory(prompt)
        else:
            raise VerificationError("Prompt does not match word problem templates.", task_id=None)

    def _parse_fraction(self, val_str: str) -> Fraction:
        val_str = val_str.strip()
        if "/" in val_str:
            parts = val_str.split()
            if len(parts) == 1:
                return Fraction(parts[0])
            elif len(parts) == 2:
                return Fraction(parts[0]) + Fraction(parts[1])
            else:
                raise ValueError("Invalid mixed fraction format")
        return Fraction(val_str)

    def _solve_recipe(self, prompt: str) -> str:
        # Original requirement match
        # "requires X cups of sugar to make Y cookies", "calls for X cups of sugar for Y servings"
        orig_match = re.search(
            r"\b(?:requires|calls\s+for|uses)\s+(?P<sugar>[0-9\/\s\.]+)\s+(?:cup|cups)\s+(?:of\s+sugar\s+)?(?:to\s+make|for)\s+(?P<servings>[\d,]+)\s+(?P<unit>cookies|servings|serves)\b",
            prompt,
            re.IGNORECASE
        )
        if not orig_match:
            raise VerificationError("Recipe original sugar requirement not found or ambiguous.")

        # Target match
        # "want to make Z cookies", "scale it to Z servings", "scale to Z servings"
        target_match = re.search(
            r"\b(?:want\s+to\s+make|scale\s+(?:it\s+)?to|make|for)\s+(?P<target>[\d,]+)\s+(?P<unit>cookies|servings|serves)\b",
            prompt,
            re.IGNORECASE
        )
        if not target_match:
            raise VerificationError("Recipe target servings not found.")

        # Check if target match matches the same servings as the original match
        # Since target_match regex is broad, it might find the original servings first if we aren't careful.
        # We find all matches of target servings, and make sure we identify the target one.
        targets = re.findall(
            r"\b(?:want\s+to\s+make|scale\s+(?:it\s+)?to|make|for)\s+([\d,]+)\s+(?:cookies|servings|serves)\b",
            prompt,
            re.IGNORECASE
        )
        # Filter out the original servings count
        orig_servings_str = orig_match.group("servings").replace(",", "")
        target_candidates = [t.replace(",", "") for t in targets if t.replace(",", "") != orig_servings_str]
        if not target_candidates:
            raise VerificationError("Recipe target servings not found or matches original servings.")
        target_servings_str = target_candidates[0]

        # Cost match
        # "costs $C per cup", "price is $C per cup", "cost of $C per cup"
        cost_match = re.search(
            r"\b(?:cost|costs|price)(?:\s+(?:is|at))?\s+\$(?P<cost>[\d\.,]+)\s+per\s+(?:cup|unit)\b",
            prompt,
            re.IGNORECASE
        )
        if not cost_match:
            raise VerificationError("Recipe cost per cup not found.")

        # Verify units consistency
        orig_unit = orig_match.group("unit").lower()
        # Find unit of target servings
        target_unit_match = re.search(
            rf"\b{target_servings_str}\s+(?P<unit>cookies|servings|serves)\b",
            prompt,
            re.IGNORECASE
        )
        if not target_unit_match:
            raise VerificationError("Could not verify target unit.")
        target_unit = target_unit_match.group("unit").lower()
        # cookies vs servings vs serves must match (singular/plural difference is fine)
        def normalize_unit(u: str) -> str:
            if u.startswith("cookie"):
                return "cookie"
            if u.startswith("serv"):
                return "serve"
            return u

        if normalize_unit(orig_unit) != normalize_unit(target_unit):
            raise VerificationError(f"Recipe units mismatch: {orig_unit} vs {target_unit}")

        # Strict unexplained numbers check
        all_numbers = re.findall(r"\d+(?:,\d+)*(?:\.\d+)?", prompt)
        # Parse ingredients
        try:
            sugar_cups = self._parse_fraction(orig_match.group("sugar"))
            orig_servings = Fraction(orig_servings_str)
            target_servings = Fraction(target_servings_str)
            cost_per_cup = Fraction(cost_match.group("cost").replace(",", ""))
        except Exception as e:
            raise VerificationError(f"Failed to parse recipe quantities: {e}")

        if sugar_cups <= 0 or orig_servings <= 0 or target_servings <= 0 or cost_per_cup <= 0:
            raise VerificationError("Recipe quantities must be positive.")

        # Calculate
        required_sugar = sugar_cups * target_servings / orig_servings
        total_cost = required_sugar * cost_per_cup

        # Verify all numbers in the prompt are explained
        # Check if the fraction was mixed or single fraction or decimal
        sugar_str_raw = orig_match.group("sugar").strip()
        expected_nums = []
        if "/" in sugar_str_raw:
            if len(sugar_str_raw.split()) == 2:
                parts = sugar_str_raw.split()
                expected_nums.extend([str(parts[0])])
                f_part = Fraction(parts[1])
                expected_nums.extend([str(f_part.numerator), str(f_part.denominator)])
            else:
                f_part = Fraction(sugar_str_raw)
                expected_nums.extend([str(f_part.numerator), str(f_part.denominator)])
        else:
            expected_nums.append(sugar_str_raw)
            
        expected_nums.extend([orig_servings_str, target_servings_str])
        # cost might be formatted with decimals, match the string
        expected_nums.append(cost_match.group("cost").replace(",", ""))

        from collections import Counter
        # Normalize all to decimal strings for comparison
        def norm(n: str) -> str:
            n_clean = n.replace(",", "")
            if "/" in n_clean:
                return str(float(Fraction(n_clean)))
            return str(float(n_clean))

        try:
            expected_counts = Counter(norm(x) for x in expected_nums)
            actual_counts = Counter(norm(x) for x in all_numbers)
            # Allow minor differences if they don't contain extra unexplained numbers
            if not all(actual_counts[k] <= expected_counts[k] for k in actual_counts):
                raise VerificationError("Recipe contains unexplained extra numbers.")
        except Exception as e:
            if isinstance(e, VerificationError):
                raise e
            raise VerificationError(f"Provenance checks failed: {e}")

        # Construct final output format
        # If sugar is a clean fraction, represent it nicely
        sugar_decimal = Decimal(str(float(required_sugar)))
        cost_decimal = Decimal(str(float(total_cost)))
        
        # Format response
        cost_str = f"${cost_decimal:.2f}"
        if sugar_decimal % 1 == 0:
            sugar_str = str(int(sugar_decimal))
        else:
            sugar_str = f"{sugar_decimal:.6f}".rstrip('0').rstrip('.')
            
        return f"The recipe requires {sugar_str} cups of sugar and will cost {cost_str}."

    def _solve_inventory(self, prompt: str) -> str:
        # Match starting stock
        start_match = re.search(
            r"\b(?:starts with|starting (?:stock|inventory) (?:is|of)|initial (?:stock|inventory) (?:is|of)|inventory is|start with)\s+(?P<start>[\d,]+)(?:\s+units)?\b",
            prompt,
            re.IGNORECASE
        )
        if not start_match:
            raise VerificationError("Inventory starting stock not found.")

        # Match reduction percentage
        pct_match = re.search(
            r"\b(?:reduced|reduction|decreased|sells|sell|sold) (?:by\s+)?(?P<pct>\d+(?:\.\d+)?)\%\s*(?P<suffix>(?:of|due\s+to|from|than)\s+[\w\s\-]+)?",
            prompt,
            re.IGNORECASE
        )
        if not pct_match:
            raise VerificationError("Inventory reduction percentage base is ambiguous or missing.")
            
        suffix = (pct_match.group("suffix") or "").strip().lower()
        if suffix:
            # Suffix is present. If it doesn't refer to stock or promotion, it's ambiguous!
            if not any(k in suffix for k in ["stock", "promotion", "initial", "starting"]):
                raise VerificationError("Inventory reduction percentage base is ambiguous or missing.")

        # Match restock
        restock_match = re.search(
            r"\b(?:restock(?:s)?(?: by receiving)?|receives|receive|restocked with|adds|restock)\s+(?P<restock>[\d,]+)(?!\s*(?:\.\d+)?\%)(?:\s+units)?\b",
            prompt,
            re.IGNORECASE
        )
        if not restock_match:
            raise VerificationError("Inventory restock count not found.")

        # Match final sale/shipment
        ship_match = re.search(
            r"\b(?:ship(?:s|ped)?(?: out)?|sell(?:s)?|sold|shipped|ship)\s+(?P<shipped>[\d,]+)(?!\s*(?:\.\d+)?\%)(?:\s+units)?\b",
            prompt,
            re.IGNORECASE
        )
        if not ship_match:
            raise VerificationError("Inventory final shipment count not found.")

        # Unexplained numbers check
        prompt_without_quarter_labels = re.sub(
            r"\bQ[1-4]\b", "", prompt, flags=re.IGNORECASE
        )
        all_numbers = re.findall(
            r"\d+(?:,\d+)*(?:\.\d+)?", prompt_without_quarter_labels
        )
        try:
            start = Decimal(start_match.group("start").replace(",", ""))
            pct = Decimal(pct_match.group("pct"))
            restock = Decimal(restock_match.group("restock").replace(",", ""))
            shipped = Decimal(ship_match.group("shipped").replace(",", ""))
        except Exception as e:
            raise VerificationError(f"Failed to parse inventory counts: {e}")

        if start < 0 or pct < 0 or restock < 0 or shipped < 0 or pct > 100:
            raise VerificationError("Inventory quantities must be non-negative, pct <= 100.")

        expected_nums = [
            start_match.group("start").replace(",", ""),
            pct_match.group("pct"),
            restock_match.group("restock").replace(",", ""),
            ship_match.group("shipped").replace(",", "")
        ]

        from collections import Counter
        def norm(n: str) -> str:
            return str(float(n.replace(",", "")))

        expected_counts = Counter(norm(x) for x in expected_nums)
        actual_counts = Counter(norm(x) for x in all_numbers)
        if not all(actual_counts[k] <= expected_counts[k] for k in actual_counts):
            raise VerificationError("Inventory contains unexplained extra numbers.")

        # Calculate remaining units
        reduced_amount = start * (pct / Decimal("100"))
        remaining = start - reduced_amount + restock - shipped

        if remaining % 1 == 0:
            return str(int(remaining))
        return f"{remaining:.2f}".rstrip('0').rstrip('.')
