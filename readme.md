# 🌐 Mini RAG Tool with Exa.ai and Gemini

A powerful Retrieval-Augmented Generation (RAG) tool that combines real-time web search with advanced AI to provide accurate, up-to-date answers to your questions.

## 🚀 Features

- **Real-time Web Search**: Access current information from across the web
- **Weather Integration**: Get current weather and 5-day forecasts for any city worldwide
- **Smart Date Handling**: Understands natural date formats (e.g., "5 September", "tomorrow")
- **Citation Support**: All answers include source references for verification
- **Interactive Interface**: User-friendly command-line interface with intelligent prompts

## 🏗️ Architecture
 User Query → Weather Detection → OpenWeatherMap API (if weather query)
↓
Exa.ai Web Search → Content Retrieval → Context Formatting
↓
Gemini AI Processing → Answer Generation → User Response




## ⭐ Why Exa.ai is Crucial for This Project

Exa.ai is the **core differentiator** that makes this RAG tool truly powerful:

### 🔍 **Intelligent Search Capabilities**
- **Neural Search**: Exa uses AI to understand query intent, not just keyword matching
- **Content Extraction**: Retrieves clean, relevant text content from web pages
- **Smart Highlights**: Automatically extracts the most relevant passages for your query
- **Autoprompting**: Enhances queries automatically for better results

### 🎯 **Superior to Traditional Search APIs**
Unlike traditional search APIs that return just links and snippets, Exa provides:
- **Structured content** with proper context preservation
- **Relevant highlights** tailored to your specific query
- **Clean text extraction** without HTML clutter
- **Quality filtering** of sources

### 💡 **The Exa Advantage in RAG**
Without Exa.ai, this would be just another chatbot with static knowledge. With Exa:
- **Answers are always current** with real-time web data
- **Information is verifiable** through cited sources
- **Context is rich and relevant** thanks to intelligent content extraction
- **Users get comprehensive answers** backed by multiple sources


## 🌤️ Weather Functionality
The tool supports:
Current weather for any city worldwide
5-day forecasts with temperature and humidity
Natural date parsing: "tomorrow", "5 September", "31st August"
Automatic fallback to web search for dates beyond 5 days

## 🔧 How It Works
Query Analysis: Detects if query is weather-related or requires web search
API Integration: Uses OpenWeatherMap for weather data when appropriate
Web Search: Exa.ai searches and retrieves relevant web content
Context Processing: Formats search results with source citations
AI Generation: Gemini creates comprehensive answers based on retrieved context
Response Delivery: Presents well-structured answers with source references

## Use Cases
Research Assistance: Get current information on any topic
Weather Forecasting: Quick weather checks for planning
Fact Verification: Cross-reference information with multiple sources
Learning Tool: Explore topics with up-to-date information
News Monitoring: Stay informed about recent developments


## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd exa-rag-tool

2. **Create virtual environment**
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows