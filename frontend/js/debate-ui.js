/**
 * UI rendering functions for policy debate interface
 */
const DebateUI = {
    /**
     * Render a policy debate message
     */
    renderMessage(message, speechName, speechType) {
        const { model_alias, stance, speaker_position, content, citations, latency_ms } = message;
        
        const latencySec = (latency_ms / 1000).toFixed(1);
        const stanceLabel = stance === 'aff' ? 'AFF' : 'NEG';
        
        const speechTypeLabel = this.getSpeechTypeLabel(speechType);
        
        const citationsHTML = citations.length > 0 
            ? `<div class="citations">
                 <strong>Sources:</strong><br>
                 ${citations.map(c => `<div class="citation">[${c.id}] ${c.text}</div>`).join('')}
               </div>`
            : '';

        return `
            <div class="message ${stance}">
                <div class="message-header">
                    <span><strong>${speechName}</strong> - ${speaker_position} (${stanceLabel}): ${model_alias}</span>
                    <span class="message-meta">${latencySec}s • ${speechTypeLabel}</span>
                </div>
                <div class="message-content">${content}</div>
                ${citationsHTML}
            </div>
        `;
    },

    getSpeechTypeLabel(type) {
        const labels = {
            'constructive': 'Constructive',
            'cx_question': 'Cross-Ex Question',
            'cx_answer': 'Cross-Ex Answer',
            'rebuttal': 'Rebuttal'
        };
        return labels[type] || type;
    },

    /**
     * Render a moderator message
     */
    renderModeratorMessage(content) {
        return `
            <div class="message moderator">
                <div class="message-header">
                    <span>Moderator Interjection</span>
                </div>
                <div class="message-content">${content}</div>
            </div>
        `;
    },

    /**
     * Update current speech display
     */
    updateSpeechIndicator(speechName, speechType) {
        document.getElementById('current-speech-name').textContent = speechName;
        const badge = document.getElementById('speech-type-badge');
        badge.textContent = this.getSpeechTypeLabel(speechType);
        
        // Color code by type
        if (speechType === 'constructive') {
            badge.style.backgroundColor = '#4a90e2';
        } else if (speechType.startsWith('cx')) {
            badge.style.backgroundColor = '#ff8c42';
        } else if (speechType === 'rebuttal') {
            badge.style.backgroundColor = '#e94560';
        }
    },

    /**
     * Update progress bar
     */
    updateProgress(currentIndex, total) {
        const percentage = ((currentIndex + 1) / total) * 100;
        document.getElementById('progress-fill').style.width = `${percentage}%`;
        document.getElementById('progress-text').textContent = `Speech ${currentIndex + 1} of ${total}`;
    },

    /**
     * Append message to conversation window
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
        document.getElementById('interject-btn').disabled = true;
        document.getElementById('continue-btn').disabled = true;
        document.getElementById('end-topic-btn').disabled = true;
        document.getElementById('moderator-input').disabled = true;
    },

    /**
     * Enable moderator controls
     */
    enableControls() {
        document.getElementById('interject-btn').disabled = false;
        document.getElementById('continue-btn').disabled = false;
        document.getElementById('end-topic-btn').disabled = false;
        document.getElementById('moderator-input').disabled = false;
    },

    /**
     * Show error message in conversation window
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
    },

    /**
     * Show debate complete message
     */
    showDebateComplete() {
        const message = `
            <div class="message moderator" style="background-color: rgba(74, 144, 226, 0.2); border-color: #4a90e2;">
                <div class="message-header">
                    <span style="color: #4a90e2;">✓ Debate Complete</span>
                </div>
                <div class="message-content">
                    <strong>All speeches have been delivered!</strong><br>
                    The policy debate has concluded. You can now export the transcript or start a new debate.
                </div>
            </div>
        `;
        this.appendMessage(message);
        this.disableControls();
        document.getElementById('continue-btn').textContent = 'Debate Complete';
    }
};
