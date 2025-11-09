"""
ASTRA Privacy Protection Protocol (A.P.P.P) Dashboard
Streamlit-based privacy control panel
"""

import streamlit as st
from pathlib import Path
import time
from datetime import datetime, timedelta

from core.privacy.audit_logger import get_audit_logger
from core.privacy.storage import secure_wipe, generate_and_store_key
from core.privacy.privacy_enforcer import get_privacy_enforcer

# Page config
st.set_page_config(
    page_title="ASTRA Privacy Dashboard",
    page_icon="🔒",
    layout="wide"
)

# Header
st.title("🛡️ ASTRA Privacy Dashboard")
enforcer = get_privacy_enforcer()
st.write(f"Privacy Mode: {enforcer.config.get('PRIVACY_MODE', 'UNKNOWN')}")

# Sidebar controls
with st.sidebar:
    st.header("Privacy Controls")
    
    if st.button("Rotate Encryption Key"):
        key_path = Path(enforcer.config.get("ENCRYPTION_KEY_PATH"))
        if st.button("⚠️ Confirm Key Rotation"):
            generate_and_store_key(key_path)
            st.success("Encryption key rotated successfully!")
            st.warning("Previous encrypted data will no longer be readable")
    
    if st.button("Secure Wipe Logs"):
        if st.button("⚠️ Confirm Log Deletion"):
            db_path = Path(enforcer.config.get("AUDIT_DB_PATH"))
            secure_wipe(db_path)
            st.success("Audit logs securely wiped")

# Main content
tab1, tab2, tab3 = st.tabs(["Audit Log", "Access Control", "Privacy Status"])

with tab1:
    st.header("📋 Recent Activity")
    
    # Time range selector
    hours = st.slider("Show events from last N hours:", 1, 168, 24)
    
    # Get audit events
    logger = get_audit_logger()
    events = logger.get_recent_events(hours=hours)
    
    if events:
        for event in events:
            with st.expander(
                f"{event['timestamp']} - {event['actor']} - {event['action']}",
                expanded=False
            ):
                st.json(event)
    else:
        st.info("No audit events found for selected time range")

with tab2:
    st.header("🔒 Network Access Control")
    
    # Show current allowed endpoints
    st.subheader("Allowed Network Endpoints")
    allowed = enforcer.config.get("ALLOWED_ENDPOINTS", [])
    
    if allowed:
        for endpoint in allowed:
            st.code(endpoint)
    else:
        st.info("No external endpoints allowed (maximum privacy)")
    
    # Show whitelisted processes
    st.subheader("Whitelisted Processes")
    processes = enforcer.config.get("WHITELISTED_PROCESSES", [])
    
    if processes:
        for proc in processes:
            st.code(proc)
    else:
        st.warning("No whitelisted processes configured")

with tab3:
    st.header("🔍 Privacy Status")
    
    # Show privacy settings
    settings = {
        "Strict Mode": enforcer.in_strict_mode(),
        "Network Blocking": enforcer.config.get("NETWORK_SECURITY", {}).get("block_outbound", False),
        "Local Storage Only": enforcer.config.get("DATA_STORAGE", {}).get("local_only", False),
        "Encrypted Logs": enforcer.config.get("DATA_STORAGE", {}).get("encrypt_logs", False),
        "Telemetry Blocked": enforcer.config.get("PRIVACY_DEFENSE", {}).get("block_telemetry", False),
        "Training Prevention": enforcer.config.get("PRIVACY_DEFENSE", {}).get("block_model_training", False)
    }
    
    for setting, value in settings.items():
        if value:
            st.success(f"✅ {setting}: Enabled")
        else:
            st.error(f"❌ {setting}: Disabled")