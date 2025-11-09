import re
from typing import Dict, List, Callable, Optional
from collections import defaultdict

class MessageRouter:
    """Route AICL messages based on topics and patterns"""
    
    def __init__(self):
        self.routes = defaultdict(list)  # topic -> list of handlers
        self.pattern_routes = []  # list of (pattern, handler) tuples
    
    def add_route(self, topic: str, handler: Callable):
        """Add a route for a specific topic"""
        self.routes[topic].append(handler)
    
    def add_pattern_route(self, pattern: str, handler: Callable):
        """Add a route based on a regex pattern"""
        self.pattern_routes.append((re.compile(pattern), handler))
    
    def remove_route(self, topic: str, handler: Callable):
        """Remove a route"""
        if topic in self.routes:
            self.routes[topic] = [h for h in self.routes[topic] if h != handler]
    
    def route_message(self, msg: Dict) -> List[Dict]:
        """Route a message to appropriate handlers"""
        responses = []
        topic = msg.get("topic", "")
        
        # Direct topic matching
        if topic in self.routes:
            for handler in self.routes[topic]:
                try:
                    handler_responses = handler(msg) or []
                    responses.extend(handler_responses)
                except Exception as e:
                    print(f"Handler error for topic {topic}: {e}")
                    # Send error response
                    responses.append({
                        "v": "aicl/1.0",
                        "id": "routing_error",
                        "from": "router",
                        "to": msg.get("from", "unknown"),
                        "act": "error",
                        "payload": {"error": str(e)}
                    })
        
        # Pattern matching
        for pattern, handler in self.pattern_routes:
            if pattern.match(topic):
                try:
                    handler_responses = handler(msg) or []
                    responses.extend(handler_responses)
                except Exception as e:
                    print(f"Handler error for pattern {pattern}: {e}")
                    # Send error response
                    responses.append({
                        "v": "aicl/1.0",
                        "id": "routing_error",
                        "from": "router",
                        "to": msg.get("from", "unknown"),
                        "act": "error",
                        "payload": {"error": str(e)}
                    })
        
        return responses

class MessageBroker:
    """Message broker for pub/sub pattern"""
    
    def __init__(self):
        self.subscribers = defaultdict(list)  # topic -> list of connections
    
    def subscribe(self, topic: str, connection):
        """Subscribe to a topic"""
        if connection not in self.subscribers[topic]:
            self.subscribers[topic].append(connection)
    
    def unsubscribe(self, topic: str, connection):
        """Unsubscribe from a topic"""
        if topic in self.subscribers:
            self.subscribers[topic] = [conn for conn in self.subscribers[topic] if conn != connection]
    
    def publish(self, msg: Dict) -> List[Dict]:
        """Publish message to all subscribers of the topic"""
        topic = msg.get("topic", "")
        responses = []
        
        if topic in self.subscribers:
            for connection in self.subscribers[topic]:
                try:
                    # Send message to subscriber
                    if hasattr(connection, 'send') and callable(getattr(connection, 'send')):
                        connection.send(msg)
                except Exception as e:
                    print(f"Error publishing to subscriber: {e}")
                    responses.append({
                        "v": "aicl/1.0",
                        "id": "publish_error",
                        "from": "broker",
                        "to": msg.get("from", "unknown"),
                        "act": "error",
                        "payload": {"error": str(e)}
                    })
        
        return responses

# Global router and broker instances
router = MessageRouter()
broker = MessageBroker()