"""Image generation service using OpenAI DALL-E."""

from __future__ import annotations

import os
import base64
from pathlib import Path
from typing import List

from openai import OpenAI

from ..models.schemas import ImageSpec


class ImageServiceOpenAI:
    """Service for generating images using OpenAI DALL-E."""

    def __init__(self, output_dir: Path = Path("images")):
        """Initialize image service.

        Args:
            output_dir: Directory to save generated images
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def generate_image(self, prompt: str) -> bytes:
        """Generate image bytes from prompt using DALL-E.

        Args:
            prompt: Text prompt for image generation

        Returns:
            Raw image bytes

        Raises:
            RuntimeError: If generation fails
        """
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            
            # Get base64 encoded image
            b64_image = response.data[0].b64_json
            
            # Decode to bytes
            image_bytes = base64.b64decode(b64_image)
            
            return image_bytes
            
        except Exception as e:
            raise RuntimeError(f"DALL-E image generation failed: {e}")

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
        
        print(f"📸 Processing {len(image_specs)} image(s) with DALL-E...")

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
