# RAG Auto-Tuning Pipeline Deployment Guide

This guide covers the deployment and configuration of the RAG auto-tuning pipeline, which handles weight calibration, A/B testing, and configuration management.

## Components

1. Weight Calibrator (`calibrator.py`)
   - Optimizes RAG weights using golden set
   - Manages versioned configurations
   - Provides A/B testing framework
   - Supports rollback functionality

2. Nightly Calibration Job (`nightly_calibration.py`)
   - Automated weight optimization
   - Safety checks and automatic rollback
   - Prometheus metrics integration

3. Golden Set (`data/golden_set.json`)
   - Curated test queries and relevant documents
   - Used for evaluating retrieval quality

## Directory Structure

```bash
/opt/astra/
├── src/astra/rag/tuning/
│   ├── calibrator.py
│   └── nightly_calibration.py
├── data/
│   └── golden_set.json
├── configs/rag/
│   └── rag_config_v*.json
└── deploy/systemd/
    ├── rag-calibration.service
    └── rag-calibration.timer
```

## Installation Steps

1. Set up directories:

   ```bash
   sudo mkdir -p /opt/astra/configs/rag
   sudo mkdir -p /var/log/rag
   sudo chown -R rag-service:rag-service /opt/astra /var/log/rag
   ```

2. Install systemd services:

   ```bash
   sudo cp deploy/systemd/rag-calibration.* /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable rag-calibration.timer
   sudo systemctl start rag-calibration.timer
   ```

3. Configure Prometheus metrics:

   ```yaml
   # /etc/prometheus/prometheus.yml
   scrape_configs:
     - job_name: 'rag'
       static_configs:
         - targets: ['localhost:9090']
   ```

## Configuration

1. Golden Set:
   - Place your golden set JSON file in `/opt/astra/data/golden_set.json`
   - Format should match the example in this repo
   - Regularly update with new queries based on user patterns

2. Calibration Settings:
   - Max versions kept: 5 by default
   - Concurrent queries: 3 by default
   - Nightly job runs at 2 AM with 30-minute random delay

3. Monitoring:
   - Key metrics available in Prometheus:
     - `rag_calibration_score`: Current nDCG@10 score
     - `rag_config_version`: Active configuration version
     - `rag_rollback_count`: Number of rollbacks performed

## Usage

1. Manual Calibration:

   ```python
   from astra.rag.tuning.calibrator import RagCalibrator
   
   calibrator = RagCalibrator(
       rag_fusion=rag_system,
       golden_set_path=Path("data/golden_set.json"),
       config_dir=Path("configs/rag")
   )
   result = await calibrator.calibrate()
   ```

2. A/B Testing:

   ```python
   test_weights = {"semantic": 0.6, "keyword": 0.4}
   control, test = await calibrator.start_ab_test(
       test_weights,
       duration_hours=24
   )
   ```

3. Manual Rollback:

   ```python
   success = await calibrator.rollback(version=5)
   ```

## Monitoring

1. Check service status:

   ```bash
   sudo systemctl status rag-calibration.timer
   sudo systemctl status rag-calibration.service
   ```

2. View logs:

   ```bash
   sudo tail -f /var/log/rag/calibration.log
   ```

3. Prometheus queries:

   ```promql
   # Current calibration score
   rate(rag_calibration_score[24h])
   
   # Rollback frequency
   rate(rag_rollback_count[7d])
   ```

## Troubleshooting

1. Calibration Failures:
   - Check logs for error messages
   - Verify golden set format and accessibility
   - Ensure sufficient permissions for config directory

2. Performance Issues:
   - Adjust concurrent_queries in calibrator
   - Check resource utilization during calibration
   - Monitor calibration duration

3. Configuration Problems:
   - Verify config file permissions
   - Check JSON format of saved configs
   - Ensure proper version numbering

## Best Practices

1. Golden Set Management:
   - Regularly update with new query patterns
   - Include diverse query types
   - Maintain high-quality relevance judgments

2. Monitoring:
   - Set up alerts for metric degradation
   - Monitor rollback frequency
   - Track calibration duration

3. Maintenance:
   - Regularly validate golden set
   - Archive old configurations
   - Review and update evaluation metrics
