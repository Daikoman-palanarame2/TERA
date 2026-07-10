import os
import pickle
import json
import datetime
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from typing import List

from app.router.bm25_index import BM25Index
from app.router.feature_extractor import FeatureExtractor
from app.training.dataset import load_csv_dataset, split_dataset
from app.training.metrics import compute_brier_score, compute_ece

"""
This module implements the feature extraction loop, the offline model fitting steps,
validation evaluations, and persistence of model artifacts.
"""

def generate_feature_matrix(prompts: List[str], bm25_corpus: List[str]) -> np.ndarray:
    """
    Purpose:
        Helper method to extract the 4D feature vectors for a list of prompts 
        using the existing FeatureExtractor.
        
    Inputs:
        prompts: List of prompts to extract features for.
        bm25_corpus: Reference list of training prompts to populate the BM25 Index.
        
    Outputs:
        A 2D numpy array of shape (N, 4) containing the features.
        
    Time Complexity:
        O(M * (L + Q * log(N))) where M is prompts size, L is average prompt length, 
        Q is query token count, and N is bm25_corpus size.
        
    Memory Complexity:
        O(M * 4) to store feature matrix and O(N) for local BM25 index copy.
    """
    bm25 = BM25Index(bm25_corpus)
    extractor = FeatureExtractor(bm25_index=bm25)
    
    features_list = []
    for prompt in prompts:
        v = extractor.extract(prompt)
        features_list.append([v.length, v.symbol_ratio, v.regex_density, v.bm25_score])
        
    return np.array(features_list)


def run_training_pipeline(dataset_path: str, output_dir: str, seed: int = 42) -> dict:
    """
    Purpose:
        Executes the offline training pipeline:
        1. Loads labeled prompts.
        2. Splitting (60% Train / 20% Cal / 20% Val).
        3. Features generation.
        4. Trains Logistic Regression model on Train.
        5. Trains Isotonic Regression calibrator on Calibration.
        6. Validates models on Validation split.
        7. Serializes all artifacts (logistic, isotonic, corpus, metadata).
        
    Inputs:
        dataset_path: Path to the labeled CSV dataset.
        output_dir: Directory where artifacts will be saved.
        seed: Random seed for splitting and training determinism.
        
    Outputs:
        A dictionary containing validation performance metrics.
        
    Time Complexity:
        O(N * (L + Q * log(N))) dominated by feature extraction over dataset size N.
        
    Memory Complexity:
        O(N) to store dataset, features, and model objects.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load dataset
    dataset = load_csv_dataset(dataset_path)
    if not dataset:
        raise ValueError(f"Dataset at {dataset_path} is empty or invalid.")
        
    # 2. Split dataset
    train_set, cal_set, val_set = split_dataset(dataset, seed=seed)
    
    train_prompts = [item[0] for item in train_set]
    train_labels = np.array([item[1] for item in train_set])
    
    cal_prompts = [item[0] for item in cal_set]
    cal_labels = np.array([item[1] for item in cal_set])
    
    val_prompts = [item[0] for item in val_set]
    val_labels = np.array([item[1] for item in val_set])
    
    # 3. Reference corpus for BM25 (using training subset prompts)
    bm25_corpus = train_prompts
    
    # 4. Generate features
    print("Generating feature matrices...")
    X_train = generate_feature_matrix(train_prompts, bm25_corpus)
    X_cal = generate_feature_matrix(cal_prompts, bm25_corpus)
    X_val = generate_feature_matrix(val_prompts, bm25_corpus)
    
    # 5. Fit Logistic Regression
    print("Training Logistic Regression classifier...")
    lr_model = LogisticRegression(random_state=seed, solver="liblinear")
    lr_model.fit(X_train, train_labels)
    
    # 6. Predict raw scores on Calibration subset & fit Isotonic Regression
    print("Training Isotonic Regression calibration model...")
    cal_scores = lr_model.predict_proba(X_cal)[:, 1]
    
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(cal_scores, cal_labels)
    
    # 7. Evaluate on Validation subset
    print("Evaluating models on validation subset...")
    val_scores = lr_model.predict_proba(X_val)[:, 1]
    val_probs = calibrator.predict(val_scores)
    
    # Classification metrics
    val_preds = (val_probs >= 0.5).astype(int)
    val_acc = float(np.mean(val_preds == val_labels))
    val_ece = compute_ece(val_labels, val_probs)
    val_brier = compute_brier_score(val_labels, val_probs)
    
    metrics = {
        "accuracy": val_acc,
        "ece": val_ece,
        "brier_score": val_brier
    }
    
    print(f"Validation Accuracy: {val_acc:.4f}")
    print(f"Validation ECE: {val_ece:.4f}")
    print(f"Validation Brier Score: {val_brier:.4f}")
    
    # 8. Save artifacts
    print(f"Saving artifacts to {output_dir}...")
    logistic_path = os.path.join(output_dir, "logistic_model.pkl")
    isotonic_path = os.path.join(output_dir, "isotonic_model.pkl")
    corpus_path = os.path.join(output_dir, "bm25_corpus.txt")
    metadata_path = os.path.join(output_dir, "training_metadata.json")
    
    with open(logistic_path, "wb") as f:
        pickle.dump(lr_model, f)
        
    with open(isotonic_path, "wb") as f:
        pickle.dump(calibrator, f)
        
    with open(corpus_path, "w", encoding="utf-8") as f:
        for doc in bm25_corpus:
            f.write(doc.replace("\n", " ") + "\n")
            
    metadata = {
        "schema_version": "1.0.0",
        "feature_version": "1.0.0",
        "training_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dataset_size": len(dataset),
        "split_ratios": {
            "train": 0.6,
            "calibration": 0.2,
            "validation": 0.2
        },
        "split_sizes": {
            "train": len(train_set),
            "calibration": len(cal_set),
            "validation": len(val_set)
        },
        "random_seed": seed,
        "logistic_regression_parameters": lr_model.get_params(),
        "scikit_learn_version": sklearn.__version__,
        "validation_metrics": metrics
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print("Training pipeline execution completed successfully.")
    return metrics
