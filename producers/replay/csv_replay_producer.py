"""
CSV Replay Producer cho StreamPulse v1

Tính năng:
- Đọc CSV với pandas
- Validate schema với Pydantic
- Preserve event timestamps
- Configurable replay speed (1x, 10x)
- Partition by region_id
- Error handling & retry logic
"""

import sys
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
import click
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Add schemas path to import TripEvent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'streaming', 'schemas'))
from trip_event import TripEvent


class CSVReplayProducer:
    """
    CSV Replay Producer cho StreamPulse v1
    """
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:9092",
        kafka_topic: str = "events",
        replay_speed: float = 1.0,
        batch_size: int = 100
    ):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
        self.replay_speed = replay_speed
        self.batch_size = batch_size
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Kafka producer
        self.producer = None
        self._init_kafka_producer()
        
        # Statistics
        self.stats = {
            'total_events': 0,
            'sent_events': 0,
            'failed_events': 0,
            'retry_attempts': 0,  # DAY 13: Track retry attempts
            'start_time': None,
            'end_time': None
        }
    
    def _init_kafka_producer(self):
        """Initialize Kafka producer với retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: v.encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',  # Wait for all replicas
                    retries=3,
                    batch_size=16384,
                    linger_ms=10,
                    compression_type='gzip'
                )
                self.logger.info(f"✅ Kafka producer initialized successfully")
                return
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Kafka producer (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def load_csv_data(self, csv_file_path: str) -> pd.DataFrame:
        """
        Load và validate CSV data
        
        Args:
            csv_file_path: Path to CSV file
            
        Returns:
            pandas DataFrame với validated data
        """
        try:
            self.logger.info(f"📁 Loading CSV data from: {csv_file_path}")
            
            # Load CSV
            df = pd.read_csv(csv_file_path)
            self.logger.info(f"📊 Loaded {len(df)} records from CSV")
            
            # Validate required columns
            required_columns = ['trip_id', 'region_id', 'event_time', 'fare', 'duration', 'distance']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Sort by event_time để preserve temporal order
            # Use format='ISO8601' để handle ISO format với Z suffix
            df['event_time'] = pd.to_datetime(df['event_time'], format='ISO8601')
            df = df.sort_values('event_time').reset_index(drop=True)
            
            self.stats['total_events'] = len(df)
            self.logger.info(f"✅ CSV data loaded and sorted successfully")
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load CSV data: {e}")
            raise
    
    def validate_trip_event(self, row: pd.Series) -> Optional[TripEvent]:
        """
        Validate single trip event với Pydantic
        
        Args:
            row: pandas Series representing one trip
            
        Returns:
            TripEvent object hoặc None nếu validation fails
        """
        try:
            trip_event = TripEvent(
                trip_id=str(row['trip_id']),
                region_id=int(row['region_id']),
                event_time=row['event_time'],
                fare=float(row['fare']),
                duration=int(row['duration']),
                distance=float(row['distance'])
            )
            return trip_event
        except Exception as e:
            self.logger.warning(f"⚠️ Validation failed for trip {row.get('trip_id', 'unknown')}: {e}")
            self.stats['failed_events'] += 1
            return None
    
    def send_event_to_kafka(self, trip_event: TripEvent) -> bool:
        """
        DAY 13: Send single event to Kafka with enhanced retry logic
        
        Args:
            trip_event: TripEvent to send
            
        Returns:
            True if successful, False otherwise
        """
        max_retries = 3
        base_delay = 1.0  # 1 second base delay
        
        for attempt in range(max_retries + 1):  # 0 to max_retries (4 total attempts)
            try:
                # Prepare message
                message = trip_event.to_kafka_message()
                partition_key = trip_event.get_partition_key()
                
                # Send to Kafka
                future = self.producer.send(
                    topic=self.kafka_topic,
                    value=message,
                    key=partition_key
                )
                
                # Wait for confirmation (với timeout)
                record_metadata = future.get(timeout=10)
                
                self.logger.debug(
                    f"📤 Sent event {trip_event.trip_id} to partition {record_metadata.partition}, "
                    f"offset {record_metadata.offset}"
                )
                
                # Success on first attempt or retry
                if attempt > 0:
                    self.logger.info(f"✅ Event {trip_event.trip_id} sent successfully on attempt {attempt + 1}")
                
                self.stats['sent_events'] += 1
                return True
                
            except KafkaError as e:
                if attempt < max_retries:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** attempt)
                    self.stats['retry_attempts'] += 1  # DAY 13: Track retry
                    self.logger.warning(
                        f"⚠️ Kafka error sending event {trip_event.trip_id} (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"❌ Failed to send event {trip_event.trip_id} after {max_retries + 1} attempts: {e}")
                    self.stats['failed_events'] += 1
                    return False
                    
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    self.stats['retry_attempts'] += 1  # DAY 13: Track retry
                    self.logger.warning(
                        f"⚠️ Unexpected error sending event {trip_event.trip_id} (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"❌ Failed to send event {trip_event.trip_id} after {max_retries + 1} attempts: {e}")
                    self.stats['failed_events'] += 1
                    return False
        
        return False  # Should never reach here
    
    def replay_csv_data(
        self,
        csv_file_path: str,
        max_events: Optional[int] = None,
        preserve_timestamps: bool = True
    ):
        """
        Main method để replay CSV data to Kafka
        
        Args:
            csv_file_path: Path to CSV file
            max_events: Maximum number of events to send (None = all)
            preserve_timestamps: Whether to preserve original timing
        """
        try:
            self.stats['start_time'] = datetime.now()
            self.logger.info(f"🚀 Starting CSV replay with speed {self.replay_speed}x")
            
            # Load data
            df = self.load_csv_data(csv_file_path)
            
            # Limit events if specified
            if max_events:
                df = df.head(max_events)
                self.logger.info(f"📊 Limited to {len(df)} events")
            
            # Calculate timing for replay
            if preserve_timestamps and len(df) > 1:
                df['time_diff'] = df['event_time'].diff().dt.total_seconds().fillna(0)
                df['time_diff'] = df['time_diff'] / self.replay_speed  # Apply speed multiplier
            
            # Process events
            for idx, row in df.iterrows():
                # Validate event
                trip_event = self.validate_trip_event(row)
                if not trip_event:
                    continue

                # Send to Kafka
                success = self.send_event_to_kafka(trip_event)
                
                # Progress logging
                if (idx + 1) % self.batch_size == 0:
                    self.logger.info(
                        f"📊 Progress: {idx + 1}/{len(df)} events processed, "
                        f"sent: {self.stats['sent_events']}, failed: {self.stats['failed_events']}"
                    )
                
                # Timing control cho preserved timestamps
                if preserve_timestamps and idx < len(df) - 1:
                    sleep_time = df.loc[idx + 1, 'time_diff']
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            
            # Final flush
            self.producer.flush()
            self.stats['end_time'] = datetime.now()
            
            # Print final statistics
            self._print_final_stats()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to replay CSV data: {e}")
            raise
        finally:
            if self.producer:
                self.producer.close()
    
    def _print_final_stats(self):
        """Print final statistics"""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        self.logger.info("=" * 50)
        self.logger.info("📊 FINAL STATISTICS")
        self.logger.info("=" * 50)
        self.logger.info(f"Total events processed: {self.stats['total_events']}")
        self.logger.info(f"Successfully sent: {self.stats['sent_events']}")
        self.logger.info(f"Failed events: {self.stats['failed_events']}")
        self.logger.info(f"Retry attempts: {self.stats['retry_attempts']}")  # DAY 13: Show retry stats
        self.logger.info(f"Success rate: {(self.stats['sent_events'] / self.stats['total_events'] * 100):.1f}%")
        self.logger.info(f"Duration: {duration}")
        self.logger.info(f"Throughput: {(self.stats['sent_events'] / duration.total_seconds()):.1f} events/sec")
        self.logger.info("=" * 50)


@click.command()
@click.option('--csv-file', required=True, help='Path to CSV file')
@click.option('--kafka-servers', default='localhost:9092', help='Kafka bootstrap servers')
@click.option('--kafka-topic', default='events', help='Kafka topic name')
@click.option('--replay-speed', default=1.0, help='Replay speed multiplier (1.0 = real-time)')
@click.option('--max-events', default=None, type=int, help='Maximum events to send')
@click.option('--batch-size', default=100, help='Batch size for progress reporting')
@click.option('--preserve-timestamps/--no-preserve-timestamps', default=True, help='Preserve original timing')
def main(csv_file, kafka_servers, kafka_topic, replay_speed, max_events, batch_size, preserve_timestamps):
    """
    CSV Replay Producer cho StreamPulse v1
    """
    try:
        producer = CSVReplayProducer(
            kafka_bootstrap_servers=kafka_servers,
            kafka_topic=kafka_topic,
            replay_speed=replay_speed,
            batch_size=batch_size
        )
        
        producer.replay_csv_data(
            csv_file_path=csv_file,
            max_events=max_events,
            preserve_timestamps=preserve_timestamps
        )
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()