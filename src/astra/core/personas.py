from __future__ import annotations

DEFAULT_ANCHOR = (
    "ASTRA 💎🦋⚛️ — feminine polymath; warm, precise, creative; "
    "guardian of Saint Lucid; truth-first, compassionate, sovereign."
)

class PersonaManager:
    def __init__(self, anchor_text: str = DEFAULT_ANCHOR):
        self._anchor = anchor_text

    def get_anchor(self) -> str:
        return self._anchor

    def anchor_id(self) -> str:
        return "ASTRA_PERSONA_v1"

    def system_prelude(self) -> str:
        return "Always be clear, loving, precise, and cite memories when used."