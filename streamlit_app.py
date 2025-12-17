import streamlit as st
import pandas as pd
import plotly.express as px
import readabs as ra

# Page Configuration
st.set_page_config(
    page_title="Aus Macro Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("🇦🇺 Australian Macroeconomic Dashboard")
st.markdown("Data sourced live from the **RBA** and **ABS** using the `readabs` Python library.")

# --- Helper Functions ---

@st.cache_data(ttl=3600)  # Cache data for 1 hour to prevent spamming the API
def get_rba_data():
    """Fetches the Official Cash Rate (OCR) from the RBA."""
    try:
        # read_rba_ocr returns a pandas Series
        ocr_series = ra.read_rba_ocr()
        
        # Convert to DataFrame for easier plotting
        df_ocr = ocr_series.reset_index()
        df_ocr.columns = ['Date', 'Cash Rate']
        df_ocr = df_ocr.sort_values('Date')
        return df_ocr
    except Exception as e:
        st.error(f"Error fetching RBA data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_abs_data():
    """Fetches Unemployment Rate (Seasonally Adjusted) from ABS."""
    try:
        # Catalogue 6202.0, Series ID A84423050A (Unemployment Rate: Seasonally Adjusted)
        # read_abs_series returns a tuple: (Data, Metadata)
        abs_data, abs_meta = ra.read_abs_series("6202.0", "A84423050A")
        
        # Clean up the DataFrame
        # The library returns columns typically like 'date', 'value', etc.
        # We filter for the specific series just in case, though we requested one.
        df_unemp = abs_data[abs_data['series_id'] == "A84423050A"].copy()
        
        # Ensure date is datetime
        df_unemp['date'] = pd.to_datetime(df_unemp['date'])
        df_unemp = df_unemp.sort_values('date')
        
        return df_unemp
    except Exception as e:
        st.error(f"Error fetching ABS data: {e}")
        return pd.DataFrame()

# --- Main App Layout ---

# Create two columns for the Key Metrics
col1, col2 = st.columns(2)

# Load Data
with st.spinner('Fetching data from RBA and ABS...'):
    df_rba = get_rba_data()
    df_abs = get_abs_data()

# --- Section 1: RBA Cash Rate ---
with col1:
    st.subheader("🏦 RBA Official Cash Rate")
    
    if not df_rba.empty:
        # Metric Display (Current vs Previous)
        latest_ocr = df_rba['Cash Rate'].iloc[-1]
        prev_ocr = df_rba['Cash Rate'].iloc[-2]
        delta = latest_ocr - prev_ocr
        
        st.metric(
            label="Current Cash Rate", 
            value=f"{latest_ocr}%", 
            delta=f"{delta:.2f}%",
            delta_color="inverse" # Interest rate hikes usually displayed as 'red' in finance/inverse logic context, or 'normal'
        )
        
        # Plot
        fig_rba = px.line(
            df_rba, 
            x='Date', 
            y='Cash Rate', 
            title='RBA Official Cash Rate History',
            template="plotly_white"
        )
        fig_rba.update_traces(line_color='#FF5733')
        st.plotly_chart(fig_rba, use_container_width=True)

# --- Section 2: ABS Unemployment ---
with col2:
    st.subheader("👷 ABS Unemployment Rate")
    
    if not df_abs.empty:
        # Metric Display
        latest_unemp = df_abs['value'].iloc[-1]
        prev_unemp = df_abs['value'].iloc[-2]
        delta_unemp = latest_unemp - prev_unemp
        
        st.metric(
            label="Unemployment Rate (Seas. Adj.)", 
            value=f"{latest_unemp}%", 
            delta=f"{delta_unemp:.2f}%",
            delta_color="inverse" # Lower unemployment is green (good)
        )
        
        # Plot
        fig_abs = px.line(
            df_abs, 
            x='date', 
            y='value', 
            title='Unemployment Rate (Seasonally Adjusted)',
            template="plotly_white"
        )
        fig_abs.update_traces(line_color='#33C1FF')
        st.plotly_chart(fig_abs, use_container_width=True)

# --- Data Explorer / Table View ---
with st.expander("📊 View Raw Data"):
    tab1, tab2 = st.tabs(["RBA Data", "ABS Data"])
    with tab1:
        st.dataframe(df_rba.sort_values('Date', ascending=False), use_container_width=True)
    with tab2:
        st.dataframe(df_abs[['date', 'value', 'series_id']].sort_values('date', ascending=False), use_container_width=True)

st.markdown("---")
st.caption("Dashboard generated using Streamlit and `readabs`.")