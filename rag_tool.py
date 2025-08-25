import os
from exa_py import Exa
import google.generativeai as genai
from dotenv import load_dotenv
import textwrap
import requests
import argparse
 
load_dotenv()


exa = Exa(api_key=os.getenv('EXA_API_KEY'))
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def search_with_exa(query, num_results=5):
    """
    Uses Exa.ai to search the web and retrieve clean text content from the top results.
    """
    print(f"🔍 Searching the web for: '{query}'...")
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


def get_current_weather(city="Mohali"):
    """
    Get current weather data from OpenWeatherMap API
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return "Weather API key not configured. Please add OPENWEATHER_API_KEY to your .env file"
    
    try:
        # Handle common city variations for your area
        city_mapping = {
            'mohali': 'Mohali',
            'chandigarh': 'Chandigarh',
            'panchkula': 'Panchkula'
        }
        
        city_lower = city.lower()
        if city_lower in city_mapping:
            city = city_mapping[city_lower]
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 404:
            # Try with Chandigarh if Mohali not found
            if city.lower() == 'mohali':
                return get_current_weather("Chandigarh")
            return f"City '{city}' not found. Please check the city name."
        elif response.status_code != 200:
            return f"Weather API error: {response.status_code}"
            
        response.raise_for_status()
        data = response.json()
        
        # Format weather data
        return f"Current weather in {city}: {data['weather'][0]['description']}, Temperature: {data['main']['temp']}°C, Humidity: {data['main']['humidity']}%"
    
    except Exception as e:
        return f"Error fetching weather: {str(e)}"


def extract_city_from_query(query):
    """
    Try to extract city name from weather queries
    """
    # Remove question marks and split into words
    words = query.lower().replace('?', '').split()
    
    # Common weather-related words to ignore
    weather_keywords = {'what', 'is', 'the', 'weather', 'temperature', 'of', 
                       'forecast', 'in', 'at', 'for', 'today', 'tomorrow',
                       'how', 'hot', 'cold', 'humid', 'rain', 'snow', 'update',
                       'date', 'and'}
    
    # Find the word after "in" or look for city names
    city_name = "Mohali"  # default for your area
    
    # Look for pattern: "weather in [city]" or "temperature in [city]"
    if 'in' in words:
        in_index = words.index('in')
        if in_index + 1 < len(words):
            potential_city = words[in_index + 1]
            if potential_city not in weather_keywords and len(potential_city) > 2:
                return potential_city.capitalize()
    
    # If no "in" found, look for the last word that's not a weather keyword
    for word in reversed(words):
        if word not in weather_keywords and len(word) > 2:
            return word.capitalize()
    
    return city_name






def main():
    """
    Main function to run the simple RAG tool.
    """
    parser = argparse.ArgumentParser(description="RAG Tool with Exa.ai and Gemini")
    parser.add_argument("query", nargs='?', help="Your question to research")
    parser.add_argument("--num-results", type=int, default=5, help="Number of search results")
    parser.add_argument("--city", default="London", help="City for weather queries")
    
    args = parser.parse_args()
    
    print("\n=== Mini RAG Tool with Exa.ai and Gemini ===")
    
    # Get user input if not provided as argument
    if args.query:
        user_query = args.query
    else:
        user_query = input("\nPlease enter your question: ").strip()
    
    if not user_query:
        print("Please enter a valid question.")
        return
    
    # Check if this is a weather query
    weather_keywords = ['weather', 'temperature', 'forecast', 'humidity', 'rain']
    is_weather_query = any(keyword in user_query.lower() for keyword in weather_keywords)
    
    if is_weather_query:
        city_from_query = extract_city_from_query(user_query)
        weather_info = get_current_weather(city_from_query)
        print(f"\n🌤️  {weather_info}")
        
        # Ask if user wants additional search
        proceed = input("\nWould you like to also search for related information? (y/n): ")
        if proceed.lower() != 'y':
            return  # Exit if user doesn't want search
        # If user says 'y', continue with the normal RAG flow
    
  

    try:
        search_results = search_with_exa(user_query, args.num_results)
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return
    
    if not search_results:
        print("Failed to retrieve search results. Exiting.")
        return
    
    # ADD THESE MISSING LINES:
    # Step 2: Format the results into a context string
    context = format_context(search_results)
    
    # (Optional) Print context for debugging
    print("\n--- Retrieved Context ---")
    print(context[:1000] + "..." if len(context) > 1000 else context)
    
    # Step 3: Generate a final answer using the context and Gemini
    final_answer = generate_answer_with_gemini(user_query, context)
    
    # Step 4: Present the answer to the user
    print("\n" + "="*50)
    print("Answer:")
    print("="*50)
    print(final_answer)

# Run the main function if the script is executed directly
if __name__ == "__main__":
    main()
