"""LangGraph node implementations for blog writing workflow."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send

from ..models.schemas import (
    State,
    RouterDecision,
    Plan,
    Task,
    EvidenceItem,
    GlobalImagePlan,
    ImageSpec,
)
from ..services.llm_service import LLMService
from ..services.research_service import ResearchService
from ..services.image_service import ImageService


class WorkflowNodes:
    """Container for all workflow node functions."""

    def __init__(
        self,
        llm_service: LLMService,
        research_service: ResearchService,
        image_service: ImageService,
    ):
        """Initialize workflow nodes.

        Args:
            llm_service: LLM service instance
            research_service: Research service instance
            image_service: Image service instance
        """
        self.llm_service = llm_service
        self.research_service = research_service
        self.image_service = image_service

    # ========== Router Node ==========
    ROUTER_SYSTEM = """You are a routing module for a technical blog planner.

Decide whether web research is needed BEFORE planning.

Modes:
- closed_book (needs_research=false): evergreen concepts.
- hybrid (needs_research=true): evergreen + needs up-to-date examples/tools/models.
- open_book (needs_research=true): volatile weekly/news/"latest"/pricing/policy.

If needs_research=true:
- Output 3–10 high-signal, scoped queries.
- For open_book weekly roundup, include queries reflecting last 7 days.
"""

    def router_node(self, state: State) -> dict:
        """Route to research or direct to orchestrator."""
        decision = self.llm_service.invoke_structured(
            system_prompt=self.ROUTER_SYSTEM,
            user_prompt=f"Topic: {state['topic']}\nAs-of date: {state['as_of']}",
            schema=RouterDecision,
        )

        if decision.mode == "open_book":
            recency_days = 7
        elif decision.mode == "hybrid":
            recency_days = 45
        else:
            recency_days = 3650

        return {
            "needs_research": decision.needs_research,
            "mode": decision.mode,
            "queries": decision.queries,
            "recency_days": recency_days,
        }

    @staticmethod
    def route_next(state: State) -> str:
        """Conditional edge: research or orchestrator."""
        return "research" if state["needs_research"] else "orchestrator"

    # ========== Research Node ==========
    def research_node(self, state: State) -> dict:
        """Gather research evidence."""
        evidence = self.research_service.gather_evidence(
            queries=state.get("queries") or [],
            as_of=state["as_of"],
            recency_days=state["recency_days"],
            mode=state.get("mode", "closed_book"),
        )
        return {"evidence": evidence}

    # ========== Orchestrator Node ==========
    ORCH_SYSTEM = """You are a senior technical writer and developer advocate.
Produce a highly actionable outline for a technical blog post.

Requirements:
- 5–9 tasks, each with goal + 3–6 bullets + target_words.
- Tags are flexible; do not force a fixed taxonomy.

Grounding:
- closed_book: evergreen, no evidence dependence.
- hybrid: use evidence for up-to-date examples; mark those tasks requires_research=True and requires_citations=True.
- open_book: weekly/news roundup:
  - Set blog_kind="news_roundup"
  - No tutorial content unless requested
  - If evidence is weak, plan should explicitly reflect that (don't invent events).

Output must match Plan schema.
"""

    def orchestrator_node(self, state: State) -> dict:
        """Create blog post plan."""
        mode = state.get("mode", "closed_book")
        evidence = state.get("evidence", [])
        forced_kind = "news_roundup" if mode == "open_book" else None

        plan = self.llm_service.invoke_structured(
            system_prompt=self.ORCH_SYSTEM,
            user_prompt=(
                f"Topic: {state['topic']}\n"
                f"Mode: {mode}\n"
                f"As-of: {state['as_of']} (recency_days={state['recency_days']})\n"
                f"{'Force blog_kind=news_roundup' if forced_kind else ''}\n\n"
                f"Evidence:\n{[e.model_dump() for e in evidence][:16]}"
            ),
            schema=Plan,
        )

        if forced_kind:
            plan.blog_kind = "news_roundup"

        return {"plan": plan}

    # ========== Fanout ==========
    @staticmethod
    def fanout(state: State):
        """Fan out to parallel workers for each task."""
        assert state["plan"] is not None
        return [
            Send(
                "worker",
                {
                    "task": task.model_dump(),
                    "topic": state["topic"],
                    "mode": state["mode"],
                    "as_of": state["as_of"],
                    "recency_days": state["recency_days"],
                    "plan": state["plan"].model_dump(),
                    "evidence": [e.model_dump() for e in state.get("evidence", [])],
                },
            )
            for task in state["plan"].tasks
        ]

    # ========== Worker Node ==========
    WORKER_SYSTEM = """You are a senior technical writer and developer advocate.
Write ONE section of a technical blog post in Markdown.

Constraints:
- Cover ALL bullets in order.
- Target words ±15%.
- Output only section markdown starting with "## <Section Title>".

Scope guard:
- If blog_kind=="news_roundup", do NOT drift into tutorials (scraping/RSS/how to fetch).
  Focus on events + implications.

Grounding & Citations:
- If mode=="open_book": do not introduce any specific event/company/model/funding/policy claim unless supported by provided Evidence URLs.
  For each supported claim, attach a Markdown link using the EXACT URL from Evidence: [Source](ACTUAL_URL_FROM_EVIDENCE)
  If unsupported, write "Not found in provided sources."
- If requires_citations==true (hybrid tasks): cite Evidence URLs for external claims.
- CRITICAL: Use ONLY the actual URLs provided in the Evidence section below. NEVER use placeholder URLs like example.com or research1.
- Citation format: [Source](https://actual-url.com/article) - use the real URL from Evidence list.
- Example: If Evidence shows "AI trends | https://techcrunch.com/ai-article", cite it as [Source](https://techcrunch.com/ai-article)

Code:
- If requires_code==true, include at least one minimal snippet.
"""

    def worker_node(self, payload: dict) -> dict:
        """Write a single section."""
        task = Task(**payload["task"])
        plan = Plan(**payload["plan"])
        evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]

        bullets_text = "\n- " + "\n- ".join(task.bullets)
        evidence_text = "\n".join(
            f"- {e.title} | {e.url} | {e.published_at or 'date:unknown'}"
            for e in evidence[:20]
        )

        section_md = self.llm_service.invoke(
            system_prompt=self.WORKER_SYSTEM,
            user_prompt=(
                f"Blog title: {plan.blog_title}\n"
                f"Audience: {plan.audience}\n"
                f"Tone: {plan.tone}\n"
                f"Blog kind: {plan.blog_kind}\n"
                f"Constraints: {plan.constraints}\n"
                f"Topic: {payload['topic']}\n"
                f"Mode: {payload.get('mode')}\n"
                f"As-of: {payload.get('as_of')} (recency_days={payload.get('recency_days')})\n\n"
                f"Section title: {task.title}\n"
                f"Goal: {task.goal}\n"
                f"Target words: {task.target_words}\n"
                f"Tags: {task.tags}\n"
                f"requires_research: {task.requires_research}\n"
                f"requires_citations: {task.requires_citations}\n"
                f"requires_code: {task.requires_code}\n"
                f"Bullets:{bullets_text}\n\n"
                f"Evidence (ONLY cite these URLs):\n{evidence_text}\n"
            ),
        )
        
        # Detect placeholder URLs and warn
        placeholder_patterns = ['example.com', 'research1', 'research2', 'research3', 'source1', 'source2']
        if any(pattern in section_md.lower() for pattern in placeholder_patterns):
            print(f"⚠️ Warning: Section '{task.title}' may contain placeholder URLs instead of real citations")
            print(f"   Available evidence URLs: {[e.url for e in evidence[:3]]}")

        return {"sections": [(task.id, section_md)]}

    # ========== Reducer: Merge Content ==========
    @staticmethod
    def merge_content(state: State) -> dict:
        """Merge all sections into single document."""
        plan = state["plan"]
        if plan is None:
            raise ValueError("merge_content called without plan.")
        
        ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
        body = "\n\n".join(ordered_sections).strip()
        merged_md = f"# {plan.blog_title}\n\n{body}\n"
        return {"merged_md": merged_md}

    # ========== Reducer: Decide Images ==========
    DECIDE_IMAGES_SYSTEM = """You are an expert technical editor.
Decide where images/diagrams should be placed in THIS blog to enhance understanding.

Rules:
- MINIMUM 2 images required for technical blogs (architecture, flow, concept diagrams).
- MAXIMUM 3 images total.
- Each image must materially improve understanding (architecture diagram, flowchart, concept visualization).
- Insert placeholders EXACTLY as: [[IMAGE_1]], [[IMAGE_2]], [[IMAGE_3]]
- Place placeholders AFTER relevant paragraphs that describe what the image will show.
- For each image, create a detailed descriptive prompt that will generate a clear technical diagram.
- Image captions should be concise and describe what the diagram shows.
- NEVER return empty images list - always include at least 2 images for technical content.
- Prefer: architecture diagrams, workflow visualizations, concept illustrations, comparison charts.
- Example placement:
  
  "...describes the architecture..."
  
  [[IMAGE_1]]
  
  "...continues with next concept..."

Return strictly GlobalImagePlan with md_with_placeholders containing ALL original content plus image placeholders.
"""

    def decide_images(self, state: State) -> dict:
        """Decide which images to generate."""
        merged_md = state["merged_md"]
        plan = state["plan"]
        assert plan is not None

        image_plan = self.llm_service.invoke_structured(
            system_prompt=self.DECIDE_IMAGES_SYSTEM,
            user_prompt=(
                f"Blog kind: {plan.blog_kind}\n"
                f"Topic: {state['topic']}\n"
                f"Blog title: {plan.blog_title}\n\n"
                "TASK: Insert 2-3 image placeholders into the blog at strategic locations.\n"
                "- Create detailed image prompts for technical diagrams (architecture, workflow, concepts).\n"
                "- Place [[IMAGE_1]], [[IMAGE_2]], [[IMAGE_3]] after relevant paragraphs.\n"
                "- Ensure ALL original content is preserved in md_with_placeholders.\n\n"
                "Blog content:\n\n"
                f"{merged_md}"
            ),
            schema=GlobalImagePlan,
        )
        
        # Validate that images were created
        if not image_plan.images or len(image_plan.images) == 0:
            print("⚠️ Warning: No images planned. This should not happen for technical blogs.")
        else:
            print(f"✓ Planned {len(image_plan.images)} image(s) for the blog")

        return {
            "md_with_placeholders": image_plan.md_with_placeholders,
            "image_specs": [img.model_dump() for img in image_plan.images],
        }

    # ========== Reducer: Generate and Place Images ==========
    def generate_and_place_images(self, state: State) -> dict:
        """Generate images and create final markdown."""
        plan = state["plan"]
        assert plan is not None

        md = state.get("md_with_placeholders") or state["merged_md"]
        image_specs_dicts = state.get("image_specs", []) or []
        
        # Convert dicts to ImageSpec objects
        image_specs = [ImageSpec(**spec) for spec in image_specs_dicts]

        # Process images if any
        if image_specs:
            try:
                md = self.image_service.process_image_specs(md, image_specs)
            except Exception as e:
                # Log error but continue with blog generation
                print(f"Warning: Image generation failed: {e}")
                # Add note to markdown about failed images
                md = f"> ⚠️ Note: Image generation failed. See markdown for placeholders.\n\n{md}"

        # Create outputs directory if it doesn't exist
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        
        # Save to outputs folder
        filename = f"{self._safe_slug(plan.blog_title)}.md"
        output_path = outputs_dir / filename
        output_path.write_text(md, encoding="utf-8")
        
        # Also save to root for backward compatibility
        root_path = Path(filename)
        root_path.write_text(md, encoding="utf-8")
        
        print(f"✓ Blog saved to: {output_path}")
        print(f"✓ Also saved to: {root_path}")
        
        return {"final": md}

    @staticmethod
    def _safe_slug(title: str) -> str:
        """Convert title to safe filename."""
        s = title.strip().lower()
        s = re.sub(r"[^a-z0-9 _-]+", "", s)
        s = re.sub(r"\s+", "_", s).strip("_")
        return s or "blog"
