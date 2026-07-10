import unittest
import sys
import os

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.router.route_types import RouteOption, RoutingDecision
from app.router.feature_extractor import FeatureVector
from app.verification.verification_types import SchemaType, VerificationStatus, FailureReason
from app.verification.rovl import ROVL
from app.inference.inference_types import InferenceRequest, InferenceResponse, ModelOutput
from app.inference.model_interface import ModelInterface
from app.inference.cheap_model import CheapModel
from app.inference.dense_model import DenseModel
from app.inference.orchestrator import InferenceOrchestrator

class DummyRouter:
    """
    A lightweight, deterministic router mock to test the orchestrator 
    independent of regression model weights.
    """
    def __init__(self, selected_route: RouteOption, probability: float = 0.8) -> None:
        self.selected_route = selected_route
        self.probability = probability

    def route(
        self, 
        prompt: str, 
        c2: float, 
        c3: float, 
        lambda_coeff: float, 
        alpha_dense: float
    ) -> RoutingDecision:
        return RoutingDecision(
            selected_route=self.selected_route,
            calibrated_probability=self.probability,
            cheap_utility=0.6,
            dense_utility=0.4,
            cascade_utility=0.7,
            feature_vector=FeatureVector(
                length=len(prompt), 
                symbol_ratio=0.0, 
                regex_density=0, 
                bm25_score=0.0
            )
        )


class TestInferenceOrchestrator(unittest.TestCase):
    def setUp(self):
        # Default mock models
        self.cheap_model = CheapModel(
            default_text="Cheap completion\n",
            default_probs=[0.99, 0.99],
            behavior_override={
                "trigger_fail": {
                    "text": "Malformed json text",
                    "token_probs": [0.99]
                },
                "high_entropy": {
                    "text": "Entropy test completion\n",
                    "token_probs": [0.1] * 50
                }
            }
        )
        self.dense_model = DenseModel(default_text="Dense clean completion\n")
        self.rovl = ROVL(entropy_threshold=3.0)

    def test_direct_dense_routing(self):
        """
        Tests the direct dense model path when the router selects RouteOption.DENSE.
        """
        router = DummyRouter(RouteOption.DENSE)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        request = InferenceRequest(
            prompt="Hello dense model",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.8
        )
        
        response = orchestrator.run(request)
        
        self.assertEqual(response.selected_route, RouteOption.DENSE)
        self.assertEqual(response.final_response, "Dense clean completion\n")
        self.assertFalse(response.escalated)
        self.assertIsNone(response.verification_result)
        
        # Verify metadata values
        self.assertEqual(response.metadata["router_probability"], 0.8)
        self.assertEqual(response.metadata["cheap_utility"], 0.6)
        self.assertEqual(response.metadata["dense_utility"], 0.4)
        self.assertEqual(response.metadata["cascade_utility"], 0.7)
        self.assertEqual(response.metadata["verification_time_ms"], 0.0)
        self.assertGreaterEqual(response.metadata["inference_time_ms"], 0.0)
        self.assertIsNone(response.metadata["escalation_reason"])

    def test_direct_cheap_routing_success(self):
        """
        Tests direct cheap path when the router selects RouteOption.CHEAP and validation passes.
        """
        router = DummyRouter(RouteOption.CHEAP)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        request = InferenceRequest(
            prompt="Success case prompt",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.8
        )
        
        response = orchestrator.run(request)
        
        self.assertEqual(response.selected_route, RouteOption.CHEAP)
        self.assertEqual(response.final_response, "Cheap completion\n")
        self.assertFalse(response.escalated)
        self.assertIsNotNone(response.verification_result)
        self.assertEqual(response.verification_result.status, VerificationStatus.PASS)

    def test_direct_cheap_routing_escalation(self):
        """
        Tests that cheap path escalates to the dense model when verification fails.
        """
        router = DummyRouter(RouteOption.CHEAP)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        # prompt contains 'trigger_fail' to trigger malformed json failure in CheapModel override
        request = InferenceRequest(
            prompt="JSON trigger_fail prompt",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.8,
            schema_type=SchemaType.JSON
        )
        
        response = orchestrator.run(request)
        
        self.assertEqual(response.selected_route, RouteOption.CHEAP)
        self.assertEqual(response.final_response, "Dense clean completion\n")
        self.assertTrue(response.escalated)
        self.assertEqual(response.verification_result.status, VerificationStatus.FAIL)
        # It fails schema validation because it is malformed
        self.assertIn(FailureReason.SCHEMA, response.verification_result.failure_reasons)
        self.assertEqual(response.metadata["escalation_reason"], "schema")

    def test_cascade_routing_success(self):
        """
        Tests the cascading route path when cheap validation passes.
        """
        router = DummyRouter(RouteOption.CASCADE)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        request = InferenceRequest(
            prompt="Normal cascading prompt",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.8
        )
        
        response = orchestrator.run(request)
        
        self.assertEqual(response.selected_route, RouteOption.CASCADE)
        self.assertEqual(response.final_response, "Cheap completion\n")
        self.assertFalse(response.escalated)

    def test_cascade_routing_escalation(self):
        """
        Tests the cascading route path when cheap validation fails, escalating to dense.
        """
        router = DummyRouter(RouteOption.CASCADE)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        # trigger high_entropy override in CheapModel
        request = InferenceRequest(
            prompt="high_entropy prompt",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.8
        )
        
        response = orchestrator.run(request)
        
        self.assertEqual(response.selected_route, RouteOption.CASCADE)
        self.assertEqual(response.final_response, "Dense clean completion\n")
        self.assertTrue(response.escalated)
        self.assertEqual(response.verification_result.status, VerificationStatus.FAIL)
        self.assertEqual(response.verification_result.failure_reasons, [FailureReason.ENTROPY])
        self.assertEqual(response.metadata["escalation_reason"], "entropy")

    def test_dependency_injection_custom_mock(self):
        """
        Tests that custom mock models implementing ModelInterface inject correctly.
        """
        class CustomMockModel(ModelInterface):
            def generate(self, prompt: str) -> ModelOutput:
                return ModelOutput(text="Custom output\n", metadata={"source": "custom_mock"})

        router = DummyRouter(RouteOption.CHEAP)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=CustomMockModel(),
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        request = InferenceRequest(prompt="Hello", c2=10.0, c3=100.0, lambda_coeff=0.5, alpha_dense=0.8)
        response = orchestrator.run(request)
        
        self.assertEqual(response.final_response, "Custom output\n")
        self.assertEqual(response.metadata["model_metadata"]["source"], "custom_mock")

    def test_cheap_model_throwing_exception(self):
        """
        Verifies that cheap model exceptions propagate out of the orchestrator.
        """
        class ExceptionModel(ModelInterface):
            def generate(self, prompt: str) -> ModelOutput:
                raise RuntimeError("Cheap model OOM")

        router = DummyRouter(RouteOption.CHEAP)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=ExceptionModel(),
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        request = InferenceRequest(prompt="Hello", c2=10.0, c3=100.0, lambda_coeff=0.5, alpha_dense=0.8)
        
        with self.assertRaises(RuntimeError) as context:
            orchestrator.run(request)
            
        self.assertIn("Cheap model OOM", str(context.exception))

    def test_dense_model_throwing_exception(self):
        """
        Verifies that dense model exceptions propagate out of the orchestrator.
        """
        class ExceptionModel(ModelInterface):
            def generate(self, prompt: str) -> ModelOutput:
                raise RuntimeError("Dense model offline")

        router = DummyRouter(RouteOption.DENSE)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=ExceptionModel(),
            rovl=self.rovl
        )
        
        request = InferenceRequest(prompt="Hello", c2=10.0, c3=100.0, lambda_coeff=0.5, alpha_dense=0.8)
        
        with self.assertRaises(RuntimeError) as context:
            orchestrator.run(request)
            
        self.assertIn("Dense model offline", str(context.exception))

    def test_edge_prompts_empty_and_long(self):
        """
        Tests empty prompts and extremely long prompts.
        """
        router = DummyRouter(RouteOption.CHEAP)
        orchestrator = InferenceOrchestrator(
            router=router,
            cheap_model=self.cheap_model,
            dense_model=self.dense_model,
            rovl=self.rovl
        )
        
        # Empty prompt
        req_empty = InferenceRequest(prompt="", c2=10.0, c3=100.0, lambda_coeff=0.5, alpha_dense=0.8)
        res_empty = orchestrator.run(req_empty)
        self.assertEqual(res_empty.routing_decision.feature_vector.length, 0)
        self.assertEqual(res_empty.final_response, "Cheap completion\n")
        
        # Extremely long prompt
        req_long = InferenceRequest(prompt="a" * 10000, c2=10.0, c3=100.0, lambda_coeff=0.5, alpha_dense=0.8)
        res_long = orchestrator.run(req_long)
        self.assertEqual(res_long.routing_decision.feature_vector.length, 10000)
        self.assertEqual(res_long.final_response, "Cheap completion\n")

if __name__ == "__main__":
    unittest.main()
