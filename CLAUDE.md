# AI Debate Simulator Project Rules

## CRITICAL: Follow DALS Workflow

This project was initially built WITHOUT following the DALS workflow (all code written directly by Claude API). **This was a mistake and must not be repeated.**

### For ALL Future Development on This Project

**MANDATORY: Use the DALS workflow documented in `/Users/ssmithers/Desktop/CODE/dals/CLAUDE.md`**

1. **Detect Model** — Query LM Studio to find currently loaded model
2. **Plan** — Claude Opus 4.6 designs the approach and creates prompts
3. **Generate** — Send prompts to LM Studio (GLM-4.7-Flash, Devstral, etc.)
4. **Review** — Claude Opus 4.6 reviews generated code
5. **Correct** — Claude Opus 4.6 fixes any bugs, style issues, or spec deviations
6. **Verify** — Test the code works correctly

**Why This Matters:**
- Cost: LM Studio is free, Claude API is expensive
- Principle: Local models should do heavy lifting, Claude API for planning/review only
- Consistency: All DALS-related projects should follow the same workflow

## Project Architecture

### Backend (Flask + Python)
- **Flask API** (`backend/app.py`) - REST endpoints for debate management
- **Debate Manager** (`backend/debate_manager.py`) - Core orchestration, policy debate flow
- **Model Client** (`backend/model_client.py`) - Unified interface for LM Studio + Anthropic API
- **Citation Processor** (`backend/citation_processor.py`) - Extract/format [Source: ...] citations
- **Models** (`backend/models.py`) - Pydantic data structures

### Frontend (Vanilla JS)
- **Main UI** (`frontend/index.html`) - Setup screen with settings, debate view
- **API Client** (`frontend/js/api.js`) - Backend communication wrapper
- **Debate UI** (`frontend/js/debate-ui.js`) - Message rendering, formatting
- **App Logic** (`frontend/js/app.js`) - Event handling, state management

### Key Design Decisions
1. **Sequential LM Studio calls** - Cannot parallelize (LM Studio limitation)
2. **Opus formatting layer** - All model responses pass through Claude Opus for consistent output
3. **Policy debate structure** - 16 speeches (configurable to 8 or 12)
4. **No framework** - Vanilla JS for simplicity and minimal dependencies

## Known Issues (Documented for Future Reference)

### Thinking Block Leakage
- Local LLMs (GLM-4.7-Flash, DeepSeek R1) leak reasoning in responses
- Solved by: `_strip_thinking_blocks()` + routing through Opus for final formatting
- See `debate_manager.py` lines 267-305 (stripping) and 345-398 (Opus formatting)

### Claude Opus API Requirements
- Conversation must END with user message (no assistant message prefill)
- Solved by: Check in `model_client.py` lines 99-105
- See commit: "Fix Claude Opus API error and over-aggressive content stripping"

### Settings Visibility
- Settings were initially hidden in modal (bad UX)
- Solved by: Moving settings to main setup screen
- See commit: "Move settings to main setup screen"

## Model Usage in Debates

The application offers two models for debating:
- **Claude Opus 4.6** - Cloud model via Anthropic API (uses monthly credits first)
- **GLM-4.7-Flash 30B** - Local model via LM Studio (free)

Both models' outputs are formatted by Claude Opus to ensure consistency.

## Testing

```bash
# Start Flask server
cd /Users/ssmithers/Desktop/CODE/aidebate
python3 backend/app.py

# Test API
curl http://localhost:5000/api/models

# Start debate
curl -X POST http://localhost:5000/api/debate/start \
  -H "Content-Type: application/json" \
  -d '{"topic":"Test topic", "model1":"claude-opus", "model2":"glm-flash", "model1_position":"2A/1N", "num_speeches":8}'
```

## Future Development Guidelines

When adding features or fixing bugs:
1. ✅ Use DALS workflow (LM Studio for code generation)
2. ✅ Test both models (Opus and GLM-Flash) in debates
3. ✅ Verify thinking blocks are stripped correctly
4. ✅ Ensure sequential LM Studio calls (no parallel requests)
5. ✅ Test all speech types (constructive, cx_question, cx_answer, rebuttal)
6. ✅ Commit frequently with clear messages
7. ✅ Update this file if you discover new patterns or issues
