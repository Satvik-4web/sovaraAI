"""
PowerPoint (.pptx) Presentation Generator module.
Generates structured presentations with title slides, bullet point slides, and content cards.
Supports python-pptx with clean fallback formatting.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.file_ops.path_security import validate_workspace_path


def generate_pptx(
    filename: str,
    title: str,
    slides: List[Dict[str, Any]],
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a PowerPoint (.pptx) presentation with title slides and bullet point content slides.

    Args:
        filename: Target output filename (e.g., 'presentation.pptx').
        title: Main presentation title.
        slides: List of slide dicts. Each dict can contain 'title', 'subtitle', 'bullet_points', 'content'.
        workspace_root: Optional workspace root directory override.

    Returns:
        Structured ExecutionResult dictionary.
    """
    start_time = time.perf_counter()

    if not filename.endswith(".pptx"):
        filename += ".pptx"

    try:
        validated_path = validate_workspace_path(filename, workspace_root)
    except ValueError as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(code=ErrorCode.PATH_TRAVERSAL_ATTEMPT, message=str(e)),
        ).to_dict()

    validated_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import pptx
        from pptx import Presentation

        prs = Presentation()

        # Add Title Slide
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_box = slide.shapes.title
        subtitle_box = slide.placeholders[1]
        title_box.text = title
        subtitle_box.text = f"SOVARA Automated Executive Briefing ({len(slides)} Slides)"

        # Add Content Slides
        bullet_slide_layout = prs.slide_layouts[1]
        for s_data in slides:
            s = prs.slides.add_slide(bullet_slide_layout)
            shapes = s.shapes
            title_shape = shapes.title
            body_shape = shapes.placeholders[1]

            title_shape.text = str(s_data.get("title", "Untitled Slide"))
            tf = body_shape.text_frame

            if "content" in s_data:
                tf.text = str(s_data["content"])

            if "bullet_points" in s_data and isinstance(s_data["bullet_points"], list):
                for idx, bp in enumerate(s_data["bullet_points"]):
                    if idx == 0 and not s_data.get("content"):
                        tf.text = str(bp)
                    else:
                        p = tf.add_paragraph()
                        p.text = str(bp)
                        p.level = 0

        prs.save(str(validated_path))
        format_used = "native_pptx"

    except ImportError:
        # Fallback formatting if python-pptx is absent
        fallback_lines = [f"# Presentation: {title}\n"]
        for idx, s_data in enumerate(slides, 1):
            fallback_lines.append(f"--- Slide {idx}: {s_data.get('title', 'Untitled')} ---")
            if "subtitle" in s_data:
                fallback_lines.append(f"Subtitle: {s_data['subtitle']}")
            if "content" in s_data:
                fallback_lines.append(f"{s_data['content']}")
            if "bullet_points" in s_data:
                for bp in s_data["bullet_points"]:
                    fallback_lines.append(f"  * {bp}")
            fallback_lines.append("")

        fallback_lines.append("<!-- Note: Install python-pptx via 'pip install python-pptx' for native .pptx binary generation -->\n")

        with open(validated_path, "w", encoding="utf-8") as f:
            f.write("\n".join(fallback_lines))
        format_used = "markdown_fallback"

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.DOCUMENT_GENERATION_ERROR,
                message=f"Failed to generate PowerPoint presentation '{filename}': {str(e)}",
            ),
        ).to_dict()

    exec_time = time.perf_counter() - start_time
    file_size = validated_path.stat().st_size

    return ExecutionResult(
        success=True,
        result={
            "filename": validated_path.name,
            "path": str(validated_path),
            "size_bytes": file_size,
            "slides_count": len(slides) + 1,  # Title slide + content slides
            "format_used": format_used,
        },
        execution_time=exec_time,
    ).to_dict()
