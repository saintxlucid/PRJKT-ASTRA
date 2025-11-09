import pytest
from astra.core.personas import PersonaManager, DEFAULT_ANCHOR

def test_persona_manager_default():
    """Test PersonaManager with default settings"""
    manager = PersonaManager()
    assert manager.get_anchor() == DEFAULT_ANCHOR
    assert manager.anchor_id() == "ASTRA_PERSONA_v1"
    assert "clear" in manager.system_prelude()
    assert "loving" in manager.system_prelude()
    assert "precise" in manager.system_prelude()

def test_persona_manager_custom_anchor():
    """Test PersonaManager with custom anchor text"""
    custom_anchor = "Custom ASTRA Persona"
    manager = PersonaManager(anchor_text=custom_anchor)
    assert manager.get_anchor() == custom_anchor
    assert manager.anchor_id() == "ASTRA_PERSONA_v1"  # ID remains constant
    assert "clear" in manager.system_prelude()  # Prelude remains constant