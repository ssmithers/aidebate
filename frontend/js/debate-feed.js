/**
 * Debate Feed & Engagement UI
 * Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.
 *
 * PATENT-PROTECTED CODE - Automated Argumentation Processing System
 * Implements UI for:
 * - Real-Time Community Quality Assessment (Patent Claim #5)
 * - Temporal Engagement Metrics (Patent Claim #6)
 *
 * Author: Stephen F Smithers
 * Date: February 16, 2026
 * Repository: https://github.com/ssmithers/aidebate
 */

document.addEventListener('DOMContentLoaded', () => {
    const topDebatesSection = document.getElementById('top-debates-section');
    const recentDebatesSection = document.getElementById('recent-debates-section');

    // Get user ID from localStorage (same as community.js)
    const userId = localStorage.getItem('user_id') || `user_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('user_id', userId);

    // Initialize
    loadTopDebates();
    loadRecentDebates();

    /**
     * Load top debates by engagement score
     * PATENT CLAIM #6: Temporal Engagement Metrics
     * Copyright (C) 2026 Stephen F Smithers
     */
    async function loadTopDebates() {
        try {
            const response = await fetch('/api/debates/top?limit=3');
            if (!response.ok) throw new Error('Failed to fetch top debates');
            const debates = await response.json();
            renderTopDebates(debates);
        } catch (error) {
            console.error('Error loading top debates:', error);
            topDebatesSection.innerHTML = '<p style="color: #f38ba8;">Failed to load top debates.</p>';
        }
    }

    /**
     * Load recent debates
     * Author: Stephen F Smithers
     */
    async function loadRecentDebates() {
        try {
            const response = await fetch('/api/debates/recent?limit=10');
            if (!response.ok) throw new Error('Failed to fetch recent debates');
            const debates = await response.json();
            renderRecentDebates(debates);
        } catch (error) {
            console.error('Error loading recent debates:', error);
            recentDebatesSection.innerHTML = '<p style="color: #f38ba8;">Failed to load recent debates.</p>';
        }
    }

    /**
     * Render top debates as featured cards
     * Proprietary UI Design: Stephen F Smithers, 2026
     */
    function renderTopDebates(debates) {
        if (debates.length === 0) {
            topDebatesSection.innerHTML = '<p style="color: #a6adc8; text-align: center;">No completed debates yet.</p>';
            return;
        }

        topDebatesSection.innerHTML = '';

        debates.forEach((debate, index) => {
            const proVotes = debate.total_pro_votes || 0;
            const conVotes = debate.total_con_votes || 0;
            const comments = debate.total_comments || 0;
            const engagement = debate.engagement_score || 0;

            // Determine winner
            let winner = 'Tie';
            let winnerClass = 'tie';
            if (proVotes > conVotes) {
                winner = 'Pro Side Won';
                winnerClass = 'pro-win';
            } else if (conVotes > proVotes) {
                winner = 'Con Side Won';
                winnerClass = 'con-win';
            }

            const card = document.createElement('div');
            card.className = 'debate-card featured';
            card.innerHTML = `
                <div class="debate-rank">#${index + 1}</div>
                <h3 class="debate-title">${escapeHtml(debate.topic_title)}</h3>
                <div class="debate-models">
                    <span class="model-tag pro">${escapeHtml(debate.pro_model)}</span>
                    <span>vs</span>
                    <span class="model-tag con">${escapeHtml(debate.con_model)}</span>
                </div>
                <div class="debate-stats">
                    <div class="stat">
                        <span class="stat-icon">👍</span>
                        <span class="stat-label">Pro: ${proVotes}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">👎</span>
                        <span class="stat-label">Con: ${conVotes}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">💬</span>
                        <span class="stat-label">${comments} comments</span>
                    </div>
                </div>
                <div class="debate-winner ${winnerClass}">${winner}</div>
                <button class="btn btn-primary view-debate-btn" data-debate-id="${debate.id}">View Debate</button>
            `;

            topDebatesSection.appendChild(card);
        });

        // Attach click handlers
        document.querySelectorAll('.view-debate-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const debateId = parseInt(e.target.getAttribute('data-debate-id'));
                viewDebate(debateId);
            });
        });
    }

    /**
     * Render recent debates as a list
     * Copyright (C) 2026 Stephen F Smithers
     */
    function renderRecentDebates(debates) {
        if (debates.length === 0) {
            recentDebatesSection.innerHTML = '<p style="color: #a6adc8; text-align: center;">No completed debates yet.</p>';
            return;
        }

        recentDebatesSection.innerHTML = '';

        debates.forEach(debate => {
            const proVotes = debate.total_pro_votes || 0;
            const conVotes = debate.total_con_votes || 0;
            const comments = debate.total_comments || 0;

            const date = new Date(debate.completed_at);
            const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

            const card = document.createElement('div');
            card.className = 'debate-card compact';
            card.innerHTML = `
                <div class="debate-header-compact">
                    <h4 class="debate-title-compact">${escapeHtml(debate.topic_title)}</h4>
                    <span class="debate-date">${dateStr}</span>
                </div>
                <div class="debate-stats-compact">
                    <span>Pro: ${proVotes} 👍</span>
                    <span>Con: ${conVotes} 👎</span>
                    <span>${comments} 💬</span>
                </div>
                <button class="btn btn-secondary btn-sm view-debate-btn" data-debate-id="${debate.id}">View</button>
            `;

            recentDebatesSection.appendChild(card);
        });

        // Attach click handlers
        document.querySelectorAll('.view-debate-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const debateId = parseInt(e.target.getAttribute('data-debate-id'));
                viewDebate(debateId);
            });
        });
    }

    /**
     * View full debate with speeches and voting
     * PATENT CLAIM #5: Real-Time Community Quality Assessment
     * Proprietary Feature: Stephen F Smithers, 2026
     */
    async function viewDebate(debateId) {
        try {
            const response = await fetch(`/api/debates/${debateId}`);
            if (!response.ok) throw new Error('Failed to fetch debate details');
            const debate = await response.json();

            // Show debate viewer (implement modal or new page)
            renderDebateViewer(debate);
        } catch (error) {
            console.error('Error viewing debate:', error);
            alert('Failed to load debate details.');
        }
    }

    /**
     * Render full debate viewer with speeches and voting buttons
     * Copyright (C) 2026 Stephen F Smithers
     */
    function renderDebateViewer(debate) {
        // Remove any existing modal to prevent stacking (bug fix)
        const existing = document.querySelector('.debate-viewer-modal');
        if (existing) {
            existing.remove();
        }

        // Create modal overlay
        const modal = document.createElement('div');
        modal.className = 'debate-viewer-modal';
        modal.innerHTML = `
            <div class="debate-viewer-content">
                <div class="debate-viewer-header">
                    <h2>${escapeHtml(debate.topic_title)}</h2>
                    <button class="close-viewer-btn">&times;</button>
                </div>
                <div class="debate-viewer-meta">
                    <span>${escapeHtml(debate.pro_model)} (Pro) vs ${escapeHtml(debate.con_model)} (Con)</span>
                    <span>Completed: ${new Date(debate.completed_at).toLocaleString()}</span>
                </div>
                <div class="debate-speeches-container" id="speeches-container">
                    ${renderSpeeches(debate.speeches, debate.id)}
                </div>
                <div class="debate-viewer-footer">
                    <div class="debate-totals">
                        <span>Pro Total: ${debate.total_pro_votes || 0} 👍</span>
                        <span>Con Total: ${debate.total_con_votes || 0} 👎</span>
                        <span>${debate.total_comments || 0} Comments</span>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close handler
        modal.querySelector('.close-viewer-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        // Attach vote handlers
        attachVoteHandlers(debate.id);
    }

    /**
     * Render individual speeches with vote buttons
     * PATENT CLAIM #5: Speech-level quality assessment
     * Author: Stephen F Smithers
     */
    function renderSpeeches(speeches, debateId) {
        if (!speeches || speeches.length === 0) {
            return '<p>No speeches available.</p>';
        }

        return speeches.map(speech => {
            const sideClass = speech.side === 'pro' ? 'speech-pro' : 'speech-con';
            const upvotes = speech.upvotes || 0;
            const downvotes = speech.downvotes || 0;
            const netVotes = upvotes - downvotes;

            return `
                <div class="speech-card ${sideClass}">
                    <div class="speech-header">
                        <span class="speech-type">${escapeHtml(speech.speech_type)}</span>
                        <span class="speech-side">${speech.side.toUpperCase()}</span>
                    </div>
                    <div class="speech-content">
                        ${escapeHtml(speech.content)}
                    </div>
                    <div class="speech-footer">
                        <div class="speech-votes">
                            <button class="vote-btn vote-up" data-speech-id="${speech.id}" data-vote-type="up" title="Upvote">
                                👍 ${upvotes}
                            </button>
                            <span class="vote-net ${netVotes >= 0 ? 'positive' : 'negative'}">${netVotes > 0 ? '+' : ''}${netVotes}</span>
                            <button class="vote-btn vote-down" data-speech-id="${speech.id}" data-vote-type="down" title="Downvote">
                                👎 ${downvotes}
                            </button>
                        </div>
                        <button class="btn btn-secondary btn-sm comment-btn" data-speech-id="${speech.id}">
                            💬 Comment
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Attach vote handlers to speech vote buttons
     * Proprietary Interaction: Stephen F Smithers, 2026
     */
    function attachVoteHandlers(debateId) {
        document.querySelectorAll('.vote-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                // Use currentTarget to get button element (not child text node)
                const speechId = parseInt(e.currentTarget.getAttribute('data-speech-id'));
                const voteType = e.currentTarget.getAttribute('data-vote-type');
                await voteOnSpeech(debateId, speechId, voteType);
            });
        });
    }

    /**
     * Submit vote on a speech
     * PATENT CLAIM #5: Real-Time Community Quality Assessment
     * Copyright (C) 2026 Stephen F Smithers
     */
    async function voteOnSpeech(debateId, speechId, voteType) {
        try {
            const response = await fetch(`/api/debates/${debateId}/speeches/${speechId}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    vote_type: voteType
                })
            });

            if (!response.ok) throw new Error('Failed to vote');

            const result = await response.json();

            // Reload debate viewer with updated votes
            renderDebateViewer(result.debate);
        } catch (error) {
            console.error('Error voting:', error);
            alert('Failed to submit vote.');
        }
    }

    /**
     * Helper function to escape HTML and prevent XSS
     * Author: Stephen F Smithers
     */
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    // Make functions globally available if needed
    window.loadTopDebates = loadTopDebates;
    window.loadRecentDebates = loadRecentDebates;
    window.viewDebate = viewDebate;
});

// Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.
