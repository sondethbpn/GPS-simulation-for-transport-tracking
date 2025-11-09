import threading
import requests
import time
import math
from datetime import datetime
from typing import List, Tuple, Dict
import random

class MultiVehicleSimulator:
    """
    Simulates multiple vehicles simultaneously using threading.
    Each vehicle runs independently on its own route.
    """
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.threads = []
        self.running = False
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in kilometers"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def interpolate_position(self, start: Tuple[float, float], end: Tuple[float, float], 
                           fraction: float) -> Tuple[float, float]:
        """Calculate intermediate position between two points"""
        lat = start[0] + (end[0] - start[0]) * fraction
        lon = start[1] + (end[1] - start[1]) * fraction
        return (lat, lon)
    
    def send_location_update(self, vehicle_id: str, lat: float, lon: float, 
                           speed: float = 0.0, status: str = "moving"):
        """Send GPS update to backend"""
        try:
            payload = {
                "vehicle_id": vehicle_id,
                "latitude": lat,
                "longitude": lon,
                "speed": speed,
                "status": status,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            response = requests.post(
                f"{self.backend_url}/update_location",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✓ {vehicle_id}: ({lat:.6f}, {lon:.6f}) - {status}")
            else:
                print(f"✗ {vehicle_id}: Update failed - Status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ {vehicle_id}: Connection error")
    
    def simulate_single_vehicle(self, vehicle_id: str, route: List[Tuple[float, float]], 
                               speed_kmh: float = 30, update_interval: int = 5,
                               stop_duration: int = 20, loop: bool = True):
        """
        Simulate a single vehicle (runs in separate thread).
        
        Args:
            vehicle_id: Unique vehicle ID
            route: List of GPS waypoints
            speed_kmh: Average speed
            update_interval: Seconds between updates
            stop_duration: Seconds to wait at each stop
            loop: Whether to loop the route
        """
        print(f"🚌 {vehicle_id} started - {len(route)} stops")
        
        while self.running:
            for i in range(len(route) - 1):
                if not self.running:
                    break
                    
                start_point = route[i]
                end_point = route[i + 1]
                
                # Simulate stop at waypoint
                if i > 0:  # Don't stop at first waypoint
                    print(f"🛑 {vehicle_id}: Stopped at waypoint {i}")
                    self.send_location_update(vehicle_id, start_point[0], start_point[1], 
                                            speed=0.0, status="stopped")
                    time.sleep(stop_duration)
                
                # Calculate segment details
                distance_km = self.calculate_distance(
                    start_point[0], start_point[1],
                    end_point[0], end_point[1]
                )
                
                time_needed_seconds = (distance_km / speed_kmh) * 3600
                num_updates = max(1, int(time_needed_seconds / update_interval))
                
                # Move along segment
                for step in range(num_updates + 1):
                    if not self.running:
                        break
                        
                    fraction = step / num_updates if num_updates > 0 else 1.0
                    current_pos = self.interpolate_position(start_point, end_point, fraction)
                    
                    # Add GPS noise
                    lat = current_pos[0] + random.uniform(-0.00005, 0.00005)
                    lon = current_pos[1] + random.uniform(-0.00005, 0.00005)
                    
                    # Calculate current speed with variation
                    current_speed = speed_kmh + random.uniform(-5, 5)
                    
                    self.send_location_update(vehicle_id, lat, lon, 
                                            speed=current_speed, status="moving")
                    time.sleep(update_interval)
            
            if not loop:
                print(f"✓ {vehicle_id}: Route completed")
                break
            else:
                print(f"🔄 {vehicle_id}: Restarting route")
                time.sleep(30)
    
    def add_vehicle(self, vehicle_id: str, route: List[Tuple[float, float]], 
                   speed_kmh: float = 30, update_interval: int = 5,
                   stop_duration: int = 20, loop: bool = True):
        """Add a vehicle to the simulation"""
        thread = threading.Thread(
            target=self.simulate_single_vehicle,
            args=(vehicle_id, route, speed_kmh, update_interval, stop_duration, loop),
            daemon=True
        )
        self.threads.append(thread)
    
    def start(self):
        """Start all vehicle simulations"""
        self.running = True
        print(f"\n{'='*60}")
        print(f"🚀 Starting simulation for {len(self.threads)} vehicles")
        print(f"{'='*60}\n")
        
        for thread in self.threads:
            thread.start()
            time.sleep(2)  # Stagger start times
    
    def stop(self):
        """Stop all simulations"""
        print("\n🛑 Stopping all simulations...")
        self.running = False
        for thread in self.threads:
            thread.join(timeout=5)
        print("✓ All simulations stopped\n")


# ============================================================================
# PREDEFINED ROUTES
# ============================================================================

def get_sample_routes() -> Dict[str, List[Tuple[float, float]]]:
    """Returns sample routes for different scenarios"""
    
    routes = {
        # Bangkok City Bus Route (longer)
        "bangkok_city": [
            (13.7563, 100.5018),  # Siam
            (13.7520, 100.5120),  # Ratchathewi
            (13.7467, 100.5345),  # Asok
            (13.7390, 100.5280),  # Phetchaburi
            (13.7308, 100.5239),  # Lumphini
            (13.7245, 100.5312),  # Silom
            (13.7200, 100.5200),  # Surasak
            (13.7278, 100.5214),  # Sala Daeng
            (13.7350, 100.5150),  # Chong Nonsi
            (13.7563, 100.5018),  # Back to Siam
        ],
        
        # University Campus Shuttle (shorter, slower)
        "campus_shuttle": [
            (13.8000, 100.5500),  # Main Gate
            (13.8020, 100.5520),  # Library
            (13.8040, 100.5510),  # Engineering
            (13.8050, 100.5530),  # Science Building
            (13.8030, 100.5550),  # Student Center
            (13.8010, 100.5540),  # Sports Complex
            (13.8000, 100.5500),  # Back to Main Gate
        ],
        
        # Express Route (faster, fewer stops)
        "express_route": [
            (13.7563, 100.5018),  # Start
            (13.7467, 100.5345),  # Stop 1
            (13.7308, 100.5239),  # Stop 2
            (13.7200, 100.5200),  # Stop 3
            (13.7563, 100.5018),  # Back to start
        ],
        
        # Van/Minibus Route (medium distance)
        "van_route": [
            (13.7600, 100.5100),  # Terminal A
            (13.7580, 100.5200),  # Stop 1
            (13.7550, 100.5300),  # Stop 2
            (13.7520, 100.5250),  # Stop 3
            (13.7500, 100.5150),  # Stop 4
            (13.7600, 100.5100),  # Back to Terminal A
        ]
    }
    
    return routes


# ============================================================================
# MAIN SIMULATION
# ============================================================================

def main():
    # Initialize simulator
    simulator = MultiVehicleSimulator(backend_url="http://localhost:8000")
    
    # Get predefined routes
    routes = get_sample_routes()
    
    # Add multiple vehicles with different configurations
    
    # Bus 1: City route, moderate speed
    simulator.add_vehicle(
        vehicle_id="BUS-01",
        route=routes["bangkok_city"],
        speed_kmh=25,
        update_interval=5,
        stop_duration=30,
        loop=True
    )
    
    # Bus 2: Same city route, delayed start (will be added to thread but starts later)
    simulator.add_vehicle(
        vehicle_id="BUS-02",
        route=routes["bangkok_city"],
        speed_kmh=28,
        update_interval=5,
        stop_duration=25,
        loop=True
    )
    
    # Campus Shuttle: Slower, shorter stops
    simulator.add_vehicle(
        vehicle_id="SHUTTLE-01",
        route=routes["campus_shuttle"],
        speed_kmh=15,
        update_interval=3,
        stop_duration=15,
        loop=True
    )
    
    # Express Bus: Faster, longer stops
    simulator.add_vehicle(
        vehicle_id="EXPRESS-01",
        route=routes["express_route"],
        speed_kmh=40,
        update_interval=5,
        stop_duration=20,
        loop=True
    )
    
    # Van: Medium speed and frequency
    simulator.add_vehicle(
        vehicle_id="VAN-01",
        route=routes["van_route"],
        speed_kmh=30,
        update_interval=4,
        stop_duration=10,
        loop=True
    )
    
    # Start simulation
    try:
        simulator.start()
        
        # Keep main thread alive
        print("\n💡 Simulation running... Press Ctrl+C to stop\n")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        simulator.stop()
        print("✅ Simulation ended gracefully")


if __name__ == "__main__":
    main()