import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import readabs as ra
import st_yled
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Aus Macro Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- Custom CSS for Metrics ---
st.markdown("""
<style>
    /* Remove default background from metrics so they blend in */
    [data-testid="stMetric"] {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("Aus Macro DB")
    st.caption("v2.1 Experimental")
    
    st.markdown("### DASHBOARDS")
    st.button("Overview", use_container_width=True, type="primary")
    st.button("Phillips Curve Model", use_container_width=True)
    
    st.markdown("### DEVELOPER")
    st.button("Source Code", use_container_width=True)
    st.button("Economic Theory", use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Assistant Mode**")
    st.caption("Online • RBA Data Ready")

# --- Helper Functions ---

def card_container(key):
    """Creates a styled container using st_yled with custom hover effects."""
    # Inject custom CSS for properties not yet supported by st_yled (radius, shadow, hover)
    st.markdown(f"""
    <style>
    .st-key-{key} {{
        border-radius: 10px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        transition: border-color 0.3s ease !important;
        padding: 15px !important;
    }}
    .st-key-{key}:hover {{
        border-color: #FF4B4B !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    return st_yled.container(
        key=key,
        background_color="#1C1C1E",
        border_color="#3A3A3C",
        border_width="1px",
        border_style="solid"
    )

@st.cache_data(ttl=3600)
def get_rba_data():
    """Fetches the Official Cash Rate (OCR) from the RBA."""
    try:
        # read_rba_ocr returns a pandas Series with a PeriodIndex
        ocr_series = ra.read_rba_ocr()
        
        # FIX 1: Convert PeriodIndex to Timestamp for Plotly compatibility
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
        abs_data, abs_meta = ra.read_abs_series("6202.0", "A84423050A")
        
        # 1. Reset index to move Dates into a column
        df_unemp = abs_data.reset_index()
        
        # 2. Lowercase all column names for consistency
        df_unemp.columns = [str(c).lower() for c in df_unemp.columns]
        
        # 3. Dynamic Renaming:
        if 'series id' in df_unemp.columns:
            df_unemp = df_unemp.rename(columns={'series id': 'date'})
            
        if 'a84423050a' in df_unemp.columns:
            df_unemp = df_unemp.rename(columns={'a84423050a': 'value'})
            
        # 4. Fallback: If 'index' exists instead, rename it to 'date'
        if 'index' in df_unemp.columns:
            df_unemp = df_unemp.rename(columns={'index': 'date'})

        # 5. Clean up Date Format
        if 'date' in df_unemp.columns:
            # FIX: Use isinstance check on the dtype attribute
            if isinstance(df_unemp['date'].dtype, pd.PeriodDtype):
                 df_unemp['date'] = df_unemp['date'].dt.to_timestamp()
            else:
                 df_unemp['date'] = pd.to_datetime(df_unemp['date'])
                 
        df_unemp = df_unemp.sort_values('date')
        
        return df_unemp
    except Exception as e:
        st.error(f"Error fetching ABS data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_inflation_data():
    """Fetches CPI Trimmed Mean from RBA Table G1."""
    try:
        # RBA Table G1: Consumer Price Inflation
        df_g1, meta = ra.read_rba_table("G1")
        
        # Column: GCPIOCPMTMYP (Trimmed Mean - Year-ended % change)
        if 'GCPIOCPMTMYP' in df_g1.columns:
            series = df_g1['GCPIOCPMTMYP']
            df = series.reset_index()
            df.columns = ['Date', 'Value']
            
            if isinstance(df['Date'].dtype, pd.PeriodDtype) or isinstance(df['Date'].iloc[0], pd.Period):
                 df['Date'] = df['Date'].dt.to_timestamp()
            
            df = df.sort_values('Date')
            # Filter out future dates (forecasts) if any, or just take the latest available
            # RBA tables might contain forecasts. Let's keep all for now or filter <= today?
            # Usually we want the latest actual.
            # Let's just return it all and handle display logic.
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching Inflation data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_exp_inflation_data():
    """Fetches Inflation Expectations from RBA Table G3."""
    try:
        # RBA Table G3: Inflation Expectations
        df_g3, meta = ra.read_rba_table("G3")
        
        # Column: GMAREXPY (Market Economists - 1 year ahead)
        if 'GMAREXPY' in df_g3.columns:
            series = df_g3['GMAREXPY']
            df = series.reset_index()
            df.columns = ['Date', 'Value']
            
            if isinstance(df['Date'].dtype, pd.PeriodDtype) or isinstance(df['Date'].iloc[0], pd.Period):
                 df['Date'] = df['Date'].dt.to_timestamp()
            
            df = df.sort_values('Date')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching Exp Inflation data: {e}")
        return pd.DataFrame()

# --- Main App Layout ---

# Load Data
with st.spinner('Fetching data from RBA and ABS...'):
    df_rba = get_rba_data()
    df_abs = get_abs_data()
    df_cpi = get_inflation_data()
    df_exp = get_exp_inflation_data()

# --- Metrics Row ---
m1, m2, m3, m4 = st.columns(4)

# 1. RBA Cash Rate
with m1:
    with card_container(key="card_m1"):
        if not df_rba.empty:
            latest_ocr = df_rba['Cash Rate'].iloc[-1]
            prev_ocr = df_rba['Cash Rate'].iloc[-2]
            delta = latest_ocr - prev_ocr
            
            st.metric(
                label="RBA Cash Rate", 
                value=f"{latest_ocr:.2f}%", 
                delta=f"{delta:.2f}% (Held)" if delta == 0 else f"{delta:.2f}%",
                delta_color="off" if delta == 0 else "inverse"
            )
        else:
            st.metric("RBA Cash Rate", "N/A")

# 2. Unemployment
with m2:
    with card_container(key="card_m2"):
        if not df_abs.empty:
            latest_unemp = df_abs['value'].iloc[-1]
            prev_unemp = df_abs['value'].iloc[-2]
            delta_unemp = latest_unemp - prev_unemp
            
            st.metric(
                label="Unemployment", 
                value=f"{latest_unemp:.2f}%", 
                delta=f"{delta_unemp:.1f}% vs prev month",
                delta_color="inverse"
            )
        else:
            st.metric("Unemployment", "N/A")

# 3. CPI (Trimmed)
with m3:
    with card_container(key="card_m3"):
        if not df_cpi.empty:
            # Get latest non-NaN value
            valid_cpi = df_cpi.dropna()
            if not valid_cpi.empty:
                latest_cpi = valid_cpi['Value'].iloc[-1]
                # Target: 2-3%
                st.metric(
                    label="CPI (Trimmed)", 
                    value=f"{latest_cpi}%", 
                    delta="Target: 2-3%",
                    delta_color="off" # Grey color for target
                )
            else:
                st.metric("CPI (Trimmed)", "N/A")
        else:
            st.metric("CPI (Trimmed)", "N/A")

# 4. Exp. Inflation (1yr)
with m4:
    with card_container(key="card_m4"):
        if not df_exp.empty:
            valid_exp = df_exp.dropna()
            if not valid_exp.empty:
                latest_exp = valid_exp['Value'].iloc[-1]
                st.metric(
                    label="Exp. Inflation (1yr)", 
                    value=f"{latest_exp}%", 
                    delta="Market Economists",
                    delta_color="off"
                )
            else:
                st.metric("Exp. Inflation (1yr)", "N/A")
        else:
            st.metric("Exp. Inflation (1yr)", "N/A")

st.markdown("---")

# --- Charts Row ---
col1, col2 = st.columns(2)

# --- Section 1: RBA Cash Rate Chart ---
with col1:
    with card_container(key="card_col1"):
        st.subheader("Cash Rate History")
        
        if not df_rba.empty:
            fig_rba = px.line(
                df_rba, 
                x='Date', 
                y='Cash Rate', 
                # title='RBA Official Cash Rate History', # Removed title to match clean look
                template="plotly_dark" # Dark theme to match image
            )
            fig_rba.update_traces(line_color='#F4D03F', hovertemplate='Date: %{x}<br>Value: %{y:.2f}%') # Yellowish color from image
            fig_rba.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                height=300
            )
            
            st.plotly_chart(fig_rba, width="stretch")

# --- Section 2: ABS Unemployment Chart ---
with col2:
    with card_container(key="card_col2"):
        st.subheader("Unemployment Trend")
        
        if not df_abs.empty:
            fig_abs = px.line(
                df_abs, 
                x='date', 
                y='value', 
                # title='Unemployment Rate (Seasonally Adjusted)',
                template="plotly_dark"
            )
            fig_abs.update_traces(line_color='#33C1FF', hovertemplate='Date: %{x}<br>Value: %{y:.2f}%') # Blue color
            fig_abs.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                height=300,
                yaxis_tickformat='.2f'
            )
            
            st.plotly_chart(fig_abs, width="stretch")

# --- Data Explorer / Table View ---
with st.expander("📊 View Raw Data"):
    tab1, tab2, tab3, tab4 = st.tabs(["RBA Cash Rate", "Unemployment", "CPI", "Exp. Inflation"])
    
    with tab1:
        if not df_rba.empty:
            st.dataframe(df_rba.sort_values('Date', ascending=False), width="stretch")
            
    with tab2:
        if not df_abs.empty:
            st.dataframe(df_abs.sort_values('date', ascending=False), width="stretch")
            
    with tab3:
        if not df_cpi.empty:
            st.dataframe(df_cpi.sort_values('Date', ascending=False), width="stretch")
            
    with tab4:
        if not df_exp.empty:
            st.dataframe(df_exp.sort_values('Date', ascending=False), width="stretch")

st.markdown("---")
st.caption("Dashboard generated using Streamlit and `readabs`.")