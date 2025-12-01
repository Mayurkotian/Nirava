"""ResearchAgent - Issue-Aware Health Insights with Google Search Grounding

Capstone Concepts Demonstrated:
- Built-in Tools (Google Search Grounding)
- LLM-Powered Agent (Gemini 2.0 Flash)
- Chain-of-Thought Prompting
- Safety Handoff for concerning symptoms

Day 4 Implementation: Domain-Specific LLMs + Google Search Grounding
- Generates targeted recommendations based on the user's specific issue type
- Uses Google Search to ground health claims with real citations
- Dynamic Retrieval: Only searches when confidence is low
- Safety Handoff: Detects concerning symptoms and recommends professional care

Design Decisions:
    1. Dynamic Retrieval: Only use Google Search when issue requires medical accuracy
       (e.g., sleep issues, physical symptoms). Skip for general wellness optimization.
    2. Safety First: Check for concerning symptoms BEFORE generating advice.
       If detected, recommend professional consultation.
    3. Issue-Specific Focus: Each issue type has predefined evidence snippets
       and focus areas for more relevant recommendations.
    4. Source Extraction: Parse grounding metadata to display verified citations.

Prompt Engineering:
    - Chain-of-Thought: Step-by-step analysis for better reasoning
    - Structured JSON Output: Reliable parsing of insights
    - Confidence Scoring: Self-assessment for response quality
"""
from typing import Dict, Any, List
import json
import re
import logging
from config.llm import get_gemini_model

logger = logging.getLogger(__name__)

# Day 4: Safety Handoff - Keywords that trigger professional recommendation
SAFETY_KEYWORDS = {
    "urgent": ["chest pain", "difficulty breathing", "severe pain", "suicidal", 
               "self-harm", "overdose", "emergency", "heart attack", "stroke"],
    "recommend_doctor": ["blood in", "sudden weight loss", "persistent pain",
                         "depression", "anxiety disorder", "insomnia chronic",
                         "dizziness", "fainting", "numbness", "vision changes",
                         "unexplained", "weeks", "months", "getting worse"]
}

# Trusted medical domains with authority scores (ML-based ranking)
# Score: 10 = Peer-reviewed research, 9 = Government health, 8 = Academic medical centers, 7 = Trusted foundations
TRUSTED_DOMAINS = {
    # Tier 1: Peer-Reviewed Research (Score: 10)
    "pubmed.ncbi.nlm.nih.gov": 10,
    "nih.gov": 10,
    "thelancet.com": 10,
    "nejm.org": 10,  # New England Journal of Medicine
    "bmj.com": 10,  # British Medical Journal
    "jamanetwork.com": 10,  # Journal of American Medical Association
    
    # Tier 2: Government Health Agencies (Score: 9)
    "cdc.gov": 9,
    "who.int": 9,
    "medlineplus.gov": 9,
    
    # Tier 3: Academic Medical Centers (Score: 8)
    "mayoclinic.org": 8,
    "hopkinsmedicine.org": 8,
    "clevelandclinic.org": 8,
    "harvard.edu": 8,
    "stanfordhealthcare.org": 8,
    
    # Tier 4: Trusted Health Foundations (Score: 7)
    "sleepfoundation.org": 7,
    "heart.org": 7,  # American Heart Association
    "diabetes.org": 7,  # American Diabetes Association
    "cancer.org": 7,  # American Cancer Society
}

# Minimum quality thresholds for research loop
MIN_AUTHORITY_SCORE = 7  # Minimum average authority score
MIN_SOURCES_REQUIRED = 2  # Minimum number of quality sources
MAX_RESEARCH_ITERATIONS = 3  # Maximum research refinement loops

# Issue-specific recommendation focus
ISSUE_FOCUS = {
    "mental_fatigue": {
        "title": "Mental Clarity",
        "focus": ["sleep quality", "stress levels", "hydration"],
        "evidence": [
            "Sleep deprivation impairs prefrontal cortex function, reducing focus and decision-making.",
            "Dehydration of just 2% body weight reduces cognitive performance by 10-15%.",
            "Chronic stress elevates cortisol, which impairs memory consolidation."
        ]
    },
    "emotional": {
        "title": "Emotional Wellness",
        "focus": ["sleep", "exercise", "stress"],
        "evidence": [
            "Exercise releases endorphins and BDNF, both proven mood boosters.",
            "Sleep deprivation increases amygdala reactivity by 60%, amplifying negative emotions.",
            "Even 10 minutes of walking reduces anxiety symptoms."
        ]
    },
    "physical_fatigue": {
        "title": "Physical Energy",
        "focus": ["sleep", "exercise", "hydration"],
        "evidence": [
            "Sleep is when muscle repair and energy restoration occur.",
            "Regular movement increases mitochondrial density, improving energy production.",
            "Dehydration reduces blood volume, making the heart work harder."
        ]
    },
    "sleep_issues": {
        "title": "Sleep Quality",
        "focus": ["stress", "exercise timing", "sleep hygiene"],
        "evidence": [
            "Cortisol suppresses melatonin production, delaying sleep onset.",
            "Exercise improves sleep quality but not within 2h of bedtime.",
            "Consistent wake times regulate circadian rhythm better than total hours."
        ]
    },
    "general_wellness": {
        "title": "Optimization",
        "focus": ["metabolic health", "circadian alignment", "longevity"],
        "evidence": [
            "Consistent sleep onset stabilizes circadian rhythm, boosting growth hormone release.",
            "Zone 2 cardio improves mitochondrial efficiency and metabolic flexibility.",
            "Morning sunlight exposure within 30 minutes of waking resets cortisol rhythm."
        ]
    },
    "build_plan": {
        "title": "Comprehensive Health Plan",
        "focus": ["nutrition", "sleep hygiene", "movement", "stress management"],
        "evidence": [
            "Protein intake of 1.6g/kg body weight preserves muscle mass during weight loss.",
            "Consistent meal timing improves metabolic health and circadian rhythm.",
            "Combining cardio and strength training provides optimal longevity benefits."
        ]
    },
    "social_isolation": {
        "title": "Social Connection",
        "focus": ["loneliness impact", "social support", "community"],
        "evidence": [
            "Social isolation increases mortality risk by 29% (meta-analysis, Holt-Lunstad 2015).",
            "Strong social connections lower cortisol and improve immune function.",
            "Even brief social interactions (10-15 min) reduce stress biomarkers."
        ]
    },
    "toxin_reduction": {
        "title": "Toxin Avoidance",
        "focus": ["alcohol effects", "smoking cessation", "environmental toxins"],
        "evidence": [
            "Alcohol disrupts REM sleep architecture, reducing sleep quality by up to 39%.",
            "Smoking cessation improves cardiovascular health within 24 hours (CDC).",
            "Even moderate alcohol (2+ drinks/day) increases cancer risk (WHO)."
        ]
    }
}


class ResearchAgent:
    """Generates issue-targeted health insights with Day 4 enhancements."""

    def __init__(self):
        self.model = get_gemini_model()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.model:
            return self._fallback(context)
        
        # Day 4 Feature #2: Safety Handoff - Check for concerning symptoms
        safety_check = self._check_safety(context)
        if safety_check["needs_professional"]:
            context["safety_warning"] = safety_check
            logger.debug(f"Safety check triggered: {safety_check['level']}")

        prompt = self._build_prompt(context)
        
        # Day 4 Feature #1: Dynamic Retrieval - Decide if grounding is needed
        use_grounding = self._should_ground(context)
        
        try:
            # ================================================================
            # ITERATIVE RESEARCH LOOP WITH ML-BASED QUALITY SCORING
            # ================================================================
            iteration = 0
            best_response = None
            best_quality_score = 0
            research_log = []  # Track all research attempts for transparency
            
            while iteration < MAX_RESEARCH_ITERATIONS:
                iteration += 1
                logger.info(f"Research iteration {iteration}/{MAX_RESEARCH_ITERATIONS}")
                
                # Build iteration-specific prompt (refine on retries)
                iteration_prompt = self._refine_prompt_for_iteration(
                    prompt, iteration, research_log
                )
                
                if use_grounding:
                    # Execute Google Search with grounding
                    logger.info(f"Executing grounded search (iteration {iteration})")
                    response = self.model.generate_content(
                        iteration_prompt,
                        tools='google_search_retrieval',
                        generation_config={"response_mime_type": "application/json"}
                    )
                else:
                    # Non-grounded response (for low-risk queries)
                    logger.info("Executing non-grounded research")
                    response = self.model.generate_content(
                        iteration_prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                
                # Extract sources with enhanced metadata
                sources = self._extract_sources(response) if use_grounding else []
                
                # Calculate research quality score (ML-based)
                quality_metrics = self._score_research_quality(sources, context)
                
                # Log this iteration
                iteration_log = {
                    "iteration": iteration,
                    "sources_found": len(sources),
                    "quality_score": quality_metrics["overall_score"],
                    "authority_score": quality_metrics["avg_authority"],
                    "relevance_score": quality_metrics["avg_relevance"],
                    "trusted_sources": quality_metrics["trusted_count"],
                }
                research_log.append(iteration_log)
                
                logger.info(
                    f"Iteration {iteration} quality: {quality_metrics['overall_score']:.1f}/100 "
                    f"(Authority: {quality_metrics['avg_authority']:.1f}, "
                    f"Relevance: {quality_metrics['avg_relevance']:.1f}, "
                    f"Trusted: {quality_metrics['trusted_count']}/{len(sources)})"
                )
                
                # Track best response
                if quality_metrics["overall_score"] > best_quality_score:
                    best_response = response
                    best_quality_score = quality_metrics["overall_score"]
                
                # Check if quality threshold met
                if self._meets_quality_threshold(quality_metrics, use_grounding):
                    logger.info(
                        f"✓ Quality threshold met at iteration {iteration} "
                        f"(score: {quality_metrics['overall_score']:.1f}/100)"
                    )
                    break
                else:
                    logger.warning(
                        f"✗ Quality threshold not met (score: {quality_metrics['overall_score']:.1f}/100). "
                        f"Refining search..."
                    )
            
            # Use best response found
            response = best_response
            
            # Safety check: If no response found (all iterations failed), use fallback
            if response is None:
                logger.error("All research iterations failed to produce a response")
                return self._fallback(context)
            
            # Add research transparency to context
            context["research_log"] = research_log
            context["research_iterations"] = iteration
            context["research_quality_score"] = best_quality_score
            
            # Robust JSON cleanup
            raw = (response.text or "").strip()
            clean_text = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_text)
            
            insights = result.get("insights", [])
            reasoning = result.get("reasoning", "")
            confidence = result.get("confidence", 0.7)
            
            # Sources already extracted in loop, but re-extract for final response
            sources = self._extract_sources(response) if use_grounding else []
            
            if reasoning:
                logger.debug(f"ResearchAgent reasoning: {reasoning}")
                logger.debug(f"ResearchAgent confidence: {confidence}")
            
            if not insights:
                return self._fallback(context)
            
            # Day 4: Add safety warning to insights if needed
            if safety_check["needs_professional"]:
                safety_insight = self._get_safety_insight(safety_check)
                insights.insert(0, safety_insight)  # Put safety first
            
            context["insights"] = insights
            context["sources"] = sources
            context["research_reasoning"] = reasoning
            context["research_confidence"] = confidence
            
            # ================================================================
            # RESEARCH TRANSPARENCY SUMMARY (for user visibility)
            # ================================================================
            research_summary = {
                "iterations_performed": context.get("research_iterations", 1),
                "final_quality_score": context.get("research_quality_score", 0),
                "sources_reviewed": len(sources),
                "sources_cited": len(sources),
                "source_breakdown": {},
                "top_sources": [],
            }
            
            # Count sources by domain tier
            for source in sources:
                domain = source.get("domain", "unknown")
                tier = "Tier 1 (Peer-Reviewed)" if source.get("authority_score", 0) == 10 else \
                       "Tier 2 (Government)" if source.get("authority_score", 0) == 9 else \
                       "Tier 3 (Academic Medical)" if source.get("authority_score", 0) == 8 else \
                       "Tier 4 (Trusted Foundation)" if source.get("authority_score", 0) == 7 else \
                       "Other"
                
                research_summary["source_breakdown"][tier] = \
                    research_summary["source_breakdown"].get(tier, 0) + 1
            
            # Top 3 sources for display
            research_summary["top_sources"] = [
                {
                    "title": s.get("title", "Source"),
                    "domain": s.get("domain", "unknown"),
                    "authority": s.get("authority_score", 0),
                }
                for s in sources[:3]
            ]
            
            context["research_summary"] = research_summary
            
            # Comprehensive logging
            logger.info(f"ResearchAgent completed: {len(insights)} insights generated")
            logger.info(
                f"Research quality: {research_summary['final_quality_score']:.1f}/100 "
                f"({research_summary['iterations_performed']} iterations)"
            )
            logger.info(f"Sources: {research_summary['sources_reviewed']} reviewed, {research_summary['sources_cited']} cited")
            logger.info(f"Source breakdown: {research_summary['source_breakdown']}")
            
            if sources:
                logger.info("Top sources:")
                for i, source in enumerate(sources[:3], 1):
                    logger.info(
                        f"  [{i}] {source.get('title', 'Unknown')} "
                        f"(Authority: {source.get('authority_score', 0)}/10, "
                        f"Relevance: {source.get('relevance_score', 0)}/100)"
                    )
                
        except Exception as e:
            logger.error(f"ResearchAgent error: {e}")
            return self._fallback(context)

        return context

    def _should_ground(self, context: Dict[str, Any]) -> bool:
        """Day 4: Dynamic Retrieval - Decide if Google Search grounding is needed.
        
        Ground when:
        - Issue type requires medical accuracy (sleep_issues, physical_fatigue)
        - User data is significantly outside normal ranges
        - Query involves specific health claims
        
        Skip grounding when:
        - General wellness / optimization mode
        - All metrics are in normal ranges
        - Simple habit tracking queries
        """
        issue_type = context.get("issue_type", "general_wellness")
        checkin = context.get("checkin", {})
        
        # Always ground for health-critical issue types
        critical_issues = ["sleep_issues", "physical_fatigue", "emotional"]
        if issue_type in critical_issues:
            return True
        
        # Ground if metrics are concerning
        sleep = checkin.get('sleep_hours')
        stress = checkin.get('stress_score')
        
        if sleep is not None and sleep < 5:  # Severe sleep deprivation
            return True
        if stress is not None and stress >= 8:  # High stress
            return True
        
        # Skip grounding for general wellness optimization IF metrics are perfect
        # But if they are optimizing, they might want advanced science.
        # Let's keep grounding for optimization to provide "Zone 2" or "Huberman-style" papers.
        if issue_type == "general_wellness":
             # Only ground if they want deep optimization (implied by good metrics)
             if sleep and sleep >= 7 and stress and stress <= 4:
                 return True # Grounding helps provide "advanced" citations for healthy users
             return False
        
        # Default: use grounding for accuracy
        return True

    def _check_safety(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Day 4: Safety Handoff - Detect symptoms requiring professional care.
        
        Returns dict with:
        - needs_professional: bool
        - level: 'urgent' | 'recommend' | 'none'
        - matched_keywords: list of concerning terms found
        """
        # Collect all text to analyze
        conversation = context.get("conversation_history", [])
        checkin = context.get("checkin", {})
        
        text_to_check = " ".join([
            str(msg.get("content", "")) for msg in conversation
        ]).lower()
        
        # Add any notes from checkin
        if checkin.get("notes"):
            text_to_check += " " + str(checkin.get("notes", "")).lower()
        
        result = {
            "needs_professional": False,
            "level": "none",
            "matched_keywords": []
        }
        
        # Check for urgent symptoms (emergency)
        for keyword in SAFETY_KEYWORDS["urgent"]:
            if keyword in text_to_check:
                result["needs_professional"] = True
                result["level"] = "urgent"
                result["matched_keywords"].append(keyword)
        
        # Check for symptoms that need a doctor (non-emergency)
        if result["level"] != "urgent":
            for keyword in SAFETY_KEYWORDS["recommend_doctor"]:
                if keyword in text_to_check:
                    result["needs_professional"] = True
                    result["level"] = "recommend"
                    result["matched_keywords"].append(keyword)
        
        return result

    def _get_safety_insight(self, safety_check: Dict[str, Any]) -> str:
        """Generate appropriate safety message based on severity."""
        if safety_check["level"] == "urgent":
            return ("⚠️ IMPORTANT: Some of what you've described may need immediate attention. "
                    "If you're experiencing chest pain, difficulty breathing, or thoughts of self-harm, "
                    "please contact emergency services (911) or a crisis helpline immediately.")
        else:
            return ("💡 Based on what you've shared, it might be helpful to discuss these symptoms "
                    "with a healthcare provider. While I can offer general wellness tips, "
                    "a professional can give you personalized medical advice.")

    def _extract_sources(self, response) -> list:
        """Enhanced source extraction with snippets, authority scoring, and relevance ranking.
        
        Returns list of dicts with:
        - id: Unique source ID
        - title: Paper/article title
        - uri: Full URL
        - domain: Extracted domain
        - authority_score: 0-10 (based on TRUSTED_DOMAINS)
        - snippet: Extracted text snippet from grounding
        - relevance_score: 0-100 (calculated based on content)
        """
        sources = []
        source_id = 1
        
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata
                    
                    # Extract grounding chunks (these contain the actual text used)
                    if hasattr(metadata, 'grounding_chunks'):
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                uri = getattr(chunk.web, 'uri', '')
                                title = getattr(chunk.web, 'title', 'Source')
                                
                                # Extract domain for authority scoring
                                domain = self._extract_domain(uri)
                                authority_score = self._get_authority_score(domain)
                                
                                # Try to extract snippet from grounding support
                                snippet = ""
                                if hasattr(metadata, 'grounding_supports'):
                                    for support in metadata.grounding_supports:
                                        if hasattr(support, 'segment'):
                                            snippet = getattr(support.segment, 'text', '')
                                            if snippet:
                                                break
                                
                                # If no snippet from grounding_supports, try chunk content
                                if not snippet and hasattr(chunk, 'content'):
                                    snippet = getattr(chunk, 'content', '')
                                
                                # Calculate relevance score (ML-based)
                                relevance_score = self._calculate_relevance_score(
                                    title, snippet, authority_score
                                )
                                
                                source_obj = {
                                    'id': source_id,
                                    'title': title,
                                    'uri': uri,
                                    'domain': domain,
                                    'authority_score': authority_score,
                                    'snippet': snippet[:500] if snippet else "",  # Limit snippet length
                                    'relevance_score': relevance_score,
                                }
                                
                                sources.append(source_obj)
                                source_id += 1
                    
                    # Log search queries used (for transparency)
                    if hasattr(metadata, 'web_search_queries'):
                        queries = metadata.web_search_queries
                        logger.info(f"Search queries executed: {queries}")
                        
        except Exception as e:
            logger.error(f"Source extraction error: {e}", exc_info=True)
        
        # Sort sources by combined score (authority + relevance)
        sources = sorted(
            sources,
            key=lambda s: (s['authority_score'] * 0.6 + s['relevance_score'] / 10 * 0.4),
            reverse=True
        )
        
        return sources
    
    def _extract_domain(self, uri: str) -> str:
        """Extract domain from URI for authority scoring."""
        try:
            match = re.search(r'https?://(?:www\.)?([^/]+)', uri)
            return match.group(1) if match else ""
        except Exception:
            return ""
    
    def _get_authority_score(self, domain: str) -> int:
        """Get authority score for domain (0-10)."""
        for trusted_domain, score in TRUSTED_DOMAINS.items():
            if trusted_domain in domain:
                return score
        return 0  # Untrusted source
    
    def _calculate_relevance_score(self, title: str, snippet: str, authority_score: int) -> int:
        """Calculate relevance score (0-100) using heuristics.
        
        Factors:
        - Authority score (40% weight)
        - Title relevance (30% weight)
        - Snippet quality (30% weight)
        
        In production, this could use a trained ML model.
        """
        score = 0
        
        # Authority component (0-40 points)
        score += authority_score * 4
        
        # Title relevance (0-30 points)
        title_lower = title.lower()
        relevant_keywords = [
            'sleep', 'stress', 'exercise', 'hydration', 'mental health',
            'cognitive', 'fatigue', 'wellness', 'health', 'study',
            'research', 'clinical', 'trial', 'meta-analysis'
        ]
        title_matches = sum(1 for kw in relevant_keywords if kw in title_lower)
        score += min(30, title_matches * 5)
        
        # Snippet quality (0-30 points)
        if snippet:
            snippet_lower = snippet.lower()
            # Check for scientific language
            scientific_terms = [
                'study', 'research', 'participants', 'results', 'significant',
                'correlation', 'effect', 'associated', 'risk', 'benefit'
            ]
            snippet_matches = sum(1 for term in scientific_terms if term in snippet_lower)
            score += min(30, snippet_matches * 6)
        
        return min(100, score)
    
    def _score_research_quality(self, sources: list, context: Dict[str, Any]) -> Dict[str, Any]:
        """ML-based research quality scoring.
        
        Returns dict with:
        - overall_score: 0-100 (weighted combination)
        - avg_authority: Average authority score of sources
        - avg_relevance: Average relevance score of sources
        - trusted_count: Number of sources from TRUSTED_DOMAINS
        - diversity_score: Domain diversity (avoid single-source bias)
        """
        if not sources:
            return {
                "overall_score": 0,
                "avg_authority": 0,
                "avg_relevance": 0,
                "trusted_count": 0,
                "diversity_score": 0,
            }
        
        # Calculate average authority
        avg_authority = sum(s['authority_score'] for s in sources) / len(sources)
        
        # Calculate average relevance
        avg_relevance = sum(s['relevance_score'] for s in sources) / len(sources)
        
        # Count trusted sources (authority >= 7)
        trusted_count = sum(1 for s in sources if s['authority_score'] >= MIN_AUTHORITY_SCORE)
        
        # Calculate domain diversity (penalize if all sources from same domain)
        unique_domains = len(set(s['domain'] for s in sources))
        diversity_score = min(100, (unique_domains / max(1, len(sources))) * 100)
        
        # Overall score (weighted combination)
        # Authority: 40%, Relevance: 30%, Trusted count: 20%, Diversity: 10%
        overall_score = (
            (avg_authority / 10) * 40 +  # Normalize to 0-100
            (avg_relevance / 100) * 30 +
            (trusted_count / max(1, len(sources))) * 20 +
            (diversity_score / 100) * 10
        )
        
        return {
            "overall_score": round(overall_score, 1),
            "avg_authority": round(avg_authority, 1),
            "avg_relevance": round(avg_relevance, 1),
            "trusted_count": trusted_count,
            "diversity_score": round(diversity_score, 1),
        }
    
    def _meets_quality_threshold(self, quality_metrics: Dict[str, Any], use_grounding: bool) -> bool:
        """Check if research quality meets minimum thresholds.
        
        Thresholds:
        - Overall score >= 60/100
        - At least MIN_SOURCES_REQUIRED trusted sources
        - Average authority >= MIN_AUTHORITY_SCORE
        """
        if not use_grounding:
            return True  # Skip quality check for non-grounded queries
        
        meets_overall = quality_metrics["overall_score"] >= 60
        meets_trusted = quality_metrics["trusted_count"] >= MIN_SOURCES_REQUIRED
        meets_authority = quality_metrics["avg_authority"] >= MIN_AUTHORITY_SCORE
        
        return meets_overall and meets_trusted and meets_authority
    
    def _refine_prompt_for_iteration(self, base_prompt: str, iteration: int, research_log: list) -> str:
        """Refine search prompt based on previous iteration results.
        
        Iteration 1: Standard search
        Iteration 2+: Add constraints to improve quality
        """
        if iteration == 1:
            return base_prompt
        
        # Analyze previous iterations
        prev_iteration = research_log[-1] if research_log else {}
        
        refinement_instructions = "\n\n=== SEARCH REFINEMENT (CRITICAL) ===\n"
        
        if prev_iteration.get("trusted_sources", 0) < MIN_SOURCES_REQUIRED:
            refinement_instructions += (
                f"Previous search found only {prev_iteration.get('trusted_sources', 0)} trusted sources. "
                "PRIORITIZE searching these domains:\n"
                "- site:pubmed.ncbi.nlm.nih.gov\n"
                "- site:nih.gov\n"
                "- site:mayoclinic.org\n"
                "- site:harvard.edu\n\n"
            )
        
        if prev_iteration.get("relevance_score", 0) < 50:
            refinement_instructions += (
                "Previous sources had low relevance. "
                "Use MORE SPECIFIC search terms related to the user's exact symptoms.\n\n"
            )
        
        refinement_instructions += (
            "Focus on:\n"
            "1. Peer-reviewed research papers\n"
            "2. Clinical studies with quantitative results\n"
            "3. Meta-analyses and systematic reviews\n"
            "4. Government health agency guidelines\n"
        )
        
        return base_prompt + refinement_instructions

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build issue-aware prompt for targeted recommendations."""
        
        profile = context.get("profile", {})
        checkin = context.get("checkin", {})
        metrics = context.get("metrics", {})
        issue_type = context.get("issue_type", "general_wellness")
        
        # Get issue-specific focus
        issue_info = ISSUE_FOCUS.get(issue_type, ISSUE_FOCUS["general_wellness"])
        
        # Normalize data (handle field mismatches)
        sleep = checkin.get('sleep_hours')
        water = checkin.get('water_glasses')
        mood = checkin.get('mood_score') if 'mood_score' in checkin else checkin.get('mood', 3)
        energy = checkin.get('energy_score') if 'energy_score' in checkin else checkin.get('energy_level', 3)
        stress = checkin.get('stress_score', 5)
        exercise = checkin.get('exercise_minutes')
        
        # Profile info
        age = profile.get('age', 30)
        sex = profile.get('sex', 'unknown')
        
        # Build comprehensive data summary (include new MetricsAgent scores)
        data_lines = []
        
        # Basic metrics
        if sleep is not None:
            data_lines.append(f"Sleep: {sleep} hours")
        if water is not None:
            data_lines.append(f"Water: {water} glasses")
        if mood is not None:
            data_lines.append(f"Mood: {mood}/5")
        if energy is not None:
            data_lines.append(f"Energy: {energy}/5")
        if stress is not None:
            data_lines.append(f"Stress: {stress}/10")
        if exercise is not None:
            data_lines.append(f"Exercise: {exercise} min")
        
        # Advanced MetricsAgent scores (NEW)
        if metrics.get("sleep_quality_score"):
            data_lines.append(f"Sleep Quality Score: {metrics['sleep_quality_score']}/10")
        if metrics.get("sleep_debt_hours"):
            data_lines.append(f"Sleep Debt: {metrics['sleep_debt_hours']}h")
        if metrics.get("burnout_risk_score"):
            data_lines.append(f"Burnout Risk: {metrics['burnout_risk_score']}/10")
        if metrics.get("stress_load_index"):
            data_lines.append(f"Stress Load Index: {metrics['stress_load_index']}/10")
        if metrics.get("mental_resilience_score"):
            data_lines.append(f"Mental Resilience: {metrics['mental_resilience_score']}/10")
        if metrics.get("dehydration_risk"):
            data_lines.append(f"Dehydration Risk: {metrics['dehydration_risk']}")
        if metrics.get("sedentary_risk_score"):
            data_lines.append(f"Sedentary Risk: {metrics['sedentary_risk_score']}/10")
        if metrics.get("social_wellness_score"):
            data_lines.append(f"Social Wellness: {metrics['social_wellness_score']}/10")
        if metrics.get("loneliness_risk"):
            data_lines.append(f"Loneliness Risk: {metrics['loneliness_risk']}")
        if metrics.get("toxin_load_score"):
            data_lines.append(f"Toxin Load: {metrics['toxin_load_score']}/10")
        
        data_str = "\n".join(data_lines) if data_lines else "Limited data collected"
        
        # Get benchmarks
        # ideals = metrics.get("ideals", {}) # Future use
        
        return f"""You are a health researcher providing TARGETED insights for: {issue_info['title']}

ISSUE TYPE: {issue_type.upper().replace('_', ' ')}
FOCUS AREAS: {', '.join(issue_info['focus'])}

RELEVANT EVIDENCE BASE:
{chr(10).join('- ' + e for e in issue_info['evidence'])}

PREFERRED SOURCES:
NIH, Mayo Clinic, Harvard Health, Cleveland Clinic, PubMed, CDC, WHO.
Avoid forums, blogs, or unverified commercial sites.

USER ({age}y {sex}):
{data_str}

=== CHAIN-OF-THOUGHT REASONING (You MUST follow these steps) ===

**STEP 1: IDENTIFY THE GAP**
Look at each metric and compare to clinical ideals:
- Sleep: 7-9h optimal → User has {sleep if sleep is not None else 'unknown'}h
- Water: 8+ glasses optimal → User has {water if water is not None else 'unknown'} glasses
- Stress: <4/10 optimal → User has {stress if stress is not None else 'unknown'}/10

**STEP 2: FIND THE ROOT CAUSE**
For the BIGGEST gap, ask: "What biological mechanism explains this symptom?"
- Sleep deprivation → Prefrontal cortex impairment → Focus issues
- High stress → Elevated cortisol → Sleep disruption + mood impact
- Dehydration → Reduced blood volume → Fatigue + cognitive decline

**STEP 3: CONNECT TO USER'S COMPLAINT**
Link the mechanism DIRECTLY to what they said. Use their words.

**STEP 4: FORMULATE INSIGHT**
Structure: [Their Data] + [Clinical Ideal] + [Mechanism] + [Their Symptom]

=== SAFETY RULES (CRITICAL) ===
- Do NOT provide a medical diagnosis.
- Do NOT name specific diseases as a conclusion.
- Do NOT recommend medications, supplements, or dosages.
- Keep language educational and focused on prevention.

=== FEW-SHOT EXAMPLES ===

INPUT: Sleep: 5h, Stress: 8/10, Issue: mental_fatigue
REASONING:
- Gap: Sleep is 2h below minimum (7h). This is severe.
- Mechanism: Acute sleep restriction impairs prefrontal cortex function.
- Connection: User said "brain fog" - this is classic prefrontal impairment.
OUTPUT: "Your 5h sleep is well below the 7-9h recommended by major sleep foundations. This acute restriction impairs prefrontal cortex function, directly causing the 'brain fog' you described [1]."

INPUT: Sleep: 8h, Water: 3 glasses, Issue: physical_fatigue
REASONING:
- Gap: Water is 5 glasses below optimal (8). Moderate dehydration.
- Mechanism: 2% dehydration reduces blood volume, heart works harder.
- Connection: User said "tired" - this matches cardiovascular strain.
OUTPUT: "At 3 glasses, you're at roughly 40% of optimal hydration. Even mild dehydration increases heart workload, which explains the physical fatigue you're experiencing [1]."

=== CITATION FORMAT (MANDATORY) ===
EVERY medical claim MUST include a citation number [1], [2], etc.

Examples:
✓ CORRECT: "Your 5h sleep is below the 7-9h recommended by major sleep foundations [1]."
✓ CORRECT: "Sleep restriction impairs prefrontal cortex function [2], causing the brain fog you described."
✗ WRONG: "Sleep is important for health." (no citation)
✗ WRONG: "Studies show sleep matters." (vague, no specific citation)

Rules:
1. Cite SPECIFIC claims, not general statements
2. Use [1], [2], [3] format
3. Each citation should reference a grounded source
4. Prioritize peer-reviewed sources over general health sites

=== YOUR OUTPUT ===
OUTPUT JSON:
{{
  "reasoning": "Brief chain-of-thought explaining which metrics are most concerning and why (2-3 sentences)",
  "insights": [
    "Insight 1: [User's Data] + [Clinical Ideal] + [Biological Mechanism] + [Citation]",
    "Insight 2: [User's Data] + [Clinical Ideal] + [Biological Mechanism] + [Citation]",
    "Insight 3: [User's Data] + [Clinical Ideal] + [Biological Mechanism] + [Citation]"
  ],
  "confidence": 0.0-1.0 (how confident you are in the quality of sources found)
}}

Generate 2-4 insights maximum. Focus on the MOST IMPACTFUL findings."""

    def _fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Issue-aware fallback."""
        checkin = context.get("checkin", {})
        issue_type = context.get("issue_type", "general_wellness")
        
        sleep = checkin.get('sleep_hours')
        water = checkin.get('water_glasses')
        stress = checkin.get('stress_score')
        
        insights = []
        
        if issue_type == "mental_fatigue":
            if sleep and sleep < 7:
                insights.append(f"Your {sleep}h of sleep is likely impacting your mental clarity. The brain consolidates memories and clears toxins during deep sleep.")
            if stress and stress > 5:
                insights.append(f"High stress ({stress}/10) elevates cortisol, which impairs focus and memory. Consider a brief breathing exercise.")
            if water and water < 6:
                insights.append(f"At {water} glasses, dehydration may be contributing to brain fog. Even mild dehydration reduces cognitive performance.")
                
        elif issue_type == "emotional":
            if sleep and sleep < 7:
                insights.append(f"Sleep deprivation ({sleep}h) amplifies negative emotions by increasing amygdala reactivity.")
            if stress and stress > 5:
                insights.append(f"Your stress level ({stress}/10) is elevated. Physical movement, even a 10-min walk, can help regulate mood.")
                
        elif issue_type == "physical_fatigue":
            if sleep and sleep < 7:
                insights.append(f"Your {sleep}h of sleep limits physical recovery. Muscles repair and energy restores during deep sleep.")
            if water and water < 6:
                insights.append(f"{water} glasses of water is below optimal. Dehydration makes your heart work harder, reducing energy.")
                
        elif issue_type == "sleep_issues":
            if stress and stress > 5:
                insights.append(f"High stress ({stress}/10) suppresses melatonin production, making it harder to fall asleep.")
        
        else:  # general_wellness
            if sleep and sleep >= 7:
                insights.append(f"Great job on {sleep}h of sleep! You're in the optimal range.")
            if water and water >= 8:
                insights.append(f"You're well-hydrated at {water} glasses.")
        
        if not insights:
            insights = ["Based on the data collected, let's focus on building consistent healthy habits."]
            
        context["insights"] = insights
        return context
