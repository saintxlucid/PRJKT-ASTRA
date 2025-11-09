"""
Generate Comprehensive Distillation Experiment Report

This script generates a comprehensive report comparing different distillation methods.
"""

import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any

def load_experiment_results(results_file: str) -> pd.DataFrame:
    """
    Load experiment results from CSV file.
    
    Args:
        results_file: Path to the results CSV file
        
    Returns:
        DataFrame with results
    """
    return pd.read_csv(results_file)

def generate_performance_comparison_plot(df: pd.DataFrame, output_file: str):
    """
    Generate performance comparison plot.
    
    Args:
        df: DataFrame with results
        output_file: Path to save the plot
    """
    # Set style
    plt.style.use('seaborn-v0_8')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create bar plot
    bars = ax.bar(df['Model'], df['Perplexity'], color='skyblue')
    
    # Customize plot
    ax.set_xlabel('Distillation Method')
    ax.set_ylabel('Perplexity (Lower is Better)')
    ax.set_title('Model Performance Comparison')
    ax.set_xticklabels(df['Model'], rotation=45, ha='right')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

def generate_detailed_report(df: pd.DataFrame, report_file: str):
    """
    Generate detailed report in Markdown format.
    
    Args:
        df: DataFrame with results
        report_file: Path to save the report
    """
    # Sort by perplexity
    df = df.sort_values('Perplexity')
    
    # Generate report
    with open(report_file, 'w') as f:
        f.write("# Distillation Experiment Report\n\n")
        
        f.write("## Summary\n\n")
        f.write("This report compares the performance of different knowledge distillation methods ")
        f.write("for training a GPT-2 student model using GPT-NeoX 20B as the teacher.\n\n")
        
        f.write("## Performance Comparison\n\n")
        f.write("| Model | Perplexity | Rank |\n")
        f.write("|-------|------------|------|\n")
        
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            f.write(f"| {row['Model']} | {row['Perplexity']:.2f} | {i} |\n")
        
        f.write("\n## Analysis\n\n")
        
        best_model = df.iloc[0]['Model']
        best_perplexity = df.iloc[0]['Perplexity']
        
        f.write(f"The best performing model was **{best_model}** with a perplexity of **{best_perplexity:.2f}**.\n\n")
        
        # Performance differences
        if len(df) > 1:
            f.write("### Performance Differences\n\n")
            for i in range(1, len(df)):
                model = df.iloc[i]['Model']
                perplexity = df.iloc[i]['Perplexity']
                diff = perplexity - best_perplexity
                f.write(f"- {model} had {diff:.2f} higher perplexity than the best model ({(diff/best_perplexity)*100:.1f}% worse)\n")
        
        f.write("\n## Recommendations\n\n")
        f.write("Based on the experimental results:\n\n")
        
        if len(df) > 1:
            f.write("1. **Best Method**: Use the {} approach for optimal performance\n".format(best_model))
            f.write("2. **Trade-offs**: Consider simpler methods if computational resources are limited\n")
            f.write("3. **Future Work**: Experiment with combining multiple distillation techniques\n")
        else:
            f.write("1. **Validation**: Run additional experiments to validate these results\n")
            f.write("2. **Expansion**: Test with larger datasets and different model configurations\n")
        
        f.write("\n## Methodology\n\n")
        f.write("All models were evaluated on the same test dataset using perplexity as the primary metric. ")
        f.write("Perplexity measures how well a language model predicts samples, with lower values indicating better performance.\n")

def main():
    parser = argparse.ArgumentParser(description="Generate Distillation Experiment Report")
    parser.add_argument("--results_file", type=str, required=True,
                        help="Path to experiment results CSV file")
    parser.add_argument("--report_file", type=str, default="distillation_report.md",
                        help="Path to save the report")
    parser.add_argument("--plot_file", type=str, default="performance_comparison.png",
                        help="Path to save the performance plot")
    
    args = parser.parse_args()
    
    # Load results
    print("Loading experiment results...")
    df = load_experiment_results(args.results_file)
    print(f"Loaded results for {len(df)} models")
    
    # Generate performance plot
    print("Generating performance comparison plot...")
    generate_performance_comparison_plot(df, args.plot_file)
    print(f"Performance plot saved to {args.plot_file}")
    
    # Generate detailed report
    print("Generating detailed report...")
    generate_detailed_report(df, args.report_file)
    print(f"Detailed report saved to {args.report_file}")
    
    print("\nReport generation completed successfully!")

if __name__ == "__main__":
    main()