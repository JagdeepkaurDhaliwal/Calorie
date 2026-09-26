"""Shared ML configuration: features, ranges, seeds, hyperparameters."""

FEATURE_ORDER = [
    "gender",
    "age",
    "height",
    "weight",
    "duration",
    "heart_rate",
    "body_temp",
]

# API / validation ranges (SRS 3.3.1)
RANGES = {
    "age": (10, 100),
    "height": (100.0, 230.0),
    "weight": (30.0, 200.0),
    "duration": (1.0, 300.0),
    "heart_rate": (40.0, 220.0),
    "body_temp": (35.0, 42.0),
}

RANDOM_STATE = 42
HOLDOUT_FRACTION = 0.20
ANN_VAL_FRACTION = 0.10

RF_N_ESTIMATORS = 200
KNN_K_GRID = list(range(3, 16, 2))
KNN_CV = 3

ANN_HIDDEN = (64, 32)
ANN_LR = 1e-3
ANN_BATCH = 32
ANN_MAX_EPOCHS = 80
ANN_PATIENCE = 10

GENDER_MALE = 0
GENDER_FEMALE = 1
