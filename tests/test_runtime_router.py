import unittest
import sys
import os

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.router.route_types import RouteOption, RoutingDecision
from app.router.utility_engine import compute_utilities
from app.router.runtime_router import RuntimeRouter
from app.router.feature_extractor import FeatureVector

class TestRuntimeRouter(unittest.TestCase):
    def setUp(self):
        # We load the existing production models trained in Phase 2
        self.models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/models"))
        self.router = RuntimeRouter(self.models_dir)

    def test_artifact_loading(self):
        """
        Verifies that RuntimeRouter initializes correctly and loads trained models.
        """
        self.assertIsNotNone(self.router.feature_extractor)
        self.assertIsNotNone(self.router.probability_estimator)
        self.assertIsNotNone(self.router.probability_estimator.logistic_model)
        self.assertIsNotNone(self.router.probability_estimator.isotonic_model)

    def test_probability_estimation(self):
        """
        Checks that probability estimator outputs a float in the range [0.0, 1.0].
        """
        # Formulate dummy feature vector
        features = FeatureVector(length=30, symbol_ratio=0.1, regex_density=1, bm25_score=0.5)
        prob = self.router.probability_estimator.estimate_success_probability(features)
        
        self.assertIsInstance(prob, float)
        self.assertTrue(0.0 <= prob <= 1.0)

    def test_utility_edge_cases_prob_zero(self):
        """
        Tests utility calculations when calibrated probability = 0.0.
        """
        c2 = 10.0
        c3 = 100.0
        lambda_coeff = 0.6
        alpha_dense = 0.8
        
        # When prob = 0.0:
        # u_cheap = 0.6 * 0.0 - (1 - 0.6) * (10 / 100) = -0.4 * 0.1 = -0.04
        # u_dense = 0.6 * 0.8 - (1 - 0.6) * 1.0 = 0.48 - 0.4 = 0.08
        # u_cascade = 0.6 * (0 + (1-0)*0.8) - 0.4 * (10/100 + (1-0)) 
        #           = 0.6 * 0.8 - 0.4 * (0.1 + 1.0) = 0.48 - 0.4 * 1.1 = 0.48 - 0.44 = 0.04
        utils = compute_utilities(
            calibrated_prob=0.0,
            c2=c2,
            c3=c3,
            lambda_coeff=lambda_coeff,
            alpha_dense=alpha_dense
        )
        
        self.assertAlmostEqual(utils["cheap"], -0.04)
        self.assertAlmostEqual(utils["dense"], 0.08)
        self.assertAlmostEqual(utils["cascade"], 0.04)

    def test_utility_edge_cases_prob_one(self):
        """
        Tests utility calculations when calibrated probability = 1.0.
        """
        c2 = 15.0
        c3 = 75.0
        lambda_coeff = 0.7
        alpha_dense = 0.85
        
        # When prob = 1.0:
        # u_cheap = 0.7 * 1.0 - (1 - 0.7) * (15 / 75) = 0.7 - 0.3 * 0.2 = 0.7 - 0.06 = 0.64
        # u_dense = 0.7 * 0.85 - (1 - 0.7) * 1.0 = 0.595 - 0.3 = 0.295
        # u_cascade = 0.7 * (1.0 + (1-1)*0.85) - 0.3 * (15/75 + (1-1))
        #           = 0.7 * 1.0 - 0.3 * 0.2 = 0.7 - 0.06 = 0.64
        utils = compute_utilities(
            calibrated_prob=1.0,
            c2=c2,
            c3=c3,
            lambda_coeff=lambda_coeff,
            alpha_dense=alpha_dense
        )
        
        self.assertAlmostEqual(utils["cheap"], 0.64)
        self.assertAlmostEqual(utils["dense"], 0.295)
        self.assertAlmostEqual(utils["cascade"], 0.64)

    def test_deterministic_routing_argmax_and_tie_breaking(self):
        """
        Verifies that equal utilities resolve deterministically based on cost order:
        cheap > cascade > dense.
        """
        # Let's define parameters that result in equal utilities for cheap and cascade.
        # As shown in the prob_one test above:
        # When prob = 1.0, c2 = 15, c3 = 75, lambda = 0.7, alpha = 0.85:
        # u_cheap = 0.64, u_dense = 0.295, u_cascade = 0.64.
        # This is a tie between CHEAP and CASCADE.
        # Under our tie-breaking priorities, cheap should be selected.
        
        # Mock the probability estimator response to return 1.0 for testing routing decision
        class MockEstimator:
            def estimate_success_probability(self, features):
                return 1.0

        original_estimator = self.router.probability_estimator
        self.router.probability_estimator = MockEstimator()
        
        try:
            decision = self.router.route(
                prompt="test prompt",
                c2=15.0,
                c3=75.0,
                lambda_coeff=0.7,
                alpha_dense=0.85
            )
            
            self.assertEqual(decision.selected_route, RouteOption.CHEAP)
            self.assertAlmostEqual(decision.cheap_utility, 0.64)
            self.assertAlmostEqual(decision.cascade_utility, 0.64)
            
        finally:
            self.router.probability_estimator = original_estimator

    def test_routing_reproducibility(self):
        """
        Tests that routing decisions are fully deterministic and repeatable.
        """
        prompt = "Write a python function to solve the equation: calculate y = 2x"
        c2 = 10.0
        c3 = 100.0
        lambda_coeff = 0.5
        alpha_dense = 0.9
        
        decision1 = self.router.route(prompt, c2, c3, lambda_coeff, alpha_dense)
        decision2 = self.router.route(prompt, c2, c3, lambda_coeff, alpha_dense)
        
        self.assertEqual(decision1.selected_route, decision2.selected_route)
        self.assertEqual(decision1.calibrated_probability, decision2.calibrated_probability)
        self.assertEqual(decision1.cheap_utility, decision2.cheap_utility)
        self.assertEqual(decision1.dense_utility, decision2.dense_utility)
        self.assertEqual(decision1.cascade_utility, decision2.cascade_utility)
        self.assertEqual(decision1.feature_vector, decision2.feature_vector)

if __name__ == "__main__":
    unittest.main()
