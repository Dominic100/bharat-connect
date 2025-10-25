# Bharat Connect - Complete Documentation

## Project Overview

**Bharat Connect** is an AI-powered cross-language content discovery platform that bridges India's linguistic divide by enabling seamless search across 10+ Indian languages. It automatically ingests, indexes, and translates content from government news (PIB RSS feeds) and educational resources (DIKSHA), making them discoverable regardless of the user's language preference.

### The Problem

India has 22 official languages and hundreds of dialects, but digital content remains siloed by language. A Hindi speaker cannot discover relevant Telugu educational resources, and an English speaker misses important regional government announcements. This linguistic fragmentation limits access to information and opportunities.

### The Solution

Bharat Connect provides:

- **Automated Multi-Source Data Ingestion**: Discovers and ingests content from RSS feeds and DIKSHA API
- **Cross-Language Semantic Search**: Search in your language, find content in any language
- **AI-Powered Translation \& Summarization**: Gemini 2.0 translates and summarizes results
- **Smart Content Discovery**: Multi-agent system learns and adapts feed sources
- **Real-Time Data Pipeline**: Daily automated updates via Fivetran → BigQuery

***

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAYER 1: DATA INGESTION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐         ┌─────────────────────────┐  │
│  │   RSS Feed MAS       │         │  DIKSHA Discovery Agent │  │
│  │  (Multi-Agent System)│         │    (API Scraper)        │  │
│  │                      │         │                         │  │
│  │ • Intelligent Feed   │         │ • Content Discovery     │  │
│  │   Agent              │         │ • Multi-language        │  │
│  │ • Validator Agent    │         │ • Batch Processing      │  │
│  │ • RAG Agent          │         │ • Rate Limiting         │  │
│  │ • Learning Agent     │         │                         │  │
│  │ • Coordinator        │         │                         │  │
│  └──────┬───────────────┘         └────────┬────────────────┘  │
│         │                                  │                    │
│         ▼                                  ▼                    │
│   discovery_results.json           diksha_content.json         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              LAYER 2: ETL & DATA WAREHOUSE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐         ┌─────────────────────────┐  │
│  │ Connector Generators │         │  Fivetran Connectors    │  │
│  │                      │         │                         │  │
│  │ • RSS Connector Gen  │────────▶│ • RSS Connector        │  │
│  │ • DIKSHA Connector   │         │ • DIKSHA Connector     │  │
│  │   Gen                │         │                         │  │
│  └──────────────────────┘         └────────┬────────────────┘  │
│                                            │                    │
│                                            ▼                    │
│                                    ┌────────────────┐           │
│                                    │   BigQuery     │           │
│                                    │                │           │
│                                    │ • rss_content  │           │
│                                    │ • diksha_      │           │
│                                    │   content      │           │
│                                    └────────┬───────┘           │
│                                             │                   │
└─────────────────────────────────────────────┼───────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LAYER 3: AI & SEARCH                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Bharat Connect Agent                         │  │
│  │                                                            │  │
│  │  ┌──────────────────┐  ┌─────────────────────────────┐  │  │
│  │  │ BigQuery Search  │  │   Gemini AI (Vertex AI)     │  │  │
│  │  │     Tool         │  │                             │  │  │
│  │  │                  │  │ • Translation Tool          │  │  │
│  │  │ • RSS Table      │  │ • Summarization Tool        │  │  │
│  │  │ • DIKSHA Table   │  │ • Rate Limiting             │  │  │
│  │  │ • Multi-lang     │  │                             │  │  │
│  │  │   filtering      │  │                             │  │  │
│  │  └──────────────────┘  └─────────────────────────────┘  │  │
│  │                                                            │  │
│  │  Flow:                                                     │  │
│  │  1. Search in user's language                             │  │
│  │  2. If no results → search all languages                  │  │
│  │  3. Translate & summarize cross-language content          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 4: USER INTERFACE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Streamlit Web Application                    │  │
│  │                                                            │  │
│  │  • Interactive language circle visualization              │  │
│  │  • Cross-language search interface                        │  │
│  │  • Real-time results with translation indicators          │  │
│  │  • Content type filtering (News/Education)                │  │
│  │  • Support for 10 Indian languages                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              LAYER 5: AUTOMATION & ORCHESTRATION                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Automated Pipeline (Daily Scheduler)            │  │
│  │                                                            │  │
│  │  1. Run RSS Feed MAS → discovery_results.json            │  │
│  │  2. Run DIKSHA Discovery → diksha_content.json           │  │
│  │  3. Generate RSS Connector                                │  │
│  │  4. Generate DIKSHA Connector                             │  │
│  │  5. Deploy RSS Connector (Fivetran)                       │  │
│  │  6. Deploy DIKSHA Connector (Fivetran)                    │  │
│  │  7. Data syncs to BigQuery automatically                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```


***

## Technology Stack

**Data Ingestion \& Processing:**

- Python 3.12
- Multi-Agent System (custom framework)
- DIKSHA Public API
- RSS Feed Parsing (feedparser)

**Data Warehouse \& ETL:**

- Google BigQuery
- Fivetran (custom Python connectors)
- Fivetran SDK

**AI \& Machine Learning:**

- Google Vertex AI (Gemini 2.0 Flash Exp)
- Translation \& Summarization
- Cross-language semantic search

**Frontend:**

- Streamlit
- Interactive data visualization

**Automation:**

- Python scheduling (APScheduler)
- Subprocess orchestration
- Error handling \& logging

***

## Project Structure

```
bharat-connect/
│
├── agents/                         # All Agents
│   ├── main.py                     # MAS entry point & orchestration
│   ├── coordinator.py              # Agent coordination logic
│   ├── intelligent_feed_agent.py   # Discovers RSS feeds
│   ├── validator_agent.py          # Validates content quality
│   ├── rag_agent.py                # Retrieval Augmented Generation
│   ├── learning_agent.py           # Learns from user behavior
│   ├── validation_store.py         # Persistent validation state
│   ├── diksha_discovery_agent.py   # DIKSHA API scraper & processor
│   ├── bharat_agent.py             # Cross-language search agent
│   └── agent_tools.py              # BigQuery & AI tools
│   
├── connectors/                      # Fivetran Connector Generation
│   ├── rss-connector/
│   │   ├── generate_connector.py   # Generates RSS Fivetran connector
│   │   └── connector.py            # Generated RSS connector (auto)
│   │
│   └── diksha-connector/
│       ├── generate_connector.py   # Generates DIKSHA Fivetran connector
│       └── connector.py            # Generated DIKSHA connector (auto)
│
├── app.py                           # Streamlit web application
├── automated_pipeline.py            # Daily automation scheduler
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git ignore file
├── .env.example                     # Environment variables template
└── README.md                        # This file
```


***

## Setup \& Installation

### Prerequisites

1. **Google Cloud Platform Account**
    - Vertex AI API enabled
    - BigQuery dataset created
    - Service account with appropriate permissions
2. **Fivetran Account**
    - API key for connector deployment
3. **Python 3.12+**

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/bharat-connect.git
cd bharat-connect

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```


### Environment Variables

Create a `.env` file:

```bash
# Google Cloud
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Fivetran
FIVETRAN_API_KEY=your-fivetran-api-key
FIVETRAN_DESTINATION=your-bigquery-destination

# BigQuery
BIGQUERY_DATASET=bharat_connect
```


***

## Usage

### 1. Run RSS Feed Discovery (Multi-Agent System)

```bash
cd agents
python main.py
```

**Output:** `discovery_results.json` containing discovered RSS feeds

### 2. Run DIKSHA Content Discovery

```bash
cd diksha
python diksha_discovery_agent.py
```

**Output:** `diksha_content.json` containing educational content

### 3. Generate \& Deploy Fivetran Connectors

```bash
# Generate RSS Connector
cd connectors/rss-connector
python generate_connector.py

# Generate DIKSHA Connector
cd ../diksha-connector
python generate_connector.py

# Deploy connectors
fivetran deploy --api-key <API_KEY> --destination <DEST> --connection rss_connector
fivetran deploy --api-key <API_KEY> --destination <DEST> --connection diksha_connector
```


### 4. Run Streamlit UI

```bash
cd ui
streamlit run app.py
```

Access at `http://localhost:8501`

### 5. Run Automated Pipeline (Daily)

```bash
python automated_pipeline.py
```

Runs daily at midnight, automating steps 1-3.

***

## Features

### Cross-Language Search

- **Language-Agnostic Discovery**: Search in Hindi, find Telugu results
- **Graceful Fallback**: Tries user's language first, then all languages
- **Translation Transparency**: Shows original language \& translation status
- **AI-Powered Summarization**: Concise 3-bullet summaries


### Supported Languages

- Hindi (हिन्दी)
- English
- Telugu (తెలుగు)
- Tamil (தமிழ்)
- Marathi (मराठी)
- Gujarati (ગુજરાતી)
- Kannada (ಕನ್ನಡ)
- Malayalam (മലയാളം)
- Bengali (বাংলা)
- Punjabi (ਪੰਜਾਬੀ)


### Content Sources

**News (RSS Feeds):**

- Press Information Bureau (PIB)
- Multiple regional offices
- 10+ language editions

**Education (DIKSHA):**

- NCERT textbooks \& resources
- State board materials
- Grade-wise content (1-12)
- Subject-specific resources

***

## Data Pipeline Flow

```
1. DATA DISCOVERY
   ├── RSS MAS discovers feeds → discovery_results.json
   └── DIKSHA Agent scrapes content → diksha_content.json

2. CONNECTOR GENERATION
   ├── generate_connector.py (RSS) → connector.py
   └── generate_connector.py (DIKSHA) → connector.py

3. FIVETRAN DEPLOYMENT
   ├── Deploy RSS connector → Fivetran
   └── Deploy DIKSHA connector → Fivetran

4. DATA SYNC
   ├── Fivetran → BigQuery (rss_content table)
   └── Fivetran → BigQuery (diksha_content table)

5. USER QUERY
   ├── Streamlit UI → Bharat Agent
   ├── BigQuery Search (both tables)
   ├── Cross-language results
   ├── Gemini AI Translation
   ├── Gemini AI Summarization
   └── Display results
```


***

## BigQuery Schema

### RSS Content Table

```sql
CREATE TABLE rss_content (
  content_id STRING,
  title STRING,
  description STRING,
  content STRING,
  language STRING,              -- 'hi', 'en', 'te', 'ta', 'mr', 'gu', 'kn', 'ml', 'bn', 'pa'
  source STRING,                -- "Press Information Bureau", etc.
  source_type STRING,           -- "Government", etc.
  rss_feed_url STRING,          -- URL of the RSS feed
  article_url STRING,           -- URL to original article
  published_date TIMESTAMP,
  ingested_at TIMESTAMP,
  keywords STRING,
  _fivetran_synced TIMESTAMP,
  _fivetran_deleted BOOLEAN,
  id STRING,                    -- Secondary ID
  url STRING                    -- Alternate URL
);
```


### DIKSHA Content Table

```sql
CREATE TABLE diksha_content (
  content_id STRING,
  title STRING,
  description STRING,
  language JSON,                -- ["en", "hi", "te"]
  subject JSON,                 -- ["Mathematics", "Science"]
  grade_level JSON,             -- ["Class 10", "Class 11"]
  board STRING,                 -- "CBSE", "State Board", "ICSE"
  medium JSON,                  -- ["English", "Hindi"]
  framework STRING,             -- Curriculum framework
  primary_category STRING,
  content_type STRING,          -- "TextBook", "Video", "Assessment"
  mime_type STRING,
  status STRING,                -- "Live", "Draft", "Retired"
  channel STRING,               -- DIKSHA channel ID
  source STRING,                -- "DIKSHA"
  diksha_url STRING,            -- URL to DIKSHA platform
  created_on STRING,            -- ISO format timestamp
  last_updated_on STRING,       -- ISO format timestamp
  _fivetran_synced TIMESTAMP,
  _fivetran_deleted BOOLEAN,
  ingested_at TIMESTAMP
);
```


***

## API Rate Limiting

**Gemini AI (Vertex AI):**

- Translation: 30 second delay between calls
- Summarization: 30 second delay between calls
- Configurable in `agent_tools.py`

**DIKSHA API:**

- 500ms delay between requests
- Batch processing (50 items per request)
- Automatic retry on rate limit errors

***

## Contributing

This project is open for contributions. Areas of improvement:

1. **More Data Sources**: Add Wikipedia, news APIs
2. **Better Translation**: Fine-tune models for Indian languages
3. **UI Enhancements**: Mobile-responsive design
4. **Performance**: Caching, parallel processing
5. **Testing**: Unit tests, integration tests

***


## License

MIT License - Feel free to use, modify, and distribute.

***

## Acknowledgments

- Google Cloud Platform (Vertex AI, BigQuery)
- Fivetran (Custom connectors)
- DIKSHA (Educational content)
- Press Information Bureau (Government news)

***

## Contact

For questions or collaboration:

- GitHub: Dominic100
- Email: aneeshdeshmukh3@gmail.com

***

**Built with ❤️ to bridge India's linguistic divide**