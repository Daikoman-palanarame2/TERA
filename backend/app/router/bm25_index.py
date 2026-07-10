import string
from typing import List
from rank_bm25 import BM25Okapi

class BM25Index:
    """
    Purpose:
        Provides a lightweight, CPU-only wrapper around the BM25 algorithm (using rank-bm25)
        to compute the lexical similarity of an incoming prompt against a reference corpus.
    
    Time Complexity:
        - Initialization: O(N * L) where N is the number of documents in the corpus and L is the average document length.
        - Similarity Query: O(Q * log(N)) where Q is the token length of the query and N is the corpus size.
    
    Memory Complexity:
        - O(V + N * L_u) where V is the vocabulary size, N is the corpus size, and L_u is the number of unique terms per document.
        - Typically scales under 5 MB for typical hackathon reference datasets.
    """

    def __init__(self, corpus: List[str] = None) -> None:
        """
        Purpose:
            Initializes the BM25 index with a local corpus of documents.
        
        Inputs:
            corpus: Optional list of prompt strings to populate the index.
        
        Outputs:
            None
        """
        self.corpus = corpus or []
        self.bm25 = None
        # Pre-compile a translation table for fast punctuation removal
        self.translator = str.maketrans("", "", string.punctuation)
        
        if self.corpus:
            self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """
        Purpose:
            Applies the specified deterministic tokenizer pipeline on the input string:
            1. Convert to lowercase.
            2. Remove all punctuation characters.
            3. Split on whitespace.
        
        Inputs:
            text: A raw string containing text to tokenize.
        
        Outputs:
            A list of string tokens.
            
        Time Complexity:
            O(L) where L is the character length of the input text.
        """
        # Convert to lowercase
        lowered = text.lower()
        # Remove punctuation
        no_punctuation = lowered.translate(self.translator)
        # Split on whitespace
        return no_punctuation.split()

    def _build_index(self) -> None:
        """
        Purpose:
            Tokenizes the corpus and constructs the BM25Okapi index.
            
        Inputs:
            None
            
        Outputs:
            None
        """
        tokenized_corpus = [self._tokenize(doc) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def get_max_similarity(self, query: str) -> float:
        """
        Purpose:
            Calculates the maximum BM25 similarity score between the query prompt
            and all documents stored in the reference corpus index.
        
        Inputs:
            query: The prompt string to compute similarity scores for.
        
        Outputs:
            A float representing the maximum similarity score. If the index or corpus is
            empty, returns 0.0 gracefully.
            
        Time Complexity:
            O(Q * log(N)) where Q is query token count and N is corpus size.
        """
        if not self.bm25 or not self.corpus:
            return 0.0
            
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return 0.0
            
        # get scores for the tokenized query
        scores = self.bm25.get_scores(tokenized_query)
        if len(scores) == 0:
            return 0.0
            
        return float(max(scores))
