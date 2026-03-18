import nextmv
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from visuals import feature_importance_chart, score_distribution_chart

FEATURE_COLS = [
    "age",
    "annual_income",
    "employment_length_years",
    "debt_to_income_ratio",
    "credit_history_length_years",
    "num_delinquencies_last_2_years",
    "loan_amount",
    "loan_purpose_encoded",
]

LOAN_PURPOSES = ["auto", "business", "debt_consolidation", "home_improvement", "personal"]


def encode_records(records):
    le = LabelEncoder()
    le.fit(LOAN_PURPOSES)
    for r in records:
        purpose = r.get("loan_purpose", "personal")
        if purpose not in LOAN_PURPOSES:
            purpose = "personal"
        r["loan_purpose_encoded"] = int(le.transform([purpose])[0])
    return records


def to_matrix(records):
    return np.array([[r[f] for f in FEATURE_COLS] for r in records], dtype=float)


def main() -> None:
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    inp = nextmv.load(options=options, path=options.input)
    data = inp.data

    historical = data["historical_data"]
    applicants = data["applicants"]

    nextmv.log(f"Historical records: {len(historical)}, applicants to score: {len(applicants)}")
    nextmv.log(f"Model: {options.model_type}, estimators: {options.n_estimators}")
    nextmv.log(f"Approval threshold: {options.approval_threshold}, review threshold: {options.review_threshold}")

    historical = encode_records(historical)
    applicants = encode_records(applicants)

    X_all = to_matrix(historical)
    y_all = np.array([int(r["defaulted"]) for r in historical])

    X_train, X_test, y_train, y_test = train_test_split(X_all, y_all, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model_map = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=options.n_estimators, random_state=42),
        "gradient_boosting": GradientBoostingClassifier(n_estimators=options.n_estimators, random_state=42),
    }
    model_type = options.model_type if options.model_type in model_map else "random_forest"
    clf = model_map[model_type]

    nextmv.redirect_stdout()

    clf.fit(X_train_s, y_train)
    test_accuracy = float(clf.score(X_test_s, y_test))
    y_pred = clf.predict(X_test_s)
    y_prob = clf.predict_proba(X_test_s)[:, list(clf.classes_).index(1)]

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_prob))
    logloss = float(log_loss(y_test, clf.predict_proba(X_test_s)))
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    nextmv.log(
        f"Accuracy: {test_accuracy:.3f} | Precision: {precision:.3f} | "
        f"Recall: {recall:.3f} | F1: {f1:.3f} | AUC-ROC: {roc_auc:.3f}"
    )

    X_app = scaler.transform(to_matrix(applicants))
    # class 0 = no default → approval score
    proba_no_default = clf.predict_proba(X_app)[:, list(clf.classes_).index(0)]

    decisions = []
    for i, ap in enumerate(data["applicants"]):
        score = float(proba_no_default[i])
        if score >= options.approval_threshold:
            decision = "approved"
        elif score >= options.review_threshold:
            decision = "review"
        else:
            decision = "denied"
        decisions.append(
            {
                "applicant_id": ap.get("id", i + 1),
                "name": ap.get("name", f"Applicant {i + 1}"),
                "approval_score": round(score, 4),
                "decision": decision,
            }
        )

    num_approved = sum(1 for d in decisions if d["decision"] == "approved")
    num_review = sum(1 for d in decisions if d["decision"] == "review")
    num_denied = sum(1 for d in decisions if d["decision"] == "denied")
    approval_rate = num_approved / len(decisions) if decisions else 0.0

    feature_names = [f.replace("_encoded", "").replace("_", " ") for f in FEATURE_COLS]
    if hasattr(clf, "feature_importances_"):
        raw_importance = clf.feature_importances_.tolist()
    else:
        raw_importance = [abs(c) for c in clf.coef_[0].tolist()]
    total = sum(raw_importance)
    importances = [v / total for v in raw_importance] if total > 0 else raw_importance

    chart1 = score_distribution_chart(decisions)
    chart2 = feature_importance_chart(feature_names, importances, model_type)

    output = nextmv.Output(
        solution={"decisions": decisions},
        assets=[chart1, chart2],
        metrics={
            "result_value": round(approval_rate, 4),
            "status": "optimal",
            "model_type": model_type,
            "accuracy": round(test_accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "log_loss": round(logloss, 4),
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "num_approved": num_approved,
            "num_review": num_review,
            "num_denied": num_denied,
            "approval_rate": round(approval_rate, 4),
            "total_applicants": len(decisions),
        },
    )

    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
