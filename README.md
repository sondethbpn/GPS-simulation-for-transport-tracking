# GPS Simulation for Transport Tracking

A real-time transport tracking system with GPS simulation capabilities. This project simulates multiple vehicles traveling along predefined routes with bus stops, and provides a full-stack application to visualize and track vehicle locations in real-time.

## Features

- **Multi-Vehicle Simulation**: Simulate multiple vehicles simultaneously using threading
- **GPS Tracking**: Real-time GPS position updates with realistic noise simulation
- **Bus Stop Detection**: Automatic detection and handling of bus stops with configurable stop durations
- **Real-Time Updates**: WebSocket support for live vehicle position broadcasting
- **RESTful API**: Comprehensive API for managing vehicles, routes, and locations
- **MongoDB Integration**: Persistent storage of vehicle data and position history
- **Interactive Dashboard**: React-based frontend with Leaflet maps for visualization
- **Route Management**: Create and manage custom routes with multiple stops

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework for building APIs
- **Motor** - Async MongoDB driver for Python
- **WebSocket** - Real-time bidirectional communication

### Frontend
- **React 19** - JavaScript UI library
- **Leaflet** - Interactive map library
- **React-Leaflet** - React component bindings for Leaflet
- **Tailwind CSS** - Utility-first CSS framework

### Database
- **MongoDB** - NoSQL database for storing vehicles, routes, and positions

## Project Structure

```
.
├── gps_simulator.py          # Main GPS simulation engine
├── multi_vehicle_simulator.py # Multi-vehicle simulation logic
├── main.py                    # FastAPI backend server
├── init_data.py              # Database initialization script
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.js
│   ├── public/
│   ├── package.json
│   └── tailwind.config.js
├── .env.local               # Environment configuration
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- MongoDB 4.4+ (local or cloud instance)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/sondethbpn/GPS-simulation-for-transport-tracking.git
cd GPS-simulation-for-transport-tracking
```

### 2. Backend Setup

#### Create Virtual Environment
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
# or
source venv/bin/activate      # On macOS/Linux
```

#### Install Dependencies
```bash
pip install fastapi uvicorn motor pydantic requests python-dotenv
```

#### Configure Environment
Create a `.env.local` file in the project root:
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=transport_tracking
```

For MongoDB Atlas (cloud):
```
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

## Usage

### Starting MongoDB

```bash
# Local MongoDB
mongod

# Or use MongoDB Atlas (update MONGODB_URL in .env.local)
```

### Starting the Backend API

```bash
# From project root
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Initialize Database

In a new terminal, populate the database with sample data:

```bash
python init_data.py
```

This creates:
- 5 sample vehicles (buses, shuttles, vans)
- 4 sample routes with bus stops

### Starting GPS Simulator

In another terminal:

```bash
python gps_simulator.py
```

The simulator will:
1. Add 5 vehicles to the simulation
2. Start simulating their movement along the Mae Chan route in Chiang Rai
3. Send GPS updates to the backend every 3-4 seconds
4. Automatically stop at designated bus stops

### Starting the Frontend

```bash
cd frontend
npm start
```

The dashboard will open at `http://localhost:3000`

## API Endpoints

### Vehicle Management
- `POST /vehicles` - Register a new vehicle
- `GET /vehicles` - Get all vehicles
- `GET /vehicles/{vehicle_id}` - Get vehicle details
- `PUT /vehicles/{vehicle_id}/status` - Update vehicle status
- `DELETE /vehicles/{vehicle_id}` - Delete a vehicle

### Route Management
- `POST /routes` - Create a new route
- `GET /routes` - Get all routes
- `GET /routes/{route_id}` - Get route details
- `DELETE /routes/{route_id}` - Delete a route

### Location Tracking
- `POST /update_location` - Receive GPS update from vehicle
- `GET /positions` - Get latest positions of all vehicles
- `GET /positions/{vehicle_id}` - Get latest position of specific vehicle
- `GET /positions/{vehicle_id}/history` - Get position history

### WebSocket
- `WS /ws` - Real-time location updates via WebSocket

### Utilities
- `GET /stats` - Get system statistics
- `DELETE /reset` - Clear all data (testing only)

## Configuration

### Vehicle Simulation Parameters

Edit `gps_simulator.py` to customize:

```python
simulator.add_vehicle(
    vehicle_id="BUS-01",
    route=MAE_CHAN_ROUTE,
    bus_stops=BUS_STOPS,
    speed_kmh=30,           # Average speed
    update_interval=4,      # Seconds between GPS updates
    stop_duration=10,       # Seconds to stop at bus stops
    loop=True              # Restart route after completion
)
```

### Route Configuration

Define routes in `init_data.py`:

```python
{
    "route_id": "ROUTE-001",
    "name": "Your Route Name",
    "description": "Route description",
    "stops": [
        {"name": "Stop A", "lat": 13.75, "lon": 100.50},
        {"name": "Stop B", "lat": 13.76, "lon": 100.51},
    ]
}
```

## Features Explained

### GPS Simulation Engine

The `MultiVehicleSimulator` class provides:

- **Distance Calculation**: Uses Haversine formula for accurate GPS distance calculations
- **Position Interpolation**: Smoothly interpolates positions between waypoints
- **GPS Noise**: Adds realistic ±5 meter GPS noise
- **Speed Variation**: Simulates realistic speed variations (±3 km/h)
- **Bus Stop Detection**: Automatically detects when vehicle is near a bus stop
- **Threading**: Each vehicle runs independently in its own thread

### Real-Time Broadcasting

The backend broadcasts location updates to all connected WebSocket clients, enabling live tracking across multiple users.

### Database Schema

**Vehicles Collection**
```javascript
{
  vehicle_id: String,
  driver_name: String,
  route_id: String,
  vehicle_type: String,
  capacity: Number,
  status: String,
  created_at: Date
}
```

**Positions Collection**
```javascript
{
  vehicle_id: String,
  latitude: Float,
  longitude: Float,
  speed: Float,
  status: String,
  timestamp: Date,
  updated_at: Date
}
```

**Routes Collection**
```javascript
{
  route_id: String,
  name: String,
  stops: Array,
  description: String,
  created_at: Date
}
```

## Example Workflows

### 1. Track a Vehicle

```bash
# Get latest position
curl http://localhost:8000/positions/BUS-01

# Get system statistics
curl http://localhost:8000/stats
```

### 2. Create Custom Route

```bash
curl -X POST http://localhost:8000/routes \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "ROUTE-NEW",
    "name": "New Route",
    "stops": [
      {"name": "Start", "lat": 13.75, "lon": 100.50},
      {"name": "End", "lat": 13.76, "lon": 100.51}
    ]
  }'
```

### 3. Register New Vehicle

```bash
curl -X POST http://localhost:8000/vehicles \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "BUS-NEW",
    "driver_name": "Driver Name",
    "route_id": "ROUTE-001",
    "vehicle_type": "bus",
    "capacity": 40
  }'
```

## Troubleshooting

### Connection to Backend Failed
- Ensure MongoDB is running
- Check `MONGODB_URL` in `.env.local`
- Verify FastAPI server is running on port 8000

### GPS Updates Not Appearing
- Confirm simulator is running
- Check WebSocket connection in browser console
- Verify vehicle exists in database: `GET /vehicles`

### No Data in Frontend
- Initialize database: `python init_data.py`
- Start GPS simulator: `python gps_simulator.py`
- Check browser console for WebSocket errors

### Performance Issues
- Reduce number of vehicles in simulation
- Increase `update_interval` to send fewer updates
- Consider upgrading MongoDB hardware

## Performance Tuning

- **Waypoint Reduction**: Current route uses every 2nd waypoint for performance
- **Update Interval**: Increase from 3-4 seconds for slower updates
- **Stop Duration**: Adjust based on realistic requirements
- **Noise Level**: Modify GPS noise in `gps_simulator.py` line 136-137

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For issues and questions, please open an issue on GitHub.

## Authors

Created by [Your Name]

## Acknowledgments

- FastAPI documentation and community
- MongoDB for robust database solutions
- Leaflet and React-Leaflet for mapping capabilities
- The open-source community for various libraries used
