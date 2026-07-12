"""
Module: backend/app/cache/semantic_cache
Purpose:
    Implements the SemanticCache class for exact prompt matching and semantic
    vector search using LMDB and the ONNX MiniLM model.
"""

import logging
import os
import hashlib
import pickle
import threading
import math
import numpy as np
import lmdb
import onnxruntime as ort
from tokenizers import Tokenizer
from typing import Optional

from app.core.config import LMDB_MAP_SIZE
from app.core.exceptions import CacheError, ConfigurationError

logger = logging.getLogger("app.cache")


class SemanticCache:
    def __init__(self, cache_dir: str, embedding_model_path: str) -> None:
        """Initialize LMDB client and load ONNX embedding model.

        Raises:
            ConfigurationError: If paths are malformed or missing.
        """
        if not cache_dir or not cache_dir.strip():
            raise ConfigurationError("Cache directory path must not be empty.")
        if not embedding_model_path or not embedding_model_path.strip():
            raise ConfigurationError("ONNX model path must not be empty.")

        model_dir = os.path.dirname(embedding_model_path)
        tokenizer_path = os.path.join(model_dir, "tokenizer.json")

        if not os.path.exists(embedding_model_path):
            raise ConfigurationError(
                f"ONNX model file not found at: {embedding_model_path}"
            )
        if not os.path.exists(tokenizer_path):
            raise ConfigurationError(
                f"Tokenizer JSON file not found at: {tokenizer_path}"
            )

        try:
            self.tokenizer = Tokenizer.from_file(tokenizer_path)
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
        except Exception as e:
            raise ConfigurationError(f"Failed to load tokenizer: {e}")

        try:
            sess_opts = ort.SessionOptions()
            sess_opts.intra_op_num_threads = 1
            sess_opts.inter_op_num_threads = 1
            self.session = ort.InferenceSession(embedding_model_path, sess_opts)
        except Exception as e:
            raise ConfigurationError(f"Failed to load ONNX model: {e}")

        try:
            os.makedirs(cache_dir, exist_ok=True)
            self.env = lmdb.open(cache_dir, map_size=LMDB_MAP_SIZE)
        except Exception as e:
            logger.error(f"LMDB initialization failed: {e}")
            raise ConfigurationError(f"LMDB initialization failed: {e}")

        self.lock = threading.Lock()

    def _get_embedding(self, text: str) -> np.ndarray:
        """Helper to generate L2-normalized sentence embedding using ONNX MiniLM model."""
        try:
            enc = self.tokenizer.encode(text)
            input_ids = np.array([enc.ids], dtype=np.int64)
            attention_mask = np.array([enc.attention_mask], dtype=np.int64)

            input_names = [i.name for i in self.session.get_inputs()]
            inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
            if "token_type_ids" in input_names:
                inputs["token_type_ids"] = np.array([enc.type_ids], dtype=np.int64)

            outputs = self.session.run(None, inputs)
            if not outputs:
                raise ValueError("model returned no outputs")
            token_embeddings = np.asarray(outputs[0])
            if token_embeddings.ndim != 3 or token_embeddings.shape[:2] != attention_mask.shape:
                raise ValueError(
                    "unexpected embedding output shape "
                    f"{token_embeddings.shape}; expected [batch, tokens, dimensions]"
                )
            if token_embeddings.shape[2] == 0 or not np.all(np.isfinite(token_embeddings)):
                raise ValueError("model returned an empty or non-finite embedding")

            # Mean pooling
            mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(float)
            sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
            sum_mask = np.sum(mask_expanded, axis=1)
            sum_mask = np.clip(sum_mask, 1e-9, None)
            embedding = sum_embeddings / sum_mask

            # L2 normalize
            norm = np.linalg.norm(embedding, axis=1, keepdims=True)
            if not np.all(np.isfinite(norm)) or np.any(norm <= 0.0):
                raise ValueError("model returned a zero-norm or non-finite embedding")
            normalized = embedding / norm
            result = normalized[0].astype(np.float32)
            if result.ndim != 1 or result.size == 0 or not np.all(np.isfinite(result)):
                raise ValueError("normalized embedding is invalid")
            return result
        except Exception as e:
            raise CacheError(f"ONNX embedding generation failed: {e}")

    def lookup(self, prompt: str, threshold: float = 0.95) -> Optional[str]:
        """Perform exact match check, followed by cosine similarity embedding search.

        Raises:
            CacheError: If database read fails.
        """
        if not prompt or not prompt.strip():
            logger.info("Cache miss: empty prompt")
            return None
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise ValueError("threshold must be a finite number between 0.0 and 1.0")
        threshold = float(threshold)
        if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be a finite number between 0.0 and 1.0")

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        try:
            with self.env.begin(write=False) as txn:
                exact_data_bytes = txn.get(prompt_hash.encode("utf-8"))
                if exact_data_bytes is not None:
                    exact_data = pickle.loads(exact_data_bytes)
                    logger.info("Cache hit (exact match)")
                    return exact_data["response"]
        except Exception as e:
            logger.error(f"LMDB read error during exact lookup: {e}")
            raise CacheError(f"LMDB read error during exact lookup: {e}")

        query_emb = self._get_embedding(prompt)
        best_sim = -1.0
        best_response = None

        try:
            with self.env.begin(write=False) as txn:
                with txn.cursor() as cursor:
                    for _key, value in cursor:
                        try:
                            data = pickle.loads(value)
                            if not isinstance(data, dict) or not isinstance(data.get("response"), str):
                                raise ValueError("invalid cache record schema")
                            stored_emb = np.asarray(data["embedding"], dtype=np.float32)
                            if (
                                stored_emb.shape != query_emb.shape
                                or not np.all(np.isfinite(stored_emb))
                            ):
                                raise ValueError("invalid stored embedding")
                            sim = float(np.dot(query_emb, stored_emb))
                            if not math.isfinite(sim):
                                raise ValueError("non-finite similarity")
                            if sim > best_sim:
                                best_sim = sim
                                best_response = data["response"]
                        except Exception as e:
                            raise CacheError(f"Corrupted semantic cache record: {e}") from e
        except Exception as e:
            logger.error(f"LMDB read error during semantic lookup: {e}")
            raise CacheError(f"LMDB read error during semantic lookup: {e}")

        if best_sim >= threshold and best_response is not None:
            logger.info(f"Semantic hit: similarity={best_sim:.4f}")
            return best_response

        logger.info("Cache miss")
        return None

    def insert(self, prompt: str, response: str) -> None:
        """Insert prompt text, embedding array, and output response into LMDB.

        Raises:
            CacheError: If database write fails.
        """
        if not prompt or not prompt.strip() or not response or not response.strip():
            logger.warning("Rejected insert: empty prompt or response")
            return

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        emb = self._get_embedding(prompt)

        with self.lock:
            try:
                data = {"prompt": prompt, "embedding": emb, "response": response}
                serialized = pickle.dumps(data)
                with self.env.begin(write=True) as txn:
                    inserted = txn.put(
                        prompt_hash.encode("utf-8"), serialized, overwrite=False
                    )
                if not inserted:
                    logger.warning("Rejected insert: duplicate prompt entry")
                    return
                logger.info("Insert: successful cache insertion")
            except Exception as e:
                logger.error(f"LMDB write error: {e}")
                raise CacheError(f"LMDB write error: {e}")
