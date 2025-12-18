# FinCore- Unified Financial Data Warehouse

A comprehensive financial data warehouse application that fetches SEC 10-K filings and stores them in either SQLite or MongoDB. Features a unified Streamlit dashboard with all analytics, visualizations, and data management capabilities in one place.

## Features

### 🏛️ Unified Dashboard (`app.py`)
- **📈 Dashboard Tab** - Financial overview with key metrics and interactive charts
- **🔍 Data Explorer Tab** - SQL query interface and data exploration
- **📊 Analytics Tab** - Advanced financial ratios and sector benchmarking
- **💾 Data Management Tab** - Fetch data from SEC EDGAR to SQLite or MongoDB
- **📄 Document Viewer Tab** - MongoDB NoSQL document viewer

### Key Capabilities
- **Dual Database Support** - Switch between SQLite and MongoDB seamlessly
- **Data Fetching** - Automated SEC 10-K filing extraction with progress tracking
- **SQL Queries** - Full SQL query interface for SQLite data
- **Financial Ratios** - ROE, Debt-to-Equity, Profit Margin, Asset Turnover
- **Advanced Metrics** - Altman Z-Score bankruptcy risk analysis
- **What-If Analysis** - Revenue growth simulation and projections
- **Visualizations** - Interactive charts using Plotly (bar, scatter, comparison charts)
- **Sector Benchmarking** - Compare companies against database averages

## Prerequisites

- Python 3.8 or higher
- MongoDB (for MongoDB features) - Optional if only using SQLite

## Installation

1. **Clone or navigate to the project directory**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MongoDB (Optional - only if using MongoDB features):**
   
   **Option A: Local MongoDB Installation**
   - Download MongoDB Community Edition: https://www.mongodb.com/try/download/community
   - Install and start MongoDB service:
     - **Windows**: MongoDB should start automatically, or run `net start MongoDB` in admin PowerShell
     - **Mac**: `brew services start mongodb-community`
     - **Linux**: `sudo systemctl start mongod`
   
   **Option B: MongoDB Atlas (Cloud)**
   - Sign up at https://www.mongodb.com/cloud/atlas
   - Create a free cluster
   - Get connection string and update it in `engine_mongo.py` and `dashboard_mongo.py`

## Configuration

### Update SEC Email Identity

The SEC requires a valid email for API access. The unified app (`app.py`) already has the email configured. If you need to update it, edit line 15 in `app.py`:

```python
set_identity("your_email@example.com")
```

For legacy scripts, update:
- `engine_mongo.py` (line 6)
- `engine.py` (line 5)
- `finance_engine.py` (line 5)

## Running the Application

### Quick Start

Simply run the unified application:

```bash
streamlit run app.py
```

The app will open at http://localhost:8501 with all features available.

### Using the Unified App

1. **Select Data Source** - Use the sidebar to switch between SQLite and MongoDB
2. **Fetch Data** - Go to the "Data Management" tab to fetch company data from SEC EDGAR
3. **Explore** - Use the "Dashboard" tab for visualizations or "Data Explorer" for SQL queries
4. **Analyze** - Check the "Analytics" tab for financial ratios and advanced metrics

### Legacy Scripts (Still Available)

- `engine.py` - Standalone SQLite data fetcher
- `engine_mongo.py` - Standalone MongoDB data fetcher
- `dashboard_mongo.py` - MongoDB-only dashboard (legacy)

## Troubleshooting MongoDB Connection

If you see connection errors:

1. **Check if MongoDB is running:**
   ```bash
   # Windows PowerShell
   Get-Service MongoDB
   
   # Mac/Linux
   brew services list | grep mongodb
   # or
   sudo systemctl status mongod
   ```

2. **Start MongoDB if not running:**
   - **Windows**: Open Services (services.msc) and start MongoDB service, or run `net start MongoDB` in admin PowerShell
   - **Mac**: `brew services start mongodb-community`
   - **Linux**: `sudo systemctl start mongod`

3. **Check MongoDB port:**
   - Default port is 27017
   - The code tries both 27017 and 27018 automatically
   - If using a different port, update the connection string in `engine_mongo.py` and `dashboard_mongo.py`

4. **Test MongoDB connection:**
   ```bash
   # Windows
   mongosh mongodb://127.0.0.1:27017
   
   # Mac/Linux
   mongosh mongodb://127.0.0.1:27017
   ```

5. **For MongoDB Atlas (Cloud):**
   - Update connection string format: `mongodb+srv://username:password@cluster.mongodb.net/`
   - Replace the connection string in both MongoDB files

## Project Structure

```
.
├── app.py                 # SQLite Streamlit dashboard
├── dashboard_mongo.py     # MongoDB Streamlit dashboard
├── engine.py             # SQLite data fetching engine
├── engine_mongo.py       # MongoDB data fetching engine
├── finance_engine.py     # Financial metrics calculator
├── database_manager.py   # SQLite database utilities
├── analytics.py          # Advanced financial metrics
├── config.toml           # Streamlit theme configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Usage Examples

### Using the Unified App

1. **Fetch Data via UI:**
   - Open the app: `streamlit run app.py`
   - Navigate to "Data Management" tab
   - Enter tickers (e.g., "NVDA, AAPL, MSFT")
   - Click "Fetch to SQLite" or "Fetch to MongoDB"

2. **Run SQL Queries:**
   - Switch to SQLite data source
   - Go to "Data Explorer" tab
   - Enter SQL query: `SELECT * FROM financials WHERE revenue > 1000000000`

3. **View Analytics:**
   - Go to "Analytics" tab
   - See financial ratios, ROE, Debt-to-Equity, Altman Z-Score

### Legacy Scripts (Command Line)

```bash
# Fetch to SQLite
python engine.py

# Fetch to MongoDB
python engine_mongo.py
```

## Notes

- The SEC API (`edgar` library) requires a valid email address
- Rate limits may apply when fetching multiple tickers
- Data is fetched from SEC EDGAR database (publicly available)
- MongoDB port defaults to 27017, with fallback to 27018

## License

This project is for educational and demonstration purposes.

## Running

<img width="1920" height="1080" alt="Screenshot 2025-12-19 001513" src="https://github.com/user-attachments/assets/c10b5486-8ed3-460b-82e2-f0617b1c2776" />
<img width="1920" height="1080" alt="Screenshot 2025-12-19 001534" src="https://github.com/user-attachments/assets/c66ba1bb-2739-41a3-83c3-abcf1bb6273c" />

