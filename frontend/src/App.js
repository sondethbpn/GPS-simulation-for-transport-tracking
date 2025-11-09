import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom vehicle icons
const createVehicleIcon = (type, status) => {
  const colors = {
    active: '#10b981',
    stopped: '#f59e0b',
    moving: '#3b82f6',
    inactive: '#6b7280'
  };
  
  const color = colors[status] || colors.moving;
  
  return L.divIcon({
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
      ">
        ${type === 'bus' ? '🚌' : type === 'van' ? '🚐' : '🚕'}
      </div>
    `,
    className: 'custom-vehicle-icon',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Component to update map center
function MapController({ center }) {
  const map = useMap();
  
  useEffect(() => {
    if (center) {
      map.setView(center, map.getZoom());
    }
  }, [center, map]);
  
  return null;
}

export default function TransportTracker() {
  const [vehicles, setVehicles] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [positions, setPositions] = useState({});
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [mapCenter, setMapCenter] = useState([20.045210, 99.893004]); // Mae Fah Luang University
  const [stats, setStats] = useState({ total: 0, active: 0 });
  
  const wsRef = useRef(null);
  const API_URL = 'http://localhost:8000';
  const WS_URL = 'ws://localhost:8000/ws';
  
  // Fetch initial data
  useEffect(() => {
    fetchVehicles();
    fetchRoutes();
    fetchPositions();
    fetchStats();
  }, []);
  
  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);
  
  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log('✓ WebSocket connected');
        setWsStatus('connected');
      };
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === 'initial_data') {
          // Load initial positions
          const posMap = {};
          message.data.forEach(pos => {
            posMap[pos.vehicle_id] = pos;
          });
          setPositions(posMap);
        } else if (message.type === 'location_update') {
          // Update single vehicle position
          setPositions(prev => ({
            ...prev,
            [message.data.vehicle_id]: message.data
          }));
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsStatus('error');
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsStatus('disconnected');
        
        // Attempt reconnection after 3 seconds
        setTimeout(() => {
          console.log('Attempting to reconnect...');
          connectWebSocket();
        }, 3000);
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setWsStatus('error');
    }
  };

  const fetchVehicles = async () => {
    try {
      const response = await fetch(`${API_URL}/vehicles`);
      const data = await response.json();
      setVehicles(data);
    } catch (error) {
      console.error('Error fetching vehicles:', error);
    }
  };

  const fetchRoutes = async () => {
    try {
      const response = await fetch(`${API_URL}/routes`);
      const data = await response.json();
      setRoutes(data);
    } catch (error) {
      console.error('Error fetching routes:', error);
    }
  };

  const fetchPositions = async () => {
    try {
      const response = await fetch(`${API_URL}/positions`);
      const data = await response.json();
      const posMap = {};
      data.forEach(pos => {
        posMap[pos.vehicle_id] = pos;
      });
      setPositions(posMap);
    } catch (error) {
      console.error('Error fetching positions:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/stats`);
      const data = await response.json();
      setStats({
        total: data.total_vehicles,
        active: data.active_vehicles
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const centerOnVehicle = (vehicleId) => {
    const position = positions[vehicleId];
    if (position) {
      setMapCenter([position.latitude, position.longitude]);
      setSelectedVehicle(vehicleId);
    }
  };

  const getVehicleInfo = (vehicleId) => {
    return vehicles.find(v => v.vehicle_id === vehicleId);
  };

  const getRouteForVehicle = (vehicleId) => {
    const vehicle = getVehicleInfo(vehicleId);
    if (vehicle) {
      return routes.find(r => r.route_id === vehicle.route_id);
    }
    return null;
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-80 bg-white shadow-lg overflow-y-auto">
        {/* Header */}
        <div className="p-4 bg-blue-600 text-white">
          <h1 className="text-xl font-bold">🚌 Transport Tracker</h1>
          <p className="text-sm text-blue-100 mt-1">Real-time Vehicle Monitoring</p>
        </div>

        {/* Stats */}
        <div className="p-4 bg-gray-50 border-b">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white p-3 rounded-lg shadow-sm">
              <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
              <div className="text-xs text-gray-600">Total Vehicles</div>
            </div>
            <div className="bg-white p-3 rounded-lg shadow-sm">
              <div className="text-2xl font-bold text-green-600">{stats.active}</div>
              <div className="text-xs text-gray-600">Active Now</div>
            </div>
          </div>
          
          {/* WebSocket Status */}
          <div className="mt-3 flex items-center text-sm">
            <div className={`w-2 h-2 rounded-full mr-2 ${
              wsStatus === 'connected' ? 'bg-green-500' : 
              wsStatus === 'error' ? 'bg-red-500' : 'bg-gray-400'
            }`}></div>
            <span className="text-gray-600">
              {wsStatus === 'connected' ? 'Live Updates Active' : 
               wsStatus === 'error' ? 'Connection Error' : 'Connecting...'}
            </span>
          </div>
        </div>

        {/* Vehicle List */}
        <div className="p-4">
          <h2 className="text-lg font-semibold mb-3 text-gray-800">Active Vehicles</h2>
          
          {Object.keys(positions).length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">🚌</div>
              <p>No vehicles tracking yet</p>
              <p className="text-sm mt-1">Start the simulator to see vehicles</p>
            </div>
          ) : (
            <div className="space-y-2">
              {Object.entries(positions).map(([vehicleId, position]) => {
                const vehicle = getVehicleInfo(vehicleId);
                const route = getRouteForVehicle(vehicleId);
                
                return (
                  <div
                    key={vehicleId}
                    onClick={() => centerOnVehicle(vehicleId)}
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedVehicle === vehicleId
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 bg-white hover:border-blue-300'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-gray-800 flex items-center">
                          <span className="mr-2">
                            {vehicle?.vehicle_type === 'bus' ? '🚌' : 
                             vehicle?.vehicle_type === 'van' ? '🚐' : '🚕'}
                          </span>
                          {vehicleId}
                        </div>
                        
                        {vehicle && (
                          <div className="text-xs text-gray-600 mt-1">
                            Driver: {vehicle.driver_name}
                          </div>
                        )}
                        
                        {route && (
                          <div className="text-xs text-gray-600">
                            Route: {route.name}
                          </div>
                        )}
                        
                        <div className="flex items-center mt-2 text-xs">
                          <span className={`px-2 py-1 rounded-full ${
                            position.status === 'moving' ? 'bg-blue-100 text-blue-700' :
                            position.status === 'stopped' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {position.status}
                          </span>
                          <span className="ml-2 text-gray-600">
                            {position.speed?.toFixed(1)} km/h
                          </span>
                        </div>
                      </div>
                      
                      <div className="text-xs text-gray-500">
                        {new Date(position.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer
          center={mapCenter}
          zoom={13}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          <MapController center={mapCenter} />
          
          {/* Vehicle Markers */}
          {Object.entries(positions).map(([vehicleId, position]) => {
            const vehicle = getVehicleInfo(vehicleId);
            const route = getRouteForVehicle(vehicleId);
            
            return (
              <Marker
                key={vehicleId}
                position={[position.latitude, position.longitude]}
                icon={createVehicleIcon(
                  vehicle?.vehicle_type || 'bus',
                  position.status
                )}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-bold text-lg mb-2">{vehicleId}</div>
                    {vehicle && (
                      <>
                        <div><strong>Driver:</strong> {vehicle.driver_name}</div>
                        <div><strong>Type:</strong> {vehicle.vehicle_type}</div>
                      </>
                    )}
                    {route && (
                      <div><strong>Route:</strong> {route.name}</div>
                    )}
                    <div><strong>Speed:</strong> {position.speed?.toFixed(1)} km/h</div>
                    <div><strong>Status:</strong> {position.status}</div>
                    <div className="text-xs text-gray-600 mt-2">
                      Updated: {new Date(position.timestamp).toLocaleString()}
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
          
          {/* Route Lines */}
          {routes.map(route => {
            const coordinates = route.stops.map(stop => [stop.lat, stop.lon]);
            return (
              <Polyline
                key={route.route_id}
                positions={coordinates}
                color="#3b82f6"
                weight={3}
                opacity={0.5}
              />
            );
          })}

          {/* Bus Stop Pins
            {BUS_STOPS.map(([lat, lon], index) => (
              <Marker
                key={`stop-${index}`}
                position={[lat, lon]}
                icon={L.icon({
                  iconUrl: 'https://cdn-icons-png.flaticon.com/512/685/685655.png', // Example bus-stop pin icon
                  iconSize: [25, 25],
                  iconAnchor: [12, 25],
                  popupAnchor: [0, -25],
                })}
              >
                <Popup>
                  <div className="text-sm font-semibold">
                    Bus Stop #{index + 1}
                  </div>
                  <div>Lat: {lat.toFixed(6)}</div>
                  <div>Lon: {lon.toFixed(6)}</div>
                </Popup>
              </Marker>
            ))} */}
        </MapContainer>
        
        {/* Map Legend */}
        <div className="absolute bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg text-sm">
          <div className="font-semibold mb-2">Status Legend</div>
          <div className="space-y-1">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-blue-500 mr-2"></div>
              <span>Moving</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></div>
              <span>Stopped</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-gray-500 mr-2"></div>
              <span>Inactive</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}