# backend/ml/tracker.py
"""MLflow experiment tracking wrapper for model training runs."""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """Wraps MLflow experiment tracking with graceful fallback.

    If MLflow is not installed, all operations are no-ops.
    """

    def __init__(self, ticker: str, market: str = "US"):
        self.ticker = ticker
        self.market = market
        self._run = None
        self._mlflow = None
        self._active = False

        from backend.ml.mlflow_config import get_mlflow, is_mlflow_available, get_or_create_experiment
        self._mlflow = get_mlflow()
        self._available = is_mlflow_available()

        if self._available:
            self._experiment_id = get_or_create_experiment()

    def start_run(self, run_name: str = None):
        """Start an MLflow run for this training session."""
        if not self._available:
            return self

        name = run_name or f"{self.ticker}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        try:
            self._run = self._mlflow.start_run(
                experiment_id=self._experiment_id,
                run_name=name,
            )
            self._active = True

            # Log base tags
            self._mlflow.set_tags({
                "ticker": self.ticker,
                "market": self.market,
                "training_date": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"[MLflow] Started run: {name}")
        except Exception as e:
            logger.warning(f"[MLflow] Failed to start run: {e}")
            self._active = False

        return self

    def log_params(self, params: dict):
        """Log hyperparameters."""
        if not self._active:
            return
        try:
            self._mlflow.log_params(params)
        except Exception as e:
            logger.warning(f"[MLflow] Failed to log params: {e}")

    def log_metrics(self, metrics: dict):
        """Log evaluation metrics."""
        if not self._active:
            return
        try:
            self._mlflow.log_metrics(metrics)
            logger.info(f"[MLflow] Metrics: {metrics}")
        except Exception as e:
            logger.warning(f"[MLflow] Failed to log metrics: {e}")

    def log_model(self, model, model_name: str = None):
        """Log and register the trained model."""
        if not self._active:
            return
        try:
            name = model_name or f"credlens-{self.ticker}"
            self._mlflow.xgboost.log_model(
                model,
                artifact_path="model",
                registered_model_name=name,
            )
            logger.info(f"[MLflow] Model logged as: {name}")
        except Exception as e:
            logger.warning(f"[MLflow] Failed to log model: {e}")

    def log_artifact(self, local_path: str):
        """Log a file artifact (e.g., SHAP plot)."""
        if not self._active:
            return
        try:
            self._mlflow.log_artifact(local_path)
        except Exception as e:
            logger.warning(f"[MLflow] Failed to log artifact: {e}")

    def set_tag(self, key: str, value: str):
        """Set a custom tag on the run."""
        if not self._active:
            return
        try:
            self._mlflow.set_tag(key, value)
        except Exception as e:
            logger.warning(f"[MLflow] Failed to set tag: {e}")

    def end_run(self):
        """End the current MLflow run."""
        if not self._active:
            return
        try:
            self._mlflow.end_run()
            self._active = False
            logger.info(f"[MLflow] Run ended for {self.ticker}")
        except Exception as e:
            logger.warning(f"[MLflow] Failed to end run: {e}")

    def __enter__(self):
        self.start_run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.set_tag("status", "FAILED")
            self.set_tag("error", str(exc_val))
        else:
            self.set_tag("status", "SUCCESS")
        self.end_run()
        return False
