# backend/ml/mlflow_config.py
"""MLflow configuration and initialization."""

import os
import logging

logger = logging.getLogger(__name__)

# ─── Configuration ───
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///backend/mlflow.db")
EXPERIMENT_NAME = "credlens-credit-risk"

# ─── Initialization ───
_mlflow_available = False
_mlflow = None

try:
    import mlflow
    _mlflow = mlflow
    _mlflow_available = True
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    logger.info(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
except ImportError:
    logger.warning("MLflow not installed. Model tracking disabled. Install with: pip install mlflow")
except Exception as e:
    logger.warning(f"MLflow initialization failed: {e}. Model tracking disabled.")


def get_mlflow():
    """Return the mlflow module if available, else None."""
    return _mlflow


def is_mlflow_available() -> bool:
    return _mlflow_available


def get_or_create_experiment(name: str = None) -> str:
    """Get or create an MLflow experiment, returns experiment_id."""
    if not _mlflow_available:
        return "0"

    exp_name = name or EXPERIMENT_NAME
    experiment = _mlflow.get_experiment_by_name(exp_name)
    if experiment is None:
        experiment_id = _mlflow.create_experiment(exp_name)
        logger.info(f"Created MLflow experiment: {exp_name} (id={experiment_id})")
    else:
        experiment_id = experiment.experiment_id
    return experiment_id
