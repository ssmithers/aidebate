# DALS Bridge Integration for aidebate

**Date**: 2026-02-15
**Status**: ✅ IMPLEMENTED

## Overview

**ALL Claude Opus 4.6 requests** from the AI Debate Simulator now route through the DALS bridge (`/Users/ssmithers/Desktop/CODE/dals/bridge.py`) to use subscription credits FIRST, then API key only when subscription is exhausted.

This includes:
1. **Debate content** - When Opus is selected as a debate participant
2. **Formatting layer** - Post-processing of all model outputs

## Architecture Change

### Before
```
aidebate → Anthropic API SDK → API key credits only
```

### After
```
aidebate → passon.md → bridge.py → Anthropic API → subscription credits first
                                 ↓
                        response.md → aidebate
```

## Implementation Details

### Modified Files

**1. `backend/model_client.py`** (lines 62-149)
- Modified `_call_anthropic()` method
- Routes ALL Opus calls through DALS bridge (debate content + formatting)
- Writes requests to `/Users/ssmithers/Desktop/CODE/dals/passon.md`
- Polls `/Users/ssmithers/Desktop/CODE/dals/response.md` for responses
- 120-second timeout for debate content (longer responses)
- Returns error if bridge is not running

**2. `backend/debate_manager.py`** (lines 315-390)
- Modified `_format_through_opus()` method
- Routes formatting requests through bridge
- 60-second timeout with 2-second polling interval
- Falls back to unformatted content if bridge timeout occurs

**3. `CLAUDE.md`**
- Updated "Key Design Decisions" to document bridge routing
- Added "DALS Bridge Requirement" section with startup instructions
- Updated "Model Usage in Debates" to explain credit usage

## How It Works

### Scenario A: Opus as Debate Participant
1. **User clicks "Next Speech"** → Opus selected as debate model
2. **Debate request** → `model_client._call_anthropic()` writes to `passon.md`
3. **Bridge detection** → bridge.py detects file hash change (polls every 10s)
4. **Opus call** → bridge sends to Opus 4.6 via subscription credits
5. **Response** → bridge writes debate content to `response.md`
6. **Polling** → aidebate detects update (polls every 2s, 120s timeout)
7. **Formatting** → Same process repeats for formatting layer
8. **Display** → Clean debate content shown to user

### Scenario B: LM Studio as Debate Participant
1. **User clicks "Next Speech"** → GLM-Flash generates raw response (local, free)
2. **Formatting request** → `debate_manager._format_through_opus()` writes to `passon.md`
3. **Bridge detection** → bridge.py detects file hash change
4. **Opus call** → bridge sends to Opus 4.6 via subscription credits
5. **Response** → bridge writes formatted output to `response.md`
6. **Polling** → aidebate detects update (polls every 2s, 60s timeout)
7. **Display** → Clean formatted content shown to user

## Bridge Status

**Currently Running**: ✅ Yes (PID 81618, started Tue 2PM)

```bash
# Check if bridge is running
ps aux | grep bridge.py | grep -v grep

# View bridge logs
tail -f /Users/ssmithers/Desktop/CODE/dals/bridge_log.md
```

## Cost Optimization

### Before Bridge Integration
- Every debate speech formatting: API key credits
- 16 speeches per debate × ~1000 tokens = ~16K tokens API key usage
- Estimated cost: $1-2 per debate

### After Bridge Integration
- Uses subscription credits first (included in monthly plan)
- API key only charged when subscription exhausted
- Significantly reduces effective cost for regular use

## Testing

### Manual Test
```bash
# Terminal 1: Ensure bridge is running
cd /Users/ssmithers/Desktop/CODE/dals
ps aux | grep bridge.py

# Terminal 2: Start aidebate
cd /Users/ssmithers/Desktop/CODE/aidebate
python3 backend/app.py

# Browser: http://localhost:5000
# Start a debate, click "Next Speech"
# Watch terminal for bridge logs:
#   [Bridge] Formatting request sent for 1AC
#   [Bridge] Formatted response received from Opus (via subscription)
```

### Expected Behavior
- Each speech formatting request logged to console
- 2-10 second delay for bridge polling (normal)
- Clean, formatted output without thinking blocks
- No API key charges until subscription exhausted

### Troubleshooting

**Problem**: Timeout after 60 seconds
```
[Bridge] ⚠️  WARNING: No response after 60s
[Bridge] ⚠️  Is bridge.py running?
```

**Solution**:
```bash
# Check if bridge is running
ps aux | grep bridge.py

# If not running, start it
cd /Users/ssmithers/Desktop/CODE/dals
./start_bridge.sh
```

## Future Enhancements

- Add bridge health check before each formatting request
- Reduce polling interval from 2s to 1s for faster response
- Add bridge reconnection logic if process dies
- Log bridge usage statistics (tokens, credits used)

---

**Implementation by**: Claude Code (Opus 4.6)
**User Requirement**: Use subscription credits first for all Opus queries
