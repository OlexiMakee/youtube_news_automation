"""
Cloud Rotation Engine (v1.1.0)
YouTube News Automation

Purpose: Manage free/paid LLM provider rotation with efficiency scoring and quota interception.

Features:
  - Provider chain: Gemini Free → OpenRouter Free → Ollama Local → OpenAI/Anthropic Paid
  - Efficiency scoring: Likes / (Likes + Dislikes) per model
  - Quota interceptor: Match response streams against known error patterns
  - Premium pass-through: Bypass free rotation if paid keys configured
  - Hot-swap: Seamlessly fallback to next provider on quota/error
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Provider:
    """LLM provider configuration."""
    id: str
    name: str
    endpoint: str
    auth_type: str  # "api_key" or "bearer_token"
    rate_limit: str
    efficiency_score: float = 0.0
    is_paid: bool = False
    env_key: Optional[str] = None

class CloudRotationEngine:
    """Manages provider rotation with efficiency scoring."""
    
    def __init__(self, db_path: str, schema_path: str = None):
        """
        Initialize rotation engine.
        
        Args:
            db_path: Path to SQLite database (for feedback storage)
            schema_path: Path to LLM providers JSON config (default: configs/schemas/llm_providers.json)
        """
        self.db_path = db_path
        self.schema_path = schema_path or Path(__file__).parent.parent.parent / "configs" / "schemas" / "llm_providers.json"
        self.providers = []
        self.quota_errors = []
        self._load_configuration()
        self._load_quota_errors()
    
    def _load_configuration(self):
        """Load provider chain from JSON schema."""
        try:
            with open(self.schema_path) as f:
                schema = json.load(f)
            
            for prov_config in schema.get("cloud_rotation_chain", []):
                provider = Provider(
                    id=prov_config["provider"],
                    name=prov_config["provider"],
                    endpoint=prov_config["endpoint"],
                    auth_type=prov_config["auth"],
                    rate_limit=prov_config["rate_limit"],
                    is_paid=prov_config.get("requires_paid_key", False),
                    env_key=prov_config.get("env_key")
                )
                self.providers.append(provider)
            
            # Reload efficiency scores from database
            self._reload_efficiency_scores()
        
        except Exception as e:
            print(f"Error loading provider config: {e}")
            self.providers = []
    
    def _reload_efficiency_scores(self):
        """Update efficiency scores from feedback table."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get efficiency scores per model
            cursor.execute(
                """
                SELECT model_id, 
                       SUM(CASE WHEN feedback_type='like' THEN 1 ELSE 0 END) as likes,
                       SUM(CASE WHEN feedback_type='dislike' THEN 1 ELSE 0 END) as dislikes
                FROM agent_feedback_memory
                GROUP BY model_id
                """
            )
            
            scores = {}
            for model_id, likes, dislikes in cursor.fetchall():
                total = (likes or 0) + (dislikes or 0)
                if total > 0:
                    scores[model_id] = (likes or 0) / total
                else:
                    scores[model_id] = 0.5  # Default neutral score
            
            # Update provider scores
            for provider in self.providers:
                provider.efficiency_score = scores.get(provider.id, 0.5)
            
            conn.close()
        
        except Exception as e:
            print(f"Error loading efficiency scores: {e}")
    
    def _load_quota_errors(self):
        """Load known quota error patterns from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT error_string FROM leaked_quota_errors ORDER BY detected_at DESC LIMIT 50"
            )
            
            self.quota_errors = [row[0] for row in cursor.fetchall()]
            conn.close()
        
        except Exception as e:
            print(f"Error loading quota errors: {e}")
            self.quota_errors = []
    
    def get_next_available_provider(self, skip_paid: bool = True) -> Optional[Provider]:
        """
        Get the highest-efficiency available provider.
        
        Args:
            skip_paid: If True, skip providers requiring paid keys
        
        Returns:
            Provider with highest efficiency score (or None if none available)
        """
        # Sort by efficiency score (descending)
        candidates = [p for p in self.providers if not (skip_paid and p.is_paid)]
        candidates.sort(key=lambda p: p.efficiency_score, reverse=True)
        
        return candidates[0] if candidates else None
    
    def check_quota_exhaustion(self, response_text: str) -> bool:
        """
        Detect if response indicates quota exhaustion.
        
        Args:
            response_text: LLM response or error message
        
        Returns:
            True if quota error detected (should hot-swap provider)
        """
        if not response_text:
            return False
        
        # Check against known error patterns
        for error_pattern in self.quota_errors:
            try:
                if re.search(error_pattern, response_text, re.IGNORECASE):
                    return True
            except re.error:
                # Skip invalid regex patterns
                pass
        
        # Also check for common quota error keywords
        keywords = ["quota", "rate limit", "429", "too many requests", "exceeded"]
        if any(kw in response_text.lower() for kw in keywords):
            self._record_quota_error(response_text)
            return True
        
        return False
    
    def _record_quota_error(self, error_text: str):
        """Log new quota error pattern to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract numeric values and clean error string
            cleaned = re.sub(r'\d{1,}', '[NUM]', error_text)[:200]
            
            cursor.execute(
                """
                INSERT INTO leaked_quota_errors (error_string, detected_at, intercepted_count)
                VALUES (?, ?, 1)
                ON CONFLICT(error_string) DO UPDATE SET intercepted_count = intercepted_count + 1
                """,
                (cleaned, datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            
            # Reload quota errors
            self._load_quota_errors()
        
        except Exception as e:
            print(f"Error recording quota error: {e}")
    
    def record_feedback(self, model_id: str, provider_id: str, prompt_text: str,
                       response_text: str, feedback_type: str, latency_ms: int):
        """
        Record user feedback (like/dislike) for efficiency scoring.
        
        Args:
            model_id: Model identifier
            provider_id: Provider identifier
            prompt_text: User input text
            response_text: LLM output text
            feedback_type: "like" or "dislike"
            latency_ms: Response latency in milliseconds
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO agent_feedback_memory
                (prompt_text, response_text, model_id, provider_id, feedback_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (prompt_text, response_text, model_id, provider_id, feedback_type, latency_ms)
            )
            
            conn.commit()
            conn.close()
            
            # Reload efficiency scores
            self._reload_efficiency_scores()
        
        except Exception as e:
            print(f"Error recording feedback: {e}")
    
    def get_provider_by_id(self, provider_id: str) -> Optional[Provider]:
        """Get provider by ID."""
        return next((p for p in self.providers if p.id == provider_id), None)
    
    def get_health_summary(self) -> Dict:
        """Get provider chain health summary."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "providers": []
        }
        
        for provider in self.providers:
            summary["providers"].append({
                "id": provider.id,
                "name": provider.name,
                "efficiency": round(provider.efficiency_score, 2),
                "is_paid": provider.is_paid
            })
        
        return summary


# Singleton instance (managed by Flask app)
_rotation_engine = None

def init_rotation_engine(db_path: str) -> CloudRotationEngine:
    """Initialize global rotation engine."""
    global _rotation_engine
    _rotation_engine = CloudRotationEngine(db_path)
    return _rotation_engine

def get_rotation_engine() -> Optional[CloudRotationEngine]:
    """Get global rotation engine instance."""
    return _rotation_engine


if __name__ == "__main__":
    # Test mode
    import sys
    from app.services.telemetry import get_metrics_summary
    
    db_path = Path(__file__).parent.parent / "data" / "youtube_news.db"
    
    engine = CloudRotationEngine(str(db_path))
    print("Provider Chain Health:")
    health = engine.get_health_summary()
    for prov in health["providers"]:
        print(f"  {prov['id']}: {prov['efficiency']:.2f} efficiency (paid={prov['is_paid']})")
    
    print("\nNext Available Provider:")
    next_prov = engine.get_next_available_provider(skip_paid=True)
    if next_prov:
        print(f"  {next_prov.id}: {next_prov.efficiency_score:.2f}")
    else:
        print("  (none available)")
