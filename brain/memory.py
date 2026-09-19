"""
Experience Memory Layer for Jev AI (jevai.org / TypeSafe AI System).
Persists lessons learned, post-mortem trade reflections, and adaptive risk metrics.
Includes 2-Strike Mistake Filter: only patterns confirmed by 2+ occurrences are promoted to memory.
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
            "pending_mistakes": {},
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
                if "pending_mistakes" not in data:
                    data["pending_mistakes"] = {}
                self.memory = data
            except Exception as e:
                print(f"[ExperienceMemory] Error loading memory: {e}")

    def save(self):
        """Save memory state to disk atomically."""
        try:
            self.file_path.write_text(json.dumps(self.memory, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[ExperienceMemory] Error saving memory: {e}")

    def clear_memory(self):
        """Reset and wipe all memory clean."""
        self.memory = {
            "lessons": [],
            "pending_mistakes": {},
            "stats": {
                "total_closed_trades": 0,
                "wins": 0,
                "losses": 0,
                "consecutive_losses": 0,
                "consecutive_wins": 0,
                "total_realized_pnl": 0.0
            }
        }
        self.save()
        print("[ExperienceMemory] Đã xóa trắng toàn bộ bộ nhớ và kinh nghiệm.")

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
        Records trade outcome. Implements 2-Strike Rule:
        Only saves mistake into official lessons if the SAME error category occurs 2 times!
        """
        is_win = pnl >= 0
        stats = self.memory["stats"]
        stats["total_closed_trades"] += 1
        stats["total_realized_pnl"] = round(stats["total_realized_pnl"] + pnl, 2)

        if "pending_mistakes" not in self.memory:
            self.memory["pending_mistakes"] = {}

        if is_win:
            stats["wins"] += 1
            stats["consecutive_wins"] += 1
            stats["consecutive_losses"] = 0
            
            # Record winning trade memory if significant
            self.save()
            return {
                "trade_id": trade_id,
                "promoted": False,
                "is_win": True,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "lesson": lesson,
                "status_msg": "Lệnh thắng ghi nhận vào thống kê."
            }

        # Losing Trade Processing (2-Strike Mistake Filter)
        stats["losses"] += 1
        stats["consecutive_losses"] += 1
        stats["consecutive_wins"] = 0

        category = mistake_category or "STOP_LOSS_TRIGGER"
        pending = self.memory["pending_mistakes"]
        prev_data = pending.get(category, {})
        current_strikes = prev_data.get("count", 0) + 1

        pending[category] = {
            "count": current_strikes,
            "last_trade_id": trade_id,
            "last_pnl_pct": round(pnl_pct, 2),
            "last_timestamp": int(time.time() * 1000),
            "last_lesson": lesson
        }

        # Strike 1: Only monitor, do NOT promote to long-term memory yet
        if current_strikes < 2:
            self.save()
            return {
                "trade_id": trade_id,
                "promoted": False,
                "strike": 1,
                "is_win": False,
                "category": category,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "lesson": lesson,
                "status_msg": f"Theo dõi lỗi '{category}' (Lần 1) - Chưa lưu vào bộ nhớ chính thức, chờ xác nhận lần 2."
            }

        # Strike 2: Pattern confirmed! Promote to official long-term memory lessons
        reinforced_lesson = f"[XÁC NHẬN LỖI LẶP LẠI (2 LẦN)]: {lesson}"
        reflection_entry = {
            "trade_id": trade_id,
            "timestamp": int(time.time() * 1000),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "is_win": False,
            "category": category,
            "lesson": reinforced_lesson,
            "strikes": current_strikes,
            "promoted": True,
            "status_msg": f"Xác nhận mẫu hình lỗi '{category}' xuất hiện 2 lần. Đã chính thức lưu vào bộ nhớ Jev AI!"
        }

        self.memory["lessons"].insert(0, reflection_entry)
        if len(self.memory["lessons"]) > 25:
            self.memory["lessons"].pop()

        # Reset pending counter for this category
        pending[category]["count"] = 0
        self.save()
        return reflection_entry

    def get_recent_lessons_prompt(self, limit: int = 4) -> str:
        """
        Formats confirmed lessons into a structured prompt block for Jev AI in-context state.
        """
        lessons = self.memory.get("lessons", [])
        if not lessons:
            return "Chưa có bài học sai lầm lặp lại nào được xác nhận. Hãy duy trì kỷ luật phân tích kỹ thuật chuẩn xác."

        lines = []
        for l in lessons[:limit]:
            lines.append(f"- [THUA {l['pnl_pct']:+.2f}%]: {l['lesson']}")

        consecutive_losses = self.memory["stats"].get("consecutive_losses", 0)
        if consecutive_losses >= 2:
            lines.append(
                f"⚠️ CẢNH BÁO: Đang có {consecutive_losses} lệnh thua liên tiếp. "
                f"Hãy đặc biệt thận trọng, chỉ mở lệnh khi độ tin cậy cực cao và tín hiệu xác nhận rõ ràng!"
            )

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistics, confirmed lessons, and pending mistake monitors."""
        pending_list = []
        for cat, data in self.memory.get("pending_mistakes", {}).items():
            if data.get("count", 0) > 0:
                pending_list.append({
                    "category": cat,
                    "count": data["count"],
                    "last_lesson": data.get("last_lesson", "")
                })

        return {
            "stats": self.memory.get("stats", {}),
            "recent_lessons": self.memory.get("lessons", [])[:6],
            "pending_mistakes": pending_list
        }

memory_store = ExperienceMemory()
