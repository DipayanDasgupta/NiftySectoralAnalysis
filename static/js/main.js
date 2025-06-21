// static/js/main.js
document.addEventListener('DOMContentLoaded', function () {
    const updateApiKeysBtn = document.getElementById('updateApiKeysBtn');
    const analysisForm = document.getElementById('analysisForm');
    const runAnalysisBtn = document.getElementById('runAnalysisBtn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const logsOutput = document.getElementById('logs-output');
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    const resultsSummaryDiv = document.getElementById('results-summary');
    const sectorChartsContainer = document.getElementById('sector-charts-container');
    const sectorDetailsContainer = document.getElementById('sector-details-container');
    const errorMessagesContainer = document.getElementById('error-messages-container');
    const errorList = document.getElementById('error-list');

    const MAX_LOG_ENTRIES = 300;
    let currentLogEntries = [];
    let sectorSentimentCharts = {}; // { canvasId: chartInstance }

    function displayErrorMessages(messages) {
        errorList.innerHTML = '';
        if (messages && messages.length > 0) {
            messages.forEach(msg => {
                const li = document.createElement('li');
                li.textContent = msg; 
                errorList.appendChild(li);
            });
            errorMessagesContainer.style.display = 'block';
        } else {
            errorMessagesContainer.style.display = 'none';
        }
    }
    
    function escapeHtml(unsafe) {
        if (unsafe === null || typeof unsafe === 'undefined') return '';
        return unsafe.toString()
             .replace(/&/g, "&")   // Corrected
             .replace(/</g, "<")    // Corrected
             .replace(/>/g, ">")    // Corrected
             .replace(/"/g, '"')  // Corrected
             .replace(/'/g, "'"); // Corrected (or ')
    }

    function appendToLog(logEntry) { // logEntry is {timestamp, message, level}
        currentLogEntries.push(logEntry);
        if (currentLogEntries.length > MAX_LOG_ENTRIES) {
            currentLogEntries.shift(); 
        }
        renderLogs();
    }

    function renderLogs() {
        logsOutput.innerHTML = ''; 
        currentLogEntries.forEach(logEntry => {
            const logElement = document.createElement('div');
            logElement.classList.add('log-entry');
            logElement.innerHTML = `<span class="log-timestamp">[${logEntry.timestamp}]</span> <span class="log-level-${logEntry.level.toUpperCase()}">[${logEntry.level.toUpperCase()}]</span> ${escapeHtml(logEntry.message)}`;
            logsOutput.appendChild(logElement);
        });
        logsOutput.scrollTop = logsOutput.scrollHeight;
    }

    clearLogsBtn.addEventListener('click', () => {
        currentLogEntries = [];
        renderLogs(); 
        appendToLog({ timestamp: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 }), message: "UI Logs cleared by user.", level: "INFO" });
    });

    updateApiKeysBtn.addEventListener('click', async () => {
        const geminiKeySess = document.getElementById('gemini_key_sess_in').value;
        const newsapiKeySess = document.getElementById('newsapi_key_sess_in').value;
        // Removed StockData and EventRegistry key inputs from here

        const payload = {};
        if (geminiKeySess) payload.gemini_key = geminiKeySess;
        if (newsapiKeySess) payload.newsapi_key = newsapiKeySess;
        
        const currentTimestamp = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });

        if (Object.keys(payload).length === 0) {
            appendToLog({ timestamp: currentTimestamp, message: "No API keys entered to update in session.", level: "WARNING" });
            return;
        }
        
        loadingIndicator.style.display = 'block';
        try {
            const response = await fetch('/api/update-api-keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            appendToLog({ timestamp: currentTimestamp, message: data.message || "API Key session update response.", level: "INFO" });
            if (!response.ok) displayErrorMessages([data.message || `Error updating keys: ${response.status}`]);
            else displayErrorMessages([]); 
        } catch (error) {
            console.error('Error updating API keys:', error);
            appendToLog({ timestamp: currentTimestamp, message: `Client-side error updating API keys: ${error}`, level: "ERROR" });
            displayErrorMessages([`Client-side error updating keys: ${error}`]);
        } finally {
            loadingIndicator.style.display = 'none';
        }
    });

    analysisForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        runAnalysisBtn.disabled = true;
        loadingIndicator.style.display = 'block';
        resultsSummaryDiv.innerHTML = '<p>Processing your request...</p>';
        
        // --- Chart and Details Cleanup ---
        Object.values(sectorSentimentCharts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        sectorSentimentCharts = {};
        while (sectorChartsContainer.firstChild) {
            sectorChartsContainer.removeChild(sectorChartsContainer.firstChild);
        }
        sectorDetailsContainer.innerHTML = '';
        // --- End Cleanup ---

        displayErrorMessages([]); 

        const formData = new FormData(analysisForm);
        const data = {};
        formData.forEach((value, key) => {
            if (key === 'selected_sectors') {
                if (!data[key]) data[key] = [];
                data[key].push(value);
            } else {
                data[key] = value;
            }
        });
        
        const currentTimestamp = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });
        // sector_news_source is now hidden input with value "NewsAPI.org"
        appendToLog({ timestamp: currentTimestamp, message: `Starting ${data.analysis_mode || 'analysis'}... (News Source: ${data.sector_news_source})`, level: "INFO" });

        try {
            const response = await fetch('/api/sector-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.logs && Array.isArray(result.logs)) {
                result.logs.forEach(logEntry => appendToLog(logEntry));
            }

            if (!response.ok || result.error) {
                const errorMessagesToDisplay = result.messages || (result.error && typeof result.error === 'string' ? [result.error] : [`Server error: ${response.status}. Check server logs.`]);
                displayErrorMessages(errorMessagesToDisplay);
                resultsSummaryDiv.innerHTML = `<p class="error-message">Analysis failed. Check errors and logs.</p>`;
                appendToLog({ timestamp: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 }), message: `Analysis failed: ${errorMessagesToDisplay.join(', ')}`, level: "ERROR" });
            } else {
                const numResults = result.results ? result.results.length : 0;
                resultsSummaryDiv.innerHTML = `<p>Analysis complete. Found ${numResults} sector result(s).</p>`;
                displaySectorResults(result.results || []);
            }
        } catch (error) {
            console.error('Client-side error during analysis fetch:', error);
            const errTimestamp = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });
            appendToLog({ timestamp: errTimestamp, message: `Client-side error during analysis: ${error.message || error}`, level: "ERROR" });
            displayErrorMessages([`Client-side error: ${error.message || 'Network error or invalid JSON response.'}`]);
            resultsSummaryDiv.innerHTML = `<p class="error-message">A client-side error occurred. Check console and logs.</p>`;
        } finally {
            runAnalysisBtn.disabled = false;
            loadingIndicator.style.display = 'none';
        }
    });

    function displaySectorResults(sectorResults) {
        // Clear containers again (defensive)
        Object.values(sectorSentimentCharts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') chart.destroy();
        });
        sectorSentimentCharts = {};
        while (sectorChartsContainer.firstChild) sectorChartsContainer.removeChild(sectorChartsContainer.firstChild);
        sectorDetailsContainer.innerHTML = '';

        if (!sectorResults || sectorResults.length === 0) {
            sectorDetailsContainer.innerHTML = "<p>No sector results to display or an error occurred globally.</p>";
            return;
        }

        sectorResults.forEach((sectorData, index) => {
            const analysis = sectorData.gemini_analysis;

            const chartWrapper = document.createElement('div');
            chartWrapper.classList.add('chart-wrapper');
            
            const chartTitle = document.createElement('h4');
            chartTitle.textContent = `Sentiment Score: ${escapeHtml(sectorData.sector_name)}`;
            chartWrapper.appendChild(chartTitle);

            const canvasId = `sectorChart-${index}`;
            const canvas = document.createElement('canvas');
            canvas.id = canvasId;
            chartWrapper.appendChild(canvas);
            sectorChartsContainer.appendChild(chartWrapper);

            if (analysis && typeof analysis.sentiment_score_llm === 'number') {
                const sentimentScore = analysis.sentiment_score_llm;
                try {
                    const ctx = document.getElementById(canvasId).getContext('2d');
                    // No need to check sectorSentimentCharts[canvasId] before destroy if we clear the object above
                    sectorSentimentCharts[canvasId] = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: [escapeHtml(sectorData.sector_name)], 
                            datasets: [{
                                label: 'LLM Sentiment Score',
                                data: [sentimentScore],
                                backgroundColor: [sentimentScore > 0.1 ? 'rgba(75, 192, 192, 0.6)' : sentimentScore < -0.1 ? 'rgba(255, 99, 132, 0.6)' : 'rgba(201, 203, 207, 0.6)'],
                                borderColor: [sentimentScore > 0.1 ? 'rgba(75, 192, 192, 1)' : sentimentScore < -0.1 ? 'rgba(255, 99, 132, 1)' : 'rgba(201, 203, 207, 1)'],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true, maintainAspectRatio: false,
                            scales: { y: { beginAtZero: false, min: -1, max: 1, title: { display: true, text: 'Score (-1 to 1)' } } },
                            plugins: { legend: { display: false } },
                            animation: { duration: 800, easing: 'easeInOutQuart' }
                        }
                    });
                } catch (e) {
                    console.error("Chart.js initialization error for " + canvasId + ": ", e);
                    const errorP = document.createElement('p');
                    errorP.textContent = "Error rendering chart.";
                    errorP.classList.add('error-message');
                    chartWrapper.appendChild(errorP);
                }
            } else {
                 const noScoreP = document.createElement('p');
                 noScoreP.textContent = "Sentiment score not available or not a number.";
                 chartWrapper.appendChild(noScoreP);
            }

            const detailItem = document.createElement('div');
            detailItem.classList.add('result-item');
            let detailHtml = `<h3>${escapeHtml(sectorData.sector_name)}</h3>`;
            detailHtml += `<p><small>LLM Context Period: ${escapeHtml(sectorData.llm_context_date_range || 'N/A')} | Articles for LLM: ${sectorData.num_articles_for_llm}</small></p>`;

            if (sectorData.error_message) {
                detailHtml += `<p class="error-message"><strong>Error for this sector:</strong> ${escapeHtml(sectorData.error_message)}</p>`;
            } else if (analysis) {
                detailHtml += `<p><strong>Overall Sentiment:</strong> ${escapeHtml(analysis.overall_sentiment || 'N/A')} (Score: ${analysis.sentiment_score_llm !== null && typeof analysis.sentiment_score_llm !== 'undefined' ? parseFloat(analysis.sentiment_score_llm).toFixed(2) : 'N/A'})</p>`;
                detailHtml += `<p><strong>Summary:</strong> ${escapeHtml(analysis.summary || 'N/A')}</p>`;
                detailHtml += `<p><strong>Reason:</strong> ${escapeHtml(analysis.sentiment_reason || 'N/A')}</p>`;
                const createListHtml = (items, listTitle) => {
                    if (items && Array.isArray(items) && items.length > 0) {
                        return `<strong>${listTitle}:</strong><ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
                    } return `<strong>${listTitle}:</strong> N/A`;
                };
                detailHtml += createListHtml(analysis.key_themes, 'Key Themes');
                detailHtml += `<p><strong>Potential Impact:</strong> ${escapeHtml(analysis.potential_impact || 'N/A')}</p>`;
                detailHtml += createListHtml(analysis.key_companies_mentioned_context, 'Companies in Context');
                detailHtml += createListHtml(analysis.risks_identified, 'Risks');
                detailHtml += createListHtml(analysis.opportunities_identified, 'Opportunities');
            } else {
                detailHtml += `<p>No analysis data available for this sector (and no specific error reported).</p>`;
            }
            detailItem.innerHTML = detailHtml;
            sectorDetailsContainer.appendChild(detailItem);
        });
    }

    appendToLog({ timestamp: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 }), message: "Frontend initialized. Ready.", level: "INFO" });
});