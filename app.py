# app.py
print("DEBUG: app.py - Script started") # ADD THIS LINE

import os
import logging
from flask import Flask, render_template, request, jsonify, session as flask_session
from datetime import datetime, timedelta
# import secrets # This was imported but not used, can be removed if truly unused
import json

print("DEBUG: app.py - Basic imports done") # ADD THIS LINE

# Import utility modules - only newsapi_helpers and gemini_utils needed now
from utils import gemini_utils, newsapi_helpers, sentiment_analyzer 
import config 

print("DEBUG: app.py - utils and config imported") # ADD THIS LINE

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
print(f"DEBUG: app.py - Flask app initialized. Secret key set: {bool(app.secret_key and app.secret_key != 'change_this_to_a_strong_random_secret_key')}") # ADD THIS LINE


# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d (%(funcName)s)] - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__) 
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("newsapi").setLevel(logging.WARNING) 
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("nltk").setLevel(logging.INFO) 
print("DEBUG: app.py - Logging configured") # ADD THIS LINE


# --- API Key Management ---
def get_api_keys_from_session_or_config():
    # print("DEBUG: get_api_keys_from_session_or_config called") # Optional: too verbose for now
    keys = {
        'newsapi': flask_session.get('newsapi_key_sess', config.NEWSAPI_ORG_API_KEY),
        'gemini': flask_session.get('gemini_key_sess', config.GEMINI_API_KEY),
    }
    # logger.debug(f"API Keys for current request - Gemini Set: {bool(keys['gemini'] and keys['gemini'] != 'YOUR_GEMINI_API_KEY_HERE')}, NewsAPI Set: {bool(keys['newsapi'] and keys['newsapi'] != 'YOUR_NEWSAPI_ORG_API_KEY_HERE')}")
    return keys

# --- Global API Clients/Sessions ---
newsapi_global_client = None

def get_or_create_newsapi_client_global(api_key_for_check, append_log_local_func):
    global newsapi_global_client
    if not hasattr(get_or_create_newsapi_client_global, 'current_key'):
        get_or_create_newsapi_client_global.current_key = None

    if newsapi_global_client is None or get_or_create_newsapi_client_global.current_key != api_key_for_check:
        append_log_local_func("NEWSAPI_APP: Initializing/Re-initializing global NewsAPI client...", "INFO")
        newsapi_global_client, err = newsapi_helpers.get_newsapi_org_client(api_key_for_check, append_log_local_func)
        if err:
            get_or_create_newsapi_client_global.current_key = None
            append_log_local_func(f"NEWSAPI_APP: Failed to initialize client: {err}", "ERROR")
        else:
            get_or_create_newsapi_client_global.current_key = api_key_for_check
            append_log_local_func("NEWSAPI_APP: Global NewsAPI client ready.", "INFO")
    return newsapi_global_client

print("DEBUG: app.py - Helper functions defined") # ADD THIS LINE

@app.route('/')
def index_page():
    print("DEBUG: app.py - Route / accessed") # ADD THIS LINE
    actual_system_today = datetime.now().date()
    context = {
        'sector_options': list(gemini_utils.NIFTY_SECTORS_QUERY_CONFIG.keys()),
        'news_source_options': ["NewsAPI.org"], 
        'system_actual_today': actual_system_today.strftime('%Y-%m-%d'),
        'default_end_date': actual_system_today.strftime('%Y-%m-%d'),
    }
    return render_template('index.html', **context)

@app.route('/api/update-api-keys', methods=['POST'])
def update_api_keys_route():
    print("DEBUG: app.py - Route /api/update-api-keys accessed") # ADD THIS LINE
    data = request.json
    keys_updated_messages = []
    log_updates = []

    def update_key(session_key_name, data_key_name, display_name):
        if data_key_name in data and data[data_key_name].strip():
            flask_session[session_key_name] = data[data_key_name]
            msg = f"{display_name} API key updated in session."
            keys_updated_messages.append(msg)
            log_updates.append(msg)

    update_key('gemini_key_sess', 'gemini_key', 'Gemini')
    update_key('newsapi_key_sess', 'newsapi_key', 'NewsAPI.org')
    
    if not keys_updated_messages:
        return jsonify({"message": "No API keys provided to update in session."}), 200
        
    logger.info(f"API keys update attempt: {'; '.join(log_updates)}")
    return jsonify({"message": "Selected API keys processed for session successfully."})


@app.route('/api/sector-analysis', methods=['POST'])
def perform_sector_analysis_route():
    print("DEBUG: app.py - Route /api/sector-analysis accessed") # ADD THIS LINE
    form_data = request.json
    # ... (rest of the function) ...
    # YOU CAN ADD MORE DEBUG PRINTS INSIDE THIS LONG FUNCTION IF NEEDED
    # For now, the print above is enough for this route definition stage
    loggable_form_data = {k: v for k, v in form_data.items() if 'key' not in k.lower()}
    logger.info(f"REQUEST DATA: /api/sector-analysis: {json.dumps(loggable_form_data, indent=2)}")
    
    ui_log_messages_for_this_request = []
    def append_log_local(message, level='INFO'):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level_upper = level.upper()
        entry = {'timestamp': timestamp, 'message': str(message), 'level': level_upper}
        ui_log_messages_for_this_request.append(entry)
        if level_upper == 'ERROR': logger.error(f"API_LOG_UI: {message}")
        elif level_upper == 'WARNING': logger.warning(f"API_LOG_UI: {message}")
        elif level_upper == 'DEBUG': logger.debug(f"API_LOG_UI: {message}")
        else: logger.info(f"API_LOG_UI: {message}")

    results_payload = []
    user_facing_errors = []
    
    current_api_keys = get_api_keys_from_session_or_config()

    selected_sectors = form_data.get('selected_sectors')
    if not selected_sectors or not isinstance(selected_sectors, list) or len(selected_sectors) == 0:
        user_facing_errors.append("Please select at least one sector.")
    
    if not current_api_keys['gemini'] or current_api_keys['gemini'] == "YOUR_GEMINI_API_KEY_HERE":
        user_facing_errors.append("Gemini API key is not configured (check session/config).")
    
    if not current_api_keys['newsapi'] or current_api_keys['newsapi'] == "YOUR_NEWSAPI_ORG_API_KEY_HERE":
        user_facing_errors.append("NewsAPI.org API key is not configured.")

    if user_facing_errors:
        append_log_local(f"Validation errors: {', '.join(user_facing_errors)}", "ERROR")
        return jsonify({'error': True, 'messages': user_facing_errors, 'logs': ui_log_messages_for_this_request, 'results': []}), 400

    actual_system_today = datetime.now().date()
    append_log_local(f"Actual system date for this request: {actual_system_today.strftime('%Y-%m-%d')}", "INFO")

    try:
        ui_end_date_str = form_data.get('end_date', actual_system_today.strftime('%Y-%m-%d'))
        ui_selected_end_date_obj = datetime.strptime(ui_end_date_str, '%Y-%m-%d').date()
        append_log_local(f"UI selected end_date: {ui_selected_end_date_obj.strftime('%Y-%m-%d')}", "INFO")
    except ValueError:
        ui_selected_end_date_obj = actual_system_today
        append_log_local(f"Invalid end_date format '{ui_end_date_str}', defaulting UI selected end_date to system today: {ui_selected_end_date_obj.strftime('%Y-%m-%d')}", "WARNING")

    lookback_days = int(form_data.get('sector_lookback', 7))
    max_articles_llm = int(form_data.get('sector_max_articles', 5))
    custom_prompt = form_data.get('sector_custom_prompt', '')

    api_query_end_date_obj = min(ui_selected_end_date_obj, actual_system_today)
    api_query_start_date_obj = api_query_end_date_obj - timedelta(days=lookback_days - 1)
    
    llm_context_start_date_obj = ui_selected_end_date_obj - timedelta(days=lookback_days - 1)
    llm_context_date_range_str = f"{llm_context_start_date_obj.strftime('%Y-%m-%d')} to {ui_selected_end_date_obj.strftime('%Y-%m-%d')}"
    
    append_log_local(f"LLM Context Range (user intended): {llm_context_date_range_str}", "INFO")
    append_log_local(f"FINAL API Query Date Range: {api_query_start_date_obj.strftime('%Y-%m-%d')} to {api_query_end_date_obj.strftime('%Y-%m-%d')}", "INFO")

    na_client = get_or_create_newsapi_client_global(current_api_keys['newsapi'], append_log_local)
    if not na_client: 
        user_facing_errors.append("Failed to initialize NewsAPI.org client.")
        return jsonify({'error': True, 'messages': user_facing_errors, 'logs': ui_log_messages_for_this_request, 'results': []}), 500

    for sector_name in selected_sectors:
        append_log_local(f"--- Processing Sector: {sector_name} using NewsAPI.org ---", "INFO")
        sector_config_details = gemini_utils.NIFTY_SECTORS_QUERY_CONFIG.get(sector_name, {})
        fetched_articles_data_list = [] 
        news_fetch_error_msg = None

        api_from_date = api_query_start_date_obj
        api_to_date = api_query_end_date_obj
        
        newsapi_earliest_allowed = actual_system_today - timedelta(days=29) 
        na_api_query_start_date_obj_constrained = max(api_from_date, newsapi_earliest_allowed)
        
        if na_api_query_start_date_obj_constrained > api_to_date:
            news_fetch_error_msg = "NewsAPI date range invalid after applying constraints (start is after end for the query period)."
            append_log_local(f"[{sector_name}] {news_fetch_error_msg}", "WARNING")
        else:
            sector_specific_keywords_na = sector_config_details.get("newsapi_keywords", [sector_name])
            india_market_keywords_na = gemini_utils.NEWSAPI_INDIA_MARKET_KEYWORDS 
            
            append_log_local(f"NewsAPI Call Params for {sector_name}: sector_kws={sector_specific_keywords_na}, country_kws={india_market_keywords_na}, from={na_api_query_start_date_obj_constrained.strftime('%Y-%m-%d')}, to={api_to_date.strftime('%Y-%m-%d')}, max_articles={max_articles_llm}", "DEBUG")
            
            fetched_articles_data_list, news_fetch_error_msg = newsapi_helpers.fetch_sector_news_newsapi(
                newsapi_client=na_client,
                sector_keywords_list=sector_specific_keywords_na,
                country_keywords_list=india_market_keywords_na,
                from_date_obj=na_api_query_start_date_obj_constrained,
                to_date_obj=api_to_date,
                max_articles_to_fetch=max_articles_llm,
                append_log_func=append_log_local
            )
        if news_fetch_error_msg:
             append_log_local(f"[{sector_name}] NewsAPI.org Error: {news_fetch_error_msg}", "ERROR")

        gemini_analysis_result_dict = None
        current_sector_error_message = news_fetch_error_msg
        
        sector_vader_scores = []
        article_contents_for_llm = []

        if fetched_articles_data_list: 
            for art_data in fetched_articles_data_list:
                if art_data.get('content'): 
                    article_contents_for_llm.append(art_data['content'])
                if 'vader_score' in art_data and isinstance(art_data['vader_score'], (float, int)):
                    sector_vader_scores.append(art_data['vader_score'])
        
        avg_vader_score_for_sector = sentiment_analyzer.get_average_vader_score(sector_vader_scores)
        vader_sentiment_label = sentiment_analyzer.get_sentiment_label_from_score(avg_vader_score_for_sector)
        append_log_local(f"[{sector_name}] Average VADER score: {avg_vader_score_for_sector:.4f} ({vader_sentiment_label}) from {len(sector_vader_scores)} articles.", "INFO")

        if news_fetch_error_msg and not article_contents_for_llm: 
            append_log_local(f"[{sector_name}] News fetch failed and no articles obtained for LLM.", "ERROR")
            current_sector_error_message = current_sector_error_message or "News fetch failed and no articles obtained for LLM."
        elif not article_contents_for_llm:
            msg = "No news articles found by NewsAPI.org with processable content for LLM analysis in the queried date range."
            append_log_local(f"[{sector_name}] {msg}", "WARNING")
            current_sector_error_message = current_sector_error_message or msg
        else:
            append_log_local(f"[{sector_name}] Analyzing {len(article_contents_for_llm)} articles with Gemini (LLM Context Date: {llm_context_date_range_str}).", "INFO")
            
            gemini_analysis_result_dict, gemini_err_str = gemini_utils.analyze_news_with_gemini(
                _api_key=current_api_keys['gemini'],
                articles_texts_list=article_contents_for_llm,
                analysis_target_name=sector_name,
                date_range_str=llm_context_date_range_str,
                custom_instructions=custom_prompt,
                append_log_func=append_log_local
            )
            if gemini_err_str:
                append_log_local(f"[{sector_name}] Gemini analysis error: {gemini_err_str}", "ERROR")
                current_sector_error_message = gemini_err_str 
        
        results_payload.append({
            'sector_name': sector_name,
            'llm_context_date_range': llm_context_date_range_str,
            'num_articles_for_llm': len(article_contents_for_llm),
            'gemini_analysis': gemini_analysis_result_dict,
            'error_message': current_sector_error_message,
            'avg_vader_score': avg_vader_score_for_sector, 
            'vader_sentiment_label': vader_sentiment_label 
        })
        
    append_log_local("--- Sector analysis processing finished for all selected sectors. ---", "INFO")
    
    return jsonify({
        'error': False, 
        'messages': ["Analysis request processed. See sector-specific results and errors."],
        'results': results_payload,
        'logs': ui_log_messages_for_this_request
    })

print("DEBUG: app.py - Route definitions done") # ADD THIS LINE

if __name__ == '__main__':
    print("DEBUG: app.py - Inside __main__ block") # ADD THIS LINE
    logger.info(f"Sentiment Analysis Dashboard (Flask) starting...")
    logger.info(f"System Date at Startup: {datetime.now().date().strftime('%Y-%m-%d')}")
    logger.info(f"Flask Secret Key: {'SET (User Defined)' if config.FLASK_SECRET_KEY and config.FLASK_SECRET_KEY != 'change_this_to_a_strong_random_secret_key' else 'NOT SET (Using default - insecure!)'}")
    
    gemini_key_status = 'NOT SET (Using placeholder)'
    if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
         gemini_key_status = f"SET (Ends with ...{config.GEMINI_API_KEY[-4:] if len(config.GEMINI_API_KEY) > 4 else '****'})"
    logger.info(f"Gemini API Key: {gemini_key_status}")

    newsapi_key_status = 'NOT SET (Using placeholder)'
    if config.NEWSAPI_ORG_API_KEY and config.NEWSAPI_ORG_API_KEY != "YOUR_NEWSAPI_ORG_API_KEY_HERE":
        newsapi_key_status = f"SET (Ends with ...{config.NEWSAPI_ORG_API_KEY[-4:] if len(config.NEWSAPI_ORG_API_KEY) > 4 else '****'})"
    logger.info(f"NewsAPI Key: {newsapi_key_status}")
    
    port = int(os.environ.get("PORT", 5003)) 
    print(f"DEBUG: app.py - Attempting to run app on host 0.0.0.0, port {port}") # ADD THIS LINE
    app.run(debug=True, host='0.0.0.0', port=port)
    print("DEBUG: app.py - app.run finished or was interrupted") # ADD THIS LINE (won't be reached if server runs indefinitely)
else:
    print("DEBUG: app.py - Script is being imported, not run directly.") # ADD THIS LINE

print("DEBUG: app.py - Script finished executing (or Flask server was stopped if it ran)") # ADD THIS LINEpython app.py