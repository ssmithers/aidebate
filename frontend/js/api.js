/**
 * API wrapper for debate backend
 */
const API = {
    baseURL: 'http://localhost:5000/api',

    async getModels() {
        const response = await fetch(`${this.baseURL}/models`);
        if (!response.ok) {
            throw new Error(`Failed to fetch models: ${response.statusText}`);
        }
        return response.json();
    },

    async startDebate(topic, model1, model2, proModel) {
        const response = await fetch(`${this.baseURL}/debate/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic,
                model1,
                model2,
                pro_model: proModel
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start debate');
        }

        return response.json();
    },

    async nextTurn(sessionId, moderatorMessage = null) {
        const response = await fetch(`${this.baseURL}/debate/turn`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                moderator_message: moderatorMessage
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to execute turn');
        }

        return response.json();
    },

    async endTopic(sessionId) {
        const response = await fetch(`${this.baseURL}/debate/end-topic`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to end topic');
        }

        return response.json();
    },

    async getHistory(sessionId) {
        const response = await fetch(`${this.baseURL}/debate/history/${sessionId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to get history');
        }

        return response.json();
    }
};
