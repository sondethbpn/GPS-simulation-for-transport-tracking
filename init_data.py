import requests

API_URL = "http://localhost:8000"

# Create sample vehicles
vehicles = [
    {
        "vehicle_id": "BUS-01",
        "driver_name": "John Doe",
        "route_id": "ROUTE-001",
        "vehicle_type": "bus",
        "capacity": 40
    },
    {
        "vehicle_id": "BUS-02",
        "driver_name": "Jane Smith",
        "route_id": "ROUTE-001",
        "vehicle_type": "bus",
        "capacity": 40
    },
    {
        "vehicle_id": "SHUTTLE-01",
        "driver_name": "Mike Johnson",
        "route_id": "ROUTE-002",
        "vehicle_type": "van",
        "capacity": 15
    },
    {
        "vehicle_id": "EXPRESS-01",
        "driver_name": "Sarah Williams",
        "route_id": "ROUTE-003",
        "vehicle_type": "bus",
        "capacity": 50
    },
    {
        "vehicle_id": "VAN-01",
        "driver_name": "Tom Brown",
        "route_id": "ROUTE-004",
        "vehicle_type": "van",
        "capacity": 12
    }
]

# Create sample routes
routes = [
    {
        "route_id": "ROUTE-001",
        "name": "Bangkok City Loop",
        "description": "Main city route",
        "stops": [
            {"name": "Siam", "lat": 13.7563, "lon": 100.5018},
            {"name": "Asok", "lat": 13.7467, "lon": 100.5345},
            {"name": "Lumphini", "lat": 13.7308, "lon": 100.5239},
            {"name": "Silom", "lat": 13.7245, "lon": 100.5312},
        ]
    },
    {
        "route_id": "ROUTE-002",
        "name": "Campus Shuttle",
        "description": "University campus route",
        "stops": [
            {"name": "Main Gate", "lat": 13.8000, "lon": 100.5500},
            {"name": "Library", "lat": 13.8020, "lon": 100.5520},
            {"name": "Engineering", "lat": 13.8040, "lon": 100.5510},
        ]
    },
    {
        "route_id": "ROUTE-003",
        "name": "Express Route",
        "description": "Fast route with fewer stops",
        "stops": [
            {"name": "Terminal A", "lat": 13.7563, "lon": 100.5018},
            {"name": "Terminal B", "lat": 13.7467, "lon": 100.5345},
        ]
    },
    {
        "route_id": "ROUTE-004",
        "name": "Van Route",
        "description": "Suburban van route",
        "stops": [
            {"name": "Station 1", "lat": 13.7600, "lon": 100.5100},
            {"name": "Station 2", "lat": 13.7580, "lon": 100.5200},
        ]
    }
]

print("Initializing vehicles...")
for vehicle in vehicles:
    response = requests.post(f"{API_URL}/vehicles", json=vehicle)
    if response.status_code == 200:
        print(f"✓ Created {vehicle['vehicle_id']}")
    else:
        print(f"✗ Failed to create {vehicle['vehicle_id']}")

print("\nInitializing routes...")
for route in routes:
    response = requests.post(f"{API_URL}/routes", json=route)
    if response.status_code == 200:
        print(f"✓ Created {route['route_id']}")
    else:
        print(f"✗ Failed to create {route['route_id']}")

print("\n✅ Initialization complete!")