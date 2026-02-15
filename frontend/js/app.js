/**
 * Main application logic for policy debate
 */
let currentSession = null;
let debateSettings = {
    temperature: 0.3,
    max_tokens: 512  // ~1 minute speeches
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Load available models
        const { models } = await API.getModels();
        DebateUI.populateModelDropdown(models, 'model1-select');
        DebateUI.populateModelDropdown(models, 'model2-select');
        
        // Enable start button when all fields are filled
        setupFormValidation();
        
        // Setup event listeners
        setupEventListeners();
    } catch (error) {
        console.error('Failed to initialize app:', error);
        alert('Failed to load models. Please ensure the backend server is running.');
    }
});

/**
 * Setup form validation
 */
function setupFormValidation() {
    const topicInput = document.getElementById('topic-input');
    const model1Select = document.getElementById('model1-select');
    const model2Select = document.getElementById('model2-select');
    const startButton = document.getElementById('start-debate-btn');

    function validateForm() {
        const isValid = topicInput.value.trim() !== '' && 
                       model1Select.value !== '' && 
                       model2Select.value !== '';
        startButton.disabled = !isValid;
    }

    topicInput.addEventListener('input', validateForm);
    model1Select.addEventListener('change', validateForm);
    model2Select.addEventListener('change', validateForm);
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Start debate button
    document.getElementById('start-debate-btn').addEventListener('click', startNewDebate);

    // New debate button (in header)
    document.getElementById('new-debate-btn').addEventListener('click', () => {
        if (confirm('Start a new debate? Current conversation will be lost.')) {
            resetToSetup();
        }
    });

    // Moderator controls
    document.getElementById('interject-btn').addEventListener('click', interjectInDebate);
    document.getElementById('continue-btn').addEventListener('click', advanceToNextSpeech);
    document.getElementById('end-topic-btn').addEventListener('click', endDebate);

    // Settings modal
    document.getElementById('settings-btn').addEventListener('click', openSettingsModal);
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', closeSettingsModal);
    });
    document.querySelector('.modal-save').addEventListener('click', saveSettings);
    document.querySelector('.modal-overlay').addEventListener('click', closeSettingsModal);

    // Export button
    document.getElementById('export-btn').addEventListener('click', exportDebate);

    // Enter key in topic input
    document.getElementById('topic-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (!document.getElementById('start-debate-btn').disabled) {
                startNewDebate();
            }
        }
    });
}

/**
 * Start a new policy debate
 */
async function startNewDebate() {
    const topic = document.getElementById('topic-input').value.trim();
    const model1 = document.getElementById('model1-select').value;
    const model2 = document.getElementById('model2-select').value;
    const model1Position = document.getElementById('position-select').value;

    if (!topic || !model1 || !model2) {
        alert('Please fill in all fields');
        return;
    }

    try {
        // Show loading
        document.getElementById('start-debate-btn').disabled = true;
        document.getElementById('start-debate-btn').textContent = 'Starting...';

        // Start debate
        currentSession = await API.startDebate(topic, model1, model2, model1Position);

        // Show debate view
        showDebateView();

        // Show ready message for opening statements
        DebateUI.appendMessage(`
            <div class="message moderator" style="background-color: rgba(74, 144, 226, 0.2); border-color: #4a90e2;">
                <div class="message-header">
                    <span style="color: #4a90e2;">✓ Debate Configured</span>
                </div>
                <div class="message-content">
                    <strong>Topic:</strong> ${currentSession.topic}<br>
                    <strong>Affirmative:</strong> ${currentSession.models.aff}<br>
                    <strong>Negative:</strong> ${currentSession.models.neg}<br><br>
                    Click <strong>"Next Speech"</strong> to begin with opening statements (1AC).
                </div>
            </div>
        `);
    } catch (error) {
        console.error('Failed to start debate:', error);
        alert(`Failed to start debate: ${error.message}`);
        document.getElementById('start-debate-btn').disabled = false;
        document.getElementById('start-debate-btn').textContent = 'Start Debate';
    }
}

/**
 * Show debate view and hide setup
 */
function showDebateView() {
    // Hide setup panel
    document.getElementById('setup-panel').style.display = 'none';

    // Show debate view
    document.getElementById('debate-view').style.display = 'block';

    // Update header
    document.getElementById('debate-topic').textContent = currentSession.topic;
    document.getElementById('aff-model-badge').textContent = `AFF: ${currentSession.models.aff}`;
    document.getElementById('neg-model-badge').textContent = `NEG: ${currentSession.models.neg}`;

    // Show header buttons
    document.getElementById('new-debate-btn').style.display = 'block';
    document.getElementById('settings-btn').style.display = 'block';
    document.getElementById('export-btn').style.display = 'block';

    // Clear conversation window
    DebateUI.clearConversation();

    // Initialize progress
    DebateUI.updateProgress(0, currentSession.debate_flow.length);
    DebateUI.updateSpeechIndicator(currentSession.current_speech.speech, currentSession.current_speech.type);
}

/**
 * Advance to next speech (auto-advance)
 */
async function advanceToNextSpeech() {
    if (!currentSession) return;

    try {
        DebateUI.showLoading();

        // Execute speech
        const result = await API.nextTurn(currentSession.session_id, null, false);

        // Render response
        result.responses.forEach(response => {
            DebateUI.appendMessage(DebateUI.renderMessage(response, result.speech_name, result.speech_type));
        });

        // Check if debate is complete
        if (result.debate_complete) {
            DebateUI.showDebateComplete();
        } else {
            // Update UI for next speech
            DebateUI.updateSpeechIndicator(result.next_speech.speech, result.next_speech.type);
            DebateUI.updateProgress(
                currentSession.debate_flow.findIndex(s => s.speech === result.next_speech.speech),
                currentSession.debate_flow.length
            );
        }
    } catch (error) {
        console.error('Failed to execute speech:', error);
        DebateUI.showError(`Failed to execute speech: ${error.message}`);
    } finally {
        DebateUI.hideLoading();
    }
}

/**
 * Moderator interjection
 */
async function interjectInDebate() {
    const message = document.getElementById('moderator-input').value.trim();
    if (message === '') {
        alert('Please enter a message to interject');
        return;
    }

    if (!currentSession) return;

    try {
        DebateUI.showLoading();

        // Add moderator message
        DebateUI.appendMessage(DebateUI.renderModeratorMessage(message));

        // Execute turn with interjection (doesn't advance speech index)
        const result = await API.nextTurn(currentSession.session_id, message, true);

        // Render response
        result.responses.forEach(response => {
            DebateUI.appendMessage(DebateUI.renderMessage(response, result.speech_name + ' (Interjection)', result.speech_type));
        });

        // Clear moderator input
        document.getElementById('moderator-input').value = '';
    } catch (error) {
        console.error('Failed to interject:', error);
        DebateUI.showError(`Failed to interject: ${error.message}`);
    } finally {
        DebateUI.hideLoading();
    }
}

/**
 * End current debate
 */
async function endDebate() {
    if (!currentSession) return;

    if (!confirm('End this debate? You can export the transcript first.')) {
        return;
    }

    try {
        await API.endTopic(currentSession.session_id);
        DebateUI.showDebateComplete();
    } catch (error) {
        console.error('Failed to end debate:', error);
        alert(`Failed to end debate: ${error.message}`);
    }
}

/**
 * Reset to setup view
 */
function resetToSetup() {
    currentSession = null;
    document.getElementById('debate-view').style.display = 'none';
    document.getElementById('setup-panel').style.display = 'flex';
    document.getElementById('topic-input').value = '';
    document.getElementById('start-debate-btn').textContent = 'Start Debate';
    document.getElementById('new-debate-btn').style.display = 'none';
    document.getElementById('settings-btn').style.display = 'none';
    document.getElementById('export-btn').style.display = 'none';
}

/**
 * Open settings modal
 */
function openSettingsModal() {
    document.getElementById('temperature-input').value = debateSettings.temperature;
    document.getElementById('max-tokens-input').value = debateSettings.max_tokens;
    document.getElementById('settings-modal').style.display = 'block';
}

/**
 * Close settings modal
 */
function closeSettingsModal() {
    document.getElementById('settings-modal').style.display = 'none';
}

/**
 * Save settings
 */
function saveSettings() {
    debateSettings.temperature = parseFloat(document.getElementById('temperature-input').value);
    debateSettings.max_tokens = parseInt(document.getElementById('max-tokens-input').value);
    closeSettingsModal();
    alert('Settings saved! They will apply to future speeches.');
}

/**
 * Export debate as JSON
 */
async function exportDebate() {
    if (!currentSession) return;

    try {
        const history = await API.getHistory(currentSession.session_id);
        const json = JSON.stringify(history, null, 2);
        
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `policy-debate-${currentSession.session_id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Failed to export debate:', error);
        alert(`Failed to export debate: ${error.message}`);
    }
}
