# Nifty News Sentiment Analyzer (Flask + JS)

This web application performs sentiment analysis on news related to selected Nifty sectors. It fetches news using NewsAPI.org and utilizes Google Gemini for Large Language Model (LLM) based sentiment analysis.

## Features

-   Fetches news for selected Nifty sectors using NewsAPI.org.
-   Performs detailed sentiment analysis using Google Gemini LLM.
-   Displays sentiment scores and detailed LLM insights (summary, themes, risks, opportunities).
-   Interactive UI built with Flask (backend) and vanilla JavaScript (frontend) with Chart.js for visualizations.
-   Allows users to configure:
    -   Analysis end date (API queries are capped at the actual current date).
    -   News lookback period.
    -   Sectors for analysis.
    -   Maximum number of articles to be processed by the LLM.
    -   Custom instructions for the LLM.
-   Server-side session management for API keys.
-   UI logging for process tracking and debugging.

## Project Structure

-   `app.py`: Main Flask application handling API requests and rendering.
-   `config.py`: Loads configuration (API keys, Flask secret) from `.env`.
-   `.env`: (To be created by user) Stores actual API keys and secrets.
-   `requirements.txt`: Python dependencies.
-   `static/`: Contains CSS (`style.css`) and JavaScript (`main.js`).
-   `templates/`: Contains the main HTML template (`index.html`).
-   `utils/`:
    -   `gemini_utils.py`: Handles interaction with Google Gemini LLM and sector configurations.
    -   `newsapi_helpers.py`: Handles news fetching from NewsAPI.org.
-   `README.md`: This file.
-   `test_newsapi.py`: A utility script to test NewsAPI.org key functionality.

## Setup Instructions (WSL - Ubuntu/Debian based)

1.  **Prerequisites:**
    *   Git: `sudo apt install git`
    *   Python 3.8+ & pip: `sudo apt install python3 python3-pip python3-venv`

2.  **Clone the Repository (or set up your project directory):**
    ```bash
    git clone https://github.com/DipayanDasgupta/NiftySectoralAnalysis.git
    cd NiftySectoralAnalysis
    ```
    (If you are initializing an existing local project, navigate to your project root, e.g., `cd ~/final`)

3.  **Create and Activate Python Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    Your terminal prompt should now start with `(venv)`.

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure API Keys:**
    *   Create a file named `.env` in the project root directory.
    *   Add your API keys to the `.env` file in the following format:
        ```env
        NEWSAPI_ORG_API_KEY="your_actual_newsapi_key"
        GEMINI_API_KEY="your_actual_gemini_api_key"
        FLASK_SECRET_KEY="a_very_strong_random_secret_key_please_change_this"
        ```
    *   Replace placeholders with your real API keys.
    *   **Important:** Change `FLASK_SECRET_KEY` to a unique, strong random string.
    *   The `.gitignore` file is configured to prevent this `.env` file from being committed to Git.

6.  **Run the Flask Application:**
    ```bash
    python app.py
    ```
    The application will typically run on `http://localhost:5003` (or the port specified in `app.py`).

7.  **Access the Application:**
    Open your web browser and navigate to the address shown in the terminal.

## Using the Application

1.  **API Keys:**
    *   The application loads API keys from the `.env` file by default.
    *   You can update the Gemini and NewsAPI.org keys for your current browser session using the "API Keys (Update Session)" section in the sidebar. Click "Update Keys in Session" after entering them. These session keys take precedence.
2.  **Sector Sentiment Analysis:**
    *   The "Analysis Mode" is set to "Sector Sentiment Analysis".
    *   Select the "End Date for Analysis". Note that API queries for news will be capped by the actual current date of the server.
    *   Set the "News Lookback (Days)".
    *   Choose one or more "Sector(s)" for analysis.
    *   Adjust "Max Articles for LLM" (per sector).
    *   Optionally, provide "LLM Instructions".
    *   Click "Run Sector Analysis".
3.  **View Results:**
    *   Sentiment scores are visualized using bar charts.
    *   Detailed textual analysis from Gemini LLM is displayed for each sector.
    *   The "Processing Log" at the bottom provides step-by-step information and any errors encountered during the request.

## Debugging Tips

-   **Server Logs:** Check the terminal where `python app.py` is running for detailed backend logs (set to DEBUG level by default in `app.py`).
-   **Browser Console:** Open your browser's developer tools (usually F12) and check the "Console" tab for JavaScript errors.
-   **UI Log:** The "Processing Log" in the web application displays messages generated during the request, including from API helper functions.
-   **Test NewsAPI Key:** Use the `test_newsapi.py` script to independently verify your NewsAPI.org key: `python test_newsapi.py`.

## Important Notes

-   **System Date:** The application's date capping logic relies on the server's system date being correct. If your WSL system date is set incorrectly (e.g., to the future), news fetching for past periods will not work as expected. Ensure `date` command in WSL shows the correct current date.
-   **NewsAPI.org Limitations:**
    -   The free tier of NewsAPI.org has request limits (e.g., 100 requests per day).
    -   It typically only allows fetching news from the last month for the `/everything` endpoint. The application attempts to respect this by constraining query start dates.
-   **LLM Costs:** Be mindful of potential costs associated with using the Google Gemini API, depending on usage.