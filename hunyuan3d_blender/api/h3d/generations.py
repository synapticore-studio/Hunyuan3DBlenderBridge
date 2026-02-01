import requests
import uuid
import base64
import io
from bpy.types import Image

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None
    print("⚠️  Warning: Pillow (PIL) not available. Image-to-3D functionality will not work.")

from ..session import get_session

def generate_3d_model(
    prompt: str, 
    title: str, 
    style: str = "", 
    count: int = 4, 
    enable_pbr: bool = True, 
    enable_low_poly: bool = False, 
    image: Image = None,
    remove_background: bool = True,
    octree_resolution: int = 256,
    inference_steps: int = 5,
    guidance_scale: float = 5.0,
    face_count: int = 40000
) -> str | None:
    """Sends a request to the Hunyuan 3D API to generate a 3D model based on a text prompt or image.

        Arguments:
            prompt: str - The prompt to generate the 3D model from.
            title: str - The title of the generation (usually the prompt).
            style: str - The style to use for the 3D model. (e.g. "china_style") Use "" for default.
            count: int - The number of 3D models to generate.
            enable_pbr: bool - Whether to enable PBR for the 3D model.
            enable_low_poly: bool - Whether to enable low poly for the 3D model.
            image: Image - Optional image for image-to-3D generation.
            remove_background: bool - Whether to remove background from input image.
            octree_resolution: int - Resolution of the generated mesh (256, 384, or 512).
            inference_steps: int - Number of inference steps (5-50).
            guidance_scale: float - Guidance scale for generation (1.0-15.0).
            face_count: int - Maximum number of faces for texture generation.
    """

    session = get_session()

    url = "https://3d.hunyuan.tencent.com/api/3d/creations/generations"

    payload = {
        "prompt": prompt,
        "title": title,  # usually the prompt
        "style": style,  # "china_style", ...
        "sceneType": "playGround3D-2.0",
        "modelType": "modelCreationV2.5",
        "count": count,
        "enable_pbr": enable_pbr,
        "enableLowPoly": enable_low_poly,
        "remove_background": remove_background,
        "octree_resolution": octree_resolution,
        "num_inference_steps": inference_steps,
        "guidance_scale": guidance_scale,
        "face_count": face_count
    }
    
    # Add image data if provided (for image-to-3D)
    if image is not None:
        if PILImage is None:
            print("❌ Error: Pillow (PIL) is required for image-to-3D generation")
            return None
            
        try:
            # Get image pixels as bytes
            width, height = image.size
            pixels = list(image.pixels)
            
            # Convert float pixels (0.0-1.0) to bytes (0-255)
            pixel_bytes = bytearray()
            for i in range(0, len(pixels), 4):
                r = int(pixels[i] * 255)
                g = int(pixels[i+1] * 255)
                b = int(pixels[i+2] * 255)
                a = int(pixels[i+3] * 255)
                pixel_bytes.extend([r, g, b, a])
            
            # Create PIL Image (requires Pillow from wheels)
            pil_image = PILImage.frombytes('RGBA', (width, height), bytes(pixel_bytes))
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            payload["image"] = f"data:image/png;base64,{img_base64}"
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            return None

    trace_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "x-product": "hunyuan3d",
        "x-source": "web",
        "trace-id": trace_id,
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "Origin": "https://3d.hunyuan.tencent.com",
        "Referer": "https://3d.hunyuan.tencent.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # Note: content-length header is auto-calculated by requests library
    }

    try:
        response = session.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        details = response.json()
        print(details)
        return details["creationsId"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during 3D model generation request: {e}")
        return None
