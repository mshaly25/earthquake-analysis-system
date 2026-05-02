import sys
import os
import streamlit as st
import urllib.request
import json
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta, date

st.set_page_config(
    page_title="Earthquake Analysis System",
    page_icon="🌍",
    layout="wide"
)

if "earthquakes" not in st.session_state:
    st.session_state.earthquakes = []
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_title" not in st.session_state:
    st.session_state.report_title = ""


def classify_quake(magnitude):
    if magnitude is None:
        return "Unclassified"
    elif magnitude >= 7.0:
        return "🔴 Major"
    elif magnitude >= 5.0:
        return "🟠 Strong"
    elif magnitude >= 3.0:
        return "🟡 Moderate"
    else:
        return "🟢 Minor"


def get_data(report_type, start_date=None, end_date=None, min_mag=2.5):
    if report_type == "Last 24 Hours":
        url   = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
        title = "Report: Last 24 Hours"
    elif report_type == "Last 7 Days":
        url   = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"
        title = "Report: Last 7 Days"
    elif report_type == "Last 30 Days":
        url   = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
        title = "Report: Last 30 Days"
    elif report_type == "Specific Day":
        start_str = start_date.strftime('%Y-%m-%d')
        end_str   = (start_date + timedelta(days=1)).strftime('%Y-%m-%d')
        url = (
            f"https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson"
            f"&starttime={start_str}"
            f"&endtime={end_str}"
            f"&minmagnitude={min_mag}"
        )
        title = f"Report: {start_str}"
    elif report_type == "Custom Period":
        start_str = start_date.strftime('%Y-%m-%d')
        end_str   = end_date.strftime('%Y-%m-%d')
        url = (
            f"https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson"
            f"&starttime={start_str}"
            f"&endtime={end_str}"
            f"&minmagnitude={min_mag}"
        )
        title = f"Report: {start_str} to {end_str}"

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return [], ""

    earthquakes = []
    for quake in data["features"]:
        mag = quake["properties"]["mag"]
        if mag is None:
            continue
        earthquakes.append({
            "place"    : quake["properties"]["place"],
            "magnitude": mag,
            "depth"    : round(quake["geometry"]["coordinates"][2], 2),
            "lat"      : quake["geometry"]["coordinates"][1],
            "lon"      : quake["geometry"]["coordinates"][0],
            "category" : classify_quake(mag)
        })

    return earthquakes, title


def build_map(earthquakes, max_points=500):
    m = folium.Map(location=[20, 0], zoom_start=2)

    display_quakes = earthquakes
    if len(earthquakes) > max_points:
        sorted_all    = sorted(earthquakes, key=lambda x: x["magnitude"], reverse=True)
        display_quakes = sorted_all[:max_points]
        st.info(
            f"Map is showing the top {max_points} strongest earthquakes "
            f"out of {len(earthquakes)} total records."
        )

    color_map = {
        "🔴 Major"   : "red",
        "🟠 Strong"  : "orange",
        "🟡 Moderate": "yellow",
        "🟢 Minor"   : "green",
        "Unclassified": "gray"
    }

    for quake in display_quakes:
        color = color_map.get(quake["category"], "blue")
        folium.CircleMarker(
            location     = [quake["lat"], quake["lon"]],
            radius       = quake["magnitude"] * 3,
            color        = color,
            fill         = True,
            fill_opacity = 0.7,
            popup        = folium.Popup(
                f"<b>{quake['place']}</b><br>"
                f"Magnitude : {quake['magnitude']}<br>"
                f"Depth     : {quake['depth']} km<br>"
                f"Category  : {quake['category']}",
                max_width=250
            ),
            tooltip=f"M {quake['magnitude']} | {quake['place']}"
        ).add_to(m)

    return m


def build_report(earthquakes, title, strongest, deepest, avg_mag, sorted_q, categories):
    lines = [
        "EARTHQUAKE ANALYSIS REPORT",
        "=" * 50,
        f"Generated   : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Report Type : {title}",
        f"Data Source : USGS Earthquake Hazards Program",
        "=" * 50,
        "",
        "SUMMARY STATISTICS",
        "-" * 30,
        f"Total Events    : {len(earthquakes)}",
        f"Average Magnitude: {round(avg_mag, 2)}",
        "",
        "CLASSIFICATION BREAKDOWN",
        "-" * 30,
    ]
    for cat, count in categories.items():
        lines.append(f"  {cat}: {count} events")

    lines += [
        "",
        "STRONGEST EVENT",
        "-" * 30,
        f"  Location  : {strongest['place']}",
        f"  Magnitude : {strongest['magnitude']}",
        f"  Depth     : {strongest['depth']} km",
        "",
        "DEEPEST EVENT",
        "-" * 30,
        f"  Location  : {deepest['place']}",
        f"  Depth     : {deepest['depth']} km",
        "",
        "TOP 10 STRONGEST EVENTS",
        "-" * 30,
    ]
    for i, q in enumerate(sorted_q[:10]):
        lines.append(f"  {i+1:2}. M{q['magnitude']} | {q['place']}")

    lines += ["", "=" * 50]
    return "\n".join(lines)


st.title("🌍 Earthquake Analysis System")
st.caption("Real-time and historical earthquake data powered by USGS")
st.divider()

with st.sidebar:
    st.header("Report Settings")

    report_type = st.selectbox(
        "Report Type",
        ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Specific Day", "Custom Period"]
    )

    start_date = end_date = None
    min_mag    = 2.5

    if report_type == "Specific Day":
        start_date = st.date_input("Select Date", value=date.today() - timedelta(days=1))
        min_mag    = st.slider("Minimum Magnitude", 0.0, 9.0, 2.5)

    elif report_type == "Custom Period":
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        end_date   = st.date_input("End Date",   value=date.today())
        min_mag    = st.slider("Minimum Magnitude", 0.0, 9.0, 4.5)

    st.divider()
    analyze_btn = st.button("Analyze", use_container_width=True)

if analyze_btn:
    with st.spinner("Fetching data from USGS..."):
        earthquakes, title = get_data(report_type, start_date, end_date, min_mag)
        st.session_state.earthquakes  = earthquakes
        st.session_state.report_ready = True
        st.session_state.report_title = title

if st.session_state.report_ready:
    earthquakes = st.session_state.earthquakes
    title       = st.session_state.report_title

    if len(earthquakes) == 0:
        st.warning("No earthquakes found for the selected period. Try lowering the minimum magnitude.")
    else:
        st.subheader(title)

        strongest = max(earthquakes, key=lambda x: x["magnitude"])
        deepest   = max(earthquakes, key=lambda x: x["depth"])
        avg_mag   = sum(q["magnitude"] for q in earthquakes) / len(earthquakes)
        sorted_q  = sorted(earthquakes, key=lambda x: x["magnitude"], reverse=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Events",       len(earthquakes))
        with col2:
            st.metric("Strongest",          f"M {strongest['magnitude']}")
        with col3:
            st.metric("Average Magnitude",  round(avg_mag, 2))
        with col4:
            st.metric("Deepest",            f"{deepest['depth']} km")

        st.divider()
        # Mobile hint
if st.session_state.report_ready == False:
    st.markdown("""
    <div style="
        background-color: #1E88E5;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        font-size: 16px;
        margin-bottom: 10px;
    ">
        📱 Mobile Users: Tap the <b>arrow (›)</b> at the top-left to open settings
    </div>
    """, unsafe_allow_html=True)
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Classification Breakdown")
            categories = {}
            for quake in earthquakes:
                cat = quake["category"]
                categories[cat] = categories.get(cat, 0) + 1
            for cat, count in categories.items():
                st.metric(cat, f"{count} events")

        with col_right:
            st.subheader("Top 10 Strongest Events")
            for i, q in enumerate(sorted_q[:10]):
                st.write(f"{i+1}. **M{q['magnitude']}** | {q['category']} | {q['place']}")

        st.divider()

        st.subheader("Seismic Map")
        st.caption("🟢 Minor  🟡 Moderate  🟠 Strong  🔴 Major | Circle size = Magnitude")
        m = build_map(earthquakes)
        st_folium(m, width=1200, height=500, returned_objects=[])

        st.divider()

        st.subheader("Download Report")

        report_text = build_report(
            earthquakes, title, strongest, deepest, avg_mag, sorted_q, categories
        )

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type"       : "Point",
                        "coordinates": [q["lon"], q["lat"]]
                    },
                    "properties": {
                        "place"    : q["place"],
                        "magnitude": q["magnitude"],
                        "depth"    : q["depth"],
                        "category" : q["category"]
                    }
                }
                for q in earthquakes
            ]
        }

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                label    = "Download Report (.txt)",
                data     = report_text,
                file_name= f"earthquake_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime     = "text/plain"
            )
        with col_d2:
            st.download_button(
                label    = "Download GeoJSON",
                data     = json.dumps(geojson_data, ensure_ascii=False, indent=2),
                file_name= f"earthquakes_{datetime.now().strftime('%Y%m%d_%H%M')}.geojson",
                mime     = "application/json"
            )

else:
    st.info("Select a report type from the sidebar and click Analyze.")
    st.markdown("""
    ### System Features
    | Feature | Description |
    |---|---|
    | Last 24 Hours | Real-time earthquake data |
    | Last 7 Days | Weekly seismic activity |
    | Last 30 Days | Monthly overview |
    | Specific Day | Historical data for any date |
    | Custom Period | Define your own date range |
    | Interactive Map | Visual seismic map with popups |
    | GeoJSON Export | Ready for GIS applications |
    | Report Export | Professional text report |
    """)
