# Image Requirements Update

## Changes Made

Updated the blog writing workflow to ensure at least 2 images are generated for every technical blog.

### Files Modified

1. **src/models/schemas.py**
   - Updated `GlobalImagePlan` schema to require minimum 2 images, maximum 3
   - Added field constraints: `min_length=2, max_length=3`

2. **src/workflow/nodes.py**
   - Updated `DECIDE_IMAGES_SYSTEM` prompt to explicitly require 2-3 images
   - Added clearer instructions for image placement and prompt creation
   - Enhanced `decide_images()` function with validation and logging
   - Added warning if no images are planned

### Key Changes

**Schema Enforcement:**
```python
images: List[ImageSpec] = Field(
    ..., 
    min_length=2,
    max_length=3,
    description="Minimum 2, maximum 3 images required for technical content."
)
```

**Prompt Requirements:**
- MINIMUM 2 images required for technical blogs
- MAXIMUM 3 images total
- Each image must be a technical diagram (architecture, flow, concept)
- Placeholders must be inserted after relevant paragraphs
- Detailed prompts required for each image

**Validation:**
- Function now logs number of planned images
- Warns if no images are created (should not happen)
- Ensures all original content is preserved

## Expected Behavior

Every blog generated will now include:
- Minimum 2 technical diagrams
- Maximum 3 technical diagrams
- Clear image placeholders: [[IMAGE_1]], [[IMAGE_2]], [[IMAGE_3]]
- Descriptive captions for each image

## Testing

Run the application and generate a blog:
```powershell
.\run.ps1
```

Expected output in console:
```
✓ Planned 2 image(s) for the blog
```
or
```
✓ Planned 3 image(s) for the blog
```

Check the generated markdown file in `outputs/` for image placeholders.

## Troubleshooting

If images still not appearing:
1. Check console for image planning logs
2. Verify `IMAGE_PROVIDER` is set in `.env`
3. Check that API keys are valid
4. Review `images/` folder for generated files
