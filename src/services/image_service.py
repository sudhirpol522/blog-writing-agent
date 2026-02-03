"""Image generation service using Google Gemini."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ..models.schemas import ImageSpec


class ImageService:
    """Service for generating images using Gemini."""

    def __init__(self, output_dir: Path = Path("images")):
        """Initialize image service.

        Args:
            output_dir: Directory to save generated images
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def generate_image(self, prompt: str) -> bytes:
        """Generate image bytes from prompt using Gemini.

        Args:
            prompt: Text prompt for image generation

        Returns:
            Raw image bytes

        Raises:
            RuntimeError: If GOOGLE_API_KEY is not set or generation fails
        """
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set.")

        client = genai.Client(api_key=api_key)

        # Use Imagen 3 for image generation (correct model name)
        resp = client.models.generate_image(
            model="imagen-3.0-generate-001",
            prompt=prompt,
            config=types.GenerateImageConfig(
                number_of_images=1,
                safety_filter_level="block_only_high",
                person_generation="allow_adult",
            ),
        )

        # Extract image bytes from Imagen 3 response
        if hasattr(resp, 'generated_images') and resp.generated_images:
            # Get the first generated image
            image = resp.generated_images[0]
            if hasattr(image, 'image') and hasattr(image.image, 'image_bytes'):
                return image.image.image_bytes
            elif hasattr(image, 'image_bytes'):
                return image.image_bytes
        
        # Fallback: try the old response format
        parts = getattr(resp, "parts", None)
        if not parts and getattr(resp, "candidates", None):
            try:
                parts = resp.candidates[0].content.parts
            except Exception:
                parts = None

        if parts:
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    return inline.data

        raise RuntimeError("No image content returned. Check API quota and model availability.")

    def generate_and_save(self, spec: ImageSpec) -> Path:
        """Generate and save image from specification.

        Args:
            spec: Image specification

        Returns:
            Path to saved image

        Raises:
            RuntimeError: If generation fails
        """
        out_path = self.output_dir / spec.filename

        # Skip if already exists
        if out_path.exists():
            return out_path

        img_bytes = self.generate_image(spec.prompt)
        out_path.write_bytes(img_bytes)
        return out_path

    def process_image_specs(
        self,
        markdown: str,
        image_specs: List[ImageSpec],
    ) -> str:
        """Generate images and replace placeholders in markdown.

        Args:
            markdown: Markdown text with placeholders
            image_specs: List of image specifications

        Returns:
            Markdown with image references
        """
        md = markdown
        
        print(f"📸 Processing {len(image_specs)} image(s)...")

        for idx, spec in enumerate(image_specs, 1):
            placeholder = spec.placeholder
            filename = spec.filename
            out_path = self.output_dir / filename

            try:
                print(f"   Generating image {idx}/{len(image_specs)}: {filename}")
                self.generate_and_save(spec)
                print(f"   ✓ Image saved: {out_path}")
                
                img_md = f"![{spec.alt}](images/{filename})\n*{spec.caption}*"
                md = md.replace(placeholder, img_md)
                
            except Exception as e:
                print(f"   ✗ Image generation failed: {e}")
                # Graceful fallback
                prompt_block = (
                    f"> **[IMAGE GENERATION FAILED]** {spec.caption}\n>\n"
                    f"> **Alt:** {spec.alt}\n>\n"
                    f"> **Prompt:** {spec.prompt}\n>\n"
                    f"> **Error:** {e}\n"
                )
                md = md.replace(placeholder, prompt_block)

        return md
