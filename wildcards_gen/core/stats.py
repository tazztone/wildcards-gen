import json
import time
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field

@dataclass
class StatsEvent:
    timestamp: float
    event_type: str
    context: Optional[str]
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

class StatsCollector:
    """
    Collects structured metrics and events during skeleton generation.
    """
    def __init__(self):
        self.start_time = time.time()
        self.events: List[StatsEvent] = []
        self.metadata: Dict[str, Any] = {}

    def log_event(self, event_type: str, message: str, context: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Record a structured event."""
        event = StatsEvent(
            timestamp=time.time() - self.start_time,
            event_type=event_type,
            context=context,
            message=message,
            data=data or {}
        )
        self.events.append(event)

    def set_metadata(self, key: str, value: Any):
        """Set execution metadata (e.g., config parameters)."""
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert all stats to a serializable dictionary."""
        return {
            "execution": {
                "duration_seconds": round(time.time() - self.start_time, 2),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "metadata": self.metadata,
            "events": [asdict(e) for e in self.events]
        }

    def save_to_json(self, path: str):
        """Save structured stats to a JSON file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Failed to save stats JSON: {e}")

    def save_summary_log(self, path: str):
        """Save a human-readable summary log."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"Generation Summary - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                
                # Grouped by type for readability
                arrangements = [e for e in self.events if e.event_type == "arrangement"]
                if arrangements:
                    f.write(f"--- Semantic Arrangements ({len(arrangements)}) ---\n")
                    for e in arrangements:
                        ctx_str = f" '{e.context}'" if e.context else ""
                        f.write(f"[{e.timestamp:6.2f}s] {e.message}{ctx_str}\n")
                        if e.data:
                            # Reformat/Clean repeated text
                            details = []
                            if 'items' in e.data: details.append(f"{e.data['items']} items")
                            if 'clusters' in e.data: details.append(f"{e.data['clusters']} groups")
                            if 'noise' in e.data: details.append(f"noise: {e.data['noise']:.1%}")
                            if details:
                                f.write(f"           ({', '.join(details)})\n")
                    f.write("\n")

                other_events = [e for e in self.events if e.event_type != "arrangement"]
                if other_events:
                    f.write("--- Other Events ---\n")
                    for e in other_events:
                        f.write(f"[{e.timestamp:6.2f}s] {e.event_type.upper()}: {e.message}\n")
                    f.write("\n")

                f.write(f"Total Duration: {time.time() - self.start_time:.2f}s\n")
        except Exception as e:
            print(f"Failed to save summary log: {e}")
