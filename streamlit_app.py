import streamlit as st
import requests
import pandas as pd
import time

# Replace with your actual Google Maps API key
GOOGLE_API_KEY = st.secrets["GOOGLE"]["key"]

def get_coordinates(city):
    """Retrieve latitude and longitude for a given city name using Google Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': city,
        'key': GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("status") != "OK":
        st.write(f"Geocoding error: {data.get('status')}")
        return None

    results = data.get('results')
    if results:
        location = results[0]['geometry']['location']
        return f"{location['lat']},{location['lng']}"
    else:
        st.write("Could not retrieve coordinates for the specified city. Please check the city name and try again.")
        return None

def search_google_maps(query, location, radius_meters=5000):
    """Search for nearby businesses using Google Places API with pagination."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'key': GOOGLE_API_KEY,
        'location': location,
        'radius': radius_meters,
        'keyword': query
    }
    businesses = []
    while True:
        response = requests.get(url, params=params)
        data = response.json()
        results = data.get('results', [])
        
        # Process and store the results
        for place in results:
            place_id = place['place_id']
            details = get_google_place_details(place_id)
            if details:
                businesses.append({
                    'Name': details.get('name', 'N/A'),
                    'Website': details.get('website', 'N/A'),
                    'Address': details.get('formatted_address', 'N/A'),
                    'Phone': details.get('formatted_phone_number', 'N/A'),
                    'Reviews': details.get('user_ratings_total', 0),
                    'Rating': details.get('rating', 'N/A'),
                    'Categories': ', '.join(details.get('types', [])),
                    'Price Level': details.get('price_level', 'N/A')
                })
            time.sleep(0.2)  # Rate limit to avoid exceeding API quotas

        # Check if there's a next page and update the params
        next_page_token = data.get("next_page_token")
        if next_page_token:
            time.sleep(2)  # Short delay before requesting the next page
            params['pagetoken'] = next_page_token
        else:
            break  # No more pages, exit the loop

    return businesses

def get_google_place_details(place_id):
    """Retrieve detailed information for a specific place using Google Place Details API."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'key': GOOGLE_API_KEY,
        'place_id': place_id,
        'fields': 'name,formatted_address,formatted_phone_number,website,user_ratings_total,rating,types,price_level'
    }
    response = requests.get(url, params=params)
    return response.json().get('result', {})

# Streamlit UI
st.title("Local Business Finder (Google API Only)")
search_term = st.text_input("Enter a search term (e.g., 'horse products', 'animal feed')", "animal feed")
city = st.text_input("Enter the city and state (e.g., 'Grants Pass, OR')", "Grants Pass, Oregon")
radius_miles = st.slider("Select search radius (miles)", min_value=1, max_value=30, value=5)
min_reviews = st.number_input("Minimum number of reviews", min_value=0, value=10)

# Convert miles to meters
radius_meters = radius_miles * 1609.34

# Adding a simple spinner during the search operation
if st.button("Search"):
    with st.spinner("Searching for businesses..."):
        # Get coordinates for the city
        location = get_coordinates(city)
        if location:
            # Perform the search if coordinates were retrieved
            google_results = search_google_maps(search_term, location, radius_meters)
            
            # Convert results to DataFrame and filter by minimum reviews
            results_df = pd.DataFrame(google_results)

            # Ensure 'Reviews' column exists before filtering
            if 'Reviews' in results_df.columns:
                results_df = results_df[results_df['Reviews'] >= min_reviews]
            else:
                st.write("No review data available for filtering.")

            # Configure the Website column as a clickable link and display results
            if not results_df.empty:
                st.write("Businesses found:")
                st.dataframe(
                    results_df,
                    column_config={
                        "Website": st.column_config.LinkColumn("Website", required=False)
                    }
                )
            else:
                st.write("No businesses found for this search term, location, and review threshold.")