"""
Experience Memory Layer for Jev AI (jevai.org / TypeSafe AI System).
Persists lessons learned, post-mortem trade reflections, and adaptive risk metrics.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class ExperienceMemory:
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_dir = Path(__file__).resolve().parent.parent / "data"
            storage_dir.mkdir(exist_ok=True)
            self.file_path = storage_dir / "memory.json"
        else:
            self.file_path = storage_path

        self.memory: Dict[str, Any] = {
            "lessons": [],
            "stats": {
                "total_closed_trades": 0,
                "wins": 0,
                "losses": 0,
                "consecutive_losses": 0,
                "consecutive_wins": 0,
                "total_realized_pnl": 0.0
            }
        }
        self.load()

    def load(self):
        """Load memory state from disk."""
        if self.file_path.exists():
            try:
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self.memory = data
            except Exception as e:
                print(f"[ExperienceMemory] Error loading memory: {e}")

    def save(self):
        """Save memory state to disk atomically."""
        try:
            self.file_path.write_text(json.dumps(self.memory, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[ExperienceMemory] Error saving memory: {e}")

    def record_trade_reflection(
        self,
        trade_id: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        lesson: str,
        mistake_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Records a post-mortem reflection into long-term memory and updates performance metrics.
        """
        is_win = pnl >= 0
        stats = self.memory["stats"]
        stats["total_closed_trades"] += 1
        stats["total_realized_pnl"] = round(stats["total_realized_pnl"] + pnl, 2)

        if is_win:
            stats["wins"] += 1
            stats["consecutive_wins"] += 1
            stats["consecutive_losses"] = 0
        else:
            stats["losses"] += 1
            stats["consecutive_losses"] += 1
            stats["consecutive_wins"] = 0

        reflection_entry = {
            "trade_id": trade_id,
            "timestamp": int(time.time() * 1000),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "is_win": is_win,
            "category": mistake_category or ("SUCCESSFUL_BREAKOUT" if is_win else "STOP_LOSS_TRIGGER"),
            "lesson": lesson
        }

        # Keep last 25 most actionable lessons
        self.memory["lessons"].insert(0, reflection_entry)
        if len(self.memory["lessons"]) > 25:
            self.memory["lessons"].pop()

        self.save()
        return reflection_entry

    def get_recent_lessons_prompt(self, limit: int = 4) -> str:
        """
        Formats recent lessons into a structured prompt block for Jev AI in-context state.
        """
        lessons = self.memory.get("lessons", [])
        if not lessons:
            return "Chưa có bài học trước đó. Hãy tiếp tục tuân thủ nghiêm ngặt quản trị rủi ro."

        lines = []
        for l in lessons[:limit]:
            status = "THẮNG (+)" if l["is_win"] else "THUA (-)"
            lines.append(f"- [{status} {l['pnl_pct']:+.2f}%]: {l['lesson']}")

        consecutive_losses = self.memory["stats"].get("consecutive_losses", 0)
        if consecutive_losses >= 2:
            lines.append(
                f"⚠️ CẢNH BÁO: Đang có {consecutive_losses} lệnh thua liên tiếp. "
                f"Hãy đặc biệt thận trọng, chỉ mở lệnh khi độ tin cậy cực cao và tín hiệu xác nhận rõ ràng!"
            )

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistics and recent lessons for dashboard presentation."""
        return {
            "stats": self.memory.get("stats", {}),
            "recent_lessons": self.memory.get("lessons", [])[:6]
        }

memory_store = ExperienceMemory()
