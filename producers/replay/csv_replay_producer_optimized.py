#!/usr/bin/env python3
"""
Performance Optimized CSV Replay Producer

PERFORMANCE OPTIMIZATIONS:
- LZ4 compression (fastest)
- Larger batch sizes (128KB)
- Optimized linger time (20ms)
- Increased buffer memory (256MB)
- Multiple in-flight requests (8)
- Leader acknowledgment only (acks=1)

Target: 10-20K events/s
"""

import sys
import os
import time
import json
import logging
from datetime import datetime
from typing import Optional, List
from kafka import KafkaProducer
from kafka.errors import KafkaError
import pandas as pd
import click

# Add schemas path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'streaming', 'schemas'))
from trip_event import TripEvent


class OptimizedProducer:
    """
    High-Performance Producer
    Target: 15-20K events/s throughput
    """
    
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize optimized Kafka producer
        self.producer = self._init_optimized_producer()
        
        # Statistics
        self.stats = {
            'total_events': 0,
            'sent_events': 0,
            'failed_events': 0,
            'start_time': None,
            'end_time': None
        }
        
    def _init_optimized_producer(self):
        """Initialize Kafka producer with performance optimizations"""
        producer_config = {
            'bootstrap_servers': 'localhost:9092',
            'value_serializer': lambda v: v.encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            
            # PERFORMANCE OPTIMIZATIONS
            'batch_size': 131072,  # 128KB batches (8x larger)
            'linger_ms': 20,       # 20ms linger for better batching
            'buffer_memory': 268435456,  # 256MB buffer (8x larger)
            'compression_type': 'gzip',  # Use gzip (lz4 not available on Windows)
            
            # Reliability vs Performance trade-off
            'acks': 1,  # Leader acknowledgment only (fastest)
            'retries': 3,
            'max_in_flight_requests_per_connection': 8,  # More concurrent requests
            
            # Advanced optimizations
            'enable_idempotence': False,  # Disable for max speed
            'max_request_size': 10485760,  # 10MB max message size
            'request_timeout_ms': 30000,   # 30s timeout
            
            # Additional performance tuning
            'send_buffer_bytes': 131072,   # 128KB send buffer
            'receive_buffer_bytes': 65536,  # 64KB receive buffer
            'metadata_max_age_ms': 300000,  # 5 min metadata refresh
        }
        
        producer = KafkaProducer(**producer_config)
        
        self.logger.info("🚀 Optimized Producer Initialized")
        self.logger.info("📊 Performance Configuration:")
        self.logger.info(f"   Linger Time: 20ms")
        self.logger.info(f"   Buffer Memory: 256MB")
        self.logger.info(f"   Compression: GZIP")
        self.logger.info(f"   In-flight Requests: 8")
        self.logger.info(f"   Acknowledgment: Leader only")
        
        return producer
    
    def preload_and_validate_data(self, csv_file_path: str, max_events: Optional[int] = None) -> List[TripEvent]:
        """Pre-load and validate all CSV data in memory"""
        self.logger.info(f"📁 Pre-loading CSV data: {csv_file_path}")
        start_time = time.time()
        
        # Load CSV
        df = pd.read_csv(csv_file_path)
        self.logger.info(f"📊 Loaded {len(df)} raw records")
        
        # Limit events if specified
        if max_events:
            df = df.head(max_events)
            self.logger.info(f"📊 Limited to {max_events} events")
        
        # Sort by event_time
        df['event_time'] = pd.to_datetime(df['event_time'], format='ISO8601')
        df = df.sort_values('event_time').reset_index(drop=True)
        
        # Batch validation
        trip_events = []
        failed_count = 0
        
        for idx, row in df.iterrows():
            try:
                trip_event = TripEvent(
                    trip_id=str(row['trip_id']),
                    region_id=int(row['region_id']),
                    event_time=row['event_time'],
                    fare=float(row['fare']),
                    duration=int(row['duration']),
                    distance=float(row['distance'])
                )
                trip_events.append(trip_event)
            except Exception as e:
                failed_count += 1
                
        load_time = time.time() - start_time
        self.stats['total_events'] = len(trip_events)
        
        self.logger.info(f"✅ Pre-loaded {len(trip_events)} valid events in {load_time:.2f}s")
        self.logger.info(f"📊 Validation: {len(trip_events)} passed, {failed_count} failed")
        
        return trip_events
    
    def async_callback(self, record_metadata=None, exception=None):
        """Async callback for send operations"""
        if exception:
            self.stats['failed_events'] += 1
            self.logger.debug(f"❌ Send failed: {exception}")
        else:
            self.stats['sent_events'] += 1
    
    def high_speed_send(self, trip_events: List[TripEvent]):
        """High-speed async sending with minimal blocking"""
        self.logger.info(f"⚡ Starting high-speed transmission of {len(trip_events)} events")
        
        self.stats['start_time'] = datetime.now()
        sent_count = 0
        
        # Send all events asynchronously
        for trip_event in trip_events:
            try:
                message = trip_event.to_kafka_message()
                partition_key = trip_event.get_partition_key()
                
                # Async send with callback
                self.producer.send(
                    topic='events',
                    value=message,
                    key=partition_key
                ).add_callback(self.async_callback).add_errback(self.async_callback)
                
                sent_count += 1
                
                # Progress logging every 1000 events
                if sent_count % 1000 == 0:
                    self.logger.info(f"📤 Sent {sent_count}/{len(trip_events)} events")
                    
            except Exception as e:
                self.logger.error(f"❌ Error sending event: {e}")
                self.stats['failed_events'] += 1
        
        # Final flush
        self.logger.info("🔄 Flushing producer buffer...")
        self.producer.flush()
        
        self.stats['end_time'] = datetime.now()
        self._print_performance_results()
    
    def _print_performance_results(self):
        """Print comprehensive performance results"""
        duration = self.stats['end_time'] - self.stats['start_time']
        duration_seconds = duration.total_seconds()
        
        self.logger.info("=" * 70)
        self.logger.info("🚀 PERFORMANCE RESULTS")
        self.logger.info("=" * 70)
        self.logger.info(f"Total events processed: {self.stats['total_events']}")
        self.logger.info(f"Successfully sent: {self.stats['sent_events']}")
        self.logger.info(f"Failed events: {self.stats['failed_events']}")
        self.logger.info(f"Success rate: {(self.stats['sent_events'] / self.stats['total_events'] * 100):.1f}%")
        self.logger.info(f"Duration: {duration}")
        
        if duration_seconds > 0:
            throughput = self.stats['sent_events'] / duration_seconds
            self.logger.info(f"📈 THROUGHPUT: {throughput:.1f} events/sec")
            
            # Performance analysis
            baseline_throughput = 10568  # Baseline throughput
            improvement = throughput / baseline_throughput
            self.logger.info(f"🚀 IMPROVEMENT: {improvement:.1f}x vs baseline")
            
            # Target analysis
            if throughput >= 15000:
                self.logger.info("🎯 ✅ TARGET ACHIEVED: ≥15K events/s")
            elif throughput >= 12000:
                self.logger.info("🎯 ⚠️ CLOSE TO TARGET: ≥12K events/s (good progress)")
            else:
                self.logger.info("🎯 ❌ TARGET NOT MET: <12K events/s")
        
        self.logger.info("=" * 70)
    
    def cleanup(self):
        """Clean up resources"""
        if self.producer:
            self.producer.close()
            self.logger.info("🧹 Producer closed")


@click.command()
@click.option('--csv-file', required=True, help='Path to CSV file')
@click.option('--max-events', default=None, type=int, help='Maximum events to send')
def main(csv_file, max_events):
    """
    High-Performance CSV Producer
    Target: 10-20K events/s
    """
    try:
        producer = OptimizedProducer()
        
        # Pre-load data
        trip_events = producer.preload_and_validate_data(csv_file, max_events)
        
        # High-speed transmission
        producer.high_speed_send(trip_events)
        
        # Cleanup
        producer.cleanup()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

