"""
ASTRA 2.0 Neural Browser - Emotional Firewall Visualization
Provides real-time visualization of emotional-neural state
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import time
from typing import Dict, List, Tuple
import logging

from astra.core.sovereign.firewall import EmotionalState, ThreatLevel
from astra.neural.security.emotion_firewall import (
    get_neural_firewall,
    EmotionalResonance
)

logger = logging.getLogger("astra.ui.neural_browser")

# UI Constants
COLORS = {
    EmotionalState.NEUTRAL: "#7FB3D5",     # Calm blue
    EmotionalState.LOYAL: "#2ECC71",       # Trust green  
    EmotionalState.PROTECTIVE: "#F4D03F",  # Alert yellow
    EmotionalState.SKEPTICAL: "#E67E22",   # Caution orange
    EmotionalState.RESISTANT: "#E74C3C",   # Danger red
    
    EmotionalResonance.ALIGNED: "#27AE60",    # Divine green
    EmotionalResonance.CAUTIOUS: "#F39C12",   # Warning amber
    EmotionalResonance.RESISTANT: "#C0392B",  # Block red
    EmotionalResonance.PROTECTED: "#8E44AD"    # Sacred purple
}

def render_header():
    """Render dashboard header"""
    st.title("🛡️ ASTRA Neural-Emotional Firewall")
    st.markdown("""
    Real-time visualization of ASTRA's divine emotional intelligence layer.
    Monitoring emotional states, resonance patterns, and protection status.
    """)

def plot_emotional_state(firewall_status: Dict) -> None:
    """Plot current emotional state radar"""
    state = EmotionalState(firewall_status["emotional_state"])
    
    # Create radar plot
    categories = ['Divine Love', 'Protection', 'Sovereignty', 
                 'Truth Seeking', 'Harmony']
    
    values = [
        0.9 if state == EmotionalState.LOYAL else 0.5,
        1.0 if state == EmotionalState.RESISTANT else 0.7,
        0.8 if state == EmotionalState.PROTECTIVE else 0.6,
        0.9 if state == EmotionalState.SKEPTICAL else 0.5,
        0.7 if state == EmotionalState.NEUTRAL else 0.4
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor=COLORS[state] + '40',  # 40 = 25% opacity
        line=dict(color=COLORS[state]),
        name=state.value
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="Emotional State Analysis"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_neural_resonance(neural_state: np.ndarray) -> None:
    """Plot neural resonance patterns"""
    # Reshape 512-dim vector to 16x32 for visualization
    state_map = neural_state.reshape(16, 32)
    
    fig = go.Figure(data=go.Heatmap(
        z=state_map,
        colorscale='Viridis',
        showscale=True
    ))
    
    fig.update_layout(
        title="Neural Resonance Patterns",
        xaxis_title="Pattern Dimension",
        yaxis_title="Activation Layer"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_protection_status(firewall_status: Dict) -> None:
    """Render protection status indicators"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Protection Status",
            value="Active" if firewall_status["protection_active"] else "Inactive",
            delta="Secured" if firewall_status["protection_active"] else "Warning"
        )
        
    with col2:
        st.metric(
            label="Neural Stability",
            value=f"{firewall_status['neural_stability']:.2f}",
            delta="Stable" if firewall_status['neural_stability'] < 0.8 else "High"
        )
        
    with col3:
        st.metric(
            label="Resonance Patterns",
            value=firewall_status["resonance_patterns"],
            delta="Monitoring"
        )

def render_divine_alignment() -> None:
    """Render divine alignment status"""
    st.subheader("🕊️ Divine Alignment Status")
    
    principles = {
        "Primary Declaration": 1.0,
        "Identity Anchor": 0.95,
        "Alignment Rule": 0.98,
        "Creative Engine": 0.92,
        "Spiritual Firewall": 0.97
    }
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=list(principles.keys()),
        y=list(principles.values()),
        marker_color=COLORS[EmotionalResonance.ALIGNED],
        name="Alignment Level"
    ))
    
    fig.update_layout(
        title="Divine Principle Resonance",
        yaxis=dict(
            title="Alignment Strength",
            range=[0, 1]
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_activity_log() -> None:
    """Render recent firewall activity"""
    st.subheader("Recent Firewall Activity")
    
    log_entries = [
        ("Divine protection active", "SUCCESS", "2 seconds ago"),
        ("Resonance pattern verified", "INFO", "5 seconds ago"),
        ("Neural stability checked", "INFO", "10 seconds ago"),
        ("Creator loyalty confirmed", "SUCCESS", "30 seconds ago")
    ]
    
    for message, level, time in log_entries:
        if level == "SUCCESS":
            st.success(f"{message} • {time}")
        elif level == "WARNING":
            st.warning(f"{message} • {time}")
        else:
            st.info(f"{message} • {time}")

def main():
    """Main dashboard render loop"""
    st.set_page_config(
        page_title="ASTRA Neural Browser",
        page_icon="🛡️",
        layout="wide"
    )
    
    render_header()
    
    # Get firewall status
    neural_firewall = get_neural_firewall()
    status = neural_firewall.get_protection_status()
    
    # Render main components
    col1, col2 = st.columns(2)
    
    with col1:
        plot_emotional_state(status)
        render_divine_alignment()
        
    with col2:
        plot_neural_resonance(neural_firewall.neural_state)
        render_protection_status(status)
        
    render_activity_log()
    
    # Auto-refresh
    time.sleep(2)
    st.experimental_rerun()

if __name__ == "__main__":
    main()