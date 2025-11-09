# Python
import os
import logging
import json
import uuid
import time
import traceback
from locust import HttpUser, task, between, events
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger('locust_load_test')

# Load environment variables from .env file if present
load_dotenv()

# Load test configuration with failsafe defaults
TEST_CONFIG = {
    # Load test parameters
    'USERS': int(os.getenv('VIRTUAL_USERS', '10')),
    'SPAWN_RATE': int(os.getenv('SPAWN_RATE', '2')),
    'TEST_TIME': int(os.getenv('TEST_TIME', '60')),
    'TARGET_HOST': os.getenv('TARGET_HOST', 'http://localhost:8001'),
    
    # Connection settings
    'CONNECTION_TIMEOUT': int(os.getenv('CONNECTION_TIMEOUT', '30')),
    'MAX_RETRIES': int(os.getenv('MAX_RETRIES', '3')),
    'RETRY_DELAY': float(os.getenv('RETRY_DELAY', '0.1')),
    
    # Debug options
    'DEBUG': os.getenv('DEBUG', 'false').lower() == 'true',
    'ENABLE_LOGGING': os.getenv('ENABLE_LOGGING', 'false').lower() == 'true',
    
    # SLO thresholds
    'SLO_LATENCY_P95': float(os.getenv('SLO_LATENCY_P95', '2.5')),  # 2.5s for CPU
    'SLO_FIRST_TOKEN': float(os.getenv('SLO_FIRST_TOKEN', '0.9')),  # 900ms for CPU
    'SLO_ERROR_RATE': float(os.getenv('SLO_ERROR_RATE', '0.02')),  # 2% error rate
    'SLO_AVAILABILITY': float(os.getenv('SLO_AVAILABILITY', '0.995')),  # 99.5% monthly
    'SLO_SHUTDOWN_TIME': float(os.getenv('SLO_SHUTDOWN_TIME', '10.0')),  # 10s graceful shutdown
    
    # Test execution
    'RAMP_TIME': int(os.getenv('RAMP_TIME', '30')),  # 30s ramp-up
    'STEADY_TIME': int(os.getenv('STEADY_TIME', '300')),  # 5m steady state
    'MEASURE_LATENCY': os.getenv('MEASURE_LATENCY', 'true').lower() == 'true',
    
    # Circuit breaker test
    'CIRCUIT_BREAKER_TEST': os.getenv('CIRCUIT_BREAKER_TEST', 'false').lower() == 'true',
    'CIRCUIT_BREAKER_THRESHOLD': int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5')),
    
    # Backpressure test
    'BACKPRESSURE_TEST': os.getenv('BACKPRESSURE_TEST', 'false').lower() == 'true',
    'MAX_QUEUE_DEPTH': int(os.getenv('MAX_QUEUE_DEPTH', '100'))
}

# Test questions for variation
TEST_QUESTIONS = [
    "What is ASTRA?",
    "How do you handle backpressure?",
    "Tell me about circuit breakers",
    "What RAG fusion methods do you use?",
    "Explain your architecture",
    "How do you ensure response quality?",
    "What metrics do you track?",
    "How do you handle errors?",
    "Describe your caching strategy",
    "What's your deployment process?"
]

class CircuitBreakerTest(HttpUser):
    """Test circuit breaker behavior by generating errors"""
    wait_time = between(0.1, 0.3)  # Fast requests to trigger breaker
    host = TEST_CONFIG['TARGET_HOST']
    weight = 1  # Lower weight than normal users
    
    def on_start(self):
        if not TEST_CONFIG['CIRCUIT_BREAKER_TEST']:
            logger.info("Circuit breaker test disabled")
            self.environment.runner.quit()
            return
    
    @task
    def trigger_circuit_breaker(self):
        """Send malformed requests to trigger errors"""
        # Send invalid query to trigger errors
        headers = {"Content-Type": "application/json"}
        data = {"invalid": "data"}
        
        with self.client.post(
            url="/answer",
            json=data,
            headers=headers,
            name="[Circuit] Error Trigger",
            catch_response=True
        ) as response:
            if response.status_code in [400, 422]:
                # Expected validation error
                response.success()
            elif response.status_code == 503:
                # Circuit breaker triggered
                logger.info("Circuit breaker activated")
                response.success()
                time.sleep(5)  # Wait for potential reset
            else:
                response.failure(f"Unexpected status: {response.status_code}")

class ApiUser(HttpUser):
    """API test user class with optimized settings"""
    wait_time = between(0.5, 2)  # Shorter wait times for better throughput
    host = TEST_CONFIG['TARGET_HOST']
    timeout_duration = TEST_CONFIG['CONNECTION_TIMEOUT']
    max_retries = TEST_CONFIG['MAX_RETRIES']
    retry_delay = TEST_CONFIG['RETRY_DELAY']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize instance variables
        self.metrics = {
            'requests': 0,
            'failures': 0,
            'response_times': [],
            'endpoints': {}
        }
        self.metrics_last_time = time.time()
        self.start_time = 0.0

    def setup(self):
        """Called when load test starts"""
        # Configure logging based on TEST_CONFIG
        log_level = logging.DEBUG if TEST_CONFIG['ENABLE_LOGGING'] else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.setLevel(log_level)
        
        logger.info(f"Starting load test with configuration: {TEST_CONFIG}")
            
    def on_start(self):
        """Called when a virtual user starts"""
        # Set initial timing
        self.start_time = time.time()
        self._init_metrics()

    @task(3)
    def test_answer_endpoint(self):
        """Test the /answer endpoint with a variety of questions"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Sample questions to test with
        questions = [
            "What is ASTRA?",
            "How does RAG fusion work?",
            "What are the key components?",
            "Tell me about the system architecture",
        ]
        
        question = TEST_QUESTIONS[int(str(uuid.uuid4().int)[-2:]) % len(TEST_QUESTIONS)]
        data = {"query": question}
        
        if TEST_CONFIG['ENABLE_LOGGING']:
            logger.info(f"Sending POST /answer request: {question}")
            
        with self.client.post(
            url="/answer",
            json=data,
            headers=headers,
            name="POST /answer",
            catch_response=True,
            timeout=self.timeout_duration
        ) as response:
            response_time = response.elapsed.total_seconds() * 1000  # Convert to ms
            
            if response.status_code == 200:
                # Track success metrics
                self.track_success(response_time, "POST /answer")
                response.success()
                if TEST_CONFIG['ENABLE_LOGGING']:
                    logger.info(f"POST /answer succeeded: {response.json()}")
            else:
                # Track failure metrics
                self.track_failure("POST /answer")
                msg = f"POST /answer failed with status {response.status_code}, response: {response.text}"
                response.failure(msg)
                if TEST_CONFIG['ENABLE_LOGGING']:
                    logger.error(msg)
                    logger.error(f"Request URL: {response.url}")
                    logger.error(f"Request Headers: {headers}")
                    logger.error(f"Request Data: {data}")

    @task(1)
    def test_streaming_endpoint(self):
        """Test the /answer/stream endpoint"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        # Sample question
        question = TEST_QUESTIONS[int(str(uuid.uuid4().int)[-2:]) % len(TEST_QUESTIONS)]
        data = {"query": question}
        
        if TEST_CONFIG['ENABLE_LOGGING']:
            print(f"[Locust] Sending POST /answer/stream request: {question}")
            
        try:
            with self.client.post(
                url="/answer/stream",
                json=data,
                headers=headers,
                name="POST /answer/stream",
                catch_response=True,
                stream=True,
                timeout=self.timeout_duration
            ) as response:
                # Start timing
                start_time = time.time()
                
                if response.status_code == 200:
                    try:
                        # Process SSE stream
                        chunks = 0
                        chunk_data = []
                        for line in response.iter_lines():
                            if not line:
                                continue
                            try:
                                decoded_line = line.decode('utf-8')
                                if decoded_line.startswith('data: '):
                                    event_data = decoded_line[6:]  # Skip 'data: ' prefix
                                    event_json = json.loads(event_data)
                                    chunks += 1
                                    chunk_data.append(event_json)
                                    
                                    if TEST_CONFIG['ENABLE_LOGGING']:
                                        print(f"[Locust] Stream chunk {chunks}: {event_json}")
                                    
                                    # Check for error events
                                    if 'error' in event_json:
                                        raise Exception(f"Server reported error: {event_json['error']}")
                                        
                            except json.JSONDecodeError:
                                if TEST_CONFIG['ENABLE_LOGGING']:
                                    logger.error(f"Failed to decode JSON from chunk: {decoded_line}")
                                continue
                            except Exception as chunk_error:
                                logger.error(f"Error processing chunk: {str(chunk_error)}")
                                raise
                        
                        # Record success metrics
                        response_time = (time.time() - start_time) * 1000  # Convert to ms
                        self.track_success(response_time, "POST /answer/stream")
                        
                        response.success()
                        if TEST_CONFIG['ENABLE_LOGGING']:
                            logger.info(f"Stream completed successfully with {chunks} chunks")
                    
                    except Exception as stream_error:
                        msg = f"Stream processing error: {str(stream_error)}"
                        self.track_failure("POST /answer/stream")
                        response.failure(msg)
                        if TEST_CONFIG['ENABLE_LOGGING']:
                            logger.error(msg)
                else:
                    # Record failure metrics
                    self.track_failure("POST /answer/stream")
                    msg = f"Stream request failed with status {response.status_code}"
                    response.failure(msg)
                    if TEST_CONFIG['ENABLE_LOGGING']:
                        logger.error(msg)
                        logger.error(f"Response: {response.text}")
        except Exception as e:
            self.track_failure("POST /answer/stream")
            msg = f"Request error: {str(e)}"
            if TEST_CONFIG['ENABLE_LOGGING']:
                logger.error(msg)
                    
    @task(2)
    def test_health_endpoints(self):
        """Test all health check endpoints"""
        headers = {"Accept": "application/json"}
        
        # Test live endpoint
        with self.client.get(
            url="/live",
            headers=headers,
            name="GET /live",
            catch_response=True
        ) as response:
            response_time = response.elapsed.total_seconds() * 1000
            if response.status_code == 200:
                self.track_success(response_time, "GET /live")
                response.success()
            else:
                self.track_failure("GET /live")
                response.failure(f"Live check failed: {response.status_code}")

        # Test ready endpoint
        with self.client.get(
            url="/ready",
            headers=headers,
            name="GET /ready",
            catch_response=True
        ) as response:
            response_time = response.elapsed.total_seconds() * 1000
            if response.status_code in [200, 503]:  # Allow both ready and draining states
                self.track_success(response_time, "GET /ready")
                response.success()
            else:
                self.track_failure("GET /ready")
                response.failure(f"Ready check failed: {response.status_code}")

        # Test full health check
        with self.client.get(
            url="/health/full",
            headers=headers,
            name="GET /health/full",
            catch_response=True
        ) as response:
            response_time = response.elapsed.total_seconds() * 1000
            if response.status_code == 200:
                health = response.json()
                self.track_success(response_time, "GET /health/full")
                
                # Check queue depth
                queue_depth = health.get('metrics', {}).get('queue_depth', 0)
                if queue_depth >= TEST_CONFIG['MAX_QUEUE_DEPTH']:
                    logger.warning(f"High queue depth detected: {queue_depth}")
                
                # Check component health
                components = health.get('components', {})
                for component, status in components.items():
                    if status.get('status') != 'healthy':
                        logger.warning(f"Unhealthy component detected: {component}")
                
                response.success()
            else:
                self.track_failure("GET /health/full")
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def test_graceful_shutdown(self):
        """Test graceful shutdown via drain endpoint"""
        if not TEST_CONFIG.get('TEST_DRAIN', False):
            return
            
        headers = {"Accept": "application/json"}
        
        # Initiate drain
        with self.client.post(
            url="/drain",
            headers=headers,
            name="POST /drain",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                drain_start = time.time()
                data = response.json()
                initial_queue = data.get('queue_depth', 0)
                
                # Monitor drain progress
                max_wait = TEST_CONFIG['SLO_SHUTDOWN_TIME']
                while time.time() - drain_start < max_wait:
                    with self.client.get("/health/full") as health_response:
                        if health_response.status_code == 200:
                            health = health_response.json()
                            current_queue = health.get('metrics', {}).get('queue_depth', 0)
                            
                            if current_queue == 0:
                                # Drain complete
                                drain_time = time.time() - drain_start
                                logger.info(f"Drain completed in {drain_time:.1f}s")
                                if drain_time <= TEST_CONFIG['SLO_SHUTDOWN_TIME']:
                                    response.success()
                                else:
                                    response.failure(f"Drain took too long: {drain_time:.1f}s")
                                return
                    
                    time.sleep(0.5)
                    
                response.failure(f"Drain did not complete within {max_wait}s")

    def _init_metrics(self):
        """Initialize metrics for this user"""
        self.metrics = {
            'requests': 0,
            'failures': 0,
            'response_times': [],
            'endpoints': {}
        }
        self.metrics_last_time = time.time()

    def track_success(self, response_time, endpoint):
        """Track successful request metrics"""
        self.metrics['requests'] += 1
        self.metrics['response_times'].append(response_time)
        self.metrics['endpoints'][endpoint] = self.metrics['endpoints'].get(endpoint, {
            'requests': 0,
            'failures': 0,
            'response_times': []
        })
        self.metrics['endpoints'][endpoint]['requests'] += 1
        self.metrics['endpoints'][endpoint]['response_times'].append(response_time)
        
    def track_failure(self, endpoint):
        """Track failed request metrics"""
        self.metrics['failures'] += 1
        self.metrics['endpoints'][endpoint] = self.metrics['endpoints'].get(endpoint, {
            'requests': 0,
            'failures': 0,
            'response_times': []
        })
        self.metrics['endpoints'][endpoint]['failures'] += 1

    def on_stop(self):
        """Print final metrics report"""
        # Calculate test duration
        duration = time.time() - self.start_time
        
        # Calculate overall metrics
        avg_response_time = sum(self.metrics['response_times']) / len(self.metrics['response_times']) if self.metrics['response_times'] else 0
        success_rate = ((self.metrics['requests'] - self.metrics['failures']) / self.metrics['requests'] * 100) if self.metrics['requests'] else 0
        
        print("\n=== Load Test Results ===")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total Requests: {self.metrics['requests']}")
        print(f"Failed Requests: {self.metrics['failures']}")
        print(f"Average Response Time: {avg_response_time:.2f} ms")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Print per-endpoint metrics
        print("\nEndpoint Metrics:")
        for endpoint, stats in self.metrics['endpoints'].items():
            endpoint_avg_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
            endpoint_success = ((stats['requests'] - stats['failures']) / stats['requests'] * 100) if stats['requests'] else 0
            print(f"\n{endpoint}:")
            print(f"  Requests: {stats['requests']}")
            print(f"  Failures: {stats['failures']}")
            print(f"  Avg Response Time: {endpoint_avg_time:.2f} ms")
            print(f"  Success Rate: {endpoint_success:.1f}%")
        
        # Check against thresholds
        print("\nThreshold Checks:")
        if success_rate < 95:
            print("[WARNING] Overall success rate below 95%")
        if avg_response_time > 3000:
            print("[WARNING] Overall average response time above 3 seconds")
            
        # Per-endpoint threshold checks
        for endpoint, stats in self.metrics['endpoints'].items():
            endpoint_avg_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
            endpoint_success = ((stats['requests'] - stats['failures']) / stats['requests'] * 100) if stats['requests'] else 0
            
            if endpoint_success < 95:
                print(f"[WARNING] {endpoint} success rate below 95%")
            if endpoint_avg_time > 3000:
                print(f"[WARNING] {endpoint} average response time above 3 seconds")
        
        print("=======================")

# To run:
# locust -f locustfile.py -u 10 -r 2 --run-time 1m