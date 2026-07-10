import os
from typing import List

from app.router.feature_extractor import FeatureExtractor
from app.router.bm25_index import BM25Index
from app.router.probability_estimator import ProbabilityEstimator
from app.router.utility_engine import compute_utilities
from app.router.route_types import RouteOption, RoutingDecision

class RuntimeRouter:
    """
    Purpose:
        The core orchestrator of the TERA decision pipeline. Loads serialized models,
        processes prompts, estimates calibrated accuracy probabilities, calculatesexpected
        utilities, and selects the optimal path.
        
    Time Complexity:
        O(L + Q * log(N)) dominated by feature extraction over input prompt.
        
    Memory Complexity:
        O(V + N * L_u) for the local BM25 index structure.
    """

    def __init__(self, models_dir: str) -> None:
        """
        Purpose:
            Instantiates the router components by loading artifacts from models_dir.
            
        Inputs:
            models_dir: Path to directory containing models (pkl, txt files).
            
        Outputs:
            None
            
        Time Complexity:
            O(1) to deserialize small regression files.
            
        Memory Complexity:
            O(1) to hold models and features data.
        """
        logistic_path = os.path.join(models_dir, "logistic_model.pkl")
        isotonic_path = os.path.join(models_dir, "isotonic_model.pkl")
        corpus_path = os.path.join(models_dir, "bm25_corpus.txt")
        
        # Load BM25 reference corpus
        corpus: List[str] = []
        if os.path.exists(corpus_path):
            with open(corpus_path, "r", encoding="utf-8") as f:
                corpus = [line.strip() for line in f if line.strip()]
                
        # Initialize sub-modules
        self.feature_extractor = FeatureExtractor(bm25_index=BM25Index(corpus))
        self.probability_estimator = ProbabilityEstimator(logistic_path, isotonic_path)

    def route(
        self,
        prompt: str,
        c2: float,
        c3: float,
        lambda_coeff: float,
        alpha_dense: float
    ) -> RoutingDecision:
        """
        Purpose:
            Takes a prompt and determines the utility-maximizing route option.
            
        Inputs:
            prompt: Raw prompt text.
            c2: Cheap model execution token cost.
            c3: Dense model execution token cost.
            lambda_coeff: Trade-off coefficient between accuracy and frugality.
            alpha_dense: Dense model baseline task domain accuracy.
            
        Outputs:
            A frozen RoutingDecision carrying the optimal selection, probabilities,
            expected utilities, and extracted FeatureVector.
            
        Time Complexity:
            O(L + Q * log(N)) dominated by feature extraction (under 0.1 ms on CPU).
            
        Memory Complexity:
            O(1) auxiliary memory.
        """
        # 1. Lexical feature extraction
        features = self.feature_extractor.extract(prompt)
        
        # 2. Estimate calibrated accuracy probability
        cal_prob = self.probability_estimator.estimate_success_probability(features)
        
        # 3. Compute expected utilities for each path
        utilities = compute_utilities(
            calibrated_prob=cal_prob,
            c2=c2,
            c3=c3,
            lambda_coeff=lambda_coeff,
            alpha_dense=alpha_dense
        )
        
        # 4. Argmax selection with deterministic tie-breaking (cheap > cascade > dense)
        # Order priorities from cheapest/preferred to most expensive
        route_priority = [RouteOption.CHEAP, RouteOption.CASCADE, RouteOption.DENSE]
        
        selected_route = route_priority[0]
        max_utility = utilities[selected_route.value]
        
        for option in route_priority[1:]:
            utility_val = utilities[option.value]
            if utility_val > max_utility:
                max_utility = utility_val
                selected_route = option
                
        return RoutingDecision(
            selected_route=selected_route,
            calibrated_probability=cal_prob,
            cheap_utility=utilities["cheap"],
            dense_utility=utilities["dense"],
            cascade_utility=utilities["cascade"],
            feature_vector=features
        )
