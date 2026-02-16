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
            const topic = debate.topic_title;

            // Determine debate type: "X vs Y" or Yes/No question
            const isVersusDebate = topic.toLowerCase().includes(' vs ') || topic.toLowerCase().includes(' versus ');

            let voteDisplay = '';

            if (isVersusDebate) {
                // Split on " vs " or " versus "
                const parts = topic.split(/\s+vs\.?\s+|\s+versus\s+/i);
                const side1 = parts[0] ? escapeHtml(parts[0].trim()) : 'Pro';
                const side2 = parts[1] ? escapeHtml(parts[1].trim()) : 'Con';

                voteDisplay = `
                    <div class="debate-versus">
                        <div class="versus-side">
                            <div class="versus-label">${side1}</div>
                            <div class="versus-votes">👍 ${proVotes}</div>
                        </div>
                        <div class="versus-side">
                            <div class="versus-label">${side2}</div>
                            <div class="versus-votes">👍 ${conVotes}</div>
                        </div>
                    </div>
                `;
            } else {
                // Yes/No question format
                voteDisplay = `
                    <h4 class="debate-title">${escapeHtml(topic)}</h4>
                    <div class="debate-yesno">
                        <div class="yesno-option">
                            <span class="yesno-label">Yes</span>
                            <span class="yesno-votes">👍 ${proVotes}</span>
                        </div>
                        <div class="yesno-option">
                            <span class="yesno-label">No</span>
                            <span class="yesno-votes">👎 ${conVotes}</span>
                        </div>
                    </div>
                `;
            }

            const card = document.createElement('div');
            card.className = 'debate-card featured';
            card.innerHTML = `
                <div class="debate-rank">#${index + 1}</div>
                ${voteDisplay}
                ${comments > 0 ? `<div class="comment-count">💬 ${comments}</div>` : ''}
                <div class="button-group-compact">
                    <button class="btn btn-secondary btn-sm view-debate-btn" data-debate-id="${debate.id}">View</button>
                    ${debate.session_id ? `<button class="btn btn-primary btn-sm export-debate-btn" data-session-id="${debate.session_id}" data-topic="${escapeHtml(topic)}">📥 Export</button>` : ''}
                </div>
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

        // Attach export handlers
        document.querySelectorAll('.export-debate-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.target.getAttribute('data-session-id');
                const topic = e.target.getAttribute('data-topic');
                exportDebateFromFeed(sessionId, topic);
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
            const topic = debate.topic_title;

            const date = new Date(debate.completed_at);
            const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            // Determine debate type
            const isVersusDebate = topic.toLowerCase().includes(' vs ') || topic.toLowerCase().includes(' versus ');

            let statsDisplay = '';
            if (isVersusDebate) {
                const parts = topic.split(/\s+vs\.?\s+|\s+versus\s+/i);
                const side1 = parts[0] ? parts[0].trim() : 'Pro';
                const side2 = parts[1] ? parts[1].trim() : 'Con';
                statsDisplay = `<span>${side1}: ${proVotes} 👍</span> <span>${side2}: ${conVotes} 👍</span>`;
            } else {
                statsDisplay = `<span>Yes: ${proVotes} 👍</span> <span>No: ${conVotes} 👎</span>`;
            }

            const card = document.createElement('div');
            card.className = 'debate-card compact';
            card.innerHTML = `
                <div class="debate-header-compact">
                    <h4 class="debate-title-compact">${escapeHtml(topic)}</h4>
                    <span class="debate-date">${dateStr}</span>
                </div>
                <div class="debate-stats-compact">
                    ${statsDisplay}
                    ${comments > 0 ? `<span>${comments} 💬</span>` : ''}
                </div>
                <div class="button-group-compact">
                    <button class="btn btn-secondary btn-sm view-debate-btn" data-debate-id="${debate.id}">View</button>
                    ${debate.session_id ? `<button class="btn btn-primary btn-sm export-debate-btn" data-session-id="${debate.session_id}" data-topic="${escapeHtml(topic)}">📥 Export</button>` : ''}
                </div>
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

        // Attach export handlers
        document.querySelectorAll('.export-debate-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.target.getAttribute('data-session-id');
                const topic = e.target.getAttribute('data-topic');
                exportDebateFromFeed(sessionId, topic);
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

            console.log('Debate data received:', debate);
            console.log('Number of speeches in debate:', debate.speeches ? debate.speeches.length : 'undefined');

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
                <div id="judgment-section" class="judgment-section" data-topic-title="${escapeHtml(debate.topic_title)}">
                    <!-- Judgment will be loaded here -->
                </div>
                <div class="debate-viewer-footer">
                    <div class="debate-totals">
                        <span>Pro Total: ${debate.total_pro_votes || 0} 👍</span>
                        <span>Con Total: ${debate.total_con_votes || 0} 👎</span>
                        <span>${debate.total_comments || 0} Comments</span>
                    </div>
                    <button class="btn btn-primary get-judgment-btn" data-debate-id="${debate.id}">
                        🏆 Get AI Judgment
                    </button>
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

        // Load existing judgments
        loadJudgments(debate.id);

        // Attach judgment button handler
        modal.querySelector('.get-judgment-btn').addEventListener('click', async () => {
            await requestJudgment(debate.id);
        });
    }

    /**
     * Render individual speeches with vote buttons
     * PATENT CLAIM #5: Speech-level quality assessment
     * Author: Stephen F Smithers
     */
    function renderSpeeches(speeches, debateId) {
        console.log('renderSpeeches called with:', speeches ? speeches.length : 0, 'speeches');

        if (!speeches || speeches.length === 0) {
            return '<p style="color: #f38ba8; padding: 2rem;">No speeches available. Debug: speeches is ' + (speeches ? 'empty array' : 'null/undefined') + '</p>';
        }

        const header = `<div style="background: #313244; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; color: #a6adc8;">
            <strong>📜 Debate Transcript</strong> — ${speeches.length} speeches loaded
        </div>`;

        const speechesHTML = speeches.map(speech => {
            // Map 'aff'/'neg' from database to 'pro'/'con' for styling
            const side = (speech.side === 'aff' || speech.side === 'pro') ? 'pro' : 'con';
            const sideClass = side === 'pro' ? 'speech-pro' : 'speech-con';
            const upvotes = speech.upvotes || 0;
            const downvotes = speech.downvotes || 0;
            const netVotes = upvotes - downvotes;

            return `
                <div class="speech-card ${sideClass}">
                    <div class="speech-header">
                        <span class="speech-type">${escapeHtml(speech.speech_type)}</span>
                        <span class="speech-side">${side.toUpperCase()}</span>
                    </div>
                    <div class="speech-content">
                        ${speech.content}
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

        return header + speechesHTML;
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

    /**
     * Load existing judgments for a debate
     * Copyright (C) 2026 Stephen F Smithers
     */
    async function loadJudgments(debateId) {
        try {
            const response = await fetch(`/api/debates/${debateId}/judgments`);
            if (!response.ok) return; // No judgments yet

            const judgments = await response.json();
            if (judgments.length > 0) {
                renderJudgments(judgments);
            }
        } catch (error) {
            console.error('Error loading judgments:', error);
        }
    }

    /**
     * Request AI judgment for a debate
     * Copyright (C) 2026 Stephen F Smithers
     */
    async function requestJudgment(debateId) {
        const button = document.querySelector('.get-judgment-btn');
        const originalText = button.textContent;

        try {
            button.textContent = '⏳ Judging...';
            button.disabled = true;

            const response = await fetch(`/api/debates/${debateId}/judge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ judge_model: 'claude-opus-4-6' })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to get judgment');
            }

            const judgment = await response.json();

            // Reload all judgments to display
            await loadJudgments(debateId);

            button.textContent = '✅ Judged!';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 2000);

        } catch (error) {
            console.error('Error requesting judgment:', error);
            alert(`Failed to get judgment: ${error.message}`);
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    /**
     * Render judgment results in the viewer
     * Copyright (C) 2026 Stephen F Smithers
     */
    function renderJudgments(judgments) {
        const container = document.getElementById('judgment-section');
        if (!container) return;

        // Get topic from data attribute to detect versus debates
        const topic = container.getAttribute('data-topic-title') || '';
        const isVersusDebate = topic.toLowerCase().includes(' vs ') || topic.toLowerCase().includes(' versus ');

        // Extract fighter/side names for versus debates
        let side1Name = 'Pro';
        let side2Name = 'Con';
        if (isVersusDebate) {
            const parts = topic.split(/\s+vs\.?\s+|\s+versus\s+/i);
            if (parts[0]) side1Name = parts[0].trim();
            if (parts[1]) side2Name = parts[1].trim().replace(/\s*\(.*?\)\s*$/, ''); // Remove "(Prime)" suffix
        }

        container.innerHTML = judgments.map(judgment => {
            let winnerLabel;
            if (judgment.winner === 'tie') {
                winnerLabel = 'Tie';
            } else if (judgment.winner === 'pro') {
                winnerLabel = side1Name;
            } else {
                winnerLabel = side2Name;
            }

            const winnerClass = judgment.winner === 'tie' ? 'tie' : judgment.winner;
            const confidence = Math.round(judgment.confidence * 100);

            // Parse criteria scores if available
            let criteriaHTML = '';
            if (judgment.criteria_scores) {
                const scores = typeof judgment.criteria_scores === 'string'
                    ? JSON.parse(judgment.criteria_scores)
                    : judgment.criteria_scores;

                criteriaHTML = `
                    <div class="criteria-scores">
                        <h4>Criteria Breakdown:</h4>
                        ${Object.entries(scores).map(([criterion, values]) => {
                            if (typeof values === 'object' && values.pro !== undefined) {
                                return `
                                    <div class="criterion-row">
                                        <span class="criterion-name">${criterion.replace(/_/g, ' ')}</span>
                                        <span class="criterion-scores">${side1Name}: ${values.pro}/10 | ${side2Name}: ${values.con}/10</span>
                                    </div>
                                `;
                            }
                            return '';
                        }).join('')}
                    </div>
                `;
            }

            return `
                <div class="judgment-card">
                    <div class="judgment-header">
                        <h3>🏆 AI Judge: ${escapeHtml(judgment.judge_model)}</h3>
                        <div class="judgment-meta">
                            <span class="judgment-winner ${winnerClass}">Winner: ${winnerLabel}</span>
                            <span class="judgment-confidence">Confidence: ${confidence}%</span>
                        </div>
                    </div>
                    <div class="judgment-reasoning">
                        <h4>Reasoning:</h4>
                        <p>${escapeHtml(judgment.reasoning)}</p>
                    </div>
                    ${criteriaHTML}
                    <div class="judgment-timestamp">
                        Judged: ${new Date(judgment.judged_at).toLocaleString()}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Export debate as markdown from the feed
     * Copyright (C) 2026 Stephen F Smithers
     */
    async function exportDebateFromFeed(sessionId, topic) {
        try {
            const response = await fetch(`/api/debate/export/${sessionId}`);
            if (!response.ok) throw new Error('Failed to export debate');

            const markdown = await response.text();

            // Create download link
            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `debate_${topic.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            console.log('Debate exported successfully');
        } catch (error) {
            console.error('Error exporting debate:', error);
            alert('Failed to export debate. Please try again.');
        }
    }

    // Make functions globally available if needed
    window.loadTopDebates = loadTopDebates;
    window.loadRecentDebates = loadRecentDebates;
    window.viewDebate = viewDebate;
    window.exportDebateFromFeed = exportDebateFromFeed;
});

// Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.
