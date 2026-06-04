from memory_os.core import MemoryOS

class TelemetryRecorder:
    """Logs LLM execution metrics (tokens, latency, cost, and statuses)."""

    def __init__(self, memory_os: MemoryOS):
        self.memory_os = memory_os

    def record_run(
        self,
        prompt_name: str,
        prompt_version: str,
        prompt_hash: str,
        provider_id: str,
        model_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        latency_ms: int = 0,
        cost: float = 0.0,
        status: str = "success"
    ) -> bool:
        """Record a single LLM execution transaction in SQLite."""
        try:
            conn = self.memory_os.get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO memory_os_telemetry (
                        prompt_name, prompt_version, prompt_hash, provider_id, model_id,
                        input_tokens, output_tokens, cached_tokens, latency_ms, cost, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt_name,
                        prompt_version,
                        prompt_hash,
                        provider_id,
                        model_id,
                        int(input_tokens),
                        int(output_tokens),
                        int(cached_tokens),
                        int(latency_ms),
                        float(cost),
                        status
                    )
                )
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            print(f"[TelemetryRecorder] Logging failed: {e}")
            return False
