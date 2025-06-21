# utils/newsapi_helpers.py
import logging
from newsapi import NewsApiClient # Ensure this is installed: pip install newsapi-python
import time
from datetime import timedelta

logger = logging.getLogger(__name__)

def get_newsapi_org_client(api_key, append_log_func=None):
    log_msg_prefix = "[NewsAPIHelper]"
    
    def _log(message, level='info'):
        full_message = f"{log_msg_prefix} {message}"
        if level.lower() == 'error': logger.error(full_message)
        elif level.lower() == 'warning': logger.warning(full_message)
        else: logger.info(full_message)
        if append_log_func: append_log_func(message, level.upper()) # Ensure level is uppercase for UI

    if not api_key or api_key == "YOUR_NEWSAPI_ORG_API_KEY_HERE": # Check against generic placeholder
        msg = "NewsAPI.org key is missing or a placeholder. Client not initialized."
        _log(msg, 'warning')
        return None, msg
    try:
        client = NewsApiClient(api_key=api_key)
        _log("NewsAPI.org client initialized successfully.")
        return client, None
    except Exception as e:
        err_msg = f"Failed to initialize NewsAPI.org client: {e}"
        _log(err_msg, 'error')
        return None, str(e)

def fetch_sector_news_newsapi(
    newsapi_client,
    sector_keywords_list, 
    country_keywords_list, 
    from_date_obj,
    to_date_obj,
    max_articles_to_fetch=20, 
    append_log_func=None
):
    log_msg_prefix = f"[NewsAPIHelper][SectorKeywords: {str(sector_keywords_list)[:30]}...]"

    def _log(message, level='info'):
        full_message = f"{log_msg_prefix} {message}"
        if level.lower() == 'error': logger.error(full_message)
        elif level.lower() == 'warning': logger.warning(full_message)
        else: logger.info(full_message)
        if append_log_func: append_log_func(message, level.upper())

    if not newsapi_client:
        msg = "NewsAPI client not available for fetching sector news."
        _log(msg, 'warning')
        return [], msg

    # Ensure keywords are properly OR'd and then AND'ed with country terms
    # Using explicit phrase matching with double quotes for each keyword.
    sector_query_part = f"({' OR '.join(f'\"{k.strip()}\"' for k in sector_keywords_list if k.strip())})"
    country_query_part = f"({' OR '.join(f'\"{k.strip()}\"' for k in country_keywords_list if k.strip())})"
    
    if sector_query_part == "()": # No valid sector keywords
        query_string = country_query_part # Fallback to country if sector keywords are empty
    elif country_query_part == "()": # No valid country keywords (unlikely but handle)
        query_string = sector_query_part
    else:
        query_string = f"{sector_query_part} AND {country_query_part}"
    
    if query_string == "()": # If both parts resulted in empty queries
        _log("No valid keywords for query construction.", "warning")
        return [], "No valid keywords provided for NewsAPI query."

    from_date_str = from_date_obj.strftime('%Y-%m-%d')
    to_date_str = to_date_obj.strftime('%Y-%m-%d')
    
    articles_data = []
    error_message_user = None
    
    page_size_for_api = min(max_articles_to_fetch, 100) # NewsAPI page_size max is 100

    _log(f"Fetching news with query: '{query_string}', From: {from_date_str}, To: {to_date_str}, PageSize: {page_size_for_api}", "debug")

    try:
        all_articles_response = newsapi_client.get_everything(
            q=query_string,
            from_param=from_date_str,
            to=to_date_str,
            language='en',
            sort_by='relevancy', 
            page_size=page_size_for_api
        )

        if all_articles_response['status'] == 'ok':
            fetched_api_articles = all_articles_response['articles']
            _log(f"API returned {all_articles_response['totalResults']} total results, received {len(fetched_api_articles)} articles in this call.", "info")
            
            unique_urls = set()
            for article in fetched_api_articles:
                if len(articles_data) >= max_articles_to_fetch:
                    _log(f"Reached max_articles_to_fetch limit ({max_articles_to_fetch}).", "info")
                    break
                
                url = article.get('url')
                if url in unique_urls:
                    _log(f"Skipping duplicate URL: {url}", "debug")
                    continue
                if url: unique_urls.add(url) # Add only if URL exists to avoid None in set

                title = article.get('title', "") or ""
                description = article.get('description', "") or ""
                
                content_for_llm = title
                if description:
                    if title and not title.endswith(('.', '!', '?')):
                        content_for_llm += ". " + description
                    else:
                        content_for_llm += " " + description
                
                if content_for_llm.strip() and content_for_llm.strip() != ".":
                    articles_data.append({
                        'content': content_for_llm.strip(),
                        'date': article.get('publishedAt', from_date_str).split('T')[0],
                        'uri': url or '', # Ensure URI is always a string
                        'source': article.get('source', {}).get('name', 'N/A')
                    })
            _log(f"Processed and returning {len(articles_data)} unique articles for LLM.", "info")
        else:
            api_err_code = all_articles_response.get('code', 'N/A')
            api_err_msg = all_articles_response.get('message', 'Unknown NewsAPI error')
            error_message_user = f"NewsAPI.org Error: {api_err_msg} (Code: {api_err_code})"
            _log(error_message_user, 'error')
            if api_err_code == 'rateLimited':
                _log("Rate limited by NewsAPI. Consider pausing or reducing request frequency.", 'warning')
            elif 'too far in the past' in api_err_msg.lower() or 'maximumAllowedDate' in api_err_code:
                _log("Query date range might be too old for NewsAPI free/developer tier.", 'warning')
                error_message_user = f"NewsAPI: Date range too old ({from_date_str} to {to_date_str}). Max is usually ~30 days back."


    except Exception as e:
        err_msg = f"An exception occurred during NewsAPI fetch: {str(e)[:150]}"
        _log(err_msg, 'error')
        logger.exception(f"{log_msg_prefix} Full NewsAPI Fetch Exception")
        error_message_user = f"NewsAPI.org fetch exception: {str(e)[:100]}"
    
    time.sleep(1.2) # API courtesy delay
    
    return articles_data, error_message_user