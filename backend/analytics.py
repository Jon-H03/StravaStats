import os
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from collections import defaultdict, Counter


def request_token() -> str:
    """
    Fetches access token from Strava API given a user's client_id, client_secret, and
    their respective refresh_token.
    :return str:
    """
    print("Requesting Token...\n")
    auth_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": "110708",
        "client_secret": "a48162de0442143d7f90d59fce70fac3bf18557d",
        "refresh_token": "9b8664d9eb65137bf8bcef136daf585d72794dae",
        "grant_type": "refresh_token",
        "f": "json"
    }
    response = requests.post(auth_url, data=data, verify=False)
    print(response.json())
    return response.json()["access_token"]


def fetch_activities(header: dict) -> list:
    """
    Fetches all activities from a user's Strava and places them in a list as JSON objects.
    :param header:
    :return list:
    """
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    all_activities = []
    request_page_num = 1
    while True:
        param = {'per_page': 200, 'page': request_page_num}
        my_dataset = requests.get(activities_url, headers=header, params=param).json()
        if len(my_dataset) == 0:
            break
        all_activities.extend(my_dataset)
        request_page_num += 1
    return all_activities


def running_stats(df) -> tuple:
    """
    Iterates through all activities and calculates different running statistics about a user.
    :param df:
    :return tuple:
    """
    i = 0
    total_distance = 0
    total_time_moving = 0
    total_elevation_gain = 0
    avg_speed_all_time = 0
    fastest_speed = 0
    for index, activity in df.iterrows():
        if activity['type'] == 'Run':
            total_distance += activity['distance']
            total_time_moving += activity['moving_time']
            total_elevation_gain += activity['total_elevation_gain']
            avg_speed_all_time += activity['average_speed']
            fastest_speed = max(fastest_speed, activity['max_speed'])
            i += 1

    total_distance = round(total_distance, 2)
    total_time_moving = round(total_distance, 2)
    total_elevation_gain = round(total_elevation_gain, 2)
    avg_speed_all_time = round(avg_speed_all_time/i, 2)
    fastest_speed = round(fastest_speed, 2)

    return total_distance, total_time_moving, total_elevation_gain, avg_speed_all_time, fastest_speed


def plot_paces(df) -> None:
    """
    Produces a bar chart of all of the user's runs within certain times (:00 - :59).
    :param df:
    :return:
    """
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
    plt.show()


def plot_average_speed_over_time(df) -> None:
    """
    Produces a scatter plot with a trend line that shows average speed over time cumulatively since the user
    started running.
    :param df:
    :return:
    """
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

    # Show the plot
    plt.show()


def plot_distance_over_time(df) -> None:
    """
    Produces a scatter plot with a trend line that shows distance over time cumulatively since the user
    started running.
    :param df:
    :return:
    """
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

    # Show the plot
    plt.show()


def plot_runs_by_weekday(df):
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
    plt.figure(figsize=(10, 6))
    plt.bar(days_of_week, counts, color=colors)
    plt.xlabel('Day of the Week')
    plt.ylabel('Number of Runs')
    plt.title('Frequency of Runs by Day of the Week')
    plt.show()

if __name__ == "__main__":
    access_token = request_token()
    header = {'Authorization': 'Bearer ' + access_token}
    all_activities = fetch_activities(header)

    df = pd.DataFrame(all_activities)

    # Uncomment these as you populate the functions
    total_distance, total_time_moving, total_elevation_gain, avg_speed_all_time, fastest_speed = running_stats(df)
    print(f"Total Distance: {total_distance} meters") # meters
    print(f"Total Time Moving: {total_time_moving}") # seconds
    print(f"Total Elevation Gain: {total_elevation_gain}") # meters
    print(f"Average Speed All Time: {avg_speed_all_time}")
    print(f"Fastest Speed: {fastest_speed}")

    plot_paces(df)
    plot_average_speed_over_time(df)
    plot_distance_over_time(df)
    plot_runs_by_weekday(df)
