// frontend/js/community.js

document.addEventListener('DOMContentLoaded', () => {
    const topicFeed = document.getElementById('topic-feed');
    const btnSuggest = document.getElementById('btn-suggest');
    const modal = document.getElementById('suggest-modal');
    const btnClose = document.querySelector('.close');
    const btnSubmitTopic = document.getElementById('btn-submit-topic');
    const topicInput = document.getElementById('suggest-topic-input');

    // Generate simple user ID (for demo purposes)
    const userId = localStorage.getItem('user_id') || `user_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('user_id', userId);

    // Initialize
    fetchTopics();

    // --- Event Listeners ---

    // Open Modal
    btnSuggest.addEventListener('click', () => {
        modal.classList.add('show');
        topicInput.focus();
    });

    // Close Modal
    btnClose.addEventListener('click', () => {
        modal.classList.remove('show');
    });

    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });

    // Submit Topic
    btnSubmitTopic.addEventListener('click', () => {
        const title = topicInput.value.trim();
        if (title) {
            suggestTopic(title);
            topicInput.value = '';
            modal.classList.remove('show');
        }
    });

    // Enter key to submit
    topicInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            btnSubmitTopic.click();
        }
    });

    // --- Functions ---

    async function fetchTopics() {
        try {
            const response = await fetch('/api/community/topics?limit=20');
            if (!response.ok) throw new Error('Failed to fetch topics');
            const topics = await response.json();
            renderTopics(topics);
        } catch (error) {
            console.error('Error fetching topics:', error);
            topicFeed.innerHTML = '<p style="color: #f38ba8; text-align: center;">Failed to load topics.</p>';
        }
    }

    function renderTopics(topics) {
        topicFeed.innerHTML = '';

        if (topics.length === 0) {
            topicFeed.innerHTML = '<p style="color: #a6adc8; text-align: center;">No topics yet. Suggest one!</p>';
            return;
        }

        topics.forEach(topic => {
            // consensus_score is 0-1, convert to percentage
            const scorePercent = Math.round((topic.consensus_score || 0) * 100);
            const isConsensus = scorePercent > 50;

            const card = document.createElement('div');
            card.className = 'topic-card';
            card.innerHTML = `
                <div class="topic-header">
                    <h3 class="topic-title">${escapeHtml(topic.title)}</h3>
                    <div class="topic-actions">
                        <button class="btn btn-run ${isConsensus ? 'show' : ''}" data-topic-id="${topic.id}" style="display: ${isConsensus ? 'block' : 'none'};">Run Debate</button>
                    </div>
                </div>

                <div class="consensus-container">
                    <div class="consensus-labels">
                        <span>Consensus: ${scorePercent}%</span>
                        <span style="color: ${isConsensus ? '#a6e3a1' : '#f38ba8'};">${isConsensus ? '✓ Ready to Run' : 'Needs More Votes'}</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${scorePercent}%; background-color: ${isConsensus ? '#a6e3a1' : '#f38ba8'};"></div>
                    </div>
                </div>

                <div class="topic-votes">
                    <div class="vote-controls">
                        <button class="vote-btn" data-topic-id="${topic.id}" data-vote-type="up" title="Upvote">▲</button>
                        <button class="vote-btn" data-topic-id="${topic.id}" data-vote-type="down" title="Downvote">▼</button>
                    </div>
                    <span style="color: #a6adc8; font-size: 0.9rem;">Complexity: ${topic.complexity_score || 0}</span>
                </div>
            `;

            topicFeed.appendChild(card);
        });

        // Attach event listeners to dynamically created buttons
        document.querySelectorAll('.vote-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const topicId = parseInt(e.target.getAttribute('data-topic-id'));
                const voteType = e.target.getAttribute('data-vote-type');
                voteTopic(topicId, voteType);
            });
        });

        document.querySelectorAll('.btn-run').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const topicId = parseInt(e.target.getAttribute('data-topic-id'));
                executeTopic(topicId);
            });
        });
    }

    async function suggestTopic(title) {
        try {
            const response = await fetch('/api/community/suggest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            if (!response.ok) throw new Error('Failed to suggest topic');
            const result = await response.json();
            console.log('Topic suggested:', result);
            fetchTopics(); // Refresh list
        } catch (error) {
            console.error('Error suggesting topic:', error);
            alert('Failed to suggest topic.');
        }
    }

    async function voteTopic(topicId, voteType) {
        try {
            const response = await fetch('/api/community/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic_id: topicId,
                    user_id: userId,
                    vote_type: voteType
                })
            });
            if (!response.ok) throw new Error('Failed to vote');
            fetchTopics(); // Refresh list to update score
        } catch (error) {
            console.error('Error voting:', error);
        }
    }

    async function executeTopic(topicId) {
        if (!confirm('Start a debate on this topic? This may take several minutes.')) return;

        try {
            const response = await fetch('/api/community/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic_id: topicId })
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to execute');
            }
            const result = await response.json();
            alert(`Debate queued! Job ID: ${result.job_id}\n\nThis feature will be fully integrated soon.`);
        } catch (error) {
            console.error('Error executing topic:', error);
            alert(`Failed to start debate: ${error.message}`);
        }
    }

    // Helper to prevent XSS
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // Make functions available globally for inline event handlers (if needed)
    window.voteTopic = voteTopic;
    window.executeTopic = executeTopic;
});
