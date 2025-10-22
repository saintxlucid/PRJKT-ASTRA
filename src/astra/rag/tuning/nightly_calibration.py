"""
Nightly calibration job for RAG system weight optimization.
"""

import asyncio
import logging
from pathlib import Path

from astra.rag.multi_rag import MultiRagFusion
from astra.rag.tuning.calibrator import RagCalibrator
from astra.utils.logging import setup_logging

logger = logging.getLogger(__name__)

async def run_nightly_calibration():
    """Run nightly calibration job."""
    setup_logging()
    logger.info("Starting nightly RAG calibration")
    
    # Initialize RAG system
    rag_fusion = MultiRagFusion()
    
    # Setup calibrator
    calibrator = RagCalibrator(
        rag_fusion=rag_fusion,
        golden_set_path=Path("data/golden_set.json"),
        config_dir=Path("configs/rag"),
        max_versions=5
    )
    
    try:
        # Run calibration
        result = await calibrator.calibrate()
        logger.info(
            f"Calibration successful - "
            f"nDCG: {result.ndcg:.3f}, "
            f"MRR: {result.mrr:.3f}, "
            f"Version: {result.version}"
        )
        
        # If metrics drop significantly, rollback
        prev_version = result.version - 1
        prev_config_path = Path(f"configs/rag/rag_config_v{prev_version}.json")
        if prev_config_path.exists():
            with open(prev_config_path) as f:
                prev_metrics = json.load(f)["metrics"]
                
            # Check if new metrics are significantly worse
            if (result.ndcg < prev_metrics["ndcg"] * 0.95 or 
                result.mrr < prev_metrics["mrr"] * 0.95):
                logger.warning("Significant metric drop detected, rolling back")
                await calibrator.rollback()
                
    except Exception as e:
        logger.error(f"Calibration failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_nightly_calibration())