from flask import Flask, jsonify, request, session, redirect, Response
from flask_cors import CORS
import io
import base64
import requests
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import os
from dotenv import load_dotenv


load_dotenv()

matplotlib.use('Agg')

app = Flask(__name__)
app.secret_key = "abc_123"
CORS(app)

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
AUTH_LINK = "https://www.strava.com/oauth/token"

activity_cache = []

@app.route('/auth/status', methods=['GET'])
def auth_status():
    if 'access_token' in session:
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False})


@app.route('/')
def root():
    return "Hello, this is the root page."

@app.route('/auth/strava', methods=['GET'])
def strava_auth():
    try:
        response = requests.post(
            AUTH_LINK,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": REFRESH_TOKEN,
                "grant_type": "refresh_token"
            }
        )
        data = response.json()
        access_token = data.get("access_token")

        if access_token:
            # Store the access token in the user's session
            session['access_token'] = access_token
            session.modified = True
            print(session)
            # Return just the access token to frontend
            return jsonify({"access_token": access_token})
        else:
            return jsonify({"error": "Failed to fetch access token"}), 400
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/callback', methods=['POST', 'OPTIONS'])
def callback():
    if request.method == 'OPTIONS':
        # Preflight request. Reply successfully:
        resp = Response("OK", content_type='application/json')
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'content-type'
        return resp

    data = request.json
    if not data:
        return jsonify({"error": "Expected JSON"}), 400

    code = data.get('code')

    if not code:
        return jsonify({"error": "No code provided"}), 400

    token_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    }

    try:
        response = requests.post(token_url, data=data)
        response_data = response.json()

        if response.ok and "access_token" in response_data:
            access_token = response_data.get('access_token')

            session['access_token'] = access_token
            session.modified = True

            session['access_token'] = access_token

            # Initialize StravaStatsAPI and get stat and plot data from it
            strava = StravaStatsAPI(session['access_token'])
            all_activities = (strava.fetch_activities())
            latlong = all_activities[0]['start_latlng']
            print(latlong)
            df = pd.DataFrame(all_activities)
            all_activities = strava.format_activities(all_activities)
            #print(all_activities[0])
            stats = strava.running_stats(df)

            plots = []
            plots.append(strava.plot_paces(df))
            plots.append(strava.plot_average_speed_over_time(df))
            plots.append(strava.plot_distance_over_time(df))
            plots.append(strava.plot_runs_by_weekday(df))

            return jsonify({"message": "Authentication successful", "access_token": access_token, "activities": all_activities,  "stats": stats, "plots": plots, "latlong": latlong})
        else:
            return jsonify(response_data), 400
    except Exception as e:
        return jsonify({"error": str(e)})



class StravaStatsAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token or session.get('access_token')
        if not self.access_token:
            raise ValueError("Failed to retrieve access token.")
        self.header = {'Authorization': 'Bearer ' + self.access_token}

    def request_token(self):
        auth_url = "https://www.strava.com/oauth/token"
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
            "f": "json"
        }
        response = requests.post(auth_url, data=data).json()
        session['access_token'] = response.get('access_token')
        session['refresh_token'] = response.get('refresh_token')
        return session['access_token']

    def fetch_activities(self):
        activities_url = "https://www.strava.com/api/v3/athlete/activities"
        all_activities = []

        # If the token is invalid, refresh it
        if not self.access_token:
            self.access_token = self.request_token()
            self.header = {'Authorization': 'Bearer ' + self.access_token}

        request_page_num = 1
        while True:
            param = {'per_page': 200, 'page': request_page_num}
            response = requests.get(activities_url, headers=self.header, params=param)
            
            if response.status_code != 200:
                # Handle token expiration or any other error
                self.access_token = self.request_token()
                self.header = {'Authorization': 'Bearer ' + self.access_token}
                continue  # re-try the request

            my_dataset = response.json()
            if not my_dataset:
                break

            all_activities.extend(my_dataset)
            request_page_num += 1
        
        return all_activities

    def format_activities(self, activities):
        formatted_activities = []

        for activity in activities:
            formatted_activity = {
                'activityPositions': activity['map']['summary_polyline'],
                'activityName': activity.get('name', ''),
                'activityType': activity.get('type', ''),
                'activityDistance': activity.get('distance', 0),
                'activityDate': activity.get('start_date', '')
            }

            formatted_activities.append(formatted_activity)

        return formatted_activities

    def running_stats(self, df) -> tuple:
        total_distance = 0
        total_time_moving = 0
        total_elevation_gain = 0
        fastest_speed = 0
        farthest_run = 0
        total_runs = 0
        shortest_run = float("inf")
        max_altitude = 0

        for i, activity in df.iterrows():
            if activity['type'] == 'Run':
                total_distance += activity['distance']
                total_time_moving += activity['moving_time']
                total_elevation_gain += activity['total_elevation_gain']
                fastest_speed = max(fastest_speed, activity['max_speed'])
                farthest_run = max(farthest_run, activity['distance'])
                shortest_run = min(shortest_run, activity['distance'])
                max_altitude = max(max_altitude, activity['elev_high'])
                total_runs += 1

        total_distance = round(total_distance/1609, 2) # divide by 1609 to convert meters to miles
        total_time_moving = round(total_time_moving/3600, 2) # divide by 3600 to convert seconds to hours
        total_elevation_gain = round(total_elevation_gain, 2) 
        avg_speed_all_time = round(total_distance/total_time_moving, 2) if total_time_moving else 0 # multiply by 1.609 to convert km to mile
        avg_pace = round(60/avg_speed_all_time, 2) if avg_speed_all_time else 0
        avg_dist_per_run = round((total_distance/total_runs), 2) if total_runs else 0
        avg_elev_gain = round((total_elevation_gain/total_runs), 2) if total_runs else 0
        fastest_speed = round(fastest_speed, 2)
        longest_streak = self.longest_activity_streak(df)
        farthest_run = round(farthest_run/1609, 2)
        shortest_run = round(shortest_run/1609, 2)
        max_altitude = round(max_altitude, 2)


        return {
            "total_runs": total_runs,
            "total_distance": total_distance,
            "total_time_moving": total_time_moving,
            "total_elevation_gain": total_elevation_gain,
            "avg_speed_all_time": avg_speed_all_time,
            "avg_pace": avg_pace,
            "avg_dist_per_run": avg_dist_per_run,
            "avg_elev_gain": avg_elev_gain,
            "fastest_speed": fastest_speed,
            "longest_streak": longest_streak,
            "farthest_run": farthest_run,
            'shortest_run': shortest_run,
            'max_altitude': max_altitude
        }
    
    def longest_activity_streak(self, df) -> int:
        if df.empty:
            return 0

        # Convert the 'start_date' column to a pandas datetime object
        df['start_date'] = pd.to_datetime(df['start_date']).dt.date

        # Drop duplicates to consider only one activity per day
        df = df.drop_duplicates(subset='start_date')

        # Sort the dataframe by date
        df = df.sort_values(by='start_date')

        # Calculate the difference between every consecutive date
        df['diff'] = df['start_date'].diff().dt.days

        streak = 1
        max_streak = 1

        for diff in df['diff']:
            # If the difference between dates is 1 day, continue the streak
            if diff == 1.0:
                streak += 1
                max_streak = max(max_streak, streak)
            # If the difference is greater (to account for same-day activities), reset streak
            elif diff > 1.0:
                streak = 1

        return max_streak


    def generate_plot_response(self, fig):
        """Convert matplotlib figure to base64 encoded PNG."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def plot_paces(self, df):
        miles_by_pace = defaultdict(float)
        for index, activity in df.iterrows():
            if activity['type'] == 'Run':
                distance_miles = activity['distance'] * 0.00062137
                moving_time_minutes = activity['moving_time'] / 60.0
                pace = moving_time_minutes / distance_miles 
                rounded_pace = round(pace)
                miles_by_pace[rounded_pace] += distance_miles

        paces = list(miles_by_pace.keys())
        miles = [miles_by_pace[pace] for pace in paces]
        sorted_indices = sorted(range(len(paces)), key=lambda k: paces[k])
        paces = [paces[i] for i in sorted_indices]
        miles = [miles[i] for i in sorted_indices]

        # Specify colors
        colors = ['#F4BFBF', '#8EA7E9', '#FAF0D7', '#8CC0DE']

        fig, ax = plt.subplots()
        bars = ax.bar(paces, miles, color=colors, width=0.8)
        ax.grid(True, which='minor')
        
        ax.set_xlabel('Pace (minutes per mile)')
        ax.set_ylabel('Total Miles Run')
        ax.set_title('Miles Run at Different Paces')
        ax.set_xlim([5, 14])
        
        xticks = np.arange(5, 16, 1)
        xticklabels = [f"{i}" for i in xticks]
        
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)
        
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, yval, round(yval, 2), va='bottom', ha='center')
        
        return self.generate_plot_response(fig)

    def plot_average_speed_over_time(self, df) -> None:
        x = pd.to_datetime(df['start_date_local'])
        y = df['average_speed']

        # Create a figure object and add subplot to it.
        fig = plt.figure()
        ax1 = fig.add_subplot(111)

        # Create a scatter plot with colors based on the average speed, using a colormap 'viridis'
        sc = ax1.scatter(x, y, c=y, cmap='Pastel2')
        # Add a color bar to indicate what colors mean in terms of average_speed
        plt.colorbar(sc)

        # Set the title of the plot
        ax1.set_title('Average Speed over Time')

        # Convert datetime to numerical format for curve fitting
        x2 = mdates.date2num(x)

        # Calculate the linear fit (polynomial of degree 1)
        z = np.polyfit(x2, y, 1)
        # Create a polynomial object
        p = np.poly1d(z)
        # Plot the trend line in red, with dashed style
        plt.plot(x, p(x2), 'r--')

        # Auto-format the x-axis to better fit the date labels, rotate them by 45 degrees
        fig.autofmt_xdate(rotation=45)

        # Make sure layout looks tight and nice
        fig.tight_layout()

        return self.generate_plot_response(fig)


    def plot_distance_over_time(self, df) -> None:
        # Convert 'start_date_local' column to datetime format and store it in variable x
        x = pd.to_datetime(df['start_date_local'])

        # Store 'distance' column values in variable y
        y = df['distance']

        # Create a figure object for the plot
        fig = plt.figure()

        # Add a subplot to the figure object
        ax1 = fig.add_subplot(111)

        # Create a scatter plot where color is based on distance, using colormap 'viridis'
        sc = ax1.scatter(x, y, c=y, cmap='Pastel2')

        # Add a color bar to show what the colors mean in terms of distance
        plt.colorbar(sc)

        # Set the title of the plot
        ax1.set_title('Distance over Time')
        ax1.set_ylabel('Distance (meters)')

        # Convert datetime x-values to a numerical format suitable for curve fitting
        x2 = mdates.date2num(x)

        # Calculate the linear fit (polynomial of degree 1)
        z = np.polyfit(x2, y, 1)

        # Create a polynomial object for the trend line
        p = np.poly1d(z)

        # Plot the trend line in red, with a dashed style
        plt.plot(x, p(x2), 'r--')

        # Auto-format x-axis dates and rotate labels for better visibility
        fig.autofmt_xdate(rotation=45)

        # Ensure layout is tight and clean
        fig.tight_layout()

        return self.generate_plot_response(fig)


    def plot_runs_by_weekday(self, df):
        # Convert the 'start_date_local' column to datetime format
        df['start_date_local'] = pd.to_datetime(df['start_date_local'])

        # Extract only the 'Run' activities and the start date
        run_df = df[df['type'] == 'Run']
        run_days = run_df['start_date_local'].dt.day_name()

        # Count the occurrences of each weekday
        weekday_counts = Counter(run_days)

        # Sort by day of the week
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        counts = [weekday_counts.get(day, 0) for day in days_of_week]

        # Specify colors
        colors = ['#F4BFBF', '#8EA7E9', '#FAF0D7', '#8CC0DE']

        # Create bar plot
        fig = plt.figure(figsize=(10, 6))
        plt.bar(days_of_week, counts, color=colors)
        plt.xlabel('Day of the Week')
        plt.ylabel('Number of Runs')
        plt.title('Frequency of Runs by Day of the Week')
        
        return self.generate_plot_response(fig)
    
# Add other routes for your plots as well, maybe sending back just the data needed to create the plots on the frontend

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
