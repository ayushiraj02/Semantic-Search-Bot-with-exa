import os
from exa_py import Exa
import google.generativeai as genai
from dotenv import load_dotenv
import textwrap
import requests
import argparse
from datetime import datetime, timedelta
import re
 
load_dotenv()

exa = Exa(api_key=os.getenv('EXA_API_KEY'))
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def search_with_exa(query, num_results=5, is_weather=False):
    """
    Uses Exa.ai to search the web and retrieve clean text content from the top results.
    Optimized for weather queries with better sources.
    """
    print(f"🔍 Searching the web for: '{query}'...")
    
    # Enhance weather queries with better sources
    if is_weather and "weather" in query.lower():
        query = f"{query} forecast weather.com OR accuweather.com OR wunderground.com OR timeanddate.com"
    
    try:
        search_response = exa.search_and_contents(
            query,
            type="neural",
            use_autoprompt=True,
            text={
                "max_characters": 2000,
                "include_html_tags": False
            },
            highlights={
                "highlights_per_url": 3,
                "num_sentences": 2,
                "query": query
            }, 
            num_results=num_results
        )
        return search_response.results
    except Exception as e:
        print(f"❌ Error calling Exa API: {e}")
        return None

def format_context(search_results):
    """
    Formats the search results into a single string of context for the LLM.
    Includes source URLs for citation.
    """
    if not search_results:
        return "No search results were found."
    
    context_parts = ["Here is the context from a web search for your question:"]
    for i, result in enumerate(search_results):
        content = ""
        if hasattr(result, 'highlights') and result.highlights:
            content = "... ".join(result.highlights)
        elif hasattr(result, 'text') and result.text:
            content = textwrap.shorten(result.text, width=500, placeholder="...")
        else:
            content = "No content available for this result."
        
        context_parts.append(f"[Source {i+1}: {result.url}]\n{content}\n")
    
    return "\n\n".join(context_parts)

def generate_answer_with_gemini(user_query, context):
    """
    Sends the user query and retrieved context to Google's Gemini API to generate a final answer.
    """
    print("🧠 Generating answer with Gemini...")
    
    # This is the crucial prompt for the RAG system.
    system_instructions = """You are a helpful AI assistant. Your knowledge is limited to ONLY the context provided below from a recent web search.
    Instructions:
    1. Answer the user's question based STRICTLY on the provided context.
    2. If the context does not contain the answer, you must clearly state "I cannot find a definitive answer based on the recent search results."
    3. Be concise, informative, and factual.
    4. Cite your sources by referring to the source numbers in brackets (e.g., [Source 1]) throughout your answer.
    """
    
    # Combine the instructions, context, and user question into a single prompt for Gemini
    full_prompt = f"""{system_instructions}

    {context}

    User Question: {user_query}
    
    Now, provide your answer based on the context above:
    """
    
    try:
        # Generate content using the combined prompt
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"❌ Error calling Gemini API: {e}"

def is_date_beyond_forecast_range(date_str):
    """
    Check if a date is beyond the 5-day forecast range of OpenWeatherMap API
    """
    try:
        if not date_str:
            return False
            
        if isinstance(date_str, str):
            # Handle relative dates
            if date_str.lower() in ['today', 'now']:
                target_date = datetime.now().date()
            elif date_str.lower() == 'tomorrow':
                target_date = (datetime.now() + timedelta(days=1)).date()
            else:
                # Handle various date formats including ordinal numbers (1st, 2nd, etc.)
                date_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
                current_year = datetime.now().year
                date_obj = datetime.strptime(f"{date_clean} {current_year}", "%d %B %Y")
                target_date = date_obj.date()
        else:
            target_date = date_str
        
        max_forecast_date = datetime.now().date() + timedelta(days=4)
        return target_date > max_forecast_date
        
    except ValueError:
        return False

def get_weather_forecast(city="Mohali", date=None):
    """
    Get weather forecast data from OpenWeatherMap API for a specific date
    Works for any city worldwide
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return "Weather API key not configured. Please add OPENWEATHER_API_KEY to your .env file"
    
    try:
        # First get coordinates for the city
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        geo_response = requests.get(geo_url)
        
        if geo_response.status_code != 200 or not geo_response.json():
            return f"City '{city}' not found. Please check the city name."
            
        location = geo_response.json()[0]
        lat, lon = location['lat'], location['lon']
        city_name = location.get('name', city)  # Use the official city name from API
        
        # Get 5-day forecast
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        forecast_response = requests.get(forecast_url)
        
        if forecast_response.status_code != 200:
            return f"Weather API error: {forecast_response.status_code}"
            
        forecast_data = forecast_response.json()
        
        # If no specific date requested, return current weather
        if not date:
            current_weather = get_current_weather(city)
            return current_weather
            
        # Parse the requested date
        try:
            if isinstance(date, str):
                # Handle relative dates
                if date.lower() in ['today', 'now']:
                    target_date = datetime.now().date()
                elif date.lower() == 'tomorrow':
                    target_date = (datetime.now() + timedelta(days=1)).date()
                else:
                    # Try to parse date string (e.g., "5 september", "31st august")
                    # Remove ordinal suffixes (st, nd, rd, th)
                    date_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date)
                    current_year = datetime.now().year
                    date_str = f"{date_clean} {current_year}"
                    target_date = datetime.strptime(date_str, "%d %B %Y").date()
            else:
                target_date = date
        except ValueError:
            return f"Could not understand the date '{date}'. Please use formats like 'today', 'tomorrow', or '5 September'."
        
        # Check if date is within 5-day forecast range
        today = datetime.now().date()
        max_forecast_date = today + timedelta(days=4)  # 5-day forecast includes today + 4 days
        
        if target_date < today:
            return f"Cannot provide weather for past dates. The forecast is only available for dates from {today.strftime('%B %d')} to {max_forecast_date.strftime('%B %d')}."
        
        if target_date > max_forecast_date:
            return f"Forecast not available for {target_date.strftime('%B %d')}. The OpenWeatherMap API only provides 5-day forecasts (up to {max_forecast_date.strftime('%B %d')})."
        
        # Find forecast for the target date
        forecasts_for_date = []
        for forecast in forecast_data['list']:
            forecast_date = datetime.fromtimestamp(forecast['dt']).date()
            if forecast_date == target_date:
                forecasts_for_date.append(forecast)
        
        if not forecasts_for_date:
            return f"No forecast available for {target_date.strftime('%B %d')} in {city_name}."
        
        # Get the most relevant forecast (usually midday)
        best_forecast = max(forecasts_for_date, key=lambda x: 12 - abs(datetime.fromtimestamp(x['dt']).hour - 12))
        
        # Format weather forecast
        date_str = target_date.strftime('%B %d')
        return (f"Weather forecast for {city_name} on {date_str}: "
                f"{best_forecast['weather'][0]['description'].title()}, "
                f"Temperature: {best_forecast['main']['temp']}°C, "
                f"Humidity: {best_forecast['main']['humidity']}%")
    
    except Exception as e:
        return f"Error fetching weather forecast: {str(e)}"

def get_current_weather(city="Mohali"):
    """
    Get current weather data from OpenWeatherMap API for any city worldwide
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return "Weather API key not configured. Please add OPENWEATHER_API_KEY to your .env file"
    
    try:
        # First get coordinates for the city to get the official name
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        geo_response = requests.get(geo_url)
        
        if geo_response.status_code != 200 or not geo_response.json():
            return f"City '{city}' not found. Please check the city name."
            
        location = geo_response.json()[0]
        city_name = location.get('name', city)  # Use the official city name from API
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 404:
            return f"City '{city_name}' not found. Please check the city name."
        elif response.status_code != 200:
            return f"Weather API error: {response.status_code}"
            
        response.raise_for_status()
        data = response.json()
        
        # Format weather data
        return (f"Current weather in {city_name}: {data['weather'][0]['description'].title()}, "
                f"Temperature: {data['main']['temp']}°C, "
                f"Humidity: {data['main']['humidity']}%")
    
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

def extract_weather_info_from_query(query):
    """
    Try to extract city name and date from weather queries
    Returns: (city, date)
    """
    # Remove question marks and make lowercase
    query = query.lower().replace('?', '')
    
    # Common weather-related words to ignore
    weather_keywords = {'what', 'is', 'the', 'weather', 'temperature', 'of', 
                       'forecast', 'in', 'at', 'for', 'today', 'tomorrow',
                       'how', 'hot', 'cold', 'humid', 'rain', 'snow', 'update',
                       'date', 'and', 'will', 'be', 'on'}
    
    # Extract date information
    date = None
    date_patterns = [
        r'tomorrow',
        r'today',
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, query)
        if match:
            if pattern == r'tomorrow':
                date = 'tomorrow'
            elif pattern == r'today':
                date = 'today'
            else:
                day = match.group(1)
                month = match.group(2)
                date = f"{day} {month}"
            # Remove the date part from the query to help city extraction
            query = re.sub(pattern, '', query)
            break
    
    # Extract city name - look for words that aren't weather keywords
    words = query.split()
    potential_cities = []
    
    # Look for pattern: "weather in [city]" 
    if 'in' in words:
        in_index = words.index('in')
        if in_index + 1 < len(words):
            potential_city = words[in_index + 1]
            if potential_city not in weather_keywords and len(potential_city) > 2:
                return (potential_city.capitalize(), date)
    
    # If no "in" found, look for words that might be city names
    for word in words:
        if (word not in weather_keywords and len(word) > 2 and 
            not word.isdigit() and not re.match(r'^\d', word)):
            potential_cities.append(word)
    
    # Return the longest potential city name (most specific)
    if potential_cities:
        city = max(potential_cities, key=len).capitalize()
    else:
        city = "Mohali"  # default
    
    return (city, date)

def get_valid_input(prompt, valid_responses=None):
    """
    Get valid input from user with error handling
    """
    while True:
        try:
            user_input = input(prompt).strip().lower()
            if not user_input:
                continue
                
            if valid_responses:
                if user_input in valid_responses:
                    return user_input
                else:
                    print(f"Please enter one of: {', '.join(valid_responses)}")
            else:
                return user_input
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting program. Goodbye!")
            exit()
        except Exception as e:
            print(f"Input error: {e}")

def main():
    """
    Main function to run the simple RAG tool with an infinite question loop.
    """
    parser = argparse.ArgumentParser(description="RAG Tool with Exa.ai and Gemini")
    parser.add_argument("query", nargs='?', help="Your question to research")
    parser.add_argument("--num-results", type=int, default=5, help="Number of search results")
    parser.add_argument("--city", default="Mohali", help="City for weather queries")
    
    args = parser.parse_args()
    
    print("\n=== Mini RAG Tool with Exa.ai and Gemini ===")
    
    while True:
        # Get user input if not provided as argument
        if args.query:
            user_query = args.query
            args.query = None  # Clear query to allow interactive input in next iteration
        else:
            user_query = get_valid_input("\nPlease enter your question (or 'quit' to exit): ")
        
        if not user_query:
            continue
            
        if user_query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        # Check if this is a weather query
        weather_keywords = ['weather', 'temperature', 'forecast', 'humidity', 'rain', 'snow']
        is_weather_query = any(keyword in user_query.lower() for keyword in weather_keywords)
        
        if is_weather_query:
            city, date = extract_weather_info_from_query(user_query)
            
            # Check if date is beyond API range
            if date and is_date_beyond_forecast_range(date):
                print(f"📅 Date beyond 5-day forecast range. Searching web for weather information...")
                weather_info = None
            else:
                if date:
                    weather_info = get_weather_forecast(city, date)
                else:
                    weather_info = get_current_weather(city)
                
                if weather_info:
                    print(f"\n🌤️  {weather_info}")
                    
                    # Only ask about additional search if API provided valid data
                    if "not available" not in weather_info.lower() and "error" not in weather_info.lower():
                        proceed = get_valid_input("\nWould you like additional information? (y/n): ", ['y', 'n', 'yes', 'no'])
                        if proceed in ['n', 'no']:
                            continue
        
        # If weather API couldn't provide data or it's not a weather query, proceed with web search
        try:
            search_results = search_with_exa(user_query, args.num_results, is_weather=is_weather_query)
        except Exception as e:
            print(f"❌ Error during search: {e}")
            continue
        
        if not search_results:
            print("Failed to retrieve search results. Continuing to next query.")
            continue
        
        # Format the results into a context string
        context = format_context(search_results)
        
        # (Optional) Print context for debugging
        print("\n--- Retrieved Context ---")
        print(context[:1000] + "..." if len(context) > 1000 else context)
        
        # Generate a final answer using the context and Gemini
        final_answer = generate_answer_with_gemini(user_query, context)
        
        # Present the answer to the user
        print("\n" + "="*50)
        print("Answer:")
        print("="*50)
        print(final_answer)

# Run the main function if the script is executed directly
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting program. Goodbye!")