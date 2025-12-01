# 🎥 Nirava Video Script (2-3 Minutes)

## 📝 Script Outline

### INTRO (0:00-0:20) - Problem Statement
**[Show yourself on camera]**

> "Hi, I'm Mayur Kotian. Every day, millions of people Google 'why am I so tired?' or 'I can't focus.' What they get is either generic advice like 'drink more water' or alarming WebMD results that cause anxiety, not answers.
>
> 76% of adults experience stress symptoms, but personalized health guidance costs $10-30/month, excluding low-income populations. Medical appointments take weeks for non-urgent concerns.
>
> I built Nirava to solve this problem."

---

### WHY AGENTS? (0:20-0:40)
**[Show architecture diagram from README]**

> "Why agents? Because health advice needs specialists, not a one-size-fits-all chatbot.
>
> Nirava uses a 6-agent system that mimics a medical team:
> - IntakeAgent: Asks only relevant questions based on your symptoms
> - MetricsAgent: Calculates 30+ health scores (BMI, sleep quality, burnout risk)
> - ResearchAgent: Grounds advice in real medical sources using Google Search
> - PlannerAgent: Generates tiny, achievable actions matched to your energy level
> - NutritionAgent: Creates culturally-aware meal plans (supports 6 dietary laws)
> - CoachAgent: Synthesizes everything into an empathetic response
>
> Each agent is an expert. Together, they provide medical-grade guidance."

---

### DEMO (0:40-1:30)
**[Screen recording: `python adk_main.py`]**

**Show this interaction:**
```
You: I can't focus at work, my brain feels foggy

Nirava: I'm sorry to hear that. Let me ask a few quick questions...
        How many hours did you sleep last night?

You: About 5 hours

Nirava: Got it. What's your stress level? (1=calm, 10=overwhelmed)

You: 8 out of 10

Nirava: Okay. How many glasses of water have you had today?

You: Maybe 3

[Continue through mood, energy, exercise]

Nirava: [Shows final response with:
- 6-Pillar Dashboard
- Key Insight: "Sleep deprivation + high stress = impaired prefrontal cortex"
- 3 Micro-Actions: "Set phone to DND at 9pm", "Drink water now", "5-min walk"
- Citations from NIH, Mayo Clinic]
```

**Narration during demo:**
> "Watch how Nirava works. I tell it I can't focus. It classifies this as mental fatigue and asks only relevant questions—sleep, stress, water—not my BMI.
>
> After collecting data, it runs the analysis pipeline. The MetricsAgent calculates my sleep quality is 4/10. The ResearchAgent grounds the advice in real medical sources. The PlannerAgent generates 3 tiny actions I can do right now, matched to my low energy.
>
> Notice the citations—every claim is backed by trusted sources like NIH and Mayo Clinic."

---

### ARCHITECTURE (1:30-1:50)
**[Show architecture diagram again]**

> "The architecture is a hybrid workflow:
> - Phase 1: Conversational loop—IntakeAgent iterates until it has enough data
> - Phase 2: Sequential pipeline—each agent enriches the context
>
> Key features:
> - Google Search Grounding for medical accuracy
> - Session management with checkpoint/resume
> - Context compaction for long conversations
> - Full observability with tracing and metrics
> - Cultural sensitivity—supports Hindu, Jain, Halal, Kosher diets"

---

### THE BUILD (1:50-2:20)
**[Show code briefly or just talk]**

> "I built this using:
> - Gemini 2.0 Flash for all LLM agents
> - Google ADK for agent orchestration
> - Python with clean multi-agent architecture
> - 30+ deterministic health calculations
> - Iterative research loop with ML-based quality scoring
>
> The code demonstrates all 13 key concepts from the Google AI Intensive Course:
> Multi-agent systems, loop agents, sequential agents, custom tools, Google Search grounding, session management, context compaction, observability, and more.
>
> It's production-ready with comprehensive error handling, logging, and fallbacks."

---

### SOCIAL IMPACT (2:20-2:40)
**[Show yourself on camera]**

> "This is 'Agents for Good' in action. Nirava democratizes health guidance:
> - Zero cost—no subscription, no paywall
> - Culturally inclusive—supports 6 dietary laws, not just Western diets
> - Medical rigor—30+ validated calculations, not generic advice
> - Safety first—automatic handoff for urgent symptoms
>
> If deployed at scale, Nirava could reduce ER visits for non-urgent concerns, improve health literacy in underserved communities, and prevent burnout by catching early warning signs."

---

### CLOSING (2:40-3:00)
**[Show yourself on camera]**

> "Nirava is an AI health companion that reasons like a doctor, educates like a teacher, and cares like a friend. It's open-source, production-ready, and designed to make health guidance accessible to everyone.
>
> Thank you for watching. Check out the code on GitHub: github.com/Mayurkotian/Nirava"

---

## 🎬 Recording Tips

1. **Use QuickTime Screen Recording** (Mac):
   - Open QuickTime Player → File → New Screen Recording
   - Record terminal session showing `python adk_main.py`

2. **Use Loom or OBS Studio** for picture-in-picture:
   - Show yourself in corner while screen recording

3. **Keep it under 3 minutes** (judges prefer concise)

4. **Upload to YouTube**:
   - Title: "Nirava: AI Health Companion - Google AI Agents Capstone 2025"
   - Description: Link to GitHub repo
   - Visibility: Unlisted (so only judges with link can view)

5. **Add captions** (YouTube auto-generates, just review for accuracy)

---

## 📊 What to Show in Demo

**Terminal Output to Capture:**
```
=== Nirava Health Companion (ADK Edition) ===
[ADK] Agent 'NiravaHealthAgent' initialized with model 'gemini-2.0-flash-lite'

Type 'exit' to quit.

Nirava: Hey! I'm Nirava. 👋
[Show greeting with 3 journey options]

You: I can't focus at work, my brain feels foggy
[Show IntakeAgent asking questions]

You: About 5 hours
[Show data collection]

[Show final response with:
- 6-Pillar Dashboard
- Insights with citations
- Micro-actions
- Meal plan (if Build Plan chosen)]
```

---

## ⏰ Time Breakdown

| Section | Time | Content |
|---------|------|---------|
| Intro | 0:00-0:20 | Problem statement |
| Why Agents | 0:20-0:40 | Architecture overview |
| Demo | 0:40-1:30 | Live terminal interaction |
| Architecture | 1:30-1:50 | Diagram walkthrough |
| The Build | 1:50-2:20 | Tech stack & concepts |
| Social Impact | 2:20-2:40 | Agents for Good |
| Closing | 2:40-3:00 | Call to action |

**Total: 3 minutes**

---

## 🎯 Key Messages to Hit

1. **Problem**: Health guidance is either too generic or too expensive
2. **Solution**: Multi-agent system that mimics a medical team
3. **Innovation**: Google Search grounding + cultural sensitivity
4. **Impact**: Democratizes health guidance for underserved populations
5. **Quality**: Production-ready with 13 key concepts demonstrated

---

Good luck! 🚀
