/**
 * UI rendering functions for debate interface
 */
const DebateUI = {
    /**
     * Render a debate message
     * @param {Object} message - Message object from API
     * @returns {string} HTML string
     */
    renderMessage(message) {
        const { model_alias, stance, content, citations, latency_ms } = message;
        
        const latencySec = (latency_ms / 1000).toFixed(1);
        const stanceLabel = stance === 'pro' ? 'PRO' : 'CON';
        const modelLabel = stance === 'pro' ? 'Model 1' : 'Model 2';
        
        const citationsHTML = citations.length > 0 
            ? `<div class="citations">
                 <strong>Sources:</strong><br>
                 ${citations.map(c => `<div class="citation">[${c.id}] ${c.text}</div>`).join('')}
               </div>`
            : '';

        return `
            <div class="message ${stance}">
                <div class="message-header">
                    <span>${modelLabel} (${stanceLabel}): ${model_alias}</span>
                    <span class="message-meta">${latencySec}s</span>
                </div>
                <div class="message-content">${content}</div>
                ${citationsHTML}
            </div>
        `;
    },

    /**
     * Render a moderator message
     * @param {string} content - Message content
     * @returns {string} HTML string
     */
    renderModeratorMessage(content) {
        return `
            <div class="message moderator">
                <div class="message-header">
                    <span>Moderator</span>
                </div>
                <div class="message-content">${content}</div>
            </div>
        `;
    },

    /**
     * Append message to conversation window
     * @param {string} html - Message HTML
     */
    appendMessage(html) {
        const conversationWindow = document.getElementById('conversation-window');
        conversationWindow.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },

    /**
     * Scroll conversation window to bottom
     */
    scrollToBottom() {
        const conversationWindow = document.getElementById('conversation-window');
        conversationWindow.scrollTop = conversationWindow.scrollHeight;
    },

    /**
     * Show loading indicator
     */
    showLoading() {
        document.getElementById('loading-indicator').style.display = 'flex';
        this.disableControls();
    },

    /**
     * Hide loading indicator
     */
    hideLoading() {
        document.getElementById('loading-indicator').style.display = 'none';
        this.enableControls();
    },

    /**
     * Disable moderator controls
     */
    disableControls() {
        document.getElementById('send-btn').disabled = true;
        document.getElementById('continue-btn').disabled = true;
        document.getElementById('end-topic-btn').disabled = true;
        document.getElementById('moderator-input').disabled = true;
    },

    /**
     * Enable moderator controls
     */
    enableControls() {
        document.getElementById('send-btn').disabled = false;
        document.getElementById('continue-btn').disabled = false;
        document.getElementById('end-topic-btn').disabled = false;
        document.getElementById('moderator-input').disabled = false;
    },

    /**
     * Show error message in conversation window
     * @param {string} error - Error message
     */
    showError(error) {
        const errorHTML = `
            <div class="message moderator">
                <div class="message-header">
                    <span style="color: #e94560;">Error</span>
                </div>
                <div class="message-content" style="color: #e94560;">${error}</div>
            </div>
        `;
        this.appendMessage(errorHTML);
    },

    /**
     * Clear conversation window
     */
    clearConversation() {
        document.getElementById('conversation-window').innerHTML = '';
    },

    /**
     * Populate model dropdown
     * @param {Array} models - Array of model objects
     */
    populateModelDropdown(models, selectId) {
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Select a model</option>';
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.alias;
            option.textContent = `${model.name} (${model.alias})`;
            select.appendChild(option);
        });
    }
};
