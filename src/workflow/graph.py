"""LangGraph workflow construction."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from langgraph.graph import StateGraph, START, END

from ..models.schemas import State
from ..services.llm_service import LLMService
from ..services.research_service import ResearchService

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import IMAGE_PROVIDER, LLM_MODEL, LLM_TEMPERATURE

from .nodes import WorkflowNodes


def create_blog_workflow():
    """Create and compile the blog writing workflow.

    Returns:
        Compiled LangGraph application
    """
    # Initialize services
    llm_service = LLMService(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    research_service = ResearchService(llm_service)
    
    # Choose image service based on configuration
    if IMAGE_PROVIDER == "google" and os.getenv("GOOGLE_API_KEY"):
        print("📸 Using Google Imagen 3 for image generation")
        from ..services.image_service import ImageService
        image_service = ImageService()
    elif os.getenv("OPENAI_API_KEY"):
        print("📸 Using OpenAI DALL-E 3 for image generation")
        from ..services.image_service_openai import ImageServiceOpenAI
        image_service = ImageServiceOpenAI()
    else:
        print("⚠️  No image API key found - images will be disabled")
        from ..services.image_service import ImageService
        image_service = ImageService()  # Will fail gracefully

    # Initialize nodes
    nodes = WorkflowNodes(llm_service, research_service, image_service)

    # Build reducer subgraph
    reducer_graph = StateGraph(State)
    reducer_graph.add_node("merge_content", nodes.merge_content)
    reducer_graph.add_node("decide_images", nodes.decide_images)
    reducer_graph.add_node("generate_and_place_images", nodes.generate_and_place_images)
    reducer_graph.add_edge(START, "merge_content")
    reducer_graph.add_edge("merge_content", "decide_images")
    reducer_graph.add_edge("decide_images", "generate_and_place_images")
    reducer_graph.add_edge("generate_and_place_images", END)
    reducer_subgraph = reducer_graph.compile()

    # Build main graph
    main_graph = StateGraph(State)
    main_graph.add_node("router", nodes.router_node)
    main_graph.add_node("research", nodes.research_node)
    main_graph.add_node("orchestrator", nodes.orchestrator_node)
    main_graph.add_node("worker", nodes.worker_node)
    main_graph.add_node("reducer", reducer_subgraph)

    main_graph.add_edge(START, "router")
    main_graph.add_conditional_edges(
        "router", 
        nodes.route_next, 
        {"research": "research", "orchestrator": "orchestrator"}
    )
    main_graph.add_edge("research", "orchestrator")
    main_graph.add_conditional_edges("orchestrator", nodes.fanout, ["worker"])
    main_graph.add_edge("worker", "reducer")
    main_graph.add_edge("reducer", END)

    return main_graph.compile()
