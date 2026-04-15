import os
import sys
import json

from kafka import KafkaConsumer  # type: ignore


def main():
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topic = sys.argv[1] if len(sys.argv) > 1 else "txn_events"
    group_id = os.getenv("KAFKA_GROUP_ID", "upi-demo-consumer")

    print(f"[consumer] connecting to {brokers} topic={topic} group={group_id}")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=brokers.split(","),
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=group_id,
    )

    for msg in consumer:
        print(json.dumps(msg.value))


if __name__ == "__main__":
    main()


