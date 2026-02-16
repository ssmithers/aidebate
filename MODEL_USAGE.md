# AI Debate Simulator - Model Usage & Credit Breakdown

**Last Updated**: 2026-02-15

## Model Usage by Function

| Function | Model | Type | Credit Source | Cost per Use |
|----------|-------|------|---------------|--------------|
| **Debate Content (User's Choice)** | | | | |
| Option 1: | Claude Opus 4.6 | Anthropic API | **Subscription → API Key** | ~$0.15 per speech |
| Option 2: | GLM-4.7-Flash 30B | LM Studio (local) | FREE | $0.00 |
| Option 3: | Devstral Small 2 24B | LM Studio (local) | FREE | $0.00 |
| | | | | |
| **Output Formatting (Always)** | Claude Haiku 4.5 | Anthropic API | **Subscription → API Key** | ~$0.001 per speech |
| | | | | |
| **Planning/Architecture (Me)** | Claude Opus 4.6 | Claude Code | **Subscription → API Key** | Included in session |

---

## Credit Source Explanation

### ✅ Anthropic Subscription Credits (Used First)
- **What**: Your monthly Claude Pro/Team subscription
- **When used**: Automatically used FIRST for all Anthropic API calls
- **How**: Built into Anthropic SDK and Claude Code - no configuration needed
- **Applies to**:
  - Opus 4.6 debate content (when selected)
  - Haiku 4.5 formatting (always used)
  - Claude Code (me) for planning

### 💳 API Key Credits (Fallback)
- **What**: Pay-per-token usage from your ANTHROPIC_API_KEY
- **When used**: Only AFTER subscription credits are exhausted
- **Cost**: See pricing table below

---

## Detailed Breakdown by Component

### 1. Debate Content Generation

**User selects models in dropdown** - can choose any combination:

#### Option A: Opus 4.6 (Cloud)
- **Model**: claude-opus-4-6
- **Type**: Anthropic API call
- **Credit flow**:
  1. ✅ Uses subscription credits first
  2. 💳 Falls back to API key if subscription exhausted
- **Cost**: ~1500 tokens input + 1000 tokens output = ~$0.15 per speech
- **Total per 16-speech debate**: ~$2.40 (if using API key)

#### Option B: GLM-4.7-Flash 30B (Local)
- **Model**: zai-org/glm-4.7-flash
- **Type**: LM Studio at 192.168.1.198:5555
- **Credit flow**: None - runs on your local hardware
- **Cost**: **$0.00** (free)
- **Total per 16-speech debate**: **$0.00**

#### Option C: Devstral Small 2 24B (Local)
- **Model**: devstral-small-2-24b-instruct-2512
- **Type**: LM Studio at 192.168.1.198:5555
- **Credit flow**: None - runs on your local hardware
- **Cost**: **$0.00** (free)
- **Total per 16-speech debate**: **$0.00**

---

### 2. Output Formatting (Always Haiku)

**Applies to ALL debate content** - cleans thinking blocks, formats output

- **Model**: claude-haiku-4-5
- **Type**: Anthropic API call (direct)
- **Credit flow**:
  1. ✅ Uses subscription credits first
  2. 💳 Falls back to API key if subscription exhausted
- **Cost**: ~800 tokens input + 200 tokens output = ~$0.001 per speech
- **Why Haiku**: 60x cheaper than Opus, perfect for simple cleaning tasks
- **Total per 16-speech debate**: ~$0.016 (if using API key)

---

### 3. Planning & Architecture (Claude Code - Me)

- **Model**: Claude Opus 4.6 (sonnet-4-5 in this session)
- **Type**: Claude Code session
- **Credit flow**:
  1. ✅ Uses subscription credits first
  2. 💳 Falls back to API key if subscription exhausted
- **Cost**: Included in your Claude Code session
- **Notes**: This is me (the assistant) - not part of the debate app

---

## Cost Examples

### Scenario 1: Local Models Only (Cheapest)
```
Debate: GLM-Flash vs Devstral (16 speeches)
  - Content generation: $0.00 (local)
  - Formatting (Haiku): $0.016 (subscription)

Total: ~$0.02 if subscription exhausted, $0.00 if using subscription
```

### Scenario 2: Opus vs Local (Mixed)
```
Debate: Opus vs GLM-Flash (16 speeches, 8 each)
  - Opus content: 8 × $0.15 = $1.20 (subscription → API key)
  - GLM content: 8 × $0.00 = $0.00 (local)
  - Formatting (Haiku): $0.016 (subscription → API key)

Total: ~$1.22 if API key, much less if using subscription
```

### Scenario 3: Opus vs Opus (Most Expensive)
```
Debate: Opus vs Opus (16 speeches)
  - Opus content: 16 × $0.15 = $2.40 (subscription → API key)
  - Formatting (Haiku): $0.016 (subscription → API key)

Total: ~$2.42 if API key, significantly less if using subscription
```

---

## Anthropic Pricing (API Key Rates)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| **Opus 4.6** | $15.00 | $75.00 |
| **Sonnet 4.5** | $3.00 | $15.00 |
| **Haiku 4.5** | $0.25 | $1.25 |

**Subscription credits**: Included in monthly plan, exhausted first for ALL API calls

---

## How Subscription Credits Work

### Automatic Priority
1. You make an API call to Anthropic (Opus, Sonnet, or Haiku)
2. Anthropic SDK checks if you have subscription credits
3. **If yes**: Deducts from subscription (no API key charge)
4. **If no**: Falls back to API key (pay-per-token)

### No Configuration Needed
- This behavior is **automatic** in the Anthropic SDK
- Claude Code uses this same system
- You don't need to do anything - it just works

### When Subscription Exhausted
- API calls automatically switch to API key billing
- You'll see charges on your Anthropic account
- Refills on your next billing cycle

---

## Recommendations

### For Cost Optimization
1. **Use local models for debates** (GLM-Flash, Devstral)
   - Zero cost, decent quality
   - Haiku formatting is cheap enough (~$0.02 per debate)

2. **Reserve Opus for important debates**
   - Special topics where quality matters most
   - Mix with local model (e.g., Opus vs GLM-Flash)

3. **Monitor subscription usage**
   - Check Anthropic dashboard for credit balance
   - Switch to local-only when running low

### For Quality
1. **Opus vs Opus debates** - Highest quality arguments
2. **Opus vs Local** - Good balance of quality and cost
3. **Local vs Local** - Free but may need more cleaning

---

## LM Studio Model Detection

Before each session, run model detection:

```bash
cd /Users/ssmithers/Desktop/CODE/aidebate
python3 backend/lm_studio_detector.py
```

This will:
- Query LM Studio at 192.168.1.198:5555
- Detect currently loaded model
- Add to models.json if new
- Display in dropdown for user selection

**Current loaded model**: GLM-4.7-Flash 30B

---

## Summary

**Key Points**:
- ✅ ALL Anthropic API calls use **subscription credits first**
- 💳 API key only charged when subscription exhausted
- 🆓 Local LM Studio models are completely free
- 🎯 Haiku formatting costs ~$0.001 per speech (negligible)
- 💰 Total cost depends on model selection - can be $0.00 or ~$2.40 per debate

**Best practices**:
- Use local models when quality is "good enough"
- Save Opus for high-stakes debates
- Haiku formatting is cheap enough to always use
- Monitor subscription credit balance

---

**Implementation Status**: ✅ Complete
**Subscription priority**: ✅ Automatic (built into Anthropic SDK)
**No bridge needed**: ✅ Direct API calls handle subscription priority
