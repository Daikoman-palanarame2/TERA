import unittest
import sys
import os

# Add backend directory to sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.router.bm25_index import BM25Index
from app.router.feature_extractor import FeatureExtractor, FeatureVector

class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        # Sample corpus for BM25 testing
        self.corpus = [
            "Write a python script to solve a math formula.",
            "Summarize the main points of this document.",
            "Translate this text into Spanish or French.",
            "Debug the stacktrace error in this python function."
        ]
        self.bm25_index = BM25Index(self.corpus)
        self.extractor_empty_bm25 = FeatureExtractor()  # Uses empty index by default
        self.extractor_with_bm25 = FeatureExtractor(bm25_index=self.bm25_index)

    def test_empty_prompt(self):
        """
        Tests that an empty prompt yields 0 values for all features and does not divide by zero.
        """
        features = self.extractor_empty_bm25.extract("")
        self.assertEqual(features.length, 0)
        self.assertEqual(features.symbol_ratio, 0.0)
        self.assertEqual(features.regex_density, 0)
        self.assertEqual(features.bm25_score, 0.0)

    def test_english_sentence(self):
        """
        Tests a standard English sentence with basic punctuation.
        """
        prompt = "Hello, this is a simple text query."
        features = self.extractor_empty_bm25.extract(prompt)
        self.assertEqual(features.length, len(prompt))
        # Symbols should count only ',' and '.' -> 2 symbols
        # Length is 35. Ratio: 2 / 35 = 0.05714
        self.assertAlmostEqual(features.symbol_ratio, 2.0 / len(prompt))
        self.assertEqual(features.regex_density, 0)

    def test_mathematical_expression(self):
        """
        Tests a prompt containing mathematical syntax.
        """
        prompt = "Calculate the sum: y = 2 * x + (3 / z)"
        features = self.extractor_with_bm25.extract(prompt)
        
        # Verify it triggers the "calculate" regex keyword
        self.assertGreaterEqual(features.regex_density, 1)
        
        # Symbols: ':', '=', '*', '+', '(', '/', ')' -> 7 symbols
        # Length: 39. Ratio: 7 / 39 = 0.179487
        self.assertEqual(features.length, len(prompt))
        self.assertAlmostEqual(features.symbol_ratio, 7.0 / len(prompt))

    def test_python_code(self):
        """
        Tests a prompt containing python code block syntax.
        """
        prompt = "def get_sum(a, b):\n    return a + b  # code"
        features = self.extractor_with_bm25.extract(prompt)
        
        # Verify it triggers "code" related keyword
        self.assertGreaterEqual(features.regex_density, 1)
        
        # Symbols: '(', '_', ',', ')', ':', '+', '#' -> 7 symbols (newlines and spaces ignored)
        # Length: 43. Ratio: 7 / 43
        self.assertEqual(features.length, len(prompt))
        self.assertAlmostEqual(features.symbol_ratio, 7.0 / len(prompt))

    def test_json_input(self):
        """
        Tests a prompt containing a JSON payload string.
        """
        prompt = '{"status": "ok", "count": 10}  # json'
        features = self.extractor_with_bm25.extract(prompt)
        
        # Verify it triggers "json" keyword
        self.assertGreaterEqual(features.regex_density, 1)
        
        # Symbols: '{', '"', '"', ':', '"', '"', ',', '"', '"', ':', '}', '#' -> 12 symbols
        # Length: 37. Ratio: 12 / 37
        self.assertEqual(features.length, len(prompt))
        self.assertAlmostEqual(features.symbol_ratio, 12.0 / len(prompt))

    def test_symbol_heavy_text(self):
        """
        Tests text composed strictly of non-alphanumeric, non-space symbol characters.
        """
        prompt = "!!!@@@###$$$"
        features = self.extractor_empty_bm25.extract(prompt)
        self.assertEqual(features.length, len(prompt))
        self.assertEqual(features.symbol_ratio, 1.0)  # 12 symbols / 12 length

    def test_regex_keyword_detection(self):
        """
        Tests that each of the 10 configured categories increments regex_density.
        """
        keywords = [
            "summarize", "explain", "extract", "translate", "debug", 
            "classify", "compare", "calculate", "code", "json"
        ]
        for kw in keywords:
            features = self.extractor_empty_bm25.extract(f"Please {kw} this task.")
            self.assertGreaterEqual(features.regex_density, 1, f"Failed keyword: {kw}")

    def test_empty_bm25_corpus(self):
        """
        Tests that BM25 similarity defaults to 0.0 if the reference index is empty.
        """
        features = self.extractor_empty_bm25.extract("Write a python script")
        self.assertEqual(features.bm25_score, 0.0)

    def test_sample_bm25_corpus(self):
        """
        Tests that BM25 similarity returns a correct score when querying a matching corpus.
        """
        # Exact match of a corpus document should yield high score
        features = self.extractor_with_bm25.extract("Write a python script to solve a math formula.")
        self.assertGreater(features.bm25_score, 0.0)
        
        # Partially matching query
        features_partial = self.extractor_with_bm25.extract("solve python error")
        self.assertGreater(features_partial.bm25_score, 0.0)

    def test_very_long_prompt(self):
        """
        Tests that very long prompts (e.g. 10,000 characters) execute successfully and correctly.
        """
        long_prompt = "hello " * 2000  # 12,000 characters
        features = self.extractor_empty_bm25.extract(long_prompt)
        self.assertEqual(features.length, len(long_prompt))
        self.assertEqual(features.symbol_ratio, 0.0)  # Contains only letters and spaces
        self.assertEqual(features.regex_density, 0)

    def test_unicode_non_english_prompt(self):
        """
        Tests prompts with non-ASCII and Unicode characters.
        """
        # "Résumé: Ce message a été traduit en French. 計算する = 1 + 2"
        prompt = "Résumé: Ce message a été traduit en French. 計算する = 1 + 2"
        features = self.extractor_with_bm25.extract(prompt)
        
        # Verify it triggers regex matches ("french" matches "translate" category)
        self.assertGreaterEqual(features.regex_density, 1)
        
        # Alphanumeric includes Unicode letters like 'é', 'ç' and Japanese characters '計算する'
        # Symbols: ':', '.', '=', '+' -> 4 symbols
        # Length: 58. Ratio: 4 / 58 = 0.068965
        self.assertEqual(features.length, len(prompt))
        self.assertAlmostEqual(features.symbol_ratio, 4.0 / len(prompt))

if __name__ == "__main__":
    unittest.main()
