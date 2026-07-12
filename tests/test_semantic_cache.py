"""
Unit tests for the TERA SemanticCache module.
"""

import unittest
import sys
import os
import tempfile
import threading
from unittest.mock import patch

import numpy as np

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.cache.semantic_cache import SemanticCache
from app.core.exceptions import CacheError, ConfigurationError


class _Encoding:
    def __init__(self, text: str):
        self.ids = [max(1, ord(char) % 31) for char in text] or [1]
        self.attention_mask = [1] * len(self.ids)
        self.type_ids = [0] * len(self.ids)


class _Tokenizer:
    @classmethod
    def from_file(cls, _path: str):
        return cls()

    def encode(self, text: str):
        return _Encoding(text)


class _Input:
    def __init__(self, name: str):
        self.name = name


class _Session:
    def __init__(self, _path, _options):
        pass

    def get_inputs(self):
        return [_Input("input_ids"), _Input("attention_mask")]

    def run(self, _outputs, inputs):
        ids = inputs["input_ids"]
        embeddings = np.zeros((1, ids.shape[1], 8), dtype=np.float32)
        for index, token_id in enumerate(ids[0]):
            embeddings[0, index, token_id % 8] = 1.0
        return [embeddings]

class TestSemanticCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = self.temp_dir.name
        model_dir = os.path.join(self.temp_dir.name, "model")
        os.makedirs(model_dir)
        self.embedding_model_path = os.path.join(model_dir, "model.onnx")
        open(self.embedding_model_path, "wb").close()
        open(os.path.join(model_dir, "tokenizer.json"), "w").close()
        self.patches = (
            patch("app.cache.semantic_cache.Tokenizer", _Tokenizer),
            patch("app.cache.semantic_cache.ort.InferenceSession", _Session),
        )
        for active_patch in self.patches:
            active_patch.start()
        self.cache = SemanticCache(self.cache_dir, self.embedding_model_path)

    def tearDown(self):
        self.cache.env.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def test_configuration_errors(self):
        """Tests that incorrect/missing config paths raise ConfigurationError."""
        with self.assertRaises(ConfigurationError):
            SemanticCache("", self.embedding_model_path)
        with self.assertRaises(ConfigurationError):
            SemanticCache(self.cache_dir, "")
        with self.assertRaises(ConfigurationError):
            SemanticCache(self.cache_dir + "_nonexistent", "/nonexistent/model.onnx")

    def test_exact_lookup_and_insert(self):
        """Tests that exact prompt lookup returns cached response."""
        prompt = "What is the capital of France?"
        response = "Paris is the capital of France."
        
        # Miss
        self.assertIsNone(self.cache.lookup(prompt))
        
        # Insert
        self.cache.insert(prompt, response)
        
        # Hit
        self.assertEqual(self.cache.lookup(prompt), response)

    def test_exact_miss(self):
        """Tests that exact match miss returns None."""
        self.assertIsNone(self.cache.lookup("Non-existent prompt"))

    def test_semantic_hit(self):
        """Tests that semantic similarity lookup returns cached response above threshold."""
        vectors = {
            "Hello world": np.array([1.0, 0.0], dtype=np.float32),
            "Hello worlds": np.array([0.99, 0.1], dtype=np.float32),
        }
        with patch.object(self.cache, "_get_embedding", side_effect=lambda text: vectors[text]):
            self.cache.insert("Hello world", "Hi there")
            res = self.cache.lookup("Hello worlds", threshold=0.90)
        self.assertEqual(res, "Hi there")

    def test_threshold_failure(self):
        """Tests that semantic lookup returns None if similarity is below threshold."""
        vectors = {
            "Hello world": np.array([1.0, 0.0], dtype=np.float32),
            "Goodbye world": np.array([0.0, 1.0], dtype=np.float32),
        }
        with patch.object(self.cache, "_get_embedding", side_effect=lambda text: vectors[text]):
            self.cache.insert("Hello world", "Hi there")
            res = self.cache.lookup("Goodbye world", threshold=0.95)
        self.assertIsNone(res)

    def test_threshold_validation(self):
        for threshold in (-0.01, 1.01, float("nan"), float("inf"), True, "0.9"):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    self.cache.lookup("Prompt", threshold=threshold)

    def test_invalid_model_embedding_is_rejected(self):
        with patch.object(
            self.cache.session,
            "run",
            return_value=[np.zeros((1, 6, 8), dtype=np.float32)],
        ):
            with self.assertRaises(CacheError):
                self.cache._get_embedding("Prompt")

    def test_concurrent_duplicate_insert_never_overwrites(self):
        barrier = threading.Barrier(8)

        def insert(response: str):
            barrier.wait()
            self.cache.insert("same prompt", response)

        threads = [threading.Thread(target=insert, args=(f"response-{i}",)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        stored = self.cache.lookup("same prompt")
        self.assertIn(stored, {f"response-{i}" for i in range(8)})
        with self.cache.env.begin(write=False) as txn:
            self.assertEqual(txn.stat()["entries"], 1)

    def test_duplicate_prevention(self):
        """Tests that duplicate insert doesn't overwrite/add new record and logs warning."""
        prompt = "Hello"
        self.cache.insert(prompt, "First")
        
        # Attempt to insert duplicate
        self.cache.insert(prompt, "Second")
        
        # Should retain "First"
        self.assertEqual(self.cache.lookup(prompt), "First")

    def test_validation_rejection(self):
        """Tests that empty prompts or responses are rejected from insertion."""
        # Empty prompt
        self.cache.insert("", "Response")
        self.assertIsNone(self.cache.lookup(""))
        
        # Empty response
        self.cache.insert("Prompt", "")
        self.assertIsNone(self.cache.lookup("Prompt"))

    def test_corrupted_lmdb(self):
        """Tests that CacheError is raised if LMDB gets closed or corrupted."""
        self.cache.env.close()
        with self.assertRaises(CacheError):
            self.cache.lookup("Prompt")
        with self.assertRaises(CacheError):
            self.cache.insert("Prompt", "Response")

    def test_concurrent_access(self):
        """Tests that concurrent insertions and lookups operate thread-safely."""
        errors = []
        
        def run_thread(tid: int):
            try:
                for i in range(10):
                    prompt = f"Prompt_{tid}_{i}"
                    response = f"Response_{tid}_{i}"
                    self.cache.insert(prompt, response)
                    
                    # Lookup exact match
                    res = self.cache.lookup(prompt)
                    if res != response:
                        errors.append(f"Thread {tid} got invalid exact match: {res}")
            except Exception as e:
                errors.append(f"Thread {tid} encountered error: {e}")

        threads = []
        for t in range(5):
            thread = threading.Thread(target=run_thread, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(len(errors), 0, f"Concurrent access test failed with errors: {errors}")

if __name__ == "__main__":
    unittest.main()
