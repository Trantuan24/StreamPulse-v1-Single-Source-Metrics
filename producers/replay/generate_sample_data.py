"""
Generate Sample Trip Data cho StreamPulse v1
Author: Trần Duy Tuấn
Date: 2025-08-17

Tạo realistic sample data với:
- 300 trip records
- Timestamps distributed trong 1 ngày
- Chỉ 6 columns cần thiết cho schema
- Data phù hợp với Pydantic validation
"""

import csv
import random
from datetime import datetime, timedelta
from typing import List, Dict
import sys
import os

# Add schemas path to import TripEvent for validation
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'streaming', 'schemas'))
from trip_event import TripEvent


class SampleDataGenerator:
    """
    Generator cho realistic trip sample data
    """
    
    def __init__(self, num_records: int = 300):
        self.num_records = num_records
        self.base_date = datetime(2025, 8, 17, 6, 0, 0)  # Start at 6 AM today
        
        # Realistic data ranges
        self.regions = [1, 2, 3, 4, 5]  # 5 regions
        self.fare_ranges = {
            1: (8.0, 45.0),    # Urban center
            2: (12.0, 35.0),   # Suburban
            3: (15.0, 60.0),   # Airport area
            4: (6.0, 25.0),    # Residential
            5: (20.0, 80.0)    # Business district
        }
        self.duration_ranges = {
            1: (300, 2400),    # 5-40 minutes
            2: (600, 3600),    # 10-60 minutes
            3: (900, 4800),    # 15-80 minutes
            4: (240, 1800),    # 4-30 minutes
            5: (1200, 5400)    # 20-90 minutes
        }
        self.distance_ranges = {
            1: (1.0, 15.0),    # Short urban trips
            2: (3.0, 25.0),    # Suburban trips
            3: (8.0, 45.0),    # Airport trips
            4: (0.5, 12.0),    # Local trips
            5: (5.0, 35.0)     # Business trips
        }
    
    def generate_trip_id(self, index: int) -> str:
        """Generate unique trip ID"""
        return f"trip_{index:06d}"
    
    def generate_region_id(self) -> int:
        """Generate region ID với weighted distribution"""
        # Region 1 và 5 có traffic cao hơn
        weights = [0.3, 0.2, 0.15, 0.15, 0.2]  # Sum = 1.0
        return random.choices(self.regions, weights=weights)[0]
    
    def generate_event_time(self, index: int) -> datetime:
        """
        Generate realistic event time distributed trong ngày
        
        Peak hours: 7-9 AM, 12-1 PM, 5-7 PM
        """
        # Distribute events across 18 hours (6 AM - 12 AM)
        total_minutes = 18 * 60  # 1080 minutes
        
        # Add some randomness but maintain order
        base_minutes = (index / self.num_records) * total_minutes
        
        # Add peak hour bias
        hour_of_day = (base_minutes // 60) + 6  # Start from 6 AM
        
        # Peak hour adjustments
        if 7 <= hour_of_day <= 9:  # Morning peak
            base_minutes += random.uniform(-30, 30)
        elif 12 <= hour_of_day <= 13:  # Lunch peak
            base_minutes += random.uniform(-20, 20)
        elif 17 <= hour_of_day <= 19:  # Evening peak
            base_minutes += random.uniform(-30, 30)
        else:  # Off-peak
            base_minutes += random.uniform(-60, 60)
        
        # Ensure we don't go negative or beyond the day
        base_minutes = max(0, min(base_minutes, total_minutes - 1))
        
        return self.base_date + timedelta(minutes=base_minutes)
    
    def generate_fare(self, region_id: int, duration: int, distance: float) -> float:
        """Generate realistic fare based on region, duration, and distance"""
        base_min, base_max = self.fare_ranges[region_id]
        
        # Base fare from region
        base_fare = random.uniform(base_min, base_max)
        
        # Adjust based on distance (longer = more expensive)
        distance_factor = 1.0 + (distance - 5.0) * 0.02  # +2% per km above 5km
        
        # Adjust based on duration (longer = slightly more expensive)
        duration_factor = 1.0 + (duration - 1200) * 0.0001  # +0.01% per second above 20min
        
        # Apply factors
        final_fare = base_fare * distance_factor * duration_factor
        
        # Add some randomness
        final_fare *= random.uniform(0.9, 1.1)
        
        # Round to 2 decimal places and ensure within bounds
        final_fare = round(max(5.0, min(final_fare, 100.0)), 2)
        
        return final_fare
    
    def generate_duration(self, region_id: int) -> int:
        """Generate realistic trip duration in seconds"""
        min_duration, max_duration = self.duration_ranges[region_id]
        
        # Use normal distribution for more realistic values
        mean = (min_duration + max_duration) / 2
        std = (max_duration - min_duration) / 6  # 99.7% within range
        
        duration = int(random.normalvariate(mean, std))
        
        # Ensure within bounds
        return max(min_duration, min(duration, max_duration))
    
    def generate_distance(self, region_id: int, duration: int) -> float:
        """Generate realistic distance based on region and duration"""
        min_distance, max_distance = self.distance_ranges[region_id]
        
        # Base distance from region
        base_distance = random.uniform(min_distance, max_distance)
        
        # Adjust based on duration (longer trips = longer distance, but not linear)
        # Average speed: 15-30 km/h in city traffic
        expected_distance = (duration / 3600) * random.uniform(15, 30)
        
        # Blend base and expected distance
        final_distance = (base_distance + expected_distance) / 2
        
        # Add some randomness
        final_distance *= random.uniform(0.8, 1.2)
        
        # Round to 1 decimal place and ensure within bounds
        final_distance = round(max(0.5, min(final_distance, 50.0)), 1)
        
        return final_distance
    
    def generate_single_trip(self, index: int) -> Dict[str, any]:
        """Generate single trip record"""
        trip_id = self.generate_trip_id(index)
        region_id = self.generate_region_id()
        event_time = self.generate_event_time(index)
        duration = self.generate_duration(region_id)
        distance = self.generate_distance(region_id, duration)
        fare = self.generate_fare(region_id, duration, distance)
        
        return {
            'trip_id': trip_id,
            'region_id': region_id,
            'event_time': event_time.isoformat() + 'Z',
            'fare': fare,
            'duration': duration,
            'distance': distance
        }
    
    def validate_trip(self, trip_data: Dict[str, any]) -> bool:
        """Validate trip data với Pydantic schema"""
        try:
            TripEvent(**trip_data)
            return True
        except Exception as e:
            print(f"⚠️ Validation failed for {trip_data['trip_id']}: {e}")
            return False
    
    def generate_sample_data(self) -> List[Dict[str, any]]:
        """Generate all sample trip data"""
        print(f"🚀 Generating {self.num_records} sample trip records...")
        
        trips = []
        valid_trips = 0
        
        for i in range(self.num_records):
            trip = self.generate_single_trip(i)
            
            # Validate with Pydantic
            if self.validate_trip(trip):
                trips.append(trip)
                valid_trips += 1
            else:
                # Regenerate if validation fails
                print(f"🔄 Regenerating trip {i}...")
                trip = self.generate_single_trip(i)
                if self.validate_trip(trip):
                    trips.append(trip)
                    valid_trips += 1
            
            # Progress reporting
            if (i + 1) % 50 == 0:
                print(f"📊 Progress: {i + 1}/{self.num_records} generated, {valid_trips} valid")
        
        print(f"✅ Generated {len(trips)} valid trips out of {self.num_records} attempts")
        return trips
    
    def save_to_csv(self, trips: List[Dict[str, any]], filename: str):
        """Save trips to CSV file"""
        print(f"💾 Saving data to {filename}...")
        
        fieldnames = ['trip_id', 'region_id', 'event_time', 'fare', 'duration', 'distance']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trips)
        
        print(f"✅ Saved {len(trips)} records to {filename}")
    
    def print_statistics(self, trips: List[Dict[str, any]]):
        """Print data statistics"""
        if not trips:
            return
        
        print("\n" + "="*50)
        print("📊 DATA STATISTICS")
        print("="*50)
        
        # Region distribution
        region_counts = {}
        for trip in trips:
            region = trip['region_id']
            region_counts[region] = region_counts.get(region, 0) + 1
        
        print("Region distribution:")
        for region in sorted(region_counts.keys()):
            count = region_counts[region]
            percentage = (count / len(trips)) * 100
            print(f"  Region {region}: {count} trips ({percentage:.1f}%)")
        
        # Time range
        times = [datetime.fromisoformat(trip['event_time'].replace('Z', '')) for trip in trips]
        print(f"\nTime range:")
        print(f"  Start: {min(times).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End: {max(times).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Value ranges
        fares = [trip['fare'] for trip in trips]
        durations = [trip['duration'] for trip in trips]
        distances = [trip['distance'] for trip in trips]
        
        print(f"\nValue ranges:")
        print(f"  Fare: ${min(fares):.2f} - ${max(fares):.2f} (avg: ${sum(fares)/len(fares):.2f})")
        print(f"  Duration: {min(durations)}s - {max(durations)}s (avg: {sum(durations)/len(durations):.0f}s)")
        print(f"  Distance: {min(distances):.1f}km - {max(distances):.1f}km (avg: {sum(distances)/len(distances):.1f}km)")
        
        print("="*50)


def main():
    """Main function"""
    print("🚀 StreamPulse v1 - Sample Data Generator")
    print("="*50)

    # Generate data
    generator = SampleDataGenerator(num_records=300)
    trips = generator.generate_sample_data()

    # Save to CSV trong ops/data directory (đúng cấu trúc dự án)
    output_file = "../../ops/data/streampulse_sample_trips.csv"

    # Create ops/data directory if not exists
    os.makedirs("../../ops/data", exist_ok=True)

    generator.save_to_csv(trips, output_file)
    generator.print_statistics(trips)

    print(f"\n🎯 Sample data ready for testing!")
    print(f"📁 File: {output_file}")
    print(f"📊 Records: {len(trips)}")
    print(f"🔧 Ready for CSV Replay Producer!")


if __name__ == "__main__":
    main()