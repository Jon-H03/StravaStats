import React from 'react';
import '../App.css';

const LoginPage = ({ setIsLoading, setIsAuthenticated }) => {  // Accept setIsLoading prop
  const handleLogin = () => {
    setIsLoading(true);  // Set the isLoading state to true when attempting to authenticate
    setIsAuthenticated(true);
    const clientID = "110708";
    const redirectURI = `http://stravastats.s3-website-us-west-1.amazonaws.com/callback`; 
    const responseType = "code";
    const scope = "activity:read_all"; 

    const authURL = `https://www.strava.com/oauth/authorize?client_id=${clientID}&redirect_uri=${redirectURI}&response_type=${responseType}&scope=${scope}`;

    // Redirect the user to the Strava OAuth page
    console.log("Redirecting to Strava for authentication...");
    window.location.href = authURL;

    // NOTE: The actual setIsLoading(false) call will be handled in the callback or after authentication is completed/failed, likely in your App component or CallbackManager.
  };

  return (
    <div className="login-box">
      <h1>Strava Stats for Runners Login</h1>
      <button onClick={handleLogin}>Log in with Strava</button>
    </div>
  );
};

export default LoginPage;
