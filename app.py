import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ------------------ CONFIG ------------------
st.set_page_config(layout="wide")

# ------------------ HEADER ------------------
col1, col2, col3 = st.columns([1, 4, 1])

with col1:
    st.markdown("### 🏷️ LOGO")

with col2:
    st.markdown("<h2 style='text-align: center;'>EXECUTIVE DASHBOARD</h2>", unsafe_allow_html=True)

with col3:
    today = datetime.now().strftime("%d %B %Y")
    st.markdown(f"<div style='text-align: right;'>{today}</div>", unsafe_allow_html=True)

st.markdown("---")

# ------------------ SIDEBAR ------------------
st.sidebar.title("Menu")

menu = st.sidebar.radio(
    "",
    ["Upload Data", "Gantt Diagram", "KPI's", "Download"]
)

# ------------------ MAIN AREA ------------------

# Upload Data
if menu == "Upload Data":
    st.header("Upload Data")

    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.success("File uploaded successfully!")
        st.dataframe(df)

        st.session_state["data"] = df

# Gantt Diagram
elif menu == "Gantt Diagram":
    st.header("Gantt Diagram")

    if "data" in st.session_state:
        df = st.session_state["data"]

        # Vérifie colonnes
        if all(col in df.columns for col in ["Task", "Start", "Finish"]):

            fig = px.timeline(
                df,
                x_start="Start",
                x_end="Finish",
                y="Task",
                color="Task"
            )

            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("Dataset must contain: Task, Start, Finish")

    else:
        st.info("Please upload data first.")

# KPI's
elif menu == "KPI's":
    st.header("Key Performance Indicators")

    if "data" in st.session_state:
        df = st.session_state["data"]

        col1, col2, col3 = st.columns(3)

        col1.metric("Number of Tasks", len(df))

        if "Start" in df.columns and "Finish" in df.columns:
            total_duration = df["Finish"].max() - df["Start"].min()
            col2.metric("Total Duration", total_duration)

        col3.metric("Data Loaded", "Yes")

        st.dataframe(df.describe())

    else:
        st.info("Please upload data first.")

# Download
elif menu == "Download":
    st.header("Download Data")

    if "data" in st.session_state:
        df = st.session_state["data"]

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="processed_data.csv",
            mime="text/csv",
        )

    else:
        st.info("No data to download.")