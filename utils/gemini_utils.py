# utils/gemini_utils.py
import google.generativeai as genai
import json
import logging

logger = logging.getLogger(__name__)

NIFTY_SECTORS_QUERY_CONFIG = {
    "Nifty IT": {
        "newsapi_keywords": [
            "Information Technology India", "Infosys", "TCS", "Wipro", "HCL Technologies",
            "Tech Mahindra", "LTI Mindtree", "software services India", "cloud computing India",
            "artificial intelligence India", "NASSCOM", "Indian IT exports", "Bengaluru tech"
        ]
    },
    "Nifty Bank": {
        "newsapi_keywords": [
            "Banking India", "HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank",
            "RBI", "non-performing assets India", "digital banking India", "UPI India",
            "banking reforms India", "fintech India"
        ]
    },
    "Nifty Auto": {
        "newsapi_keywords": [
            "Automobile industry India", "Maruti Suzuki", "Tata Motors", "Mahindra & Mahindra",
            "Bajaj Auto", "Hero MotoCorp", "electric vehicles India", "auto sales India",
            "auto components India", "FAME scheme India", "BS6 norms India"
        ]
    },
    "Nifty Pharma": {
        "newsapi_keywords": [
            "Pharmaceuticals India", "Sun Pharma", "Dr Reddy's Labs", "Cipla", "Aurobindo Pharma",
            "Lupin", "pharma exports India", "generic drugs India", "DCGI", "USFDA India",
            "pharma R&D India"
        ]
    },
    "Nifty FMCG": {
        "newsapi_keywords": [
            "FMCG India", "Hindustan Unilever", "ITC India", "Nestle India", "Britannia",
            "Dabur India", "Godrej Consumer", "FMCG sales India", "rural consumption India",
            "FMCG marketing India", "FMCG e-commerce India"
        ]
    },
    "Nifty Consumer Durables": {
        "newsapi_keywords": [
            "Consumer durables India", "Havells India", "Voltas", "Whirlpool India",
            "Crompton Greaves", "Bajaj Electricals", "home appliances India",
            "consumer electronics India", "durables sales India", "smart appliances India"
        ]
    },
    "Nifty Financial Services": {
        "newsapi_keywords": [
            "Financial services India", "Bajaj Finance", "HDFC Life", "SBI Life Insurance",
            "Shriram Finance", "Cholamandalam Finance", "NBFC India", "insurance India",
            "SEBI", "fintech India", "digital finance India"
        ]
    },
    "Nifty Media": {
        "newsapi_keywords": [
            "Media India", "Zee Entertainment", "Sun TV Network", "PVR Inox", "Dish TV",
            "Network18", "digital media India", "OTT India", "media advertising India",
            "TRAI", "media consumption India"
        ]
    },
    "Nifty Metal": {
        "newsapi_keywords": [
            "Metals India", "Tata Steel", "JSW Steel", "Hindalco", "Vedanta", "SAIL",
            "steel production India", "aluminium India", "mining India", "metal prices India"
        ]
    },
    "Nifty PSU Bank": {
        "newsapi_keywords": [
            "Public sector banks India", "State Bank of India", "Bank of Baroda",
            "Punjab National Bank", "Canara Bank", "Union Bank of India", "RBI",
            "PSU bank reforms India", "non-performing assets PSU banks", "PSU bank mergers India"
        ]
    },
    "Nifty Private Bank": {
        "newsapi_keywords": [
            "Private banks India", "HDFC Bank", "ICICI Bank", "Axis Bank",
            "Kotak Mahindra Bank", "IndusInd Bank", "RBI", "private bank loans India",
            "digital banking India", "fintech India"
        ]
    },
    "Nifty Realty": {
        "newsapi_keywords": [
            "Real estate India", "DLF", "Godrej Properties", "Oberoi Realty",
            "Prestige Estates", "Brigade Enterprises", "RERA India", "housing India",
            "commercial real estate India", "real estate prices India"
        ]
    },
    "Nifty Commodities": {
        "newsapi_keywords": [
            "Commodities India", "UltraTech Cement", "Shree Cement", "Pidilite Industries",
            "Asian Paints", "Grasim Industries", "cement industry India", "chemicals India",
            "commodities prices India", "commodities exports India"
        ]
    },
    "Nifty Energy": {
        "newsapi_keywords": [
            "Energy India", "Reliance Industries", "NTPC", "Power Grid", "Adani Green Energy",
            "Tata Power", "renewable energy India", "solar energy India", "energy policy India",
            "energy demand India"
        ]
    },
    "Nifty Infrastructure": {
        "newsapi_keywords": [
            "Infrastructure India", "Larsen & Toubro", "Adani Ports", "GMR Infrastructure",
            "IRB Infrastructure", "KNR Constructions", "roads India", "smart cities India",
            "infrastructure financing India", "railways India"
        ]
    },
    "Nifty PSE": {
        "newsapi_keywords": [
            "Public sector enterprises India", "ONGC", "Coal India", "BHEL", "GAIL India",
            "IOC", "PSE disinvestment India", "PSE reforms India", "Indian PSE stocks",
            "PSE earnings India"
        ]
    },
    "Nifty Oil & Gas": {
        "newsapi_keywords": [
            "Oil and gas India", "Reliance Industries", "ONGC", "Indian Oil", "BPCL",
            "HPCL", "GAIL India", "oil exploration India", "gas distribution India",
            "oil prices India", "LNG India"
        ]
    },
    "Nifty Healthcare": {
        "newsapi_keywords": [
            "Healthcare India", "Apollo Hospitals", "Fortis Healthcare", "Max Healthcare",
            "Metropolis Healthcare", "Dr Lal PathLabs", "hospitals India", "telemedicine India",
            "healthcare policy India", "diagnostics India"
        ]
    },
    "Nifty Midcap Liquid 15": {
        "newsapi_keywords": [
            "Midcap India", "Ashok Leyland", "Bharat Forge", "Container Corporation",
            "Tata Power", "Godrej Properties", "midcap stocks India", "midcap growth India",
            "midcap earnings India", "midcap investments India"
        ]
    },
    "Nifty CPSE": {
        "newsapi_keywords": [
            "CPSE India", "NTPC", "Power Grid", "Oil India", "NBCC India", "BHEL",
            "CPSE disinvestment India", "CPSE reforms India", "Indian CPSE stocks",
            "CPSE earnings India"
        ]
    },
    "Nifty Services Sector": {
        "newsapi_keywords": [
            "Services sector India", "Infosys", "HDFC Bank", "Bharti Airtel", "TCS",
            "ICICI Bank", "IT services India", "financial services India", "telecom India",
            "services growth India"
        ]
    },
    "Nifty India Manufacturing": {
        "newsapi_keywords": [
            "Manufacturing India", "Siemens India", "Cummins India", "ABB India",
            "Bharat Electronics", "Larsen & Toubro", "make in India", "manufacturing growth India",
            "industrial manufacturing India", "manufacturing policy India"
        ]
    }
}


NEWSAPI_INDIA_MARKET_KEYWORDS = ["India", "Indian market", "NSE", "BSE", "Indian economy"]

def analyze_news_with_gemini(
    _api_key, articles_texts_list, analysis_target_name, date_range_str,
    custom_instructions="", append_log_func=None
):
    log_msg_prefix = f"[Gemini][{analysis_target_name}]"
    
    def _log(message, level='info'):
        full_message = f"{log_msg_prefix} {message}"
        if level == 'error': logger.error(full_message)
        elif level == 'warning': logger.warning(full_message)
        else: logger.info(full_message)
        if append_log_func: append_log_func(message, level) 

    _log(f"Starting analysis with {len(articles_texts_list)} articles for dates {date_range_str}.")

    if not _api_key or _api_key == "YOUR_GEMINI_API_KEY_HERE":
        err_msg = "Gemini API Key not provided or is a placeholder."
        _log(err_msg, 'error')
        return None, err_msg

    try:
        genai.configure(api_key=_api_key)
    except Exception as e:
        err_msg = f"Failed to configure Gemini API: {str(e)[:150]}"
        _log(err_msg, 'error')
        return None, err_msg

    MAX_TOTAL_CHARS_FOR_LLM = 25000
    truncated_articles_texts_list = []; current_chars = 0; num_original_articles = len(articles_texts_list)
    for text in articles_texts_list:
        if current_chars + len(text) > MAX_TOTAL_CHARS_FOR_LLM and truncated_articles_texts_list: break
        text_to_add = text[:MAX_TOTAL_CHARS_FOR_LLM - current_chars]
        truncated_articles_texts_list.append(text_to_add); current_chars += len(text_to_add)
        if current_chars >= MAX_TOTAL_CHARS_FOR_LLM: break
    
    if len(truncated_articles_texts_list) < num_original_articles:
        warn_msg = f"Truncated input: {num_original_articles} to {len(truncated_articles_texts_list)} articles ({current_chars} chars)."
        _log(warn_msg, 'warning')
    
    combined_text = "\n\n--- ARTICLE SEPARATOR ---\n\n".join(truncated_articles_texts_list)
    
    default_response_structure = { "summary": "N/A", "overall_sentiment": "Neutral", "sentiment_score_llm": 0.0, "sentiment_reason": "N/A", "key_themes": [], "potential_impact": "N/A", "key_companies_mentioned_context": [], "risks_identified": [], "opportunities_identified": []}

    if not combined_text.strip():
        _log("No news content for analysis after potential truncation.")
        final_response = default_response_structure.copy()
        final_response["summary"] = "No news content was available for analysis."
        final_response["sentiment_reason"] = "No articles available or all were empty."
        return final_response, None

    prompt = f"""
    Analyze the following news articles about the '{analysis_target_name}' in the Indian market from the period '{date_range_str}'.
    Articles are concatenated and separated by '--- ARTICLE SEPARATOR ---'.

    --- NEWS CONTENT START ---
    {combined_text}
    --- NEWS CONTENT END ---

    {custom_instructions if custom_instructions else "Focus on financial and market implications for the sector. Be concise and objective."}

    Your task is to provide a structured analysis in JSON format. The JSON object must include the following keys:
    - "summary": A concise 2-3 sentence summary of the key news and developments for '{analysis_target_name}'.
    - "overall_sentiment": Classify the overall sentiment. Choose one: "Strongly Positive", "Positive", "Neutral", "Negative", "Strongly Negative".
    - "sentiment_score_llm": A float value between -1.0 (Strongly Negative) and 1.0 (Strongly Positive). Neutral is 0.0.
    - "sentiment_reason": A brief 1-sentence explanation for the assigned sentiment and score.
    - "key_themes": A list of 2-3 dominant themes emerging from the news concerning '{analysis_target_name}'. Each theme a short string.
    - "potential_impact": A 1-sentence assessment of the potential impact on '{analysis_target_name}'.
    - "key_companies_mentioned_context": A list of key companies mentioned related to '{analysis_target_name}', with brief context (e.g., "Infosys - Positive earnings report"). Empty list or broader industry trends if no specific companies central.
    - "risks_identified": A list of 1-2 potential risks for '{analysis_target_name}'. Each risk a short string. Empty list if none.
    - "opportunities_identified": A list of 1-2 potential opportunities for '{analysis_target_name}'. Each opportunity a short string. Empty list if none.

    Ensure the output is ONLY the JSON object, without any preceding or succeeding text, and no markdown formatting for the JSON block itself.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        generation_config = genai.types.GenerationConfig(temperature=0.3)
        response = model.generate_content(prompt, generation_config=generation_config)
        
        cleaned_response_text = ""
        if hasattr(response, 'text') and response.text: cleaned_response_text = response.text.strip()
        elif response.parts: cleaned_response_text = "".join(part.text for part in response.parts).strip()
        else: raise ValueError("Gemini response is empty or in an unexpected format.")

        if cleaned_response_text.startswith("```json"): cleaned_response_text = cleaned_response_text[len("```json"):].strip()
        if cleaned_response_text.endswith("```"): cleaned_response_text = cleaned_response_text[:-len("```")].strip()
        
        json_start_index = cleaned_response_text.find('{'); json_end_index = cleaned_response_text.rfind('}')
        if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
            cleaned_response_text = cleaned_response_text[json_start_index : json_end_index+1]
        else: 
            _log(f"Could not find valid JSON structure in response: '{cleaned_response_text[:200]}...'", 'error')
            raise json.JSONDecodeError("Could not find valid JSON structure in response.", cleaned_response_text, 0)

        result = json.loads(cleaned_response_text)
        
        for key in default_response_structure.keys():
            if key not in result:
                _log(f"Gemini response missing key '{key}'. Using default.", 'warning')
                result[key] = default_response_structure[key]
            if isinstance(default_response_structure[key], list) and not isinstance(result.get(key), list):
                _log(f"Gemini response key '{key}' is not a list as expected. Defaulting to empty list.", 'warning')
                result[key] = []

        _log("Analysis successfully completed.")
        return result, None

    except json.JSONDecodeError as e:
        err_msg = f"Gemini JSON Decode Error: {str(e)[:150]}. Response: '{cleaned_response_text[:200]}...'"
        _log(err_msg, 'error')
        return None, "Gemini returned an invalid JSON. Please check server logs."
    except Exception as e:
        err_msg = f"Gemini Analysis Error: {str(e)[:150]}"
        _log(f"{err_msg} - Full traceback on server.", 'error')
        logger.exception(f"{log_msg_prefix} Full Gemini Exception") 
        return None, f"Error during Gemini analysis: {str(e)[:100]}"