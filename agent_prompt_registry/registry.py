"""Main prompt registry."""

import json
import random
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from jinja2 import Template

from .models import Prompt, PromptVersion, Experiment, ExperimentVariant


class PromptRegistry:
    """Registry for managing prompts with versioning and A/B testing."""

    def __init__(self, db_path: str = "~/.prompt-registry.db"):
        """Initialize registry.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                name TEXT PRIMARY KEY,
                current_version INTEGER DEFAULT 1,
                active_experiment TEXT,
                tags TEXT,
                metadata TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                author TEXT,
                message TEXT,
                metadata TEXT,
                UNIQUE(prompt_name, version),
                FOREIGN KEY(prompt_name) REFERENCES prompts(name)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                name TEXT PRIMARY KEY,
                prompt_name TEXT NOT NULL,
                variants TEXT NOT NULL,
                success_metric TEXT DEFAULT 'success',
                status TEXT DEFAULT 'running',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                winner TEXT,
                confidence REAL,
                FOREIGN KEY(prompt_name) REFERENCES prompts(name)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_name TEXT NOT NULL,
                variant TEXT NOT NULL,
                success INTEGER NOT NULL,
                metrics TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(experiment_name) REFERENCES experiments(name)
            )
        """)

        conn.commit()
        conn.close()

    def register(
        self,
        name: str,
        prompt: str,
        author: Optional[str] = None,
        message: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptVersion:
        """Register or update a prompt.

        Args:
            name: Prompt identifier
            prompt: Prompt content (can include Jinja2 templates)
            author: Author of this version
            message: Commit message
            tags: Tags for categorization
            metadata: Additional metadata

        Returns:
            Created PromptVersion
        """
        conn = sqlite3.connect(self.db_path)

        # Check if prompt exists
        cursor = conn.execute("SELECT current_version FROM prompts WHERE name = ?", (name,))
        row = cursor.fetchone()

        if row:
            # Update existing
            new_version = row[0] + 1
            conn.execute(
                "UPDATE prompts SET current_version = ? WHERE name = ?",
                (new_version, name)
            )
        else:
            # Create new
            new_version = 1
            conn.execute(
                "INSERT INTO prompts (name, current_version, tags, metadata) VALUES (?, ?, ?, ?)",
                (name, 1, json.dumps(tags or []), json.dumps(metadata))
            )

        # Add version
        created_at = datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT INTO prompt_versions (prompt_name, version, content, created_at, author, message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, new_version, prompt, created_at, author, message, json.dumps(metadata))
        )

        conn.commit()
        conn.close()

        return PromptVersion(
            version=new_version,
            content=prompt,
            created_at=created_at,
            author=author,
            message=message,
            metadata=metadata
        )

    def get(
        self,
        name: str,
        version: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get a prompt by name.

        Args:
            name: Prompt identifier
            version: Specific version (default: current)
            variables: Template variables to render

        Returns:
            Rendered prompt content
        """
        conn = sqlite3.connect(self.db_path)

        if version:
            cursor = conn.execute(
                "SELECT content FROM prompt_versions WHERE prompt_name = ? AND version = ?",
                (name, version)
            )
        else:
            cursor = conn.execute(
                """
                SELECT pv.content FROM prompt_versions pv
                JOIN prompts p ON pv.prompt_name = p.name AND pv.version = p.current_version
                WHERE p.name = ?
                """,
                (name,)
            )

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise KeyError(f"Prompt not found: {name}" + (f" v{version}" if version else ""))

        content = row[0]

        # Render template if variables provided
        if variables:
            template = Template(content)
            content = template.render(**variables)

        return content

    def get_variant(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Get a prompt variant for A/B testing.

        Args:
            name: Prompt identifier
            variables: Template variables

        Returns:
            Tuple of (rendered content, variant name)
        """
        conn = sqlite3.connect(self.db_path)

        # Check for active experiment
        cursor = conn.execute(
            "SELECT name, variants FROM experiments WHERE prompt_name = ? AND status = 'running'",
            (name,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            # No experiment, return default
            return self.get(name, variables=variables), "default"

        variants_data = json.loads(row[1])

        # Weighted random selection
        total_weight = sum(v["weight"] for v in variants_data.values())
        rand = random.randint(1, total_weight)

        cumulative = 0
        selected_variant = None
        for variant_name, variant_data in variants_data.items():
            cumulative += variant_data["weight"]
            if rand <= cumulative:
                selected_variant = variant_name
                break

        content = variants_data[selected_variant]["content"]

        if variables:
            template = Template(content)
            content = template.render(**variables)

        return content, selected_variant

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all prompts.

        Returns:
            List of prompt summaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name, current_version, active_experiment, tags FROM prompts ORDER BY name"
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "name": row[0],
                "current_version": row[1],
                "active_experiment": row[2],
                "tags": json.loads(row[3]) if row[3] else []
            }
            for row in rows
        ]

    def get_history(self, name: str) -> List[PromptVersion]:
        """Get version history for a prompt.

        Args:
            name: Prompt identifier

        Returns:
            List of versions (newest first)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT version, content, created_at, author, message, metadata
            FROM prompt_versions
            WHERE prompt_name = ?
            ORDER BY version DESC
            """,
            (name,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            PromptVersion(
                version=row[0],
                content=row[1],
                created_at=row[2],
                author=row[3],
                message=row[4],
                metadata=json.loads(row[5]) if row[5] else None
            )
            for row in rows
        ]

    def rollback(self, name: str, version: int) -> None:
        """Rollback to a previous version.

        Args:
            name: Prompt identifier
            version: Version to rollback to
        """
        conn = sqlite3.connect(self.db_path)

        # Verify version exists
        cursor = conn.execute(
            "SELECT 1 FROM prompt_versions WHERE prompt_name = ? AND version = ?",
            (name, version)
        )
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Version {version} not found for prompt {name}")

        conn.execute(
            "UPDATE prompts SET current_version = ? WHERE name = ?",
            (version, name)
        )
        conn.commit()
        conn.close()

    def create_experiment(
        self,
        name: str,
        variants: Dict[str, str],
        traffic_split: Optional[Dict[str, int]] = None,
        success_metric: str = "success"
    ) -> Experiment:
        """Create an A/B experiment.

        Args:
            name: Prompt name to experiment on
            variants: Dict of variant_name -> prompt_content
            traffic_split: Dict of variant_name -> percentage (must sum to 100)
            success_metric: Metric to optimize for

        Returns:
            Created Experiment
        """
        if traffic_split is None:
            # Equal split
            weight = 100 // len(variants)
            traffic_split = {k: weight for k in variants}

        if sum(traffic_split.values()) != 100:
            raise ValueError("Traffic split must sum to 100")

        experiment_variants = {
            k: ExperimentVariant(name=k, content=v, weight=traffic_split[k])
            for k, v in variants.items()
        }

        experiment = Experiment(
            name=f"{name}-experiment",
            prompt_name=name,
            variants=experiment_variants,
            success_metric=success_metric
        )

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO experiments (name, prompt_name, variants, success_metric, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                experiment.name,
                experiment.prompt_name,
                json.dumps({k: {"content": v.content, "weight": v.weight} for k, v in experiment_variants.items()}),
                success_metric,
                "running",
                experiment.created_at
            )
        )

        # Update prompt with active experiment
        conn.execute(
            "UPDATE prompts SET active_experiment = ? WHERE name = ?",
            (experiment.name, name)
        )

        conn.commit()
        conn.close()

        return experiment

    def record_outcome(
        self,
        prompt_name: str,
        variant: str,
        success: bool,
        metrics: Optional[Dict[str, float]] = None
    ) -> None:
        """Record an experiment outcome.

        Args:
            prompt_name: Prompt identifier
            variant: Variant that was used
            success: Whether the interaction was successful
            metrics: Additional metrics
        """
        conn = sqlite3.connect(self.db_path)

        # Find active experiment
        cursor = conn.execute(
            "SELECT name FROM experiments WHERE prompt_name = ? AND status = 'running'",
            (prompt_name,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"No active experiment for prompt {prompt_name}")

        experiment_name = row[0]

        conn.execute(
            """
            INSERT INTO experiment_outcomes (experiment_name, variant, success, metrics, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (experiment_name, variant, 1 if success else 0, json.dumps(metrics), datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def get_experiment_results(self, prompt_name: str) -> Dict[str, Any]:
        """Get experiment results.

        Args:
            prompt_name: Prompt identifier

        Returns:
            Results dictionary
        """
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            "SELECT name, variants FROM experiments WHERE prompt_name = ? AND status = 'running'",
            (prompt_name,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {}

        experiment_name = row[0]

        cursor = conn.execute(
            """
            SELECT variant, SUM(success), COUNT(*), AVG(success)
            FROM experiment_outcomes
            WHERE experiment_name = ?
            GROUP BY variant
            """,
            (experiment_name,)
        )
        outcomes = cursor.fetchall()
        conn.close()

        results = {}
        best_variant = None
        best_rate = 0

        for outcome in outcomes:
            variant, successes, trials, success_rate = outcome
            results[variant] = {
                "trials": trials,
                "successes": int(successes),
                "success_rate": round(success_rate, 4)
            }
            if success_rate > best_rate:
                best_rate = success_rate
                best_variant = variant

        results["winner"] = best_variant
        results["total_trials"] = sum(r["trials"] for r in results.values() if isinstance(r, dict) and "trials" in r)

        return results

    def export(self, filepath: str) -> None:
        """Export all prompts to YAML.

        Args:
            filepath: Output path
        """
        import yaml

        prompts = self.list_prompts()
        export_data = {}

        for p in prompts:
            history = self.get_history(p["name"])
            current = history[0] if history else None
            export_data[p["name"]] = {
                "content": current.content if current else "",
                "version": p["current_version"],
                "tags": p["tags"]
            }

        with open(filepath, "w") as f:
            yaml.dump(export_data, f, default_flow_style=False)

    def import_prompts(self, filepath: str) -> int:
        """Import prompts from YAML.

        Args:
            filepath: Input path

        Returns:
            Number of prompts imported
        """
        import yaml

        with open(filepath) as f:
            data = yaml.safe_load(f)

        count = 0
        for name, prompt_data in data.items():
            self.register(
                name=name,
                prompt=prompt_data.get("content", ""),
                tags=prompt_data.get("tags"),
                message="Imported from file"
            )
            count += 1

        return count
