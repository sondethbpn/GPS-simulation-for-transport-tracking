import threading
import requests
import time
import math
from datetime import datetime
from typing import List, Tuple, Dict, Set
import random
import json

class MultiVehicleSimulator:
    """
    Simulates multiple vehicles simultaneously using threading.
    Each vehicle runs independently on its own route with designated bus stops.
    Adjusted for Mae Chan, Chiang Rai routes.
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
    
    def find_nearest_stop_index(self, current_pos: Tuple[float, float], 
                                bus_stops: List[Tuple[float, float]], 
                                threshold_km: float = 0.03) -> int:
        """Find if current position is near a bus stop"""
        for idx, stop in enumerate(bus_stops):
            distance = self.calculate_distance(
                current_pos[0], current_pos[1],
                stop[0], stop[1]
            )
            if distance <= threshold_km:
                return idx
        return -1
    
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
                print(f"✓ {vehicle_id}: ({lat:.6f}, {lon:.6f}) @ {speed:.1f} km/h - {status}")
            else:
                print(f"✗ {vehicle_id}: Update failed - Status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ {vehicle_id}: Connection error - {str(e)[:50]}")
    
    def simulate_single_vehicle(self, vehicle_id: str, route: List[Tuple[float, float]], 
                               bus_stops: List[Tuple[float, float]],
                               speed_kmh: float = 25, update_interval: int = 3,
                               stop_duration: int = 10, loop: bool = True):
        """
        Simulate a single vehicle (runs in separate thread).
        
        Args:
            vehicle_id: Unique vehicle ID
            route: List of GPS waypoints (lat, lon)
            bus_stops: List of designated bus stop locations
            speed_kmh: Average speed in km/h
            update_interval: Seconds between GPS updates
            stop_duration: Seconds to wait at bus stops
            loop: Whether to loop the route
        """
        print(f"🚌 {vehicle_id} started - {len(route)} waypoints, {len(bus_stops)} bus stops")
        
        iteration = 0
        stopped_at_stops: Set[int] = set()  # Track which stops we've visited this iteration
        
        while self.running:
            iteration += 1
            stopped_at_stops.clear()
            print(f"🔄 {vehicle_id}: Starting iteration {iteration}")
            
            for i in range(len(route) - 1):
                if not self.running:
                    break
                    
                start_point = route[i]
                end_point = route[i + 1]
                
                # Calculate segment details
                distance_km = self.calculate_distance(
                    start_point[0], start_point[1],
                    end_point[0], end_point[1]
                )
                
                # Skip very short segments (GPS noise)
                if distance_km < 0.0001:
                    continue
                
                # Calculate movement parameters
                time_needed_seconds = (distance_km / speed_kmh) * 3600
                num_updates = max(1, int(time_needed_seconds / update_interval))
                
                # Move along segment
                for step in range(num_updates + 1):
                    if not self.running:
                        break
                        
                    fraction = step / num_updates if num_updates > 0 else 1.0
                    current_pos = self.interpolate_position(start_point, end_point, fraction)
                    
                    # Add realistic GPS noise (±5 meters)
                    lat_noise = random.uniform(-0.00004, 0.00004)
                    lon_noise = random.uniform(-0.00004, 0.00004)
                    lat = current_pos[0] + lat_noise
                    lon = current_pos[1] + lon_noise
                    
                    # Check if we're near a bus stop
                    stop_idx = self.find_nearest_stop_index((lat, lon), bus_stops)
                    
                    if stop_idx != -1 and stop_idx not in stopped_at_stops:
                        # We're at a bus stop and haven't stopped here yet
                        stopped_at_stops.add(stop_idx)
                        print(f"🛑 {vehicle_id}: Bus Stop {stop_idx + 1}/{len(bus_stops)}")
                        
                        # Stop at bus stop
                        self.send_location_update(
                            vehicle_id, lat, lon, 
                            speed=0.0, 
                            status="stopped"
                        )
                        time.sleep(stop_duration)
                        
                        # Resume moving
                        current_speed = speed_kmh + random.uniform(-3, 3)
                        self.send_location_update(
                            vehicle_id, lat, lon, 
                            speed=current_speed, 
                            status="moving"
                        )
                    else:
                        # Normal movement
                        speed_variation = random.uniform(-3, 3)
                        current_speed = max(0, speed_kmh + speed_variation)
                        
                        self.send_location_update(
                            vehicle_id, lat, lon, 
                            speed=current_speed, 
                            status="moving"
                        )
                    
                    # Don't sleep after last update of segment
                    if step < num_updates:
                        time.sleep(update_interval)
            
            if not loop:
                print(f"✓ {vehicle_id}: Route completed")
                self.send_location_update(
                    vehicle_id, route[-1][0], route[-1][1],
                    speed=0.0, status="completed"
                )
                break
            else:
                print(f"🔄 {vehicle_id}: Restarting route (30s pause)")
                time.sleep(30)
    
    def add_vehicle(self, vehicle_id: str, route: List[Tuple[float, float]], 
                   bus_stops: List[Tuple[float, float]],
                   speed_kmh: float = 25, update_interval: int = 3,
                   stop_duration: int = 10, loop: bool = True):
        """Add a vehicle to the simulation"""
        thread = threading.Thread(
            target=self.simulate_single_vehicle,
            args=(vehicle_id, route, bus_stops, speed_kmh, update_interval, 
                  stop_duration, loop),
            daemon=True
        )
        self.threads.append(thread)
    
    def start(self):
        """Start all vehicle simulations"""
        self.running = True
        print(f"\n{'='*60}")
        print(f"🚀 Starting simulation for {len(self.threads)} vehicles")
        print(f"{'='*60}\n")
        
        for i, thread in enumerate(self.threads):
            thread.start()
            if i < len(self.threads) - 1:
                time.sleep(5)  # Stagger start times
    
    def stop(self):
        """Stop all simulations"""
        print("\n🛑 Stopping all simulations...")
        self.running = False
        for thread in self.threads:
            thread.join(timeout=5)
        print("✓ All simulations stopped\n")


# ============================================================================
# ROUTE DATA - Reduced to half the waypoints for better performance
# ============================================================================

# Mae Chan, Chiang Rai Route (every 2nd waypoint from original)
MAE_CHAN_ROUTE = [
    (20.0589569, 99.8997827), (20.0589582, 99.8996909), (20.0589355, 99.8993425),
    (20.0589009, 99.8991599), (20.058791, 99.898817), (20.0586996, 99.8986305),
    (20.0584751, 99.8983486), (20.0581434, 99.8979867), (20.0575624, 99.8975002),
    (20.0568365, 99.8967415), (20.0566951, 99.8966574), (20.0565872, 99.8965966),
    (20.056496, 99.8965552), (20.0562761, 99.8964775), (20.0562133, 99.8964639),
    (20.0560645, 99.8964495), (20.0558569, 99.8964328), (20.0556463, 99.8964208),
    (20.0554879, 99.8963948), (20.055355, 99.8963608), (20.0552151, 99.8962873),
    (20.05516, 99.8962275), (20.0550769, 99.8960826), (20.0550564, 99.8958915),
    (20.0550735, 99.8956552), (20.0550666, 99.8954516), (20.0550507, 99.8953296),
    (20.0550091, 99.8952005), (20.0549606, 99.8950741), (20.0549065, 99.8949481),
    (20.054836, 99.8947932), (20.0547274, 99.8945201), (20.0546603, 99.8943543),
    (20.0546082, 99.8941628), (20.0544771, 99.8937535), (20.0543244, 99.8934594),
    (20.0541843, 99.8932663), (20.0539791, 99.8930004), (20.0538175, 99.8928392),
    (20.0537012, 99.8927505), (20.0533984, 99.892581), (20.0532655, 99.8925256),
    (20.0531458, 99.8924896), (20.0528449, 99.8924002), (20.052722, 99.892367),
    (20.0525432, 99.8922973), (20.0524128, 99.8922423), (20.0522484, 99.8921459),
    (20.0520554, 99.891986), (20.0517808, 99.891755), (20.0515781, 99.8915859),
    (20.0510214, 99.8912703), (20.0508656, 99.8911985), (20.0507811, 99.8911678),
    (20.0506111, 99.8911174), (20.0504197, 99.8910882), (20.0501086, 99.8910858),
    (20.0498053, 99.891089), (20.0496038, 99.8911119), (20.0493906, 99.8911608),
    (20.0491683, 99.8912209), (20.048963, 99.8913104), (20.0488773, 99.8913592),
    (20.0488828, 99.8914971), (20.0487638, 99.8917959), (20.0483837, 99.8926419),
    (20.0482148, 99.8930229), (20.048174, 99.8931777), (20.0480829, 99.8932677),
    (20.0480069, 99.8929921), (20.0474814, 99.8931788), (20.0472262, 99.8930518),
    (20.0478682, 99.8929353), (20.0481098, 99.8929922), (20.0482137, 99.8929819),
    (20.0483744, 99.8926391), (20.0487557, 99.8917927), (20.0488731, 99.8914955),
    (20.0488701, 99.8913636), (20.0485134, 99.8915811), (20.0483635, 99.8916736),
    (20.048277, 99.8917428), (20.0480538, 99.8919394), (20.0478905, 99.8920593),
    (20.0477889, 99.8921119), (20.0475088, 99.8921777), (20.0473112, 99.8921947),
    (20.0468359, 99.8921076), (20.0466459, 99.8920038), (20.0462317, 99.8917914),
    (20.0459942, 99.8916797), (20.0457743, 99.8915592), (20.0454988, 99.8914141),
    (20.0453126, 99.8913307), (20.0451397, 99.8913095), (20.0447601, 99.8913119),
    (20.0444026, 99.891434), (20.0442243, 99.8916175), (20.0442208, 99.89196),
    (20.0441321, 99.8926272), (20.0441098, 99.8928826), (20.0440683, 99.8930463),
    (20.0438959, 99.8934262), (20.0436854, 99.8939553), (20.0436697, 99.894098),
    (20.0436659, 99.8942996), (20.0437399, 99.8945951), (20.0438845, 99.8948917),
    (20.0439097, 99.8953155), (20.0438139, 99.8956119), (20.0436256, 99.8958459),
    (20.0434757, 99.8961175), (20.0434593, 99.8962389), (20.0435545, 99.8963951),
    (20.0434244, 99.8965611), (20.0432867, 99.8966475), (20.0431047, 99.8966429),
    (20.0429812, 99.8965172), (20.0429591, 99.8962633), (20.0430883, 99.8957219),
    (20.0433418, 99.8952759), (20.0434291, 99.8949686), (20.0434379, 99.8948374),
    (20.0435716, 99.8943687), (20.0436495, 99.8942091), (20.0436631, 99.8940131),
    (20.0437089, 99.8938177), (20.0440777, 99.8929796), (20.0440994, 99.8928541),
    (20.0441641, 99.892329), (20.0442095, 99.8918253), (20.0442241, 99.8915146),
    (20.0441894, 99.8913807), (20.0447384, 99.8911876), (20.0450994, 99.8911848),
    (20.0454387, 99.8912766), (20.0456496, 99.8913485), (20.046094, 99.8916081),
    (20.0464981, 99.8919067), (20.0467636, 99.8920671), (20.0470613, 99.8921615),
    (20.0474083, 99.8921742), (20.0476294, 99.8921464), (20.0478355, 99.8920791),
    (20.0479747, 99.8919929), (20.0480823, 99.8919008), (20.0482981, 99.8917121),
    (20.0484177, 99.8916277), (20.0486601, 99.8914812), (20.048965, 99.8912989),
    (20.0491672, 99.891213), (20.0494899, 99.8911295), (20.0496934, 99.8910957),
    (20.0499015, 99.8910759), (20.0503165, 99.8910777), (20.0505258, 99.891083),
    (20.0510115, 99.8912496), (20.0513753, 99.8914568), (20.0517806, 99.8917387),
    (20.0523178, 99.8921751), (20.0524206, 99.8922322), (20.0526852, 99.8923437),
    (20.0530252, 99.8924426), (20.0536142, 99.8926818), (20.0539847, 99.8929921),
    (20.0541946, 99.8932597), (20.0544146, 99.8935988), (20.0545584, 99.8939365),
    (20.0548677, 99.894832), (20.0550159, 99.8951847), (20.0550785, 99.8954484),
    (20.0550706, 99.8958159), (20.0550704, 99.8959905), (20.0551356, 99.8961715),
    (20.0551902, 99.8962517), (20.0552935, 99.8963253), (20.0555114, 99.8963909),
    (20.0556462, 99.8964082), (20.0560645, 99.896436), (20.0563388, 99.8964788),
    (20.0565733, 99.8965736), (20.0568733, 99.8967472), (20.0577513, 99.8972588),
    (20.0581589, 99.8975592), (20.0583456, 99.8977335), (20.0587598, 99.8982991),
    (20.0588697, 99.8985018), (20.059008, 99.8988345), (20.0590993, 99.8991899),
    (20.0591296, 99.8995896), (20.058957, 99.8996017)
]

# Bus Stop Locations
BUS_STOPS = [
    (20.058752, 99.898396),
    (20.057039, 99.896930),
    (20.054683, 99.894515),
    (20.052544, 99.892316),
    (20.050816843021277, 99.89121969349162),
    (20.049137353450433, 99.891250485570452),
    (20.048193, 99.893221),
    (20.047264832318994, 99.89314563095694),
    (20.045503, 99.891442),
    (20.043881444753783, 99.89348617576454),
    (20.043919609786567, 99.89490923095694),
    (20.043311336533844, 99.89529707515575),
    (20.043845538331563, 99.8934754469289),
    (20.045659393241642, 99.89133178188165),
    (20.049391118491396, 99.89111283095696),
    (20.05083048583872, 99.89115650886787),
    (20.052689636083315, 99.89234180090831),
    (20.05473222049373, 99.89448019896511),
    (20.056897650552507, 99.89711855304603),
    (20.05806378447924, 99.89787541746388),
    (20.058966957817436, 99.8995173298247),
    (20.041244, 99.894427)
]


# ============================================================================
# MAIN SIMULATION
# ============================================================================

def main():
    """
    Main simulation function for Mae Chan, Chiang Rai route
    """
    print("\n" + "="*60)
    print("🚍 Mae Chan Vehicle Simulator v2.0")
    print("📍 Location: Mae Chan, Chiang Rai, Thailand")
    print("="*60 + "\n")
    
    # Initialize simulator
    simulator = MultiVehicleSimulator(backend_url="http://localhost:8000")
    
    # Analyze the route
    route_length = len(MAE_CHAN_ROUTE)
    bus_stop_count = len(BUS_STOPS)
    
    print(f"📊 Route Analysis:")
    print(f"   - Total waypoints: {route_length} (optimized)")
    print(f"   - Bus stops: {bus_stop_count}")
    
    # Calculate total distance
    total_distance = 0
    for i in range(len(MAE_CHAN_ROUTE) - 1):
        dist = simulator.calculate_distance(
            MAE_CHAN_ROUTE[i][0], MAE_CHAN_ROUTE[i][1],
            MAE_CHAN_ROUTE[i+1][0], MAE_CHAN_ROUTE[i+1][1]
        )
        total_distance += dist
    
    print(f"   - Total distance: {total_distance:.2f} km")
    print(f"   - Start: ({MAE_CHAN_ROUTE[0][0]:.6f}, {MAE_CHAN_ROUTE[0][1]:.6f})")
    print(f"   - End: ({MAE_CHAN_ROUTE[-1][0]:.6f}, {MAE_CHAN_ROUTE[-1][1]:.6f})")
    print()
    
    # Add vehicles based on the provided vehicle details
    
    # BUS-01 - John Doe
    print("➕ Adding BUS-01 (Driver: John Doe)")
    simulator.add_vehicle(
        vehicle_id="BUS-01",
        route=MAE_CHAN_ROUTE,
        bus_stops=BUS_STOPS,
        speed_kmh=30,
        update_interval=4,
        stop_duration=10,
        loop=True
    )
    
    # BUS-02 - Jane Smith
    print("➕ Adding BUS-02 (Driver: Jane Smith)")
    simulator.add_vehicle(
        vehicle_id="BUS-02",
        route=MAE_CHAN_ROUTE,
        bus_stops=BUS_STOPS,
        speed_kmh=28,
        update_interval=4,
        stop_duration=10,
        loop=True
    )
    
    # SHUTTLE-01 - Mike Johnson (Van)
    print("➕ Adding SHUTTLE-01 (Driver: Mike Johnson)")
    simulator.add_vehicle(
        vehicle_id="SHUTTLE-01",
        route=MAE_CHAN_ROUTE,
        bus_stops=BUS_STOPS,
        speed_kmh=25,
        update_interval=3,
        stop_duration=10,
        loop=True
    )
    
    # EXPRESS-01 - Sarah Williams
    print("➕ Adding EXPRESS-01 (Driver: Sarah Williams)")
    simulator.add_vehicle(
        vehicle_id="EXPRESS-01",
        route=MAE_CHAN_ROUTE,
        bus_stops=BUS_STOPS,
        speed_kmh=40,
        update_interval=4,
        stop_duration=10,
        loop=True
    )
    
    # VAN-01 - Tom Brown
    print("➕ Adding VAN-01 (Driver: Tom Brown)")
    simulator.add_vehicle(
        vehicle_id="VAN-01",
        route=MAE_CHAN_ROUTE,
        bus_stops=BUS_STOPS,
        speed_kmh=32,
        update_interval=4,
        stop_duration=10,
        loop=True
    )
    
    print()
    
    # Start simulation
    try:
        simulator.start()
        
        # Keep main thread alive
        print("💡 Simulation running...")
        print("📱 Backend: http://localhost:8000")
        print(f"🚏 {bus_stop_count} bus stops configured")
        print("⏱️  Stop duration: 10 seconds")
        print("⌨️  Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n")
        simulator.stop()
        print("✅ Simulation ended gracefully")
        print("\nThank you for using Mae Chan Vehicle Simulator! 🙏\n")


if __name__ == "__main__":
    main()