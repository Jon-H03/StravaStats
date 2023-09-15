import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import './App.css';
import { MapContainer, TileLayer, Polyline, Popup } from 'react-leaflet';
import ImageGallery from 'react-image-gallery';
import LoginPage from './pages/LoginPage';
import CallbackManager from './components/CallbackManager';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activities, setActivities] = useState([]);
  const [stats, setStats] = useState(null);
  const [plots, setPlots] = useState(null);
  const [latlong, setLatLong] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const handleStatsReceived = (stats, plots, activities, latlong) => {
    setStats(stats);
    setPlots(plots);
    setActivities(activities);
    setLatLong(latlong);
  };

  const images = plots?.map(plot => ({
    original: `data:image/png;base64,${plot}`,
    thumbnail: `data:image/png;base64,${plot}`,
  })) || [];


  return (
    <Router>
      <Routes>
          <Route 
          path="/login" 
          element={isAuthenticated ? <Navigate to="/" /> : <LoginPage setIsLoading={setIsLoading} setIsAuthenticated={setIsAuthenticated} />} />
          <Route
          path="/callback"
          element={
            <CallbackManager
              onAuthenticated={() => setIsAuthenticated(true)}
              onStatsReceived={handleStatsReceived}
            />
          }
        />
        <Route path="/" element={isAuthenticated ? (
          <>
              <h1 className='title'>Strava Stats for Runners  🏃‍♀️🏃‍♂️💨</h1>
              <h2 className='subhead'>General Stats & Interactive Map</h2>
              <div className='container'>

                <div className='stats'>
                  {stats && (
                    <div>
                        <h2>All-Time Totals:</h2>
                        <p>Total Runs: {stats['total_runs']}</p>
                        <p>Total Distance: {stats['total_distance']} miles</p>
                        <p>Total Time Moving: {stats['total_time_moving']} hours</p>
                        <p>Total Elevation Gain: {stats['total_elevation_gain']} meters</p>
                        <br></br>
                        <h2>All-Time Averages:</h2>
                        <p>Average Speed All-Time: {stats['avg_speed_all_time']} mph</p>
                        <p>Average Pace per Mile: {stats['avg_pace']} /mile</p>
                        <p>Average Distance per Run: {stats['avg_dist_per_run']} miles</p>
                        <p>Average Elevation Gain: {stats['avg_elev_gain']} meters</p>
                        <br></br>
                        <h2>Other All-Time Stats:</h2>
                        <p>Fastest Speed: {stats['fastest_speed']} mph</p>
                        <p>Longest Streak: {stats['longest_streak']} days</p>
                        <p>Farthest Distance: {stats['farthest_run']} miles</p>
                        <p>Shortest Distance: {stats['shortest_run']} miles</p>
                        <p>Max Altitude: {stats['max_altitude']} meters</p>
                    </div>
                  )}
                  </div>
                  <div className='activities'>
                    {latlong && activities && activities.length !== 0 && (
                    <MapContainer center={latlong || [43.41136, -106.280024]} zoom={6} scrollWheelZoom={true}>
                      <TileLayer
                        attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      />
                      {activities.map((activity, i) => {
                        const decodedCoords = polyline.decode(activity.activityPositions);
                        return (
                          <Polyline key={i} positions={decodedCoords}>
                            <Popup>
                              <div>
                                <h2>{"Name: " + activity.activityName}</h2>
                                <h3>{"Activity Type: " + activity.activityType}</h3>
                                <h3>{"Distance: " + activity.activityDistance + " m"}</h3>
                              </div>
                            </Popup>
                          </Polyline>
                        );
                      })}
                    </MapContainer>
                )}
                </div>

              </div>
              <div className='plots'>
              {plots && (
                <div>
                  <h2>Plots:</h2>
                  <ImageGallery items={images} />
                </div>
              )}
              </div>

            </>
          ) : <Navigate to="/login" />
        } />
      </Routes>
    </Router>
  );
}

export default App;