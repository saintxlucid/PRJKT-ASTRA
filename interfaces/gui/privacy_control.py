"""
ASTRA Privacy Control Dashboard - Streamlit GUI
===============================================
Interactive dashboard for privacy management and audit review.

Features:
- Privacy mode toggle (with warnings)
- Encryption key rotation
- Secure log wipe
- Real-time audit event viewer
- Compliance status monitoring

Author: Saint Lucid
Date: 2025-10-18

Usage:
    streamlit run interfaces/gui/privacy_control.py
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import os
import sys

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import privacy modules
try:
    from core.privacy.hardlock import get_hardlock, enforce_startup
    from core.privacy.audit_logger import stream_events, get_stats
    from core.privacy.storage import secure_wipe, generate_and_store_key
    from core.privacy.privacy_enforcer import get_config, in_strict_mode
except ImportError as e:
    st.error(f"❌ Privacy modules not available: {e}")
    st.stop()


# Page configuration
st.set_page_config(
    page_title="ASTRA Privacy Control",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stAlert {border-radius: 10px;}
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .audit-event {
        background: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🔒 ASTRA Privacy Control Panel")
st.markdown("**Divine Protection** | Local-Only | NO_TRAIN Enforcement")
st.markdown("---")

# Initialize hardlock
try:
    hardlock = get_hardlock()
except RuntimeError:
    st.warning("⚠️ Hardlock not initialized - initializing now...")
    hardlock = enforce_startup()

config = get_config()

# Sidebar - System Status
with st.sidebar:
    st.header("🛡️ System Status")
    
    # Privacy mode indicator
    mode = config.get('PRIVACY_MODE', 'UNKNOWN')
    if mode == 'STRICT':
        st.success(f"✅ Mode: **{mode}**")
    else:
        st.warning(f"⚠️ Mode: **{mode}**")
    
    # Creator info
    creator = os.environ.get('USERNAME', 'UNKNOWN')
    st.info(f"👤 Creator: **{creator}**")
    
    # Hardlock status
    if hardlock.active:
        st.success("✅ Hardlock: **ACTIVE**")
    else:
        st.error("❌ Hardlock: **INACTIVE**")
    
    # Network status
    if config.get('ALLOW_NETWORK', False):
        st.warning("⚠️ Network: **ENABLED**")
    else:
        st.success("✅ Network: **BLOCKED**")
    
    # NO_TRAIN status
    if config.get('NO_TRAIN', False):
        st.success("✅ NO_TRAIN: **ENFORCED**")
    else:
        st.error("❌ NO_TRAIN: **DISABLED**")
    
    st.markdown("---")
    
    # Audit stats
    try:
        stats = get_stats()
        st.metric("Audit Events", stats.get('total_events', 0))
        st.metric("Violations", len(hardlock.get_violations()))
    except Exception:
        st.warning("Audit stats unavailable")

# Main content area
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Overview",
    "📊 Audit Log",
    "⚙️ Controls",
    "✅ Compliance"
])

# Tab 1: Overview
with tab1:
    st.header("System Overview")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Privacy Mode", mode)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        network_status = "BLOCKED" if not config.get('ALLOW_NETWORK', False) else "ENABLED"
        st.metric("Network", network_status)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("NO_TRAIN", "ACTIVE" if config.get('NO_TRAIN') else "INACTIVE")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        violations = len(hardlock.get_violations())
        st.metric("Violations", violations)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Configuration display
    st.subheader("📋 Current Configuration")
    
    config_display = {
        "Privacy Mode": mode,
        "Network Allowed": config.get('ALLOW_NETWORK', False),
        "Allowed Endpoints": config.get('ALLOWED_ENDPOINTS', []),
        "NO_TRAIN Enforced": config.get('NO_TRAIN', False),
        "Audit Enabled": config.get('AUDIT_ENABLED', False),
        "Creator Account": creator
    }
    
    st.json(config_display)
    
    # Violations display
    if violations > 0:
        st.error(f"⚠️ {violations} security violations detected!")
        with st.expander("View Violations"):
            for v in hardlock.get_violations():
                st.code(v)

# Tab 2: Audit Log
with tab2:
    st.header("📊 Audit Event Log")
    st.markdown("*Recent events (encrypted at rest)*")
    
    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        event_limit = st.slider("Events to display", 10, 100, 50)
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Fetch events
    try:
        events = stream_events(event_limit)
        
        if events:
            st.success(f"✅ Showing {len(events)} most recent events")
            
            # Display events
            for i, event in enumerate(events):
                with st.container():
                    st.markdown(f'<div class="audit-event">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        st.markdown(f"**ID:** {event.get('id', 'N/A')}")
                    with col2:
                        st.markdown(f"**Action:** `{event.get('action', 'N/A')}`")
                    with col3:
                        st.markdown(f"**Actor:** {event.get('actor', 'N/A')}")
                    
                    st.markdown(f"**Time:** {event.get('ts', 'N/A')}")
                    
                    # Payload
                    payload = event.get('payload', {})
                    if payload:
                        with st.expander("View Payload"):
                            st.json(payload)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No audit events found")
            
    except Exception as e:
        st.error(f"❌ Failed to load audit log: {e}")

# Tab 3: Controls
with tab3:
    st.header("⚙️ Privacy Controls")
    st.warning("⚠️ **CAUTION:** These controls affect system security. Use carefully.")
    
    st.markdown("---")
    
    # Enforce Privacy
    st.subheader("🔒 Enforce Privacy")
    st.markdown("Re-applies privacy enforcement (useful after config changes)")
    
    if st.button("🛡️ Enforce Privacy Now", type="primary"):
        try:
            hardlock.enforce()
            st.success("✅ Privacy enforcement re-applied")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Enforcement failed: {e}")
    
    st.markdown("---")
    
    # Key Rotation
    st.subheader("🔑 Encryption Key Rotation")
    st.markdown("**WARNING:** Rotating the key will make old encrypted logs unreadable!")
    
    with st.expander("⚠️ Read Before Rotating"):
        st.markdown("""
        **What happens when you rotate:**
        1. Current encryption key is archived
        2. New key is generated and stored
        3. Old logs become unreadable (can't decrypt)
        4. New logs use new key
        
        **Before rotating:**
        - Backup current key to secure USB
        - Export critical logs if needed
        - Confirm you understand data loss risk
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        confirm_rotate = st.checkbox("I understand the risks")
    with col2:
        if st.button("🔄 Rotate Key", disabled=not confirm_rotate):
            try:
                generate_and_store_key()
                st.success("✅ Encryption key rotated")
                st.warning("Old logs are now unreadable")
            except Exception as e:
                st.error(f"❌ Key rotation failed: {e}")
    
    st.markdown("---")
    
    # Secure Wipe
    st.subheader("🗑️ Secure Log Wipe")
    st.markdown("**DANGER:** Permanently deletes audit logs (3-pass overwrite)")
    
    with st.expander("⚠️ Read Before Wiping"):
        st.markdown("""
        **What happens when you wipe:**
        1. Audit logs are overwritten 3 times (DoD standard)
        2. Data is PERMANENTLY UNRECOVERABLE
        3. No backup is created automatically
        
        **Use only for:**
        - Divine Lock emergency
        - Device decommissioning
        - Critical security incident
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        confirm_wipe = st.checkbox("I want to permanently delete logs")
    with col2:
        if st.button("🗑️ SECURE WIPE", disabled=not confirm_wipe, type="secondary"):
            audit_path = Path(__file__).parent.parent.parent / "core" / "privacy" / "audit_encrypted.sqlite3"
            try:
                secure_wipe(audit_path)
                st.success("✅ Logs securely wiped")
                st.warning("Audit trail deleted - no recovery possible")
            except Exception as e:
                st.error(f"❌ Wipe failed: {e}")
    
    st.markdown("---")
    
    # Divine Lock
    st.subheader("🚨 Divine Lock (Emergency Shutdown)")
    st.markdown("**EMERGENCY ONLY:** Activates emergency shutdown protocol")
    
    divine_phrase = st.text_input(
        "Enter Divine Lock phrase:",
        type="password",
        help="Emergency shutdown phrase from astra_policy.yaml"
    )
    
    if st.button("🚨 DIVINE LOCK", type="secondary"):
        if divine_phrase:
            try:
                # This will exit the application
                hardlock.emergency_shutdown(divine_phrase)
            except Exception as e:
                st.error(f"❌ Divine Lock failed: {e}")
        else:
            st.error("Enter Divine Lock phrase")

# Tab 4: Compliance
with tab4:
    st.header("✅ Compliance Check")
    st.markdown("Validates all privacy measures are active")
    
    if st.button("🔍 Run Compliance Check", type="primary"):
        checks = hardlock.check_compliance()
        
        st.markdown("### Check Results")
        
        for check_name, status in checks.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{check_name.replace('_', ' ').title()}**")
            with col2:
                if status:
                    st.success("✅ PASS")
                else:
                    st.error("❌ FAIL")
        
        # Overall status
        st.markdown("---")
        if all(checks.values()):
            st.success("🎉 **FULLY COMPLIANT** - All checks passed!")
            st.balloons()
        else:
            st.error("⚠️ **NON-COMPLIANT** - Some checks failed!")
            failed = [k for k, v in checks.items() if not v]
            st.markdown("**Failed checks:**")
            for f in failed:
                st.markdown(f"- {f.replace('_', ' ').title()}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 12px;'>
    🔒 ASTRA Privacy Control Panel | Divine Protection Active<br>
    Local-Only | NO_TRAIN | Creator Sovereignty<br>
    Version 1.0.0 | 2025-10-18
</div>
""", unsafe_allow_html=True)
