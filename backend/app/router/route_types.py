from dataclasses import dataclass
from enum import Enum
from app.router.feature_extractor import FeatureVector

"""
This module defines the public route options and decision structure
returned by the TERA routing agent.
"""

class RouteOption(str, Enum):
    CHEAP = "cheap"
    DENSE = "dense"
    CASCADE = "cascade"


@dataclass(frozen=True)
class RoutingDecision:
    """
    Purpose:
        An immutable data container holding the routing route choice, success probability,
        path utilities, and the extracted prompt feature vector.
    
    Fields:
        selected_route: The chosen RouteOption enum.
        calibrated_probability: Calibrated probability that the cheap model will succeed.
        cheap_utility: Expected utility score of the direct cheap model path.
        dense_utility: Expected utility score of the direct dense model path.
        cascade_utility: Expected utility score of the cascading models path.
        feature_vector: The FeatureVector instance computed for the query prompt.
    """
    selected_route: RouteOption
    calibrated_probability: float
    cheap_utility: float
    dense_utility: float
    cascade_utility: float
    feature_vector: FeatureVector
