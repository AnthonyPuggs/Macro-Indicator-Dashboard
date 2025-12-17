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

@st.cache_data(ttl=3600)
def get_rba_data():
    """Fetches the Official Cash Rate (OCR) from the RBA."""
    try:
        # read_rba_ocr returns a pandas Series with a PeriodIndex
        ocr_series = ra.read_rba_ocr()
        
        # FIX 1: Convert PeriodIndex to Timestamp for Plotly compatibility
        # If the index is already datetime, this line is harmless. 
        # If it is a Period (e.g. '2023-11'), it becomes 2023-11-01.
        if isinstance(ocr_series.index, pd.PeriodIndex):
            ocr_series.index = ocr_series.index.to_timestamp()
        
        # Convert to DataFrame
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
        # Catalogue 6202.0, Series ID A84423050A
        # This function returns a tuple: (DataFrame, Metadata)
        abs_data, abs_meta = ra.read_abs_series("6202.0", "A84423050A")
        
        # FIX: Remove the manual filtering for 'series_id'. 
        # The function read_abs_series already fetched the specific data we asked for.
        df_unemp = abs_data.copy()
        
        # Normalize column names to lowercase to avoid "Date" vs "date" issues
        df_unemp.columns = [c.lower() for c in df_unemp.columns]
        
        # Ensure the date column is in the right format
        # Sometimes it comes as a 'Period' (e.g., "Sep-2023") which crashes plots
        if 'date' in df_unemp.columns:
            if pd.api.types.is_period_dtype(df_unemp['date']):
                 df_unemp['date'] = df_unemp['date'].dt.to_timestamp()
            else:
                 df_unemp['date'] = pd.to_datetime(df_unemp['date'])
                 
        df_unemp = df_unemp.sort_values('date')
        
        return df_unemp
    except Exception as e:
        st.error(f"Error fetching ABS data: {e}")
        # DEBUG: If it fails, uncomment the line below to see what columns ARE there
        # st.write("Available columns:", ra.read_abs_series("6202.0", "A84423050A")[0].columns)
        return pd.DataFrame()

# --- Main App Layout ---

col1, col2 = st.columns(2)

# Load Data
with st.spinner('Fetching data from RBA and ABS...'):
    df_rba = get_rba_data()
    df_abs = get_abs_data()

# --- Section 1: RBA Cash Rate ---
with col1:
    st.subheader("🏦 RBA Official Cash Rate")
    
    if not df_rba.empty:
        latest_ocr = df_rba['Cash Rate'].iloc[-1]
        prev_ocr = df_rba['Cash Rate'].iloc[-2]
        delta = latest_ocr - prev_ocr
        
        st.metric(
            label="Current Cash Rate", 
            value=f"{latest_ocr}%", 
            delta=f"{delta:.2f}%",
            delta_color="inverse"
        )
        
        fig_rba = px.line(
            df_rba, 
            x='Date', 
            y='Cash Rate', 
            title='RBA Official Cash Rate History',
            template="plotly_white"
        )
        fig_rba.update_traces(line_color='#FF5733')
        
        # FIX 3: Replaced deprecated use_container_width=True with width="stretch"
        st.plotly_chart(fig_rba, width="stretch")

# --- Section 2: ABS Unemployment ---
with col2:
    st.subheader("👷 ABS Unemployment Rate")
    
    if not df_abs.empty:
        latest_unemp = df_abs['value'].iloc[-1]
        prev_unemp = df_abs['value'].iloc[-2]
        delta_unemp = latest_unemp - prev_unemp
        
        st.metric(
            label="Unemployment Rate (Seas. Adj.)", 
            value=f"{latest_unemp}%", 
            delta=f"{delta_unemp:.2f}%",
            delta_color="inverse"
        )
        
        fig_abs = px.line(
            df_abs, 
            x='date', 
            y='value', 
            title='Unemployment Rate (Seasonally Adjusted)',
            template="plotly_white"
        )
        fig_abs.update_traces(line_color='#33C1FF')
        
        # FIX 3: Replaced deprecated use_container_width=True with width="stretch"
        st.plotly_chart(fig_abs, width="stretch")

# --- Data Explorer ---
with st.expander("📊 View Raw Data"):
    tab1, tab2 = st.tabs(["RBA Data", "ABS Data"])
    with tab1:
        if not df_rba.empty:
            st.dataframe(df_rba.sort_values('Date', ascending=False), width="stretch")
    with tab2:
        if not df_abs.empty:
            st.dataframe(df_abs[['date', 'value', 'series_id']].sort_values('date', ascending=False), width="stretch")

st.markdown("---")
st.caption("Dashboard generated using Streamlit and `readabs`.")