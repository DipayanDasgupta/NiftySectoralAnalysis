# app.py
import os
import logging
from flask import Flask, render_template, request, jsonify, session as flask_session
from datetime import datetime, timedelta
import json

from utils import gemini_utils, newsapi_helpers, sentiment_analyzer 
import config 

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

# --- Logging Setup --- (Keep as is)
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d (%(funcName)s)] - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__) 
logging.getLogger("werkzeug").setLevel(logging.WARNING)
# ... (other library log levels) ...
logging.getLogger("nltk").setLevel(logging.INFO)


# --- API Key Management & Global Clients --- (Keep as is)
def get_api_keys_from_session_or_config():
    keys = {
        'newsapi': flask_session.get('newsapi_key_sess', config.NEWSAPI_ORG_API_KEY),
        'gemini': flask_session.get('gemini_key_sess', config.GEMINI_API_KEY),
    }
    return keys

newsapi_global_client = None
def get_or_create_newsapi_client_global(api_key_for_check, append_log_local_func):
    global newsapi_global_client
    if not hasattr(get_or_create_newsapi_client_global, '_current_newsapi_key'):
        get_or_create_newsapi_client_global._current_newsapi_key = None

    if newsapi_global_client is None or get_or_create_newsapi_client_global._current_newsapi_key != api_key_for_check:
        append_log_local_func("NEWSAPI_APP: Initializing/Re-initializing global NewsAPI client...", "INFO")
        newsapi_global_client, err = newsapi_helpers.get_newsapi_org_client(api_key_for_check, append_log_local_func)
        if err:
            get_or_create_newsapi_client_global._current_newsapi_key = None 
            newsapi_global_client = None 
            append_log_local_func(f"NEWSAPI_APP: Failed to initialize client: {err}", "ERROR")
        else:
            get_or_create_newsapi_client_global._current_newsapi_key = api_key_for_check
            append_log_local_func("NEWSAPI_APP: Global NewsAPI client ready.", "INFO")
    return newsapi_global_client

@app.route('/')
def index_page():
    # ... (Keep as is) ...
    actual_system_today = datetime.now().date()
    sector_config = gemini_utils.NIFTY_SECTORS_QUERY_CONFIG
    # Pass the full config to the template so JS can access stock lists for dynamic dropdowns
    context = {
        'sector_options': list(sector_config.keys()),
        'news_source_options': ["NewsAPI.org"], 
        'system_actual_today': actual_system_today.strftime('%Y-%m-%d'),
        'default_end_date': actual_system_today.strftime('%Y-%m-%d'),
        'sector_stock_config_json': json.dumps({sector: list(details.get("stocks", {}).keys()) for sector, details in sector_config.items()})
    }
    return render_template('index.html', **context)


@app.route('/api/update-api-keys', methods=['POST'])
def update_api_keys_route():
    # ... (Keep as is) ...
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

# --- Helper for ui_log_messages ---
def setup_local_logger(ui_log_list):
    def append_log_local(message, level='INFO'):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level_upper = level.upper()
        entry = {'timestamp': timestamp, 'message': str(message), 'level': level_upper}
        ui_log_list.append(entry)
        if level_upper == 'ERROR': logger.error(f"API_LOG_UI: {message}")
        elif level_upper == 'WARNING': logger.warning(f"API_LOG_UI: {message}")
        elif level_upper == 'DEBUG': logger.debug(f"API_LOG_UI: {message}")
        else: logger.info(f"API_LOG_UI: {message}")
    return append_log_local

@app.route('/api/sector-analysis', methods=['POST'])
def perform_sector_analysis_route_only(): # Renamed for clarity
    form_data = request.json
    loggable_form_data = {k: v for k, v in form_data.items() if 'key' not in k.lower()}
    logger.info(f"REQUEST DATA: /api/sector-analysis (Sector Only): {json.dumps(loggable_form_data, indent=2)}")
    
    ui_log_messages_for_this_request = []
    append_log_local = setup_local_logger(ui_log_messages_for_this_request)
    
    results_payload = [] 
    user_facing_errors = []
    current_api_keys = get_api_keys_from_session_or_config()

    # --- Validation (as before) ---
    selected_sectors = form_data.get('selected_sectors')
    if not selected_sectors or not isinstance(selected_sectors, list) or len(selected_sectors) == 0:
        user_facing_errors.append("Please select at least one sector.")
    if not current_api_keys['gemini'] or current_api_keys['gemini'] == "YOUR_GEMINI_API_KEY_HERE":
        user_facing_errors.append("Gemini API key is not configured.")
    if not current_api_keys['newsapi'] or current_api_keys['newsapi'] == "YOUR_NEWSAPI_ORG_API_KEY_HERE":
        user_facing_errors.append("NewsAPI.org API key is not configured.")
    if user_facing_errors:
        return jsonify({'error': True, 'messages': user_facing_errors, 'logs': ui_log_messages_for_this_request, 'results': []}), 400

    # --- Date and Parameter Setup (as before) ---
    actual_system_today = datetime.now().date()
    append_log_local(f"Actual system date: {actual_system_today.strftime('%Y-%m-%d')}", "INFO")
    try:
        ui_end_date_str = form_data.get('end_date', actual_system_today.strftime('%Y-%m-%d'))
        ui_selected_end_date_obj = datetime.strptime(ui_end_date_str, '%Y-%m-%d').date()
    except ValueError:
        ui_selected_end_date_obj = actual_system_today
        append_log_local(f"Invalid end_date format, defaulting to system today: {ui_selected_end_date_obj.strftime('%Y-%m-%d')}", "WARNING")
    
    lookback_days = int(form_data.get('sector_lookback', 7))
    max_articles_llm_sector = int(form_data.get('sector_max_articles', 5))
    custom_prompt_from_ui = form_data.get('sector_custom_prompt', '')

    api_query_end_date_obj = min(ui_selected_end_date_obj, actual_system_today)
    api_query_start_date_obj = api_query_end_date_obj - timedelta(days=lookback_days - 1)
    llm_context_date_range_str = f"{(ui_selected_end_date_obj - timedelta(days=lookback_days - 1)).strftime('%Y-%m-%d')} to {ui_selected_end_date_obj.strftime('%Y-%m-%d')}"
    append_log_local(f"LLM Context Range: {llm_context_date_range_str}", "INFO")
    append_log_local(f"NewsAPI Query Range: {api_query_start_date_obj.strftime('%Y-%m-%d')} to {api_query_end_date_obj.strftime('%Y-%m-%d')}", "INFO")

    na_client = get_or_create_newsapi_client_global(current_api_keys['newsapi'], append_log_local)
    if not na_client:
        return jsonify({'error': True, 'messages': ["Failed to initialize NewsAPI client."], 'logs': ui_log_messages_for_this_request, 'results': []}), 500

    newsapi_earliest_allowed = actual_system_today - timedelta(days=29)
    api_query_start_date_obj_constrained = max(api_query_start_date_obj, newsapi_earliest_allowed)
    if api_query_start_date_obj_constrained > api_query_end_date_obj:
        # ... (error handling for date range) ...
        date_error_msg = "NewsAPI query date range invalid after constraints."
        append_log_local(date_error_msg, "ERROR")
        return jsonify({'error': True, 'messages': [date_error_msg], 'logs': ui_log_messages_for_this_request, 'results': []}), 400

    for sector_name_from_form in selected_sectors:
        append_log_local(f"--- Processing SECTOR: {sector_name_from_form} ---", "INFO")
        sector_full_config = gemini_utils.NIFTY_SECTORS_QUERY_CONFIG.get(sector_name_from_form, {})
        sector_news_api_keywords = sector_full_config.get("newsapi_keywords", [sector_name_from_form])
        
        # --- Sector News Fetching and Analysis (as before) ---
        fetched_sector_articles_data, sector_news_fetch_error = newsapi_helpers.fetch_sector_news_newsapi(
            na_client, sector_name_from_form, sector_news_api_keywords, gemini_utils.NEWSAPI_INDIA_MARKET_KEYWORDS,
            api_query_start_date_obj_constrained, api_query_end_date_obj, max_articles_llm_sector, append_log_local
        )
        # ... (VADER and Gemini analysis for sector as before) ...
        sector_gemini_analysis = None; current_sector_error_message = sector_news_fetch_error
        sector_article_contents_for_llm = []; sector_vader_scores = []
        if fetched_sector_articles_data:
            for art in fetched_sector_articles_data:
                if art.get('content'): sector_article_contents_for_llm.append(art['content'])
                if 'vader_score' in art: sector_vader_scores.append(art['vader_score'])
        avg_vader_score_sector = sentiment_analyzer.get_average_vader_score(sector_vader_scores)
        vader_label_sector = sentiment_analyzer.get_sentiment_label_from_score(avg_vader_score_sector)

        if not sector_article_contents_for_llm and not sector_news_fetch_error:
            current_sector_error_message = current_sector_error_message or f"No processable news for sector {sector_name_from_form}."
        
        if sector_article_contents_for_llm:
            sector_gemini_analysis, gemini_err = gemini_utils.analyze_news_with_gemini(
                current_api_keys['gemini'], sector_article_contents_for_llm, sector_name_from_form,
                llm_context_date_range_str, custom_prompt_from_ui, append_log_local, target_type="sector"
            )
            if gemini_err: current_sector_error_message = gemini_err

        results_payload.append({
            'sector_name': sector_name_from_form,
            'llm_context_date_range': llm_context_date_range_str,
            'num_articles_for_llm_sector': len(sector_article_contents_for_llm),
            'gemini_analysis_sector': sector_gemini_analysis,
            'error_message_sector': current_sector_error_message,
            'avg_vader_score_sector': avg_vader_score_sector,
            'vader_sentiment_label_sector': vader_label_sector,
            'constituent_stocks': list(sector_full_config.get("stocks", {}).keys()) # Send stock names for UI dropdown
        })
        
    append_log_local("--- Sector-only analysis finished. ---", "INFO")
    return jsonify({'error': False, 'messages': ["Sector analysis complete."], 'results': results_payload, 'logs': ui_log_messages_for_this_request})

@app.route('/api/stock-analysis', methods=['POST'])
def perform_stock_analysis_route():
    form_data = request.json # Expects: sector_name, selected_stocks_list, end_date, lookback_days, stock_max_articles, custom_prompt
    logger.info(f"REQUEST DATA: /api/stock-analysis: {json.dumps(form_data, indent=2)}")

    ui_log_messages_for_this_request = []
    append_log_local = setup_local_logger(ui_log_messages_for_this_request)

    stock_analysis_results = []
    user_facing_errors = []
    current_api_keys = get_api_keys_from_session_or_config()

    sector_name = form_data.get('sector_name')
    selected_stocks = form_data.get('selected_stocks') # This is a list of stock names
    if not sector_name or not selected_stocks or not isinstance(selected_stocks, list) or len(selected_stocks) == 0:
        user_facing_errors.append("Sector name and at least one stock must be provided.")
    # API Key checks (as in sector analysis)
    if not current_api_keys['gemini'] or current_api_keys['gemini'] == "YOUR_GEMINI_API_KEY_HERE":
        user_facing_errors.append("Gemini API key is not configured.")
    if not current_api_keys['newsapi'] or current_api_keys['newsapi'] == "YOUR_NEWSAPI_ORG_API_KEY_HERE":
        user_facing_errors.append("NewsAPI.org API key is not configured.")
    if user_facing_errors:
        return jsonify({'error': True, 'messages': user_facing_errors, 'logs': ui_log_messages_for_this_request, 'results': []}), 400
    
    # --- Date and Parameter Setup (mirrors sector analysis, but uses params from this request) ---
    actual_system_today = datetime.now().date() # Recalculate for this endpoint's context
    try:
        ui_end_date_str = form_data.get('end_date', actual_system_today.strftime('%Y-%m-%d'))
        ui_selected_end_date_obj = datetime.strptime(ui_end_date_str, '%Y-%m-%d').date()
    except ValueError:
        ui_selected_end_date_obj = actual_system_today
    
    lookback_days = int(form_data.get('lookback_days', 7))
    max_articles_llm_stock = int(form_data.get('stock_max_articles', 3))
    custom_prompt_from_ui = form_data.get('custom_prompt', '')
    
    api_query_end_date_obj = min(ui_selected_end_date_obj, actual_system_today)
    api_query_start_date_obj = api_query_end_date_obj - timedelta(days=lookback_days - 1)
    llm_context_date_range_str = f"{(ui_selected_end_date_obj - timedelta(days=lookback_days - 1)).strftime('%Y-%m-%d')} to {ui_selected_end_date_obj.strftime('%Y-%m-%d')}"
    append_log_local(f"Stock Analysis - LLM Context: {llm_context_date_range_str}, NewsAPI Query: {api_query_start_date_obj.strftime('%Y-%m-%d')} to {api_query_end_date_obj.strftime('%Y-%m-%d')}", "INFO")

    na_client = get_or_create_newsapi_client_global(current_api_keys['newsapi'], append_log_local)
    if not na_client:
        return jsonify({'error': True, 'messages': ["Failed to initialize NewsAPI client for stock analysis."], 'logs': ui_log_messages_for_this_request, 'results': []}), 500
    
    newsapi_earliest_allowed = actual_system_today - timedelta(days=29)
    api_query_start_date_obj_constrained = max(api_query_start_date_obj, newsapi_earliest_allowed)
    if api_query_start_date_obj_constrained > api_query_end_date_obj:
        date_error_msg = "NewsAPI query date range invalid for stocks after constraints."
        append_log_local(date_error_msg, "ERROR")
        return jsonify({'error': True, 'messages': [date_error_msg], 'logs': ui_log_messages_for_this_request, 'results': []}), 400

    sector_full_config = gemini_utils.NIFTY_SECTORS_QUERY_CONFIG.get(sector_name, {})
    stocks_master_list_for_sector = sector_full_config.get("stocks", {})

    for stock_name in selected_stocks:
        if stock_name not in stocks_master_list_for_sector:
            append_log_local(f"Stock '{stock_name}' not found in configuration for sector '{sector_name}'. Skipping.", "WARNING")
            stock_analysis_results.append({
                'stock_name': stock_name, 'error_message_stock': 'Stock not configured for this sector.'
            })
            continue

        append_log_local(f"--- Processing Stock: {stock_name} (Sector: {sector_name}) ---", "INFO")
        stock_specific_news_keywords = stocks_master_list_for_sector.get(stock_name, [stock_name]) # Fallback to stock name
        
        # --- Stock News Fetching and Analysis ---
        fetched_stock_articles_data, stock_news_fetch_error = newsapi_helpers.fetch_stock_news_newsapi(
            na_client, stock_name, stock_specific_news_keywords, gemini_utils.NEWSAPI_INDIA_MARKET_KEYWORDS,
            api_query_start_date_obj_constrained, api_query_end_date_obj, max_articles_llm_stock, append_log_local
        )
        # ... (VADER and Gemini analysis for stock as in previous combined function) ...
        stock_gemini_analysis = None; current_stock_error_message = stock_news_fetch_error
        stock_article_contents_for_llm = []; stock_vader_scores = []

        if fetched_stock_articles_data:
            for art in fetched_stock_articles_data:
                if art.get('content'): stock_article_contents_for_llm.append(art['content'])
                if 'vader_score' in art: stock_vader_scores.append(art['vader_score'])
        avg_vader_score_stock = sentiment_analyzer.get_average_vader_score(stock_vader_scores)
        vader_label_stock = sentiment_analyzer.get_sentiment_label_from_score(avg_vader_score_stock)

        if not stock_article_contents_for_llm and not stock_news_fetch_error : # If no articles and no explicit fetch error
             current_stock_error_message = current_stock_error_message or f"No processable news for stock {stock_name}."

        if stock_article_contents_for_llm:
            stock_gemini_analysis, gemini_err_stock = gemini_utils.analyze_news_with_gemini(
                current_api_keys['gemini'], stock_article_contents_for_llm, stock_name,
                llm_context_date_range_str, custom_prompt_from_ui, append_log_local, target_type="stock"
            )
            if gemini_err_stock: current_stock_error_message = gemini_err_stock
        
        stock_analysis_results.append({
            'stock_name': stock_name,
            'num_articles_for_llm_stock': len(stock_article_contents_for_llm),
            'gemini_analysis_stock': stock_gemini_analysis,
            'error_message_stock': current_stock_error_message,
            'avg_vader_score_stock': avg_vader_score_stock,
            'vader_sentiment_label_stock': vader_label_stock
        })

    append_log_local(f"--- Individual stock analysis for sector '{sector_name}' finished. ---", "INFO")
    return jsonify({'error': False, 'messages': [f"Stock analysis for {sector_name} complete."], 
                    'results_stocks': stock_analysis_results, # Send only stock results for this call
                    'sector_name': sector_name, # Include sector name for context on frontend
                    'logs': ui_log_messages_for_this_request})


if __name__ == '__main__':
    logger.info(f"Sentiment Analysis Dashboard (Flask) starting...")
    port = int(os.environ.get("PORT", 5003)) 
    app.run(debug=True, host='0.0.0.0', port=port)