# AI Debate Simulator - DALS-Aligned Architecture

**Date**: 2026-02-15
**Status**: ✅ IMPLEMENTED (per Brain's guidance)

## Brain's Architectural Guidance

After 7 rejected attempts to route debate content through the DALS bridge, the Brain (Claude Opus 4.6) provided clear architectural guidance:

> **"Don't send raw LLM output to Claude Opus for cleaning. Use local models for generation, Python regex for cleaning, and reserve the Brain only for judging."**

This is the correct DALS approach: **minimize API costs by keeping everything local except high-value tasks.**

---

## Current Architecture (DALS-Aligned)

| Component | Implementation | Cost |
|-----------|----------------|------|
| **Debate Content Generation** | LM Studio (GLM-Flash, Devstral) | FREE |
| **Output Cleaning** | Python regex (`_strip_thinking_blocks()`) | FREE |
| **Citation Extraction** | Python regex (`extract_citations()`) | FREE |
| **Judge/Evaluator** | *(Future feature)* Opus via bridge | Subscription credits |

### Cost per Debate
- **16 speeches**: $0.00 (100% local)
- **Judging** (optional): ~$0.10-0.20 (one Opus call at end)

---

## Model Routing

### Debate Participants (Local Models Only)

| Model | Strengths | Use For |
|-------|-----------|---------|
| **GLM-4.7-Flash 30B** | Fast, analytical | Negative (Con) arguments |
| **Devstral Small 2 24B** | Structured, precise | Affirmative (Pro) arguments |

### Future: Optional Judge (Opus via Bridge)
- Evaluates debate after completion
- Scores arguments on logic, evidence, rhetoric
- Uses subscription credits first (via DALS bridge)
- Only called once per debate (cost-efficient)

---

## Output Cleaning Pipeline

### 1. LM Studio Generates Content
```python
result = self.client.chat(model_alias, context, temp=0.3, max_tokens=2048)
# Output may contain: <think> blocks, numbered sections, meta-commentary
```

### 2. Regex Cleaner Strips Thinking Blocks
```python
cleaned = self._strip_thinking_blocks(result["content"])
# Removes:
#   - <think>...</think> tags
#   - Numbered planning sections (1. **Analyze:**, 2. **Draft:**)
#   - Meta-commentary and analysis
# Preserves:
#   - Actual debate arguments
#   - Citations [Source: ...]
```

### 3. Citation Extractor Formats Sources
```python
content, citations = extract_citations(cleaned)
# Converts: "Fact [Source: NASA]"
# To: "Fact <sup>[1]</sup>" + citation list
```

---

## Why This Architecture?

### ❌ Previous Approach (Rejected by Brain)
- Send every speech to Opus for formatting
- Cost: ~$1-2 per debate (API credits)
- Brain rejected as "not my role" - saw it as prompt injection

### ✅ Current Approach (DALS-Aligned)
- Local models generate content (free)
- Python regex cleans output (free, fast)
- Reserve Opus for high-value tasks only (judging)
- Cost: $0.00 for debates, ~$0.10-0.20 for optional judging

---

## What the Brain Rejected

The Brain identified 7 injection attempts because we were trying to make it:
1. Act as a debate participant ("You are the AFFIRMATIVE team")
2. Clean raw LLM output (low-value task, not worth API cost)

**Brain's role** (per bridge system prompt):
- Architect - Design systems
- Evaluator - Review quality (judging debates fits here)
- Strategist - Optimize routing
- Teacher - Extract patterns

**Not the Brain's role**:
- Debate participant
- Text formatter/cleaner
- Low-value batch processing

---

## Implementation Details

### Files Modified
1. **debate_manager.py** - Removed `_format_through_opus()` call, use `_strip_thinking_blocks()`
2. **models.json** - Removed Opus from debate participants, added Devstral
3. **model_client.py** - Simplified (no bridge routing for debates)

### Regex Cleaning Strategy
```python
def _strip_thinking_blocks(text: str) -> str:
    # 1. Remove <think> tags
    # 2. Find LAST numbered header (e.g., "3. **Final Output:**")
    # 3. Extract substantial paragraph (>40 chars) after last header
    # 4. Remove bullet formatting artifacts
    return cleaned_content
```

This handles GLM-Flash's consistent output pattern:
```
1. **Analyze the Request:**
   - Bullet points...

2. **Draft Argument:**
   - More bullets...

3. **Final Output:**
   [Actual debate content starts here]
```

---

## Future Enhancements

### Phase 1: Judging Feature (Uses Bridge)
```python
def judge_debate(session: DebateSession) -> dict:
    """
    Send completed debate to Opus via DALS bridge for evaluation.
    Uses subscription credits first, then API key.
    """
    summary = build_debate_summary(session)

    request = (
        "## DALS Task: Judge Debate for AI Debate Simulator\n\n"
        f"**Topic**: {session.topic}\n"
        "**Task**: Evaluate this completed policy debate and score each side.\n\n"
        f"{summary}"
    )

    # Send via bridge (uses subscription credits)
    return send_to_bridge(request)
```

**Cost**: ~$0.10-0.20 per judgment (one Opus call, ~4K tokens)

### Phase 2: Additional Local Models
- Qwen 2.5/3 Coder (analytical, structured)
- Dolphin Mistral (creative, rhetorical)
- Model-specific strengths for different speech types

---

## Testing

```bash
# Start debate app
cd /Users/ssmithers/Desktop/CODE/aidebate
python3 backend/app.py

# Browser: http://localhost:5000
# Select: GLM-Flash vs Devstral
# Run full 16-speech debate
# Cost: $0.00 (100% local)
```

---

## Lessons Learned

1. **Listen to the Brain** - When Opus rejects a task 7 times, it's giving you architectural guidance
2. **DALS principle** - Local models for bulk work, expensive models for high-value tasks only
3. **Regex > API for cleaning** - Simple pattern matching is free and fast
4. **Role boundaries matter** - The bridge Brain has a defined role; respect it

---

**Architecture approved by**: Claude Opus 4.6 (DALS Brain)
**Implementation**: Claude Sonnet 4.5 (Claude Code)
**Cost optimization**: 100% local = $0.00 per debate
