# Equipo 1
import os
import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

# SETTING PAGE CONFIG TO WIDE MODE AND ADDING A TITLE AND FAVICON
st.set_page_config(layout="wide", page_title="SF Incident Analytics", page_icon=":bridge_at_night:")

# INITIALIZE SESSION STATE
if "incident_hour" not in st.session_state:
    st.session_state.incident_hour = 0
if "selected_category" not in st.session_state:
    st.session_state.selected_category = ""

# LOAD DATA ONCE
@st.cache_resource
def load_data():
    path = "Police_Department_Incident_Reports__2018_to_Present.csv.zip"
    if not os.path.isfile(path):
        path = f"https://raw.githubusercontent.com/Charlyval01/San-Francisco-Insights-streamlit-/main/{path}"

    data = pd.read_csv(
        path,
        usecols=["Incident Datetime", "Latitude", "Longitude", "Incident Day of Week", "Incident Category"],
        parse_dates=["Incident Datetime"],
    )

    return data

# FUNCTION FOR INCIDENT MAPS
def map(data, Latitude, Longitude, zoom):
    st.write(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state={
                "latitude": Latitude,
                "longitude": Longitude,
                "zoom": zoom,
                "pitch": 50,
            },
            layers=[
                pdk.Layer(
                    "HexagonLayer",
                    data=data,
                    get_position=["Longitude", "Latitude"],
                    radius=100,
                    elevation_scale=4,
                    elevation_range=[0, 1000],
                    pickable=True,
                    extruded=True,
                ),
            ],
        )
    )

# FILTER DATA FOR A SPECIFIC HOUR AND CATEGORY, CACHE
@st.cache_data
def filterdata(df, hour_selected, category_selected, day_selected):
    df.dropna(subset=['Latitude'], inplace=True)
    df.dropna(subset=['Longitude'], inplace=True)

    # Convert "Incident Datetime" to datetime format
    df["Incident Datetime"] = pd.to_datetime(df["Incident Datetime"])

    filtered_df = df[df["Incident Datetime"].dt.hour == hour_selected]
    filtered_df = filtered_df[filtered_df["Incident Category"] == category_selected]
    filtered_df = filtered_df[filtered_df["Incident Day of Week"] == day_selected]
    return filtered_df

# CALCULATE MIDPOINT FOR GIVEN SET OF DATA
@st.cache_data
def mpoint(lat, lon):
    lat_numeric = pd.to_numeric(lat, errors="coerce")
    lon_numeric = pd.to_numeric(lon, errors="coerce")

    # Check if there are valid numeric values
    if not np.isnan(lat_numeric).all() and not np.isnan(lon_numeric).all():
        lat_avg = np.nanmean(lat_numeric)
        lon_avg = np.nanmean(lon_numeric)
        return (lat_avg, lon_avg)
    else:
        # Return a default location if no valid values are found
        return (37.7749, -122.4194)  # Default to San Francisco's coordinates

# FILTER DATA BY HOUR
@st.cache_data
def histdata(df, hr):
    filtered = df[
        (df["Incident Datetime"].dt.hour >= hr) & (df["Incident Datetime"].dt.hour < (hr + 1))
    ]

    hist = np.histogram(filtered["Incident Datetime"].dt.minute, bins=60, range=(0, 60))[0]

    return pd.DataFrame({"minute": range(60), "incidents": hist})

# UPDATE QUERY PARAMS FUNCTION
def update_query_params():
    hour_selected = st.session_state.incident_hour
    category_selected = st.session_state.selected_category
    st.experimental_set_query_params(incident_hour=hour_selected, selected_category=category_selected)

# STREAMLIT APP LAYOUT
data = load_data()

# LAYING OUT THE TOP SECTION OF THE APP
top_section_col = st.columns(1)[0]

# ADDING TITLE ABOVE THE FILTERS
with top_section_col:
    st.title("Distribution of criminal incidents in San Francisco")
    st.write("*By San Francisco City Council in conjunction with San Francisco Police Department*")

    st.markdown("""
        The following map provides an accurate visualization of how crimes are distributed in the different zones of San Francisco
        according to the week day, hour when they happened, and the type of crime committed. 
        The histogram below shows the quantity of crimes with these characteristics divided by the hours in the minute. 
        We encourage you to add crime reports in this page to update the map for all users and have more information about them.
        Use the three filters below to select the type of crime and the hour/day you want to see on the map.
    """)

# LAYING OUT THE MIDDLE SECTION OF THE APP WITH THE FILTERS
middle_section_col = st.columns(3)

# ADDING DROPDOWN FOR INCIDENT CATEGORY
with middle_section_col[1]:
    selected_category = st.selectbox("Select Incident Category", data["Incident Category"].unique())
    st.session_state.selected_category = selected_category
    update_query_params()  # Update query parameters when category is selected

with middle_section_col[0]:
    selected_day = st.selectbox("Select Incident Day", data["Incident Day of Week"].unique())
    st.session_state.selected_day = selected_day
    update_query_params()  # Update query parameters when day is selected

# ADDING HOUR SLIDER
with middle_section_col[2]:
    st.slider(
        "Select hour of incident",
        0, 23, key="incident_hour", on_change=update_query_params,
    )

# LAYING OUT THE BOTTOM SECTION OF THE APP WITH THE MAP AND HISTOGRAM
bottom_section_col = st.columns(1)[0]  # Use a single column

# SETTING THE ZOOM LOCATIONS FOR THE MAP
sf_midpoint = mpoint(data["Latitude"], data["Longitude"])
zoom_level = 12

with bottom_section_col:
    st.write(
        f"""**All incidents in SF between {st.session_state.incident_hour}:00 and {(st.session_state.incident_hour + 1) % 24}:00**"""
    )
    filtered_data = filterdata(data, st.session_state.incident_hour, st.session_state.selected_category, st.session_state.selected_day)
    map(filtered_data, sf_midpoint[0], sf_midpoint[1], 11)

    # CALCULATING DATA FOR THE HISTOGRAM
    chart_data = histdata(filtered_data, st.session_state.incident_hour)

    # LAYING OUT THE HISTOGRAM SECTION
    st.write(
        f"""**Breakdown of incidents per minute between {st.session_state.incident_hour}:00 and {(st.session_state.incident_hour + 1) % 24}:00**"""
    )

    st.altair_chart(
        alt.Chart(chart_data)
        .mark_area(
            interpolate="step-after",
        )
        .encode(
            x=alt.X("minute:Q", scale=alt.Scale(nice=False)),
            y=alt.Y("incidents:Q"),
            tooltip=["minute", "incidents"],
        )
        .configure_mark(opacity=0.8, color='red'),
        use_container_width=True,
    )

# ... (remaining code remains unchanged)
st.sidebar.header("Add New Incident")

new_date = st.sidebar.date_input("Incident Date", pd.to_datetime("today"))
new_time = st.sidebar.time_input("Incident Time", pd.to_datetime("now").time())
new_datetime = pd.to_datetime(f"{new_date} {new_time}")
new_latitude = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, step=0.0001)
new_longitude = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, step=0.0001)
new_day_of_week = st.sidebar.selectbox("Incident Day of Week", data["Incident Day of Week"].unique())
new_category = st.sidebar.text_input("Incident Category")

if st.sidebar.button("Add Incident"):
    # Create a new row with user input
    new_row = {
        "Incident Datetime": new_datetime,
        "Latitude": new_latitude,
        "Longitude": new_longitude,
        "Incident Day of Week": new_day_of_week,
        "Incident Category": new_category,
    }

    # Append the new row to the data DataFrame
    data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)

    # Display a success message
    st.sidebar.success("Incident added successfully!")

    st.write("Last Row Added:")
    st.write(data.tail(1))

    # Use st.spinner to temporarily hide and then show the updated content
    with st.spinner("Updating map and histogram..."):
        # Update the map and histogram with the new data
        filtered_data = filterdata(data, st.session_state.incident_hour, st.session_state.selected_category, st.session_state.selected_day)
        sf_midpoint = mpoint(filtered_data["Latitude"], filtered_data["Longitude"])

        # Display the map
        st.write(
            f"""**All incidents in SF between {st.session_state.incident_hour}:00 and {(st.session_state.incident_hour + 1) % 24}:00**"""
        )
        map(filtered_data, sf_midpoint[0], sf_midpoint[1], 11)

        # Display the histogram
        st.write(
            f"""**Breakdown of incidents per minute between {st.session_state.incident_hour}:00 and {(st.session_state.incident_hour + 1) % 24}:00**"""
        )
        chart_data = histdata(filtered_data, st.session_state.incident_hour)
        st.altair_chart(
            alt.Chart(chart_data)
            .mark_area(interpolate="step-after")
            .encode(x=alt.X("minute:Q", scale=alt.Scale(nice=False)), y=alt.Y("incidents:Q"), tooltip=["minute", "incidents"])
            .configure_mark(opacity=0.8, color='red'),
            use_container_width=True,
        )