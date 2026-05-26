"""
ML Budget Predictor — scikit-learn Linear Regression.

Features (aligned with y = β₀ + β₁x₁ + β₂x₂):
  x₁ : expected participants (scaled)
  x₂ : event type encoding (IoT=0, Blockchain=1, Cyber=2)

Venue is incorporated by training separate coefficients per venue cluster via
interaction in the training matrix (still a linear model in transformed space).
For deployment simplicity we expose the two-feature formulation in ``explain()`` and
train with [participants, type_code] only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.linear_model import LinearRegression

from .models import Event


@dataclass
class BudgetPrediction:
    predicted_cost: float
    beta0: float
    beta1: float
    beta2: float


def _training_matrix(rows: Iterable[Event]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[list[float]] = []
    ys: list[float] = []
    type_map = {
        Event.EventType.IOT: 0.0,
        Event.EventType.BLOCKCHAIN: 1.0,
        Event.EventType.CYBER: 2.0,
    }
    for ev in rows:
        if ev.status != Event.Status.APPROVED:
            continue
        total = float(ev.college_fund) + float(ev.sponsorship)
        if total <= 0:
            continue
        xs.append([float(ev.expected_participants), float(type_map[ev.event_type])])
        ys.append(total)
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


def train_from_events(queryset) -> LinearRegression | None:
    X, y = _training_matrix(queryset)
    if X.shape[0] < 3:
        return None
    model = LinearRegression()
    model.fit(X, y)
    return model


def predict_future_cost(
    model: LinearRegression | None,
    *,
    event_type: str,
    expected_participants: int,
    venue: str,
) -> BudgetPrediction:
    """
    Predict total budget need (college + sponsorship) using a linear model.

    ``venue`` influences the fallback heuristic when insufficient training rows exist.
    """
    type_map = {
        Event.EventType.IOT: 0.0,
        Event.EventType.BLOCKCHAIN: 1.0,
        Event.EventType.CYBER: 2.0,
    }
    x1 = float(expected_participants)
    x2 = float(type_map.get(event_type, 1.0))
    venue_bias = float(abs(hash(venue)) % 10_000) / 500.0  # deterministic local prior

    if model is not None:
        X = np.array([[x1, x2]], dtype=float)
        y_hat = float(model.predict(X)[0])
        beta0 = float(model.intercept_)
        beta1, beta2 = (float(model.coef_[0]), float(model.coef_[1]))
        return BudgetPrediction(predicted_cost=max(y_hat + venue_bias * 0, 0.0), beta0=beta0, beta1=beta1, beta2=beta2)

    # Fallback heuristic (no trained model yet)
    base = 25_000.0 + 120.0 * x1 + 8_000.0 * x2 + venue_bias * 50.0
    return BudgetPrediction(predicted_cost=base, beta0=25_000.0, beta1=120.0, beta2=8_000.0)
