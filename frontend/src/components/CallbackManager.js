import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

function CallbackManager({ onAuthenticated, onStatsReceived }) {
    const navigate = useNavigate();

    useEffect(() => {
        async function handleCallback() {
            const queryParams = new URLSearchParams(window.location.search);
            const code = queryParams.get('code');
            console.log(code);
            try {
                const response = await axios.post('http://localhost:5000/callback', { code: code });
                console.log(response);
                if (response.data && response.data.access_token) {
                    onAuthenticated();

                    // Pass the stats and plots data to the parent component
                    
                    onStatsReceived(response.data.stats, response.data.plots, response.data.activities, response.data.latlong);

                    setTimeout(() => navigate('/'));
                } else {
                    navigate('/login');
                }
            } catch (error) {
                console.error('Error during authentication callback:', error);
                navigate('/login');
            }
        }

        handleCallback();
    }, [onAuthenticated, navigate, onStatsReceived]);

    return (<div className="loading-screen">
                <i className="fas fa-spinner fa-spin"></i>
                <p>Authenticating...</p>
                
            </div>);
}
export default CallbackManager;
