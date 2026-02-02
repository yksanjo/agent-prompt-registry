"""Data models for prompt registry."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class PromptVersion:
    """A single version of a prompt."""
    version: int
    content: str
    created_at: str
    author: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "content": self.content,
            "created_at": self.created_at,
            "author": self.author,
            "message": self.message,
            "metadata": self.metadata
        }


@dataclass
class Prompt:
    """A prompt with version history."""
    name: str
    current_version: int
    versions: List[PromptVersion] = field(default_factory=list)
    active_experiment: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    @property
    def current(self) -> Optional[PromptVersion]:
        """Get current version."""
        for v in self.versions:
            if v.version == self.current_version:
                return v
        return None

    def get_version(self, version: int) -> Optional[PromptVersion]:
        """Get specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "current_version": self.current_version,
            "versions": [v.to_dict() for v in self.versions],
            "active_experiment": self.active_experiment,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class ExperimentVariant:
    """A variant in an A/B experiment."""
    name: str
    content: str
    weight: int  # percentage
    trials: int = 0
    successes: int = 0
    metrics: Dict[str, List[float]] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.trials == 0:
            return 0.0
        return self.successes / self.trials

    def avg_metric(self, metric: str) -> Optional[float]:
        if metric not in self.metrics or not self.metrics[metric]:
            return None
        return sum(self.metrics[metric]) / len(self.metrics[metric])


@dataclass
class Experiment:
    """An A/B experiment."""
    name: str
    prompt_name: str
    variants: Dict[str, ExperimentVariant]
    success_metric: str = "success"
    status: str = "running"  # running, paused, completed
    created_at: str = ""
    completed_at: Optional[str] = None
    winner: Optional[str] = None
    confidence: Optional[float] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "prompt_name": self.prompt_name,
            "variants": {
                k: {
                    "content": v.content,
                    "weight": v.weight,
                    "trials": v.trials,
                    "successes": v.successes,
                    "success_rate": v.success_rate
                }
                for k, v in self.variants.items()
            },
            "status": self.status,
            "winner": self.winner,
            "confidence": self.confidence
        }
