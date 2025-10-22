"""
Dashboard for visualizing RAG evaluation results.

Provides:
- Metric trends over time
- Query-level analysis
- System performance insights
"""
from typing import List, Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from pathlib import Path

def load_eval_runs(eval_dir: str) -> List[Dict[str, Any]]:
    """Load evaluation run data."""
    eval_path = Path(eval_dir)
    if not eval_path.exists():
        return []
        
    runs = []
    for file in eval_path.glob("eval_run_*.json"):
        try:
            with open(file) as f:
                runs.append(json.load(f))
        except Exception:
            continue
            
    return sorted(
        runs,
        key=lambda r: r["timestamp"]
    )
    
def create_metrics_df(runs: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create DataFrame of metrics."""
    records = []
    
    for run in runs:
        timestamp = datetime.fromisoformat(run["timestamp"])
        
        for k, metrics in run["metrics"].items():
            record = {
                "run_id": run["run_id"],
                "timestamp": timestamp,
                "k": k
            }
            record.update(metrics)
            records.append(record)
            
    return pd.DataFrame(records)
    
def plot_metric_trends(df: pd.DataFrame) -> None:
    """Plot metric trends over time."""
    # Reshape for plotting
    df_melted = df.melt(
        id_vars=["timestamp", "k"],
        value_vars=["ndcg@5", "ndcg@10", "hit@5", "hit@10", "diversity"],
        var_name="metric",
        value_name="value"
    )
    
    # Create line plot
    fig = px.line(
        df_melted,
        x="timestamp",
        y="value",
        color="metric",
        title="Metric Trends Over Time",
        labels={
            "timestamp": "Time",
            "value": "Score",
            "metric": "Metric"
        }
    )
    
    st.plotly_chart(fig)
    
def plot_query_performance(runs: List[Dict[str, Any]]) -> None:
    """Plot query-level performance."""
    # Get latest run
    if not runs:
        return
        
    latest_run = runs[-1]
    results = latest_run["results"]
    
    # Calculate per-query metrics
    query_metrics = []
    for result in results:
        actual_ids = [r.get("id", "") for r in result["actual_results"]]
        relevance = [
            1 if doc_id in result["expected_doc_ids"] else 0
            for doc_id in actual_ids
        ]
        
        query_metrics.append({
            "query": result["query"][:50] + "...",
            "ndcg@10": EvaluationMetrics.ndcg_at_k(relevance, 10),
            "hit@5": EvaluationMetrics.hits_at_k(
                actual_ids,
                result["expected_doc_ids"],
                5
            ),
            "diversity": EvaluationMetrics.section_diversity(
                result["actual_results"][:10]
            )
        })
        
    df = pd.DataFrame(query_metrics)
    
    # Create bar plot
    fig = go.Figure()
    
    for metric in ["ndcg@10", "hit@5", "diversity"]:
        fig.add_trace(
            go.Bar(
                name=metric,
                x=df["query"],
                y=df[metric]
            )
        )
        
    fig.update_layout(
        title="Query-Level Performance",
        xaxis_title="Query",
        yaxis_title="Score",
        barmode="group"
    )
    
    st.plotly_chart(fig)
    
def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="RAG Evaluation Dashboard",
        layout="wide"
    )
    
    st.title("RAG System Evaluation")
    
    # Load evaluation data
    eval_dir = "data/eval"
    runs = load_eval_runs(eval_dir)
    
    if not runs:
        st.error("No evaluation data found")
        return
        
    # Create metrics DataFrame
    df = create_metrics_df(runs)
    
    # Show summary stats
    latest_metrics = df.iloc[-1].to_dict()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Latest nDCG@10",
            f"{latest_metrics.get('ndcg@10', 0):.3f}"
        )
        
    with col2:
        st.metric(
            "Latest Hit@5",
            f"{latest_metrics.get('hit@5', 0):.3f}"
        )
        
    with col3:
        st.metric(
            "Section Diversity",
            f"{latest_metrics.get('diversity', 0):.3f}"
        )
        
    # Plot metrics over time
    st.subheader("Metric Trends")
    plot_metric_trends(df)
    
    # Plot query performance
    st.subheader("Query Performance")
    plot_query_performance(runs)
    
    # Show raw data
    with st.expander("View Raw Data"):
        st.dataframe(df)
        
if __name__ == "__main__":
    main()