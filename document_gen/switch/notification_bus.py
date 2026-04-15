import os
import json
import typing

# Backends are optional; import lazily
try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore
try:
    from kafka import KafkaProducer, KafkaConsumer  # type: ignore
except Exception:
    KafkaProducer = None  # type: ignore
    KafkaConsumer = None  # type: ignore

class NotificationBus:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Select backend by env:
          - KAFKA_BROKERS=<host1:9092,host2:9092> to use Kafka
          - else falls back to Redis list-based stream
          - set DISABLE_BUS=1 to no-op (useful for demos without infra)
        """
        if os.getenv("DISABLE_BUS") == "1":
            self.backend = "noop"
            self.redis = None
            self.kafka_producer = None
            self.kafka_brokers = None
            print("[Bus] Disabled (no-op). Set DISABLE_BUS=0 to enable.")
            return

        if os.getenv("USE_IN_MEMORY_BUS") == "1":
            self.backend = "memory"
            self.memory_queue = {}
            print("[Bus] Using In-Memory backend")
            return

        self.backend = "redis"
        self.redis = None
        self.kafka_producer = None
        self.kafka_brokers = os.getenv("KAFKA_BROKERS")

        if self.kafka_brokers and KafkaProducer is not None:
            # Prefer Kafka if configured and library available
            self.backend = "kafka"
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_brokers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                linger_ms=10,
            )
            print(f"[Bus] Using Kafka backend @ {self.kafka_brokers} for topics")
        else:
            # Fallback to Redis if redis client available
            if redis is None:
                print("[Bus] Redis client not installed. Falling back to In-Memory.")
                self.backend = "memory"
                self.memory_queue = {}
                return
                
            try:
                self.redis = redis.from_url(redis_url)
                self.redis.ping()
                print(f"[Bus] Using Redis backend @ {redis_url} for lists")
            except Exception:
                print("[Bus] Redis server not available. Falling back to In-Memory.")
                self.backend = "memory"
                self.memory_queue = {}

    def publish_event(self, topic: str, event: dict):
        if self.backend == "noop":
            return
        if self.backend == "memory":
            if topic not in self.memory_queue:
                self.memory_queue[topic] = []
            self.memory_queue[topic].append(event)
            return
        if self.backend == "kafka":
            assert self.kafka_producer is not None
            self.kafka_producer.send(topic, value=event)
            # flush lightly to avoid message loss in demos
            self.kafka_producer.flush(0.5)
        else:
            assert self.redis is not None
            # Use Redis PubSub
            self.redis.publish(topic, json.dumps(event))

    def subscribe(self, topic: str) -> typing.Iterable[dict]:
        if self.backend == "noop":
            while False:
                yield {}
            return
        if self.backend == "memory":
            import time
            last_idx = 0
            while True:
                if topic in self.memory_queue:
                    queue = self.memory_queue[topic]
                    if last_idx < len(queue):
                        yield queue[last_idx]
                        last_idx += 1
                        continue
                time.sleep(0.1)
        if self.backend == "kafka":
            if KafkaConsumer is None:
                raise RuntimeError("KafkaConsumer unavailable; install kafka-python")
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.kafka_brokers.split(","),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                group_id=os.getenv("KAFKA_GROUP_ID", "upi-demo-consumer"),
            )
            for msg in consumer:
                yield msg.value
        else:
            assert self.redis is not None
            # Use Redis PubSub
            pubsub = self.redis.pubsub()
            pubsub.subscribe(topic)
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield json.loads(message['data'])


    def listen(self, topic: str):
        """
        Returns a queue-like object for consuming messages.
        Useful for non-blocking or timeout-based waiting in a thread.
        """
        import queue
        import threading
        
        q = queue.Queue()
        
        def _producer():
            for event in self.subscribe(topic):
                q.put(event)
        
        t = threading.Thread(target=_producer, daemon=True)
        t.start()
        
        return q
