/**
 * Main application logic for policy debate
 */
let currentSession = null;
let debateSettings = {
    temperature: 0.3,
    max_tokens: 16384  // Allow full-length debate arguments without truncation
};

/**
 * Safely bind an event listener to an element by ID.
 * Returns the element if found, null if not (no error thrown).
 */
function bindElement(id, event, handler) {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener(event, handler);
    } else {
        console.debug(`[UI] Element #${id} not found — skipping binding`);
    }
    return el;
}

/**
 * Safely show an element by ID
 */
function showElement(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
}

/**
 * Safely hide an element by ID
 */
function hideElement(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
}

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Setup event listeners first (validates required UI elements)
        if (!setupEventListeners()) {
            alert('Failed to initialize UI: required elements are missing');
            return;
        }

        // Load available models
        const { models } = await API.getModels();
        DebateUI.populateModelDropdown(models, 'model1-select');
        DebateUI.populateModelDropdown(models, 'model2-select');

        // Enable start button when all fields are filled
        setupFormValidation();
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
 * Returns false if required elements are missing
 */
function setupEventListeners() {
    // Verify required elements exist
    const requiredIds = ['topic-input', 'start-debate-btn', 'model1-select', 'model2-select',
                         'position-select', 'temperature-input', 'max-tokens-input',
                         'configure-debate-btn', 'back-to-home-btn', 'landing-page', 'setup-panel'];
    for (const id of requiredIds) {
        if (!document.getElementById(id)) {
            console.error(`[UI] Required element #${id} is missing — app cannot initialize`);
            return false;
        }
    }

    // Required landing page navigation
    bindElement('configure-debate-btn', 'click', () => {
        hideElement('landing-page');
        showElement('setup-panel');
        hideElement('configure-debate-btn');
        showElement('back-to-home-btn');
        document.getElementById('back-to-home-btn').style.display = 'inline-block';
    });

    bindElement('back-to-home-btn', 'click', () => {
        showElement('landing-page');
        hideElement('setup-panel');
        showElement('configure-debate-btn');
        hideElement('back-to-home-btn');
        document.getElementById('configure-debate-btn').style.display = 'inline-block';
    });

    // Required debate controls
    bindElement('start-debate-btn', 'click', startNewDebate);
    bindElement('topic-input', 'keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (!document.getElementById('start-debate-btn').disabled) {
                startNewDebate();
            }
        }
    });

    // Required moderator controls (only exist in debate view)
    bindElement('interject-btn', 'click', interjectInDebate);
    bindElement('continue-btn', 'click', advanceToNextSpeech);
    bindElement('end-topic-btn', 'click', endDebate);

    // Optional feature bindings (gracefully skip if not in DOM)
    bindElement('new-debate-btn', 'click', () => {
        if (confirm('Start a new debate? Current conversation will be lost.')) {
            resetToSetup();
        }
    });
    bindElement('settings-btn', 'click', openSettingsModal);
    bindElement('export-btn', 'click', exportDebate);

    // Optional settings modal bindings
    const modalClose = document.querySelectorAll('.modal-close');
    if (modalClose.length > 0) {
        modalClose.forEach(btn => btn.addEventListener('click', closeSettingsModal));
    }
    const modalSave = document.querySelector('.modal-save');
    if (modalSave) modalSave.addEventListener('click', saveSettings);

    const modalOverlay = document.querySelector('.modal-overlay');
    if (modalOverlay) modalOverlay.addEventListener('click', closeSettingsModal);

    return true;
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

    // Read settings from form
    const temperature = parseFloat(document.getElementById('temperature-input').value);
    const maxTokens = parseInt(document.getElementById('max-tokens-input').value);
    // Update debateSettings for this session
    debateSettings = { temperature, max_tokens: maxTokens };

    try {
        // Show loading
        document.getElementById('start-debate-btn').disabled = true;
        document.getElementById('start-debate-btn').textContent = 'Starting...';

        // Start debate with settings from form (always 18 speeches - full policy debate + closing arguments)
        currentSession = await API.startDebate(topic, model1, model2, model1Position, 18);

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
    hideElement('setup-panel');

    // Show debate view
    showElement('debate-view');

    // Update header
    const topicEl = document.getElementById('debate-topic');
    const affBadgeEl = document.getElementById('aff-model-badge');
    const negBadgeEl = document.getElementById('neg-model-badge');

    if (topicEl) topicEl.textContent = currentSession.topic;
    if (affBadgeEl) affBadgeEl.textContent = `AFF: ${currentSession.models.aff}`;
    if (negBadgeEl) negBadgeEl.textContent = `NEG: ${currentSession.models.neg}`;

    // Show optional header buttons (if they exist)
    showElement('new-debate-btn');
    showElement('export-btn');

    // Show glossary sidebar
    showElement('glossary-sidebar');

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

    // Hide debate view, show setup
    hideElement('debate-view');
    const setupPanel = document.getElementById('setup-panel');
    if (setupPanel) setupPanel.style.display = 'flex';

    // Reset form inputs
    const topicInput = document.getElementById('topic-input');
    const startBtn = document.getElementById('start-debate-btn');
    if (topicInput) topicInput.value = '';
    if (startBtn) startBtn.textContent = 'Start Debate';

    // Hide optional buttons (if they exist)
    hideElement('new-debate-btn');
    hideElement('settings-btn');
    hideElement('export-btn');
    hideElement('glossary-sidebar');
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
    alert('Settings saved! They will apply to new debates (current debate will continue with original settings).');
}

/**
 * Export debate as Markdown transcript
 */
async function exportDebate() {
    if (!currentSession) return;

    try {
        const response = await fetch(`http://localhost:5000/api/debate/export/${currentSession.session_id}`);
        const markdown = await response.text();

        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Create filename from topic (sanitized)
        const topicSlug = currentSession.topic
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-|-$/g, '')
            .substring(0, 50);

        a.download = `debate-${topicSlug}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Failed to export debate:', error);
        alert(`Failed to export debate: ${error.message}`);
    }
}
