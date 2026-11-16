"""
Model Training and Hyperparameter Tuning for Sketch Category Classification
Uses scikit-learn KNeighborsClassifier to classify sketches into 5 categories:
Animal, Object, Food, Vehicle, Nature.
"""

import os
import sys
import json
import argparse
import joblib
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# Ensure ML dir is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_extraction import CATEGORY_MAP, CATEGORY_TO_ID
from generate_dataset import generate_dataset


def train_and_evaluate(dataset_dir: str = "", model_dir: str = "", samples_per_cat: int = 500, force_regenerate: bool = False):
    if not dataset_dir:
        dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    if not model_dir:
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")

    os.makedirs(dataset_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    npz_path = os.path.join(dataset_dir, "quickdraw_sampled.npz")
    if os.path.exists(npz_path) and not force_regenerate:
        print(f"Loading existing dataset from {npz_path}...")
        data = np.load(npz_path)
        X, y = data["X"], data["y"]
    else:
        print(f"Dataset not found at {npz_path}. Generating dataset with {samples_per_cat} samples/cat...")
        X, y, bitmaps, meta = generate_dataset(samples_per_category=samples_per_cat)
        np.savez_compressed(npz_path, X=X, y=y, bitmaps=bitmaps)
        meta_path = os.path.join(dataset_dir, "dataset_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    print(f"Dataset summary: Total samples = {len(y)}, Feature dimension = {X.shape[1]}")
    for cid, cname in CATEGORY_MAP.items():
        count = int(np.sum(y == cid))
        print(f"  Class {cid} ({cname}): {count} samples")

    # Train / Test split (80% train, 20% test, stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Feature Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Hyperparameter Grid Search for KNN
    print("\n--- Tuning KNN Hyperparameters ---")
    param_grid = {
        "n_neighbors": [3, 5, 7, 9, 11],
        "weights": ["uniform", "distance"],
        "metric": ["euclidean", "manhattan", "cosine"]
    }

    grid_search = GridSearchCV(
        KNeighborsClassifier(),
        param_grid,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="accuracy",
        n_jobs=-1,
        verbose=1
    )

    grid_search.fit(X_train_scaled, y_train)

    best_k = grid_search.best_params_["n_neighbors"]
    best_weights = grid_search.best_params_["weights"]
    best_metric = grid_search.best_params_["metric"]
    print(f"Best Parameters: k={best_k}, weights='{best_weights}', metric='{best_metric}'")
    print(f"Cross-Validation Accuracy: {grid_search.best_score_:.4f}")

    best_model = grid_search.best_estimator_

    # Final Evaluation on Held-Out Test Set
    y_pred = best_model.predict(X_test_scaled)
    y_prob = best_model.predict_proba(X_test_scaled)

    acc = accuracy_score(y_test, y_pred)
    prec_macro = precision_score(y_test, y_pred, average="macro")
    rec_macro = recall_score(y_test, y_pred, average="macro")
    f1_macro = f1_score(y_test, y_pred, average="macro")
    f1_weighted = f1_score(y_test, y_pred, average="weighted")

    conf_mat = confusion_matrix(y_test, y_pred).tolist()
    class_names = [CATEGORY_MAP[i] for i in range(len(CATEGORY_MAP))]
    clf_report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)

    print("\n================ TEST SET EVALUATION ================")
    print(f"Accuracy:        {acc:.4f} ({acc*100:.2f}%)")
    print(f"Macro Precision: {prec_macro:.4f}")
    print(f"Macro Recall:    {rec_macro:.4f}")
    print(f"Macro F1-Score:  {f1_macro:.4f}")
    print(f"Weighted F1:     {f1_weighted:.4f}")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=class_names))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Save trained artifacts
    model_path = os.path.join(model_dir, "knn_drawing_model.joblib")
    scaler_path = os.path.join(model_dir, "scaler.joblib")
    encoder_path = os.path.join(model_dir, "label_encoder.joblib")
    eval_path = os.path.join(model_dir, "evaluation_report.json")

    joblib.dump(best_model, model_path)
    joblib.dump(scaler, scaler_path)
    joblib.dump(CATEGORY_MAP, encoder_path)

    eval_results = {
        "best_parameters": grid_search.best_params_,
        "cross_val_accuracy": float(grid_search.best_score_),
        "test_metrics": {
            "accuracy": float(acc),
            "precision_macro": float(prec_macro),
            "recall_macro": float(rec_macro),
            "f1_macro": float(f1_macro),
            "f1_weighted": float(f1_weighted)
        },
        "confusion_matrix": conf_mat,
        "classification_report": clf_report
    }

    with open(eval_path, "w") as f:
        json.dump(eval_results, f, indent=2)

    print(f"\nTrained artifacts saved successfully:")
    print(f"  Model:   {model_path}")
    print(f"  Scaler:  {scaler_path}")
    print(f"  Encoder: {encoder_path}")
    print(f"  Metrics: {eval_path}")

    return eval_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir", type=str, default="")
    parser.add_argument("--model_dir", type=str, default="")
    parser.add_argument("--samples", type=int, default=700)
    parser.add_argument("--force", action="store_true", help="Force dataset regeneration")
    args = parser.parse_args()

    train_and_evaluate(
        dataset_dir=args.dataset_dir,
        model_dir=args.model_dir,
        samples_per_cat=args.samples,
        force_regenerate=args.force
    )

