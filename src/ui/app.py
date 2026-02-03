"""Streamlit application for blog writing agent."""

from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, List, Iterator, Tuple

import pandas as pd
import streamlit as st

# Ensure environment is loaded
from dotenv import load_dotenv
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.workflow import create_blog_workflow


class BlogWriterUI:
    """Streamlit UI for blog writing agent."""

    def __init__(self):
        """Initialize UI."""
        self.app = create_blog_workflow()
        self._md_img_re = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")
        self._caption_line_re = re.compile(r"^\*(?P<cap>.+)\*$")

    # ========== Helper Methods ==========
    @staticmethod
    def safe_slug(title: str) -> str:
        """Convert title to safe filename."""
        s = title.strip().lower()
        s = re.sub(r"[^a-z0-9 _-]+", "", s)
        s = re.sub(r"\s+", "_", s).strip("_")
        return s or "blog"

    @staticmethod
    def bundle_zip(md_text: str, md_filename: str, images_dir: Path) -> bytes:
        """Create zip bundle with markdown and images."""
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(md_filename, md_text.encode("utf-8"))
            if images_dir.exists() and images_dir.is_dir():
                for p in images_dir.rglob("*"):
                    if p.is_file():
                        z.write(p, arcname=str(p))
        return buf.getvalue()

    @staticmethod
    def images_zip(images_dir: Path) -> Optional[bytes]:
        """Create zip of images directory."""
        if not images_dir.exists() or not images_dir.is_dir():
            return None
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in images_dir.rglob("*"):
                if p.is_file():
                    z.write(p, arcname=str(p))
        return buf.getvalue()

    def try_stream(self, inputs: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
        """
        Stream graph progress using LangGraph's streaming capabilities.
        This provides real-time updates via Streamlit's SSE (Server-Sent Events).
        """
        final_state = None
        
        try:
            # Use stream_mode="updates" for node-by-node updates
            for step in self.app.stream(inputs, stream_mode="updates"):
                yield ("updates", step)
                
            # Get final state after streaming
            final_state = self.app.invoke(inputs)
            yield ("final", final_state)
            return
            
        except Exception as e:
            # Fallback to values mode
            try:
                for step in self.app.stream(inputs, stream_mode="values"):
                    yield ("values", step)
                    
                # Get final state
                if not final_state:
                    final_state = self.app.invoke(inputs)
                yield ("final", final_state)
                return
                
            except Exception:
                # Final fallback: direct invoke
                if not final_state:
                    final_state = self.app.invoke(inputs)
                yield ("final", final_state)

    @staticmethod
    def extract_latest_state(current_state: Dict[str, Any], step_payload: Any) -> Dict[str, Any]:
        """Extract latest state from step payload."""
        if isinstance(step_payload, dict):
            if len(step_payload) == 1 and isinstance(next(iter(step_payload.values())), dict):
                inner = next(iter(step_payload.values()))
                current_state.update(inner)
            else:
                current_state.update(step_payload)
        return current_state

    # ========== Markdown Rendering ==========
    def _resolve_image_path(self, src: str) -> Path:
        """Resolve image path."""
        src = src.strip().lstrip("./")
        return Path(src).resolve()

    def render_markdown_with_local_images(self, md: str):
        """Render markdown with support for local images and LaTeX formulas.
        
        Converts local image paths to base64 data URLs so they display in markdown.
        """
        import base64
        
        matches = list(self._md_img_re.finditer(md))
        if not matches:
            # No images found - render directly with LaTeX support
            st.markdown(md, unsafe_allow_html=True)
            return

        # Convert local image paths to base64 data URLs for markdown display
        md_with_data_urls = md
        images_not_found = []
        images_found = 0
        
        for m in matches:
            alt = (m.group("alt") or "").strip()
            src = (m.group("src") or "").strip()
            
            if src.startswith("http://") or src.startswith("https://"):
                # Remote images work as-is
                continue
            
            # Local image - convert to base64 data URL
            possible_paths = [
                Path(src),                        # Relative path
                Path.cwd() / src,                # Relative to working directory
                self._resolve_image_path(src),   # Absolute resolved path
            ]
            
            image_found = False
            for path in possible_paths:
                if path.exists() and path.is_file():
                    try:
                        # Read image and convert to base64
                        with open(path, "rb") as img_file:
                            img_data = img_file.read()
                            b64_data = base64.b64encode(img_data).decode()
                            
                            # Detect image format
                            img_format = path.suffix.lower().replace('.', '')
                            if img_format == 'jpg':
                                img_format = 'jpeg'
                            elif not img_format:
                                img_format = 'png'  # Default
                            
                            # Create data URL
                            data_url = f"data:image/{img_format};base64,{b64_data}"
                            
                            # Replace in markdown
                            original = f"![{alt}]({src})"
                            replacement = f"![{alt}]({data_url})"
                            md_with_data_urls = md_with_data_urls.replace(original, replacement)
                            
                            images_found += 1
                            image_found = True
                            break
                    except Exception as e:
                        # Try next path
                        continue
            
            if not image_found:
                images_not_found.append((alt, src))
        
        # Show status message
        if images_found > 0:
            st.success(f"✓ Loaded {images_found} image(s)")
        
        if images_not_found:
            with st.expander(f"⚠️ {len(images_not_found)} image(s) not found", expanded=False):
                for alt, src in images_not_found:
                    st.error(f"🖼️ **{alt}**: `{src}`")
                st.caption("Tip: Check that images were generated and saved to the `images/` folder.")
        
        # Render the markdown with embedded images
        st.markdown(md_with_data_urls, unsafe_allow_html=True)

    # ========== Past Blogs ==========
    @staticmethod
    def list_past_blogs() -> List[Path]:
        """List past blog markdown files from both root and outputs directory."""
        all_files = []
        
        # Documentation files to exclude (comprehensive list)
        excluded_docs = {
            "README.md", "QUICKSTART.md", "PROJECT_STRUCTURE.md", 
            "WINDOWS_GUIDE.md", "COMMANDS_CHEATSHEET.md", "START_HERE.md",
            "IMPROVEMENTS.md", "SSE_INFO.md", "TROUBLESHOOTING.md",
            "FIXES_SUMMARY.md", "QUICK_FIX.md", "FINAL_STATUS.md",
            "IMAGE_DISPLAY_FIX.md", "WHATS_WORKING.md", "SESSION_SUMMARY.md",
            "SOURCE_LINKS_FIX.md", "LATEST_FIX.md"
        }
        
        # Only load from outputs directory (cleaner approach)
        outputs_dir = Path("outputs")
        if outputs_dir.exists():
            output_files = [p for p in outputs_dir.glob("*.md") 
                          if p.is_file() and p.name not in excluded_docs]
            all_files.extend(output_files)
        
        # Optionally also check root for legacy blogs
        cwd = Path(".")
        root_files = [p for p in cwd.glob("*.md") 
                     if p.is_file() and p.name not in excluded_docs]
        
        # Only add root files that aren't duplicates (same name in outputs)
        output_names = {f.name for f in all_files}
        for rf in root_files:
            if rf.name not in output_names:
                # Check if it looks like a generated blog (has "understanding_" or similar patterns)
                if any(pattern in rf.name.lower() for pattern in ['understanding_', 'guide_to_', 'how_to_', 'what_is_', 'introduction_to_']):
                    all_files.append(rf)
        
        # Sort by modification time (newest first)
        all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return all_files

    @staticmethod
    def read_md_file(p: Path) -> str:
        """Read markdown file."""
        return p.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def extract_title_from_md(md: str, fallback: str) -> str:
        """Extract title from markdown."""
        for line in md.splitlines():
            if line.startswith("# "):
                t = line[2:].strip()
                return t or fallback
        return fallback

    # ========== Main UI ==========
    def run(self):
        """Run the Streamlit application."""
        st.set_page_config(
            page_title="LangGraph Blog Writer", 
            layout="wide",
            initial_sidebar_state="expanded",
        )
        
        # Add MathJax support for LaTeX formulas
        st.markdown(
            r"""
            <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
            <script>
                window.MathJax = {
                    tex: {
                        inlineMath: [['$', '$'], ['\\(', '\\)']],
                        displayMath: [['$$', '$$'], ['\\[', '\\]']],
                        processEscapes: true,
                        processEnvironments: true
                    },
                    options: {
                        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
                    }
                };
            </script>
            """,
            unsafe_allow_html=True
        )
        
        st.title("🤖 Blog Writing Agent")
        
        # Show banner if a blog was just loaded
        if "loaded_blog_name" in st.session_state:
            st.info(f"📂 **Viewing loaded blog:** {st.session_state['loaded_blog_name']} — Check the **'📝 Markdown Preview' tab** below!")
        
        # Show notification if there are past blogs available
        if "past_blogs_notified" not in st.session_state:
            past_count = len(self.list_past_blogs())
            if past_count > 0:
                st.success(f"💡 {past_count} past blog(s) available in the sidebar!")
            st.session_state["past_blogs_notified"] = True

        # Sidebar
        with st.sidebar:
            st.header("Generate New Blog")
            topic = st.text_area("Topic", height=120)
            as_of = st.date_input("As-of date", value=date.today())
            run_btn = st.button("🚀 Generate Blog", type="primary")

            # Debug info
            st.divider()
            with st.expander("📂 File Locations", expanded=False):
                st.caption("Generated files are saved to:")
                st.code(f"📝 Markdown: outputs/your-blog-title.md", language="text")
                st.code(f"🖼️ Images: images/your-image.png", language="text")
                
                # Check folder status
                outputs_exists = Path("outputs").exists()
                images_exists = Path("images").exists()
                
                col1, col2 = st.columns(2)
                with col1:
                    if outputs_exists:
                        output_count = len(list(Path("outputs").glob("*.md")))
                        st.success(f"✓ outputs/ ({output_count} files)")
                    else:
                        st.warning("✗ outputs/ not found")
                
                with col2:
                    if images_exists:
                        image_count = len(list(Path("images").glob("*")))
                        st.success(f"✓ images/ ({image_count} files)")
                    else:
                        st.warning("✗ images/ not found")
            
            # Past blogs
            st.divider()
            st.subheader("📚 Past blogs")

            past_files = self.list_past_blogs()
            if not past_files:
                st.info("No saved blogs found yet.")
                st.caption("Generate a blog to see it here!")
                
                # Debug info
                with st.expander("🔍 Troubleshooting", expanded=False):
                    st.caption("**Check these locations:**")
                    outputs_exists = Path("outputs").exists()
                    st.write(f"- `outputs/` folder exists: {outputs_exists}")
                    if outputs_exists:
                        md_count = len(list(Path("outputs").glob("*.md")))
                        st.write(f"- Files in `outputs/`: {md_count}")
                        if md_count > 0:
                            st.warning("Files found but filtered out. Check exclusion list.")
                    
                    root_md = len(list(Path(".").glob("*.md")))
                    st.write(f"- Files in root: {root_md}")
                
                selected_md_file = None
            else:
                st.caption(f"Found {len(past_files)} blog(s)")
                
                options: List[str] = []
                file_by_label: Dict[str, Path] = {}
                for p in past_files[:50]:
                    try:
                        md_text = self.read_md_file(p)
                        title = self.extract_title_from_md(md_text, p.stem)
                    except Exception as e:
                        title = p.stem
                        st.caption(f"⚠️ Error reading {p.name}: {e}")
                    
                    # Show file location
                    if p.parent.name == "outputs":
                        location = "📂 outputs/"
                    else:
                        location = "📄 root/"
                    
                    label = f"{title}\n{location}{p.name}"
                    options.append(label)
                    file_by_label[label] = p

                selected_label = st.radio(
                    "Select a blog to load",
                    options=options,
                    index=0,
                    label_visibility="collapsed",
                    key="past_blog_selector"
                )
                selected_md_file = file_by_label.get(selected_label)
                
                # Show quick preview
                if selected_md_file:
                    with st.expander("👁️ Preview", expanded=False):
                        try:
                            preview_text = self.read_md_file(selected_md_file)
                            # Show first 500 characters
                            st.text(preview_text[:500] + "..." if len(preview_text) > 500 else preview_text)
                        except Exception as e:
                            st.error(f"Cannot preview: {e}")

                if st.button("📂 Load selected blog", use_container_width=True, type="primary"):
                    if selected_md_file:
                        try:
                            # Show loading indicator
                            with st.spinner(f"Loading {selected_md_file.name}..."):
                                md_text = self.read_md_file(selected_md_file)
                                
                                # Validate content
                                if not md_text or len(md_text.strip()) == 0:
                                    st.error("❌ Blog file is empty!")
                                    st.stop()
                                
                                # Store in session state
                                st.session_state["last_out"] = {
                                    "plan": None,
                                    "evidence": [],
                                    "image_specs": [],
                                    "final": md_text,
                                }
                                st.session_state["topic_prefill"] = self.extract_title_from_md(
                                    md_text, selected_md_file.stem
                                )
                                st.session_state["loaded_blog_name"] = selected_md_file.name
                                
                            st.success(f"✓ Loaded: {selected_md_file.name}")
                            st.info("👉 Check the **'📝 Markdown Preview' tab** to view the blog!")
                            
                            # Force UI refresh to show loaded blog
                            st.rerun()
                            
                        except FileNotFoundError:
                            st.error(f"❌ File not found: {selected_md_file}")
                        except PermissionError:
                            st.error(f"❌ Permission denied: {selected_md_file}")
                        except Exception as e:
                            st.error(f"❌ Failed to load blog: {str(e)}")
                            st.exception(e)  # Show full traceback for debugging
                    else:
                        st.warning("⚠️ No blog selected. Please select a blog from the list above.")

        # Storage for latest run
        if "last_out" not in st.session_state:
            st.session_state["last_out"] = None

        # Layout tabs
        tab_plan, tab_evidence, tab_preview, tab_images, tab_logs = st.tabs(
            ["🧩 Plan", "🔎 Evidence", "📝 Markdown Preview", "🖼️ Images", "🧾 Logs"]
        )

        # Create placeholders for real-time updates in tabs
        with tab_plan:
            plan_placeholder = st.empty()
        with tab_evidence:
            evidence_placeholder = st.empty()
        with tab_preview:
            preview_placeholder = st.empty()
        with tab_images:
            images_placeholder = st.empty()
        with tab_logs:
            logs_placeholder = st.empty()

        logs: List[str] = []

        def log(msg: str):
            logs.append(msg)
            # Update logs in real-time
            logs_placeholder.text_area(
                "Event log", 
                value="\n\n".join(logs[-50:]), 
                height=520,
                key=f"logs_{len(logs)}"
            )

        # Run workflow
        if run_btn:
            if not topic.strip():
                st.warning("Please enter a topic.")
                st.stop()

            inputs: Dict[str, Any] = {
                "topic": topic.strip(),
                "mode": "",
                "needs_research": False,
                "queries": [],
                "evidence": [],
                "plan": None,
                "as_of": as_of.isoformat(),
                "recency_days": 7,
                "sections": [],
                "merged_md": "",
                "md_with_placeholders": "",
                "image_specs": [],
                "final": "",
            }

            # Progress tracking with SSE (Server-Sent Events via Streamlit)
            status = st.status("🚀 Generating blog with AI...", expanded=True)
            progress_area = st.empty()
            
            # Progress metrics
            progress_metrics = st.empty()

            current_state: Dict[str, Any] = {}
            last_node = None
            step_count = 0

            # Stream updates in real-time (SSE enabled by default in Streamlit)
            for kind, payload in self.try_stream(inputs):
                step_count += 1
                
                if kind in ("updates", "values"):
                    # Extract node name for progress tracking
                    node_name = None
                    if isinstance(payload, dict) and len(payload) == 1:
                        node_name = next(iter(payload.keys()))
                    
                    # Update status with current node
                    if node_name and node_name != last_node:
                        node_emoji = {
                            "router": "🧭",
                            "research": "🔍",
                            "orchestrator": "📋",
                            "worker": "✍️",
                            "reducer": "🔄",
                            "merge_content": "📝",
                            "decide_images": "🖼️",
                            "generate_and_place_images": "🎨"
                        }.get(node_name, "⚙️")
                        
                        status.write(f"{node_emoji} **{node_name.replace('_', ' ').title()}**")
                        last_node = node_name

                    # Update state
                    current_state = self.extract_latest_state(current_state, payload)

                    # Show progress metrics
                    plan_obj = current_state.get("plan")
                    total_tasks = 0
                    if plan_obj:
                        if hasattr(plan_obj, "tasks"):
                            total_tasks = len(plan_obj.tasks)
                        elif isinstance(plan_obj, dict):
                            total_tasks = len(plan_obj.get("tasks", []))

                    summary = {
                        "mode": current_state.get("mode") or "initializing",
                        "research_needed": current_state.get("needs_research", False),
                        "evidence_sources": len(current_state.get("evidence", []) or []),
                        "sections_planned": total_tasks,
                        "sections_written": len(current_state.get("sections", []) or []),
                        "images_planned": len(current_state.get("image_specs", []) or []),
                    }
                    
                    # Display metrics in columns
                    with progress_metrics.container():
                        cols = st.columns(4)
                        cols[0].metric("Mode", summary["mode"].replace("_", " ").title())
                        cols[1].metric("Evidence", summary["evidence_sources"])
                        cols[2].metric("Sections", f"{summary['sections_written']}/{summary['sections_planned']}")
                        cols[3].metric("Images", summary["images_planned"])
                    
                    # Real-time tab updates (SSE streaming)
                    self._update_tabs_realtime(
                        current_state,
                        plan_placeholder,
                        evidence_placeholder,
                        preview_placeholder,
                        images_placeholder,
                    )
                    
                    log(f"[{kind}] {node_name or 'update'}: {json.dumps(payload, default=str)[:800]}")

                elif kind == "final":
                    out = payload
                    st.session_state["last_out"] = out
                    status.update(label="✅ Blog Generated Successfully!", state="complete", expanded=False)
                    log(f"[final] Generation complete! Total steps: {step_count}")
                    
                    # Show completion metrics
                    with progress_metrics.container():
                        st.success(f"✓ Generation completed in {step_count} steps")
                    
                    # Force rerun to show final results
                    st.rerun()

        # Render final results (after generation completes or loaded from file)
        out = st.session_state.get("last_out")
        if out:
            # Check if this is a loaded blog (no plan) or freshly generated
            is_loaded = out.get("plan") is None and out.get("final")
            
            if is_loaded:
                # Show banner for loaded blogs
                st.info("📂 Viewing a loaded blog from file. Generate a new blog to see full details.")
            
            with tab_plan:
                plan_placeholder.empty()
                if is_loaded:
                    st.info("ℹ️ Plan data not available for loaded blogs.")
                else:
                    self._render_plan_tab_content(out)
            
            with tab_evidence:
                evidence_placeholder.empty()
                if is_loaded:
                    st.info("ℹ️ Evidence data not available for loaded blogs.")
                else:
                    self._render_evidence_tab_content(out)
            
            with tab_preview:
                preview_placeholder.empty()
                self._render_preview_tab_content(out)
            
            with tab_images:
                images_placeholder.empty()
                self._render_images_tab_content(out)
        elif not run_btn:
            with tab_preview:
                st.info("Enter a topic and click **Generate Blog** to start.")

    def _update_tabs_realtime(
        self,
        state: Dict[str, Any],
        plan_ph,
        evidence_ph,
        preview_ph,
        images_ph,
    ):
        """Update tabs with real-time progress."""
        # Update Plan tab
        plan_obj = state.get("plan")
        if plan_obj:
            with plan_ph.container():
                st.markdown("### 🧩 Plan Generated")
                if hasattr(plan_obj, "blog_title"):
                    st.success(f"**Title:** {plan_obj.blog_title}")
                elif isinstance(plan_obj, dict):
                    st.success(f"**Title:** {plan_obj.get('blog_title', 'N/A')}")
                st.info(f"📝 Sections planned: {len(plan_obj.get('tasks', []) if isinstance(plan_obj, dict) else plan_obj.tasks)}")
        else:
            with plan_ph.container():
                st.info("⏳ Waiting for plan...")
        
        # Update Evidence tab with clickable links
        evidence = state.get("evidence", [])
        if evidence:
            with evidence_ph.container():
                st.markdown("### 🔎 Research Progress")
                st.success(f"✓ Found {len(evidence)} sources")
                
                # Show first 3 sources with clickable links
                for idx, e in enumerate(evidence[:3], 1):
                    if hasattr(e, "model_dump"):
                        e_dict = e.model_dump()
                    else:
                        e_dict = e if isinstance(e, dict) else {}
                    
                    title = e_dict.get('title', 'Untitled')[:60]
                    url = e_dict.get('url', '')
                    
                    if url:
                        st.markdown(f"{idx}. [{title}...]({url})")
                    else:
                        st.markdown(f"{idx}. {title}...")
                
                if len(evidence) > 3:
                    st.caption(f"+ {len(evidence) - 3} more sources (see Evidence tab)")
        else:
            with evidence_ph.container():
                st.info("⏳ Gathering evidence...")
        
        # Update Preview tab
        sections = state.get("sections", [])
        plan_obj = state.get("plan")
        
        # Get total tasks from plan
        total_tasks = 0
        if plan_obj:
            if hasattr(plan_obj, "tasks"):
                total_tasks = len(plan_obj.tasks)
            elif isinstance(plan_obj, dict):
                total_tasks = len(plan_obj.get("tasks", []))
        
        # Calculate number of completed sections
        sections_count = len(sections) if sections else 0
        
        if total_tasks > 0:
            with preview_ph.container():
                st.markdown("### 📝 Writing Progress")
                
                # Calculate progress (ensure between 0.0 and 1.0)
                progress_value = min(max(sections_count / total_tasks, 0.0), 1.0)
                st.progress(progress_value)
                
                # Show completion status
                if sections_count > 0:
                    st.info(f"✍️ Sections complete: {sections_count}/{total_tasks}")
                else:
                    st.info(f"⏳ Starting to write... (0/{total_tasks} sections)")
        else:
            with preview_ph.container():
                if sections_count > 0:
                    st.info(f"✍️ Writing in progress... ({sections_count} sections)")
                else:
                    st.info("⏳ Preparing to write...")
        
        # Update Images tab
        image_specs = state.get("image_specs", [])
        if image_specs:
            with images_ph.container():
                st.markdown("### 🖼️ Images")
                st.success(f"🎨 {len(image_specs)} image(s) will be generated")
        else:
            with images_ph.container():
                st.info("⏳ Planning images...")

    def _render_plan_tab_content(self, out):
        """Render complete plan tab."""
        st.subheader("Plan")
        plan_obj = out.get("plan")
        if not plan_obj:
            st.info("No plan found in output.")
        else:
            if hasattr(plan_obj, "model_dump"):
                plan_dict = plan_obj.model_dump()
            elif isinstance(plan_obj, dict):
                plan_dict = plan_obj
            else:
                plan_dict = json.loads(json.dumps(plan_obj, default=str))

            st.write("**Title:**", plan_dict.get("blog_title"))
            cols = st.columns(3)
            cols[0].write("**Audience:** " + str(plan_dict.get("audience")))
            cols[1].write("**Tone:** " + str(plan_dict.get("tone")))
            cols[2].write("**Blog kind:** " + str(plan_dict.get("blog_kind", "")))

            tasks = plan_dict.get("tasks", [])
            if tasks:
                df = pd.DataFrame(
                    [
                        {
                            "id": t.get("id"),
                            "title": t.get("title"),
                            "target_words": t.get("target_words"),
                            "requires_research": t.get("requires_research"),
                            "requires_citations": t.get("requires_citations"),
                            "requires_code": t.get("requires_code"),
                            "tags": ", ".join(t.get("tags") or []),
                        }
                        for t in tasks
                    ]
                ).sort_values("id")
                st.dataframe(df, use_container_width=True, hide_index=True)

                with st.expander("Task details"):
                    st.json(tasks)

    def _render_evidence_tab_content(self, out):
        """Render complete evidence tab with clickable source links."""
        st.subheader("Evidence")
        evidence = out.get("evidence") or []
        if not evidence:
            st.info("No evidence returned (maybe closed_book mode or no Tavily key/results).")
        else:
            st.caption(f"Found {len(evidence)} source(s)")
            
            # Render each evidence item with clickable links
            for idx, e in enumerate(evidence, 1):
                if hasattr(e, "model_dump"):
                    e = e.model_dump()
                
                title = e.get("title", "Untitled")
                url = e.get("url", "")
                source = e.get("source", "Unknown")
                published = e.get("published_at", "N/A")
                
                with st.expander(f"📄 Source {idx}: {title[:80]}...", expanded=False):
                    # Title with clickable link
                    if url:
                        st.markdown(f"### [{title}]({url})")
                        st.markdown(f"🔗 **Link:** [{url}]({url})")
                    else:
                        st.markdown(f"### {title}")
                    
                    # Metadata
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Source:** {source}")
                    with col2:
                        st.markdown(f"**Published:** {published}")
                    
                    # Copy button for URL
                    if url:
                        st.code(url, language=None)
                        
            # Also show as compact table with clickable links
            st.divider()
            st.caption("Quick Reference Table")
            
            # Create markdown table with clickable links
            md_table = "| # | Title | Source | Link |\n|---|-------|--------|------|\n"
            for idx, e in enumerate(evidence, 1):
                if hasattr(e, "model_dump"):
                    e = e.model_dump()
                title = e.get("title", "Untitled")[:50]
                source = e.get("source", "Unknown")[:30]
                url = e.get("url", "")
                
                if url:
                    link = f"[🔗 Open]({url})"
                else:
                    link = "N/A"
                
                md_table += f"| {idx} | {title} | {source} | {link} |\n"
            
            st.markdown(md_table)

    def _render_preview_tab_content(self, out):
        """Render complete markdown preview tab."""
        st.subheader("Markdown Preview")
        final_md = out.get("final") or ""
        if not final_md:
            st.warning("No final markdown found.")
        else:
            # Show file save location
            plan_obj = out.get("plan")
            if hasattr(plan_obj, "blog_title"):
                blog_title = plan_obj.blog_title
            elif isinstance(plan_obj, dict):
                blog_title = plan_obj.get("blog_title", "blog")
            else:
                blog_title = self.extract_title_from_md(final_md, "blog")
            
            md_filename = f"{self.safe_slug(blog_title)}.md"
            
            # Show where files are saved
            st.info(f"📁 Saved to: `outputs/{md_filename}` and `{md_filename}`")
            
            # Enable LaTeX rendering
            st.markdown(
                """
                <style>
                .stMarkdown {
                    word-wrap: break-word;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            # Render markdown with images
            self.render_markdown_with_local_images(final_md)

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Download Markdown",
                    data=final_md.encode("utf-8"),
                    file_name=md_filename,
                    mime="text/markdown",
                    use_container_width=True,
                )
            
            with col2:
                bundle = self.bundle_zip(final_md, md_filename, Path("images"))
                st.download_button(
                    "📦 Download Bundle (MD + images)",
                    data=bundle,
                    file_name=f"{self.safe_slug(blog_title)}_bundle.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

    def _render_images_tab_content(self, out):
        """Render complete images tab."""
        st.subheader("Images")
        specs = out.get("image_specs") or []
        images_dir = Path("images")

        if not specs:
            st.info("ℹ️ No images were planned for this blog post.")
            st.caption("The AI determined that images weren't necessary for this topic.")
        else:
            # Show image plan
            st.write(f"**Image Plan:** {len(specs)} image(s)")
            
            with st.expander("View image specifications", expanded=False):
                for i, spec in enumerate(specs, 1):
                    st.markdown(f"**Image {i}:**")
                    st.json(spec)
            
            # Show generated images
            st.divider()
            st.subheader("Generated Images")
            
            if images_dir.exists():
                files = [p for p in images_dir.iterdir() if p.is_file()]
                if not files:
                    st.warning("📂 `images/` folder exists but is empty.")
                    st.caption("Images may still be generating, or generation failed. Check the Logs tab for details.")
                else:
                    st.success(f"✓ {len(files)} image(s) generated successfully!")
                    
                    for p in sorted(files):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            # Display image with proper path handling
                            try:
                                st.image(str(p), caption=p.name, use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to display {p.name}: {e}")
                        with col2:
                            st.metric("Filename", p.name)
                            st.metric("Size", f"{p.stat().st_size // 1024} KB")

                    # Download button for images
                    z = self.images_zip(images_dir)
                    if z:
                        st.download_button(
                            "⬇️ Download All Images (zip)",
                            data=z,
                            file_name="images.zip",
                            mime="application/zip",
                            use_container_width=True,
                        )
            else:
                st.warning("📂 `images/` folder not found.")
                st.caption("Images will be created here when generated.")


def main():
    """Main entry point."""
    ui = BlogWriterUI()
    ui.run()


if __name__ == "__main__":
    main()
