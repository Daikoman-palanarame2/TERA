import pickle
import numpy as np
from app.router.feature_extractor import FeatureVector

class ProbabilityEstimator:
    """
    Purpose:
        Responsible for calculating the calibrated success probability of the cheap model lane 
        by querying the trained Logistic Regression and Isotonic Regression models.
        
    Time/Memory Complexity:
        - O(1) time and memory overhead during estimation since we run inference over a single 4D vector.
    """

    def __init__(self, logistic_model_path: str, isotonic_model_path: str) -> None:
        """
        Purpose:
            Loads the serialized Logistic Regression and Isotonic Regression models.
            
        Inputs:
            logistic_model_path: Absolute or relative filepath to the serialized logistic model (.pkl).
            isotonic_model_path: Absolute or relative filepath to the serialized isotonic model (.pkl).
            
        Outputs:
            None
            
        Time Complexity:
            O(1) to open and deserialize small pkl model files.
            
        Memory Complexity:
            O(1) to hold the model parameters in memory (under 5 KB total).
        """
        with open(logistic_model_path, "rb") as f:
            self.logistic_model = pickle.load(f)
            
        with open(isotonic_model_path, "rb") as f:
            self.isotonic_model = pickle.load(f)

    def estimate_success_probability(self, features: FeatureVector) -> float:
        """
        Purpose:
            Takes a FeatureVector, runs predict_proba over it, and calibrates the raw score.
            
        Inputs:
            features: FeatureVector instance computed for the query prompt.
            
        Outputs:
            A float representing the calibrated success probability of the cheap model.
            
        Time Complexity:
            O(1) since it is a single vector lookup.
            
        Memory Complexity:
            O(1) auxiliary memory.
        """
        # Formulate a 2D features array for sklearn model input
        features_arr = np.array([[
            features.length, 
            features.symbol_ratio, 
            features.regex_density, 
            features.bm25_score
        ]])
        
        # Call predict_proba() to get raw Logistic Regression probability
        raw_prob = self.logistic_model.predict_proba(features_arr)[0, 1]
        
        # Pass raw probability into the loaded IsotonicRegression calibrator
        calibrated_prob = self.isotonic_model.predict(np.array([raw_prob]))[0]
        
        return float(calibrated_prob)
