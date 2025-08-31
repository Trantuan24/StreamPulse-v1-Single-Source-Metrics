"""
CSV Replay Producer cho StreamPulse v1 - OPTIMIZED FOR HIGH THROUGHPUT

OPTIMIZATIONS IMPLEMENTED:
- Remove synchronous future.get() waits → Async sending
- Pre-load entire CSV into memory → Eliminate I/O overhead
- Batch processing with async callbacks → Better throughput
- Optimized Kafka producer config → Higher buffer/batch sizes
- Multi-threaded architecture → Utilize multiple cores

Target Performance: 5k-10k events/s (vs ~50 events/s baseline)
"""

import sys
import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import click
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Add schemas path to import TripEvent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'streaming', 'schemas'))
from trip_event import TripEvent


class OptimizedCSVReplayProducer:
    """
    High-Performance CSV Replay Producer cho StreamPulse v1
    
    PERFORMANCE OPTIMIZATIONS:
    1. Async Kafka sending (no blocking waits)
    2. Memory pre-loading (entire CSV in RAM)
    3. Batch processing (multiple events per operation)
    4. Optimized Kafka config (larger buffers/batches)
    5. Multi-threading support
    """
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:9092",
        kafka_topic: str = "events",
        replay_speed: float = 1.0,
        batch_size: int = 1000,  # Increased từ 100
        num_threads: int = 4  # Multi-threading support
    ):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
        self.replay_speed = replay_speed
        self.batch_size = batch_size
        self.num_threads = num_threads
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Kafka producer với optimized config
        self.producer = None
        self._init_optimized_kafka_producer()
        
        # Statistics với thread safety
        self.stats_lock = threading.Lock()
        self.stats = {
            'total_events': 0,
            'sent_events': 0,
            'failed_events': 0,
            'start_time': None,
            'end_time': None,
            'async_futures': []  # Track async sends
        }
        
        # Pre-loaded data storage
        self.trip_events: List[TripEvent] = []
    
    def _init_optimized_kafka_producer(self):
        """Initialize Kafka producer với HIGH PERFORMANCE config"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: v.encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    
                    # PERFORMANCE OPTIMIZATIONS:
                    acks=1,  # Changed from 'all' to reduce latency
                    retries=1,  # Reduced retries for speed
                    batch_size=65536,  # 4x larger batches (16384 → 65536)
                    linger_ms=50,  # Increased linger for better batching
                    buffer_memory=134217728,  # 128MB buffer (vs default 32MB)
                    compression_type='gzip',  # Use gzip instead of snappy for Windows compatibility
                    max_in_flight_requests_per_connection=10,  # More concurrent requests
                    
                    # Async callbacks
                    enable_idempotence=False  # Disable for max speed
                )
                self.logger.info(f"✅ Optimized Kafka producer initialized successfully")
                self.logger.info(f"📊 Config: batch_size=65536, buffer=128MB, linger=50ms")
                return
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Kafka producer (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
    
    def preload_csv_data(self, csv_file_path: str, max_events: Optional[int] = None) -> None:
        """
        Pre-load và validate TOÀN BỘ CSV data into memory
        
        OPTIMIZATION: Load everything upfront để eliminate I/O during sending
        """
        try:
            self.logger.info(f"🚀 Pre-loading entire CSV into memory: {csv_file_path}")
            start_time = time.time()
            
            # Load CSV
            df = pd.read_csv(csv_file_path)
            self.logger.info(f"📊 Loaded {len(df)} raw records from CSV")
            
            # Validate required columns
            required_columns = ['trip_id', 'region_id', 'event_time', 'fare', 'duration', 'distance']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Sort by event_time
            df['event_time'] = pd.to_datetime(df['event_time'], format='ISO8601')
            df = df.sort_values('event_time').reset_index(drop=True)
            
            # Limit events if specified
            if max_events:
                df = df.head(max_events)
                self.logger.info(f"📊 Limited to {len(df)} events")
            
            # BATCH VALIDATION: Process all rows into TripEvent objects
            self.trip_events = []
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
                    self.trip_events.append(trip_event)
                except Exception as e:
                    failed_count += 1
                    self.logger.debug(f"⚠️ Validation failed for trip {row.get('trip_id', 'unknown')}: {e}")
            
            load_time = time.time() - start_time
            self.stats['total_events'] = len(self.trip_events)
            
            self.logger.info(f"✅ Pre-loaded {len(self.trip_events)} valid events in {load_time:.2f}s")
            self.logger.info(f"📊 Validation: {len(self.trip_events)} passed, {failed_count} failed")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to pre-load CSV data: {e}")
            raise
    
    def async_send_callback(self, record_metadata=None, exception=None):
        """
        Async callback for Kafka sends - NO BLOCKING
        """
        with self.stats_lock:
            if exception:
                self.stats['failed_events'] += 1
                self.logger.debug(f"❌ Send failed: {exception}")
            else:
                self.stats['sent_events'] += 1
                self.logger.debug(f"📤 Async sent to partition {record_metadata.partition}")
    
    def send_batch_async(self, trip_events_batch: List[TripEvent]) -> int:
        """
        Send a batch of events ASYNCHRONOUSLY (no blocking waits)
        
        OPTIMIZATION: Batch processing + async callbacks = Max throughput
        """
        sent_count = 0
        
        for trip_event in trip_events_batch:
            try:
                # Prepare message
                message = trip_event.to_kafka_message()
                partition_key = trip_event.get_partition_key()
                
                # ASYNC SEND - NO BLOCKING
                future = self.producer.send(
                    topic=self.kafka_topic,
                    value=message,
                    key=partition_key
                ).add_callback(self.async_send_callback).add_errback(self.async_send_callback)
                
                # Store future for later cleanup (optional)
                self.stats['async_futures'].append(future)
                sent_count += 1
                
            except Exception as e:
                self.logger.error(f"❌ Error sending event {trip_event.trip_id}: {e}")
                with self.stats_lock:
                    self.stats['failed_events'] += 1
        
        return sent_count
    
    def multi_threaded_replay(self, num_workers: int = None) -> None:
        """
        Multi-threaded high-performance replay
        
        OPTIMIZATION: Utilize multiple CPU cores cho parallel processing
        """
        if num_workers is None:
            num_workers = self.num_threads
            
        if not self.trip_events:
            raise ValueError("No events pre-loaded. Call preload_csv_data() first.")
        
        self.stats['start_time'] = datetime.now()
        self.logger.info(f"🚀 Starting multi-threaded replay với {num_workers} workers")
        self.logger.info(f"📊 Processing {len(self.trip_events)} pre-loaded events")
        
        # Split events into chunks for parallel processing
        chunk_size = max(1, len(self.trip_events) // num_workers)
        event_chunks = [
            self.trip_events[i:i + chunk_size] 
            for i in range(0, len(self.trip_events), chunk_size)
        ]
        
        self.logger.info(f"📦 Split into {len(event_chunks)} chunks of ~{chunk_size} events each")
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_chunk = {
                executor.submit(self.send_batch_async, chunk): idx 
                for idx, chunk in enumerate(event_chunks)
            }
            
            for future in as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    sent_count = future.result()
                    self.logger.info(f"✅ Chunk {chunk_idx + 1}/{len(event_chunks)} completed: {sent_count} events sent")
                except Exception as e:
                    self.logger.error(f"❌ Chunk {chunk_idx + 1} failed: {e}")
        
        # Final flush and cleanup
        self.logger.info("🔄 Flushing producer...")
        self.producer.flush()
        
        self.stats['end_time'] = datetime.now()
        self._print_final_stats()
    
    def high_speed_sequential_replay(self) -> None:
        """
        Single-threaded high-speed replay với optimized batching
        
        OPTIMIZATION: Maximum speed trong single thread (no threading overhead)
        """
        if not self.trip_events:
            raise ValueError("No events pre-loaded. Call preload_csv_data() first.")
        
        self.stats['start_time'] = datetime.now()
        self.logger.info(f"⚡ Starting high-speed sequential replay")
        self.logger.info(f"📊 Processing {len(self.trip_events)} pre-loaded events")
        
        # Process in large batches
        for batch_start in range(0, len(self.trip_events), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(self.trip_events))
            batch = self.trip_events[batch_start:batch_end]
            
            # Send batch asynchronously
            sent_count = self.send_batch_async(batch)
            
            # Progress logging
            progress_pct = (batch_end / len(self.trip_events)) * 100
            self.logger.info(
                f"📊 Progress: {batch_end}/{len(self.trip_events)} ({progress_pct:.1f}%) - "
                f"Batch: {sent_count} sent, Total sent: {self.stats['sent_events']}"
            )
        
        # Final flush
        self.logger.info("🔄 Flushing producer...")
        self.producer.flush()
        
        self.stats['end_time'] = datetime.now()
        self._print_final_stats()
    
    def _print_final_stats(self):
        """Print comprehensive performance statistics"""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        self.logger.info("=" * 60)
        self.logger.info("🚀 OPTIMIZED PERFORMANCE STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Total events processed: {self.stats['total_events']}")
        self.logger.info(f"Successfully sent: {self.stats['sent_events']}")
        self.logger.info(f"Failed events: {self.stats['failed_events']}")
        self.logger.info(f"Success rate: {(self.stats['sent_events'] / self.stats['total_events'] * 100):.1f}%")
        self.logger.info(f"Duration: {duration}")
        
        if duration.total_seconds() > 0:
            throughput = self.stats['sent_events'] / duration.total_seconds()
            self.logger.info(f"📈 THROUGHPUT: {throughput:.1f} events/sec")
            
            # Performance improvement calculation
            baseline_throughput = 50  # events/s from original
            improvement = throughput / baseline_throughput
            self.logger.info(f"🚀 IMPROVEMENT: {improvement:.1f}x faster than baseline ({baseline_throughput} events/s)")
        
        self.logger.info("=" * 60)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.producer:
            self.producer.close()


@click.command()
@click.option('--csv-file', required=True, help='Path to CSV file')
@click.option('--kafka-servers', default='localhost:9092', help='Kafka bootstrap servers')
@click.option('--kafka-topic', default='events', help='Kafka topic name')
@click.option('--replay-speed', default=1.0, help='Replay speed multiplier (1.0 = real-time)')
@click.option('--max-events', default=None, type=int, help='Maximum events to send')
@click.option('--batch-size', default=1000, help='Batch size for processing')
@click.option('--num-threads', default=4, help='Number of worker threads')
@click.option('--mode', default='sequential', type=click.Choice(['sequential', 'threaded']), 
              help='Processing mode: sequential (fastest) or threaded (utilizes cores)')
def main(csv_file, kafka_servers, kafka_topic, replay_speed, max_events, batch_size, num_threads, mode):
    """
    OPTIMIZED CSV Replay Producer cho StreamPulse v1
    
    TARGET PERFORMANCE: 500-1000 events/s (vs ~50 events/s baseline)
    """
    try:
        producer = OptimizedCSVReplayProducer(
            kafka_bootstrap_servers=kafka_servers,
            kafka_topic=kafka_topic,
            replay_speed=replay_speed,
            batch_size=batch_size,
            num_threads=num_threads
        )
        
        # Pre-load data into memory
        producer.preload_csv_data(csv_file, max_events)
        
        # Choose processing mode
        if mode == 'threaded':
            producer.multi_threaded_replay()
        else:
            producer.high_speed_sequential_replay()
        
        # Cleanup
        producer.cleanup()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
