# 📊 Instant BI — Chat with Your Data

![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

**Instant BI** is a powerful, AI-driven Business Intelligence application that lets you chat with your data in natural language. Upload files (CSV, Excel, PDF), connect to SQL databases (PostgreSQL, MySQL, SQLite), and get instant dashboards, KPIs, insights, and visualizations — all through a conversational interface.

---

## ✨ Features

### 🗄️ Multi-Source Data Loading
- **CSV** — comma-separated, auto-encoding detection
- **Excel** — (.xlsx/.xls), multi-sheet support
- **PDF** — table extraction + text fallback
- **PostgreSQL / MySQL / SQLite** — direct database connections
- **Generic SQL** — any SQLAlchemy-compatible database

### 🤖 Multi-LLM Support
- **OpenAI** — GPT-4o, GPT-4o-mini, o3-mini
- **Anthropic** — Claude Opus 4.8, Sonnet 4.6, Haiku 4.5
- **Google** — Gemini 2.0 Flash/Pro
- **Ollama** — Local models (Llama 3, Mistral, etc.) — no API key needed!
- **LiteLLM** — Universal fallback for any model provider

### 💬 Natural Language Chat
Ask questions like:
- *"What are the top 10 products by revenue?"*
- *"Show me sales trends over time"*
- *"What's the correlation between marketing spend and conversions?"*
- *"Generate a dashboard for this dataset"*
- *"Identify KPIs and anomalies"*

### 📈 Smart Visualizations
- Dynamic chart rendering (bar, line, scatter, pie, area, histogram, box, violin, heatmap, sunburst, funnel)
- Auto-generated dashboards
- Custom chart builder with column/type/aggregation selectors
- Interactive Plotly charts

### 💡 Auto Insights & KPIs
- **Statistical Analysis** — mean, median, std, skewness, kurtosis, normality tests
- **Correlation Detection** — significant pairwise correlations with strength/direction
- **Outlier Detection** — IQR-based with value isolation
- **Trend Analysis** — linear regression with R² and significance
- **AI Narrative Insights** — LLM-generated business insights and recommendations
- **KPI Cards** — automatically identified key metrics with delta indicators

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- pip / pip3

### 2. Setup

```bash
# Clone / enter the project directory
cd instant-bi

# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Or on Mac/Linux
# python3 -m venv venv
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys (Optional — Ollama works without)

```bash
# Copy and edit the .env file
copy .env.example .env
```

Add your API keys:
```env
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=your-google-gemini-key
```

No API keys? No problem — **Ollama** works fully locally:
- Install [Ollama](https://ollama.ai)
- Pull a model: `ollama pull llama3.1`
- Select "Ollama" in the app sidebar

### 4. Run

```bash
# Windows
run.bat

# Or directly
streamlit run app.py --server.port 8501
```

Open **http://localhost:8501** in your browser.

---

## 🧭 Application Walkthrough

### Sidebar
- **Navigation** — switch between all major features
- **LLM Model Selector** — pick your AI model (changes take effect immediately)
- **Active Data Info** — shows the current dataset stats
- **Clear & New** — reset for a fresh analysis

### Pages

| Page | Description |
|------|-------------|
| 💬 **Chat & Analyze** | Ask natural-language questions about your data |
| 📊 **Dashboard Builder** | Auto or manual dashboard construction |
| 💡 **Auto Insights** | Full statistical + AI-powered analysis |
| 🗄️ **Data Sources** | Upload files / connect databases |
| 🎨 **Chart Builder** | Custom chart builder with full control |
| ⚙️ **Settings** | App configuration and session management |

---

## 🏗️ Architecture

```
instant-bi/
├── app.py                 # Main Streamlit application (6 pages)
├── config/
│   ├── settings.py        # .env / environment configuration
│   └── __init__.py
├── data_sources/
│   ├── base.py            # Abstract DataSource + Dataset classes
│   ├── file_sources.py    # CSV, Excel, PDF loaders
│   ├── sql_sources.py     # PostgreSQL, MySQL, SQLite loaders
│   └── __init__.py
├── llm/
│   └── __init__.py        # Multi-provider LLM abstraction (OpenAI, Anthropic, Google, Ollama, LiteLLM)
├── query_engine/
│   └── engine.py          # Natural language → analysis + SQL + chart recs
├── visualization/
│   ├── __init__.py        # Plotly chart rendering + auto dashboard builder
│   └── renderers.py       # Streamlit integration helpers
├── insights/
│   └── __init__.py        # Statistical analysis + KPI detection + AI insights
├── utils/
│   └── __init__.py        # Data cleaning, profiling, formatting utilities
├── ui/
│   └── __init__.py
├── uploads/               # Uploaded file storage
├── style.css              # Custom dark/light hybrid theme
├── requirements.txt       # Python dependencies
├── .env                   # Local environment variables
└── run.bat                # Windows launcher
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit, Plotly, Custom CSS |
| **LLM Integration** | OpenAI SDK, Anthropic SDK, Google Generative AI, Ollama, LiteLLM |
| **Data Processing** | Pandas, NumPy, SciPy |
| **Database** | SQLAlchemy, psycopg2, PyMySQL |
| **File Parsing** | pdfplumber, openpyxl, PyPDF2 |
| **Statistics** | SciPy, NumPy |

---

## 💡 Example Questions

Once you've loaded data, try asking:

**General:**
- "What does this dataset contain? Give me a summary."
- "Show me the first 20 rows"
- "How many missing values are in each column?"

**Analysis:**
- "What are the top 10 values by column X?"
- "What's the average of column Y grouped by column Z?"
- "Is there a correlation between X and Y?"
- "Show me the distribution of X"

**Visualization:**
- "Create a bar chart of X by Y"
- "Show me a time series of X over date"
- "Generate a scatter plot of X vs Y colored by Z"

**Dashboard:**
- "Build a complete dashboard for this data"
- "What KPIs should I track?"
- "Give me an executive summary"

---

## 📝 License

MIT — free for personal and commercial use.

---

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

*Built with ❤️ for data teams who want instant insights.*
