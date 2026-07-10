import re
from dataclasses import dataclass
from typing import Dict
from app.router.regex_patterns import DEFAULT_PATTERNS
from app.router.bm25_index import BM25Index

@dataclass(frozen=True)
class FeatureVector:
    """
    Purpose:
        An immutable data container representing the 4-dimensional lexical feature vector 
        reproduced from the TERA research paper.
    
    Fields:
        length: Character count of the prompt.
        symbol_ratio: Ratio of non-alphanumeric and non-space characters to total character count.
        regex_density: Cumulative match count across all configured regex keyword categories.
        bm25_score: Maximum lexical similarity score against a reference corpus.
    """
    length: int
    symbol_ratio: float
    regex_density: int
    bm25_score: float


class FeatureExtractor:
    """
    Purpose:
        A CPU-only routing feature extraction module that transforms unstructured text prompts
        into structured, lightweight lexical representations in microsecond scales.
    
    Time Complexity:
        O(L + K + Q * log(N)) where L is prompt length, K is number of regex patterns,
        Q is query token count, and N is references corpus size.
    
    Memory Complexity:
        O(V + N * L_u) for local BM25 index storage (under 5 MB).
    """

    def __init__(self, patterns: Dict[str, re.Pattern] = None, bm25_index: BM25Index = None) -> None:
        """
        Purpose:
            Initializes the feature extractor with regex patterns and a BM25 similarity index.
        
        Inputs:
            patterns: Dict mapping domain category flags to compiled re.Pattern objects.
            bm25_index: Pre-constructed BM25Index instance.
        
        Outputs:
            None
        """
        self.patterns = patterns if patterns is not None else DEFAULT_PATTERNS
        self.bm25_index = bm25_index if bm25_index is not None else BM25Index()

    def extract(self, prompt: str) -> FeatureVector:
        """
        Purpose:
            Extracts the four lexical features from the prompt string and returns a FeatureVector.
        
        Inputs:
            prompt: The raw prompt string to process.
        
        Outputs:
            A frozen FeatureVector instance carrying the computed features.
            
        Time/Memory Complexity:
            Same as class definitions, executing in microseconds for typical prompt inputs.
        """
        # Feature 1: Prompt Length
        length = len(prompt)
        
        # Feature 2: Symbol Density
        if length == 0:
            symbol_ratio = 0.0
        else:
            # Count only non-alphanumeric and non-space characters to focus on structure
            non_alnum = sum(1 for c in prompt if not c.isalnum() and not c.isspace())
            symbol_ratio = float(non_alnum / length)
            
        # Feature 3: Regex Keyword Density
        regex_density = 0
        if length > 0:
            for pattern in self.patterns.values():
                regex_density += len(pattern.findall(prompt))
                
        # Feature 4: BM25 Similarity Score
        bm25_score = self.bm25_index.get_max_similarity(prompt)
        
        return FeatureVector(
            length=length,
            symbol_ratio=symbol_ratio,
            regex_density=regex_density,
            bm25_score=bm25_score
        )
