import streamlit as st
import sqlite3
import pymongo
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from edgar import Company, set_identity
import datetime

# Page Configuration
st.set_page_config(page_title="FinCore AI 2025 - Unified Dashboard", layout="wide", initial_sidebar_state="expanded")

# SEC Identity Setup
set_identity("allpubg576@gmail.com")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_mongo_client():
    """Connect to MongoDB with fallback ports"""
    ports = [27017, 27018]
    for port in ports:
        try:
            client = pymongo.MongoClient(f"mongodb://127.0.0.1:{port}/", serverSelectionTimeoutMS=2000)
            client.server_info()
            return client, port
        except:
            continue
    return None, None

def init_sqlite_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect("finance_warehouse.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financials (
            ticker TEXT,
            year INTEGER,
            revenue REAL,
            net_income REAL,
            assets REAL,
            liabilities REAL,
            equity REAL,
            PRIMARY KEY (ticker, year)
        )
    """)
    conn.commit()
    conn.close()

def calculate_advanced_metrics(row):
    """Calculate Altman Z-Score proxy"""
    try:
        if row['assets'] == 0 or row['liabilities'] == 0:
            return None
        liquidity = (row['assets'] - row['liabilities']) / row['assets']
        profitability = row['net_income'] / row['assets'] if row['assets'] != 0 else 0
        z_score = (1.2 * liquidity) + (3.3 * profitability) + (0.6 * (row['equity']/row['liabilities']))
        return round(z_score, 2)
    except:
        return None

def calculate_financial_ratios(df):
    """Calculate financial ratios"""
    df = df.copy()
    df['ROE'] = (df['net_income'] / df['equity']).round(4) if 'equity' in df.columns else None
    df['Debt_to_Equity'] = (df['liabilities'] / df['equity']).round(4) if 'equity' in df.columns else None
    df['Profit_Margin'] = (df['net_income'] / df['revenue']).round(4) if 'revenue' in df.columns else None
    df['Asset_Turnover'] = (df['revenue'] / df['assets']).round(4) if 'assets' in df.columns else None
    return df

# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def fetch_to_sqlite(tickers):
    """Fetch data and save to SQLite"""
    conn = sqlite3.connect("finance_warehouse.db")
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, t in enumerate(tickers):
        try:
            status_text.text(f"🔍 Fetching {t}... ({idx+1}/{len(tickers)})")
            company = Company(t)
            filings = company.get_filings(form="10-K", amendments=False)
            
            if filings.empty:
                st.warning(f"⚠️ No 10-K found for {t}")
                continue
            
            latest_filing = filings.latest()
            fin = latest_filing.obj().financials
            
            data = {
                "ticker": t,
                "year": datetime.datetime.now().year,
                "revenue": fin.get_revenue(),
                "net_income": fin.get_net_income(),
                "assets": fin.get_total_assets(),
                "equity": fin.get_total_equity(),
                "liabilities": fin.get_total_liabilities()
            }
            
            # Validation
            data['audit_pass'] = 1 if abs(data['assets'] - (data['liabilities'] + data['equity'])) < 1e6 else 0
            results.append(data)
            
            progress_bar.progress((idx + 1) / len(tickers))
            
        except Exception as e:
            st.error(f"❌ Error for {t}: {e}")
            continue
    
    if results:
        df = pd.DataFrame(results)
        df.to_sql("financials", conn, if_exists="append", index=False, method="multi")
        st.success(f"✅ Successfully saved {len(results)} companies to SQLite!")
    
    conn.close()
    progress_bar.empty()
    status_text.empty()

def fetch_to_mongodb(tickers):
    """Fetch data and save to MongoDB"""
    client, port = get_mongo_client()
    if client is None:
        st.error("❌ MongoDB not available. Please start MongoDB service.")
        return
    
    db = client["FinDataWarehouse"]
    collection = db["filings"]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, t in enumerate(tickers):
        try:
            status_text.text(f"🔍 Fetching {t}... ({idx+1}/{len(tickers)})")
            company = Company(t)
            filings = company.get_filings(form="10-K", amendments=False)
            
            if filings.empty:
                st.warning(f"⚠️ No 10-K found for {t}")
                continue
            
            latest_filing = filings.latest()
            fin = latest_filing.obj().financials
            
            filing_date = latest_filing.filing_date
            if isinstance(filing_date, datetime.date) and not isinstance(filing_date, datetime.datetime):
                filing_date = datetime.datetime.combine(filing_date, datetime.time.min)
            
            document = {
                "ticker": t,
                "timestamp": datetime.datetime.now(),
                "report_type": "10-K",
                "financials": {
                    "revenue": fin.get_revenue(),
                    "net_income": fin.get_net_income(),
                    "total_assets": fin.get_total_assets(),
                    "total_liabilities": fin.get_total_liabilities()
                },
                "metadata": {
                    "company_name": company.name,
                    "cik": company.cik,
                    "filing_date": filing_date
                }
            }
            
            a = document["financials"]["total_assets"]
            l = document["financials"]["total_liabilities"]
            document["audit_pass"] = 1 if a > 0 else 0
            
            collection.update_one({"ticker": t}, {"$set": document}, upsert=True)
            progress_bar.progress((idx + 1) / len(tickers))
            
        except Exception as e:
            st.error(f"❌ Error for {t}: {e}")
            continue
    
    st.success(f"✅ Successfully synced {len(tickers)} companies to MongoDB!")
    progress_bar.empty()
    status_text.empty()

# ============================================================================
# MAIN APP
# ============================================================================

st.title(" FinCore : Unified Financial Data Warehouse")
st.markdown("**Enterprise-grade financial analytics platform with SQLite & MongoDB support**")

# Initialize SQLite
init_sqlite_db()

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

# Data Source Selection
data_source = st.sidebar.radio(
    "📊 Data Source",
    ["SQLite", "MongoDB"],
    help="Select your preferred database"
)

# Load Data Based on Source
df = pd.DataFrame()
mongo_data = []

if data_source == "SQLite":
    try:
        conn = sqlite3.connect("finance_warehouse.db")
        df = pd.read_sql("SELECT * FROM financials", conn)
        conn.close()
        if not df.empty:
            st.sidebar.success(f"✅ Loaded {len(df)} records from SQLite")
        else:
            st.sidebar.info("📝 No data in SQLite. Fetch data to get started.")
    except Exception as e:
        st.sidebar.error(f"❌ SQLite Error: {e}")

else:  # MongoDB
    client, port = get_mongo_client()
    if client:
        try:
            db = client["FinDataWarehouse"]
            collection = db["filings"]
            mongo_data = list(collection.find({}, {"_id": 0}))
            
            if mongo_data:
                df_flat = pd.json_normalize(mongo_data)
                # Normalize MongoDB structure to match SQLite
                df = pd.DataFrame({
                    'ticker': df_flat['ticker'],
                    'revenue': df_flat['financials.revenue'],
                    'net_income': df_flat['financials.net_income'],
                    'assets': df_flat['financials.total_assets'],
                    'liabilities': df_flat['financials.total_liabilities'],
                    'equity': df_flat['financials.total_assets'] - df_flat['financials.total_liabilities']
                })
                st.sidebar.success(f"✅ Loaded {len(df)} records from MongoDB (port {port})")
            else:
                st.sidebar.info("📝 No data in MongoDB. Fetch data to get started.")
        except Exception as e:
            st.sidebar.error(f"❌ MongoDB Error: {e}")
    else:
        st.sidebar.warning("⚠️ MongoDB not connected. Using SQLite mode only.")

# Main Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Dashboard", 
    "🔍 Data Explorer", 
    "📊 Analytics", 
    "💾 Data Management",
    "📄 Document Viewer"
])

# ============================================================================
# TAB 1: DASHBOARD
# ============================================================================

with tab1:
    if df.empty:
        st.info("👈 Fetch data from the 'Data Management' tab to see the dashboard")
    else:
        st.header("📊 Financial Overview Dashboard")
        
        # Calculate ratios
        df_with_ratios = calculate_financial_ratios(df)
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", len(df))
        with col2:
            st.metric("Total Revenue", f"${df['revenue'].sum()/1e12:.2f}T")
        with col3:
            st.metric("Total Net Income", f"${df['net_income'].sum()/1e9:.2f}B")
        with col4:
            avg_margin = (df['net_income'] / df['revenue']).mean() * 100
            st.metric("Avg Profit Margin", f"{avg_margin:.2f}%")
        
        st.divider()
        
        # Charts Row 1
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Revenue Comparison")
            fig_rev = px.bar(df.sort_values('revenue', ascending=False), 
                            x='ticker', y='revenue',
                            title="Revenue by Company",
                            labels={'revenue': 'Revenue ($)', 'ticker': 'Ticker'},
                            template="plotly_dark",
                            color='revenue',
                            color_continuous_scale='Viridis')
            st.plotly_chart(fig_rev, use_container_width=True)
        
        with col2:
            st.subheader("Net Income Comparison")
            fig_ni = px.bar(df.sort_values('net_income', ascending=False),
                           x='ticker', y='net_income',
                           title="Net Income by Company",
                           labels={'net_income': 'Net Income ($)', 'ticker': 'Ticker'},
                           template="plotly_dark",
                           color='net_income',
                           color_continuous_scale='Plasma')
            st.plotly_chart(fig_ni, use_container_width=True)
        
        # Charts Row 2
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Profit Margin Analysis")
            if 'Profit_Margin' in df_with_ratios.columns:
                fig_margin = px.bar(df_with_ratios.sort_values('Profit_Margin', ascending=False),
                                   x='ticker', y='Profit_Margin',
                                   title="Net Profit Margin (%)",
                                   labels={'Profit_Margin': 'Profit Margin', 'ticker': 'Ticker'},
                                   template="plotly_dark",
                                   color='Profit_Margin',
                                   color_continuous_scale='Blues')
                st.plotly_chart(fig_margin, use_container_width=True)
        
        with col2:
            st.subheader("Revenue vs Net Income")
            fig_scatter = px.scatter(df, x='revenue', y='net_income',
                                    text='ticker', size='revenue',
                                    color='ticker',
                                    title="Revenue vs Net Income Scatter",
                                    labels={'revenue': 'Revenue ($)', 'net_income': 'Net Income ($)'},
                                    template="plotly_dark")
            fig_scatter.update_traces(textposition="top center")
            st.plotly_chart(fig_scatter, use_container_width=True)

# ============================================================================
# TAB 2: DATA EXPLORER
# ============================================================================

with tab2:
    st.header("🔍 Data Explorer & SQL Query")
    
    if df.empty:
        st.info("👈 Fetch data from the 'Data Management' tab to explore")
    else:
        # SQL Query Interface
        st.subheader("SQL Query Interface")
        default_query = "SELECT * FROM financials WHERE net_income > 1000"
        
        if data_source == "SQLite":
            search_query = st.text_area("Enter SQL Query", default_query, height=100)
            conn = sqlite3.connect("finance_warehouse.db")
            try:
                query_df = pd.read_sql(search_query, conn)
                st.dataframe(query_df, use_container_width=True)
                st.success(f"✅ Query returned {len(query_df)} rows")
            except Exception as e:
                st.error(f"❌ Invalid SQL Syntax: {e}")
            conn.close()
        else:
            st.info("💡 SQL queries are available only for SQLite. Switch to SQLite data source to use this feature.")
            st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        # What-If Analysis
        st.subheader("🎯 What-If Analysis")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            growth_rate = st.slider("Projected Revenue Growth (%)", -50, 100, 10, 5)
            selected_ticker = st.selectbox("Select Company", df['ticker'].unique() if not df.empty else [])
        
        with col2:
            if selected_ticker and not df.empty:
                company_data = df[df['ticker'] == selected_ticker].iloc[0]
                base_rev = company_data['revenue']
                base_ni = company_data['net_income']
                
                projected_rev = base_rev * (1 + growth_rate/100)
                # Assume profit margin stays constant
                projected_ni = base_ni * (1 + growth_rate/100)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Current Revenue", f"${base_rev:,.0f}", f"{growth_rate}%")
                    st.metric("Projected Revenue", f"${projected_rev:,.0f}")
                with col_b:
                    st.metric("Current Net Income", f"${base_ni:,.0f}", f"{growth_rate}%")
                    st.metric("Projected Net Income", f"${projected_ni:,.0f}")

# ============================================================================
# TAB 3: ANALYTICS
# ============================================================================

with tab3:
    st.header("📊 Advanced Analytics")
    
    if df.empty:
        st.info("👈 Fetch data from the 'Data Management' tab to see analytics")
    else:
        # Calculate all metrics
        df_analytics = calculate_financial_ratios(df.copy())
        df_analytics['Altman_Z_Score'] = df_analytics.apply(calculate_advanced_metrics, axis=1)
        
        # Financial Ratios Table
        st.subheader("📈 Financial Ratios")
        ratios_df = df_analytics[['ticker', 'ROE', 'Debt_to_Equity', 'Profit_Margin', 'Asset_Turnover', 'Altman_Z_Score']].copy()
        st.dataframe(ratios_df.style.format({
            'ROE': '{:.2%}',
            'Debt_to_Equity': '{:.2f}',
            'Profit_Margin': '{:.2%}',
            'Asset_Turnover': '{:.2f}',
            'Altman_Z_Score': '{:.2f}'
        }), use_container_width=True)
        
        st.divider()
        
        # Sector Benchmarking
        st.subheader("📊 Sector Benchmarking")
        col1, col2 = st.columns(2)
        
        with col1:
            avg_margin = (df['net_income'] / df['revenue']).mean()
            avg_roe = (df['net_income'] / df['equity']).mean() if 'equity' in df.columns else 0
            
            df_benchmark = df.copy()
            df_benchmark['margin'] = df_benchmark['net_income'] / df_benchmark['revenue']
            df_benchmark['vs_avg'] = df_benchmark['margin'] - avg_margin
            
            fig_bench = px.bar(df_benchmark.sort_values('margin', ascending=False),
                              x='ticker', y='margin',
                              title=f"Profit Margin vs Average ({avg_margin:.2%})",
                              labels={'margin': 'Profit Margin', 'ticker': 'Ticker'},
                              template="plotly_dark",
                              color='vs_avg',
                              color_continuous_scale='RdYlGn')
            st.plotly_chart(fig_bench, use_container_width=True)
        
        with col2:
            if 'ROE' in df_analytics.columns:
                fig_roe = px.bar(df_analytics.sort_values('ROE', ascending=False),
                                x='ticker', y='ROE',
                                title="Return on Equity (ROE)",
                                labels={'ROE': 'ROE (%)', 'ticker': 'Ticker'},
                                template="plotly_dark",
                                color='ROE',
                                color_continuous_scale='Greens')
                st.plotly_chart(fig_roe, use_container_width=True)
        
        # Altman Z-Score Analysis
        if 'Altman_Z_Score' in df_analytics.columns:
            st.subheader("🏦 Altman Z-Score Analysis")
            st.markdown("""
            **Z-Score Interpretation:**
            - **Z > 2.99**: Safe Zone (Low bankruptcy risk)
            - **1.81 < Z < 2.99**: Gray Zone (Moderate risk)
            - **Z < 1.81**: Distress Zone (High bankruptcy risk)
            """)
            
            df_z = df_analytics[['ticker', 'Altman_Z_Score']].dropna()
            if not df_z.empty:
                fig_z = px.bar(df_z.sort_values('Altman_Z_Score', ascending=False),
                              x='ticker', y='Altman_Z_Score',
                              title="Altman Z-Score by Company",
                              labels={'Altman_Z_Score': 'Z-Score', 'ticker': 'Ticker'},
                              template="plotly_dark",
                              color='Altman_Z_Score',
                              color_continuous_scale='RdYlGn')
                fig_z.add_hline(y=2.99, line_dash="dash", line_color="green", annotation_text="Safe Zone")
                fig_z.add_hline(y=1.81, line_dash="dash", line_color="red", annotation_text="Distress Zone")
                st.plotly_chart(fig_z, use_container_width=True)

# ============================================================================
# TAB 4: DATA MANAGEMENT
# ============================================================================

with tab4:
    st.header("💾 Data Management")
    
    st.subheader("📥 Fetch Data from SEC EDGAR")
    
    # Ticker Input
    ticker_input = st.text_area(
        "Enter tickers (comma-separated)",
        "NVDA, AAPL, MSFT, TSLA, JPM, WMT, LLY, XOM, GOOGL, AMZN",
        help="Enter stock tickers separated by commas"
    )
    
    tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Fetch to SQLite", type="primary", use_container_width=True):
            if tickers:
                with st.spinner("Fetching data from SEC EDGAR..."):
                    fetch_to_sqlite(tickers)
                st.rerun()
            else:
                st.error("Please enter at least one ticker")
    
    with col2:
        if st.button("📥 Fetch to MongoDB", type="primary", use_container_width=True):
            if tickers:
                client, _ = get_mongo_client()
                if client:
                    with st.spinner("Fetching data from SEC EDGAR..."):
                        fetch_to_mongodb(tickers)
                    st.rerun()
                else:
                    st.error("MongoDB not available. Please start MongoDB service.")
            else:
                st.error("Please enter at least one ticker")
    
    st.divider()
    
    # Database Statistics
    st.subheader("📊 Database Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**SQLite Database**")
        try:
            conn = sqlite3.connect("finance_warehouse.db")
            sqlite_count = pd.read_sql("SELECT COUNT(*) as count FROM financials", conn).iloc[0]['count']
            conn.close()
            st.metric("Records", sqlite_count)
        except:
            st.metric("Records", 0)
    
    with col2:
        st.markdown("**MongoDB Database**")
        client, port = get_mongo_client()
        if client:
            try:
                db = client["FinDataWarehouse"]
                collection = db["filings"]
                mongo_count = collection.count_documents({})
                st.metric("Records", mongo_count)
            except:
                st.metric("Records", 0)
        else:
            st.metric("Records", "N/A (Not Connected)")

# ============================================================================
# TAB 5: DOCUMENT VIEWER (MongoDB Only)
# ============================================================================

with tab5:
    st.header("📄 MongoDB Document Viewer")
    
    if data_source == "MongoDB":
        client, port = get_mongo_client()
        if client and mongo_data:
            selected_ticker = st.selectbox("Select Ticker", [d['ticker'] for d in mongo_data])
            raw_doc = next((d for d in mongo_data if d['ticker'] == selected_ticker), None)
            
            if raw_doc:
                st.subheader(f"Raw Document for {selected_ticker}")
                st.json(raw_doc)
                
                # Formatted View
                st.subheader("Formatted View")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Financials**")
                    if 'financials' in raw_doc:
                        fin = raw_doc['financials']
                        st.write(f"Revenue: ${fin.get('revenue', 0):,.0f}")
                        st.write(f"Net Income: ${fin.get('net_income', 0):,.0f}")
                        st.write(f"Total Assets: ${fin.get('total_assets', 0):,.0f}")
                        st.write(f"Total Liabilities: ${fin.get('total_liabilities', 0):,.0f}")
                
                with col2:
                    st.markdown("**Metadata**")
                    if 'metadata' in raw_doc:
                        meta = raw_doc['metadata']
                        st.write(f"Company: {meta.get('company_name', 'N/A')}")
                        st.write(f"CIK: {meta.get('cik', 'N/A')}")
                        st.write(f"Filing Date: {meta.get('filing_date', 'N/A')}")
        else:
            st.info("💡 Connect to MongoDB and fetch data to view documents")
    else:
        st.info("💡 Switch to MongoDB data source to view NoSQL documents")

# ============================================================================
# FOOTER
# ============================================================================

st.sidebar.divider()
st.sidebar.markdown("**FinCore AI 2025**")
st.sidebar.markdown("Enterprise Financial Analytics")
