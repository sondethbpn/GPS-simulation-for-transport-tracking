from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Set
from datetime import datetime
import json
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "transport_tracking"

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class VehicleCreate(BaseModel):
    vehicle_id: str
    driver_name: str
    route_id: str
    vehicle_type: str = "bus"  # bus, van, shuttle, etc.
    capacity: Optional[int] = None

class Vehicle(VehicleCreate):
    status: str = "inactive"  # active, inactive, maintenance
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RouteCreate(BaseModel):
    route_id: str
    name: str
    stops: List[dict]  # [{"name": "Stop A", "lat": 13.75, "lon": 100.50}, ...]
    description: Optional[str] = None

class Route(RouteCreate):
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LocationUpdate(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    speed: Optional[float] = 0.0
    status: Optional[str] = "moving"  # moving, stopped, idle
    timestamp: str

class Position(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    speed: float = 0.0
    status: str = "moving"
    timestamp: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="Realtime Transport Tracking API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None
db = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✓ Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"✓ Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"✗ Error sending to client: {e}")
                dead_connections.add(connection)
        
        # Remove dead connections
        self.active_connections -= dead_connections

manager = ConnectionManager()

# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_db_client():
    global mongodb_client, db
    print("🚀 Connecting to MongoDB...")
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    db = mongodb_client[DATABASE_NAME]
    
    # Create indexes for better performance
    await db.vehicles.create_index("vehicle_id", unique=True)
    await db.routes.create_index("route_id", unique=True)
    await db.positions.create_index("vehicle_id")
    await db.positions.create_index("timestamp")
    
    print("✓ Connected to MongoDB successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("✓ MongoDB connection closed")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Realtime Transport Tracking API",
        "version": "1.0.0",
        "endpoints": {
            "vehicles": "/vehicles",
            "routes": "/routes",
            "positions": "/positions",
            "websocket": "/ws"
        }
    }

# ----------------------------------------------------------------------------
# VEHICLE ENDPOINTS
# ----------------------------------------------------------------------------

@app.post("/vehicles", response_model=dict)
async def register_vehicle(vehicle: VehicleCreate):
    """Register a new vehicle"""
    vehicle_data = Vehicle(**vehicle.dict()).dict()
    
    # Check if vehicle already exists
    existing = await db.vehicles.find_one({"vehicle_id": vehicle.vehicle_id})
    if existing:
        raise HTTPException(status_code=400, detail="Vehicle already exists")
    
    result = await db.vehicles.insert_one(vehicle_data)
    vehicle_data["_id"] = str(result.inserted_id)
    
    return {"message": "Vehicle registered successfully", "vehicle": vehicle_data}

@app.get("/vehicles", response_model=List[dict])
async def get_all_vehicles():
    """Get all registered vehicles"""
    vehicles = []
    cursor = db.vehicles.find({})
    async for vehicle in cursor:
        vehicle["_id"] = str(vehicle["_id"])
        vehicles.append(vehicle)
    return vehicles

@app.get("/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    """Get specific vehicle details"""
    vehicle = await db.vehicles.find_one({"vehicle_id": vehicle_id})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle["_id"] = str(vehicle["_id"])
    return vehicle

@app.put("/vehicles/{vehicle_id}/status")
async def update_vehicle_status(vehicle_id: str, status: str):
    """Update vehicle status (active/inactive/maintenance)"""
    result = await db.vehicles.update_one(
        {"vehicle_id": vehicle_id},
        {"$set": {"status": status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return {"message": "Vehicle status updated", "vehicle_id": vehicle_id, "status": status}

@app.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str):
    """Delete a vehicle"""
    result = await db.vehicles.delete_one({"vehicle_id": vehicle_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Also delete all positions for this vehicle
    await db.positions.delete_many({"vehicle_id": vehicle_id})
    
    return {"message": "Vehicle deleted successfully", "vehicle_id": vehicle_id}

# ----------------------------------------------------------------------------
# ROUTE ENDPOINTS
# ----------------------------------------------------------------------------

@app.post("/routes", response_model=dict)
async def create_route(route: RouteCreate):
    """Create a new route"""
    route_data = Route(**route.dict()).dict()
    
    # Check if route already exists
    existing = await db.routes.find_one({"route_id": route.route_id})
    if existing:
        raise HTTPException(status_code=400, detail="Route already exists")
    
    result = await db.routes.insert_one(route_data)
    route_data["_id"] = str(result.inserted_id)
    
    return {"message": "Route created successfully", "route": route_data}

@app.get("/routes", response_model=List[dict])
async def get_all_routes():
    """Get all routes"""
    routes = []
    cursor = db.routes.find({})
    async for route in cursor:
        route["_id"] = str(route["_id"])
        routes.append(route)
    return routes

@app.get("/routes/{route_id}")
async def get_route(route_id: str):
    """Get specific route details"""
    route = await db.routes.find_one({"route_id": route_id})
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    route["_id"] = str(route["_id"])
    return route

@app.delete("/routes/{route_id}")
async def delete_route(route_id: str):
    """Delete a route"""
    result = await db.routes.delete_one({"route_id": route_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return {"message": "Route deleted successfully", "route_id": route_id}

# ----------------------------------------------------------------------------
# LOCATION/POSITION ENDPOINTS
# ----------------------------------------------------------------------------

@app.post("/update_location")
async def update_location(location: LocationUpdate):
    """
    Receive GPS location update from vehicle.
    Updates MongoDB and broadcasts to all connected WebSocket clients.
    """
    # Verify vehicle exists
    vehicle = await db.vehicles.find_one({"vehicle_id": location.vehicle_id})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(location.timestamp.replace('Z', '+00:00'))
    except:
        timestamp = datetime.utcnow()
    
    # Create position document
    position_data = {
        "vehicle_id": location.vehicle_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "speed": location.speed,
        "status": location.status,
        "timestamp": timestamp,
        "updated_at": datetime.utcnow()
    }
    
    # Update or insert position (upsert)
    await db.positions.update_one(
        {"vehicle_id": location.vehicle_id},
        {"$set": position_data},
        upsert=True
    )
    
    # Update vehicle status to active
    await db.vehicles.update_one(
        {"vehicle_id": location.vehicle_id},
        {"$set": {"status": "active"}}
    )
    
    # Broadcast to all WebSocket clients
    broadcast_data = {
        "type": "location_update",
        "data": {
            "vehicle_id": location.vehicle_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "speed": location.speed,
            "status": location.status,
            "timestamp": timestamp.isoformat()
        }
    }
    
    await manager.broadcast(broadcast_data)
    
    return {
        "message": "Location updated successfully",
        "vehicle_id": location.vehicle_id,
        "position": position_data
    }

@app.get("/positions")
async def get_all_positions():
    """Get latest positions of all vehicles"""
    positions = []
    cursor = db.positions.find({}).sort("updated_at", -1)
    
    async for position in cursor:
        position["_id"] = str(position["_id"])
        positions.append(position)
    
    return positions

@app.get("/positions/{vehicle_id}")
async def get_vehicle_position(vehicle_id: str):
    """Get latest position of specific vehicle"""
    position = await db.positions.find_one({"vehicle_id": vehicle_id})
    
    if not position:
        raise HTTPException(status_code=404, detail="No position data found for this vehicle")
    
    position["_id"] = str(position["_id"])
    return position

@app.get("/positions/{vehicle_id}/history")
async def get_position_history(vehicle_id: str, limit: int = 100):
    """Get position history for a vehicle (if storing history)"""
    # Note: Current implementation only keeps latest position
    # To enable history, modify update_location to insert instead of upsert
    position = await db.positions.find_one({"vehicle_id": vehicle_id})
    
    if not position:
        return []
    
    position["_id"] = str(position["_id"])
    return [position]

# ----------------------------------------------------------------------------
# WEBSOCKET ENDPOINT
# ----------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time location updates.
    Clients connect here to receive live vehicle position updates.
    """
    await manager.connect(websocket)
    
    try:
        # Send initial data: all current positions
        positions = []
        cursor = db.positions.find({})
        async for position in cursor:
            positions.append({
                "vehicle_id": position["vehicle_id"],
                "latitude": position["latitude"],
                "longitude": position["longitude"],
                "speed": position.get("speed", 0),
                "status": position.get("status", "unknown"),
                "timestamp": position["timestamp"].isoformat()
            })
        
        await websocket.send_json({
            "type": "initial_data",
            "data": positions
        })
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client requests if needed
            # For now, just keep connection alive
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ============================================================================
# ADMIN/UTILITY ENDPOINTS
# ============================================================================

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    total_vehicles = await db.vehicles.count_documents({})
    active_vehicles = await db.vehicles.count_documents({"status": "active"})
    total_routes = await db.routes.count_documents({})
    total_positions = await db.positions.count_documents({})
    
    return {
        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "total_routes": total_routes,
        "tracked_positions": total_positions,
        "websocket_connections": len(manager.active_connections)
    }

@app.delete("/reset")
async def reset_database():
    """⚠️ DANGER: Clear all data (for testing only)"""
    await db.vehicles.delete_many({})
    await db.routes.delete_many({})
    await db.positions.delete_many({})
    
    return {"message": "⚠️ All data cleared"}