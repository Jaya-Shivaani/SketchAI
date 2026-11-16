"""
Model Evaluation and Confusion Matrix Visualization Script
Loads the trained KNN model, tests predictions, and outputs evaluation summaries.
"""

import os
import sys
import json
import joblib
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_extraction import (
    CATEGORY_MAP,
    extract_features_from_strokes,
    rasterize_strokes
)


def evaluate_saved_model(dataset_dir: str = "", model_dir: str = ""):
    if not dataset_dir:
        dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    if not model_dir:
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")

    model_path = os.path.join(model_dir, "knn_drawing_model.joblib")
    scaler_path = os.path.join(model_dir, "scaler.joblib")
    npz_path = os.path.join(dataset_dir, "quickdraw_sampled.npz")

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Trained model artifacts not found in {model_dir}. Please run train_model.py first.")

    print(f"Loading model from: {model_path}")
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    print(f"Loading dataset from: {npz_path}")
    data = np.load(npz_path)
    X, y = data["X"], data["y"]

    X_scaled = scaler.transform(X)
    y_pred = model.predict(X_scaled)
    y_prob = model.predict_proba(X_scaled)

    acc = accuracy_score(y, y_pred)
    class_names = [CATEGORY_MAP[i] for i in range(len(CATEGORY_MAP))]

    print(f"\nOverall Model Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y, y_pred)
    print(cm)

    print("\nClassification Report:")
    print(classification_report(y, y_pred, target_names=class_names))

    # Test single drawing prediction format
    test_idx = 0
    sample_features = X_scaled[test_idx].reshape(1, -1)
    pred_class_id = int(model.predict(sample_features)[0])
    pred_probs = model.predict_proba(sample_features)[0]
    confidence = float(np.max(pred_probs))

    print(f"\nSample Prediction Test:")
    print(f"  Ground Truth: {CATEGORY_MAP[y[test_idx]]}")
    print(f"  Predicted:    {CATEGORY_MAP[pred_class_id]}")
    print(f"  Confidence:   {confidence*100:.2f}%")
    print(f"  Probabilities: {dict(zip(class_names, [round(p, 4) for p in pred_probs]))}")


if __name__ == "__main__":
    evaluate_saved_model()

