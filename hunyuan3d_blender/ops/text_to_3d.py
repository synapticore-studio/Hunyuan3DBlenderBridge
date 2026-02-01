import bpy
from bpy.types import Operator, Image
from bpy.props import StringProperty, IntProperty, BoolProperty, PointerProperty, FloatProperty
from collections import deque
from ..api.h3d import generate_3d_model, get_creation_details
from ..utils import TimerManager
from ..data import H3D_Data
from ..data.scn import GenerationDetails
from ..utils.ui import ui_tag_redraw


# Constants
DEFAULT_IMAGE_PROMPT = "high quality 3D model"


currently_processing_count = 0
generation_queue = deque()
timer_id = "generation_timer"
running_generations: dict[str, GenerationDetails] = {}


def get_all_running_generations() -> dict[str, GenerationDetails]:
    global running_generations
    return running_generations

def get_queue_count() -> int:
    global generation_queue
    return len(generation_queue)

def get_currently_processing_count() -> int:
    global currently_processing_count
    return currently_processing_count


def generation_timer():
    global currently_processing_count, generation_queue, running_generations
    if currently_processing_count < 3:
        if len(generation_queue) > 0:
            data = generation_queue.popleft()
            if creation_id := generate_3d_model(**data):
                currently_processing_count -= 1
                h3d_scn = H3D_Data.SCN()
                running_generations[creation_id] = h3d_scn.new_generation(creation_id)
            else:
                print("Failed to generate 3D model")
                return 4.0

    if currently_processing_count == 0:
        return None

    # get all generation details
    completed_generations = []
    invalid_generations = []
    for creation_id, generation in running_generations.items():
        creation_details = get_creation_details(creation_id)
        if creation_details is None:
            continue
        generation.load_from_response(creation_details)
        if generation.status == "success":
            completed_generations.append(creation_id)
            currently_processing_count -= 1
        if generation.status == 'fail':
            invalid_generations.append(creation_id)

    for creation_id in completed_generations:
        running_generations.pop(creation_id)

    for creation_id in invalid_generations:
        running_generations.pop(creation_id)
        h3d_scn = H3D_Data.SCN()
        h3d_scn.remove_generation(creation_id)

    # update UI
    ui_tag_redraw("VIEW_3D", "UI")

    return 4.0


class H3D_OT_TextTo3D(Operator):
    bl_idname = "h3d.text_to_3d"
    bl_label = "Generate 3D"
    bl_description = "Generate 3D model from text or image"

    prompt: StringProperty(name="Prompt", default="")
    style: StringProperty(name="Style", default="")
    count: IntProperty(name="Count", default=4, min=1)
    use_pbr: BoolProperty(name="PBR", default=True)
    image: PointerProperty(type=Image, name="Image")
    remove_background: BoolProperty(name="Remove Background", default=True)
    octree_resolution: IntProperty(name="Octree Resolution", default=256)
    inference_steps: IntProperty(name="Inference Steps", default=5)
    guidance_scale: FloatProperty(name="Guidance Scale", default=5.0)
    face_count: IntProperty(name="Face Count", default=40000)

    def execute(self, context):
        if self.count == 0:
            return {'CANCELLED'}
        
        # Get prompt and sanitize
        prompt: str = self.prompt.strip()
        
        # Validate: need either prompt or image
        if not prompt and not self.image:
            self.report({'ERROR'}, "Please provide either a prompt or an image")
            return {'CANCELLED'}
        
        # If only image is provided (no prompt), use a descriptive default
        if not prompt:
            prompt = DEFAULT_IMAGE_PROMPT
        
        self.add_to_queue({
            "prompt": prompt,
            "title": prompt,
            "style": "" if self.style == 'DEFAULT' else self.style,
            "count": self.count,
            "enable_pbr": self.use_pbr,
            "enable_low_poly": False,
            "image": self.image,
            "remove_background": self.remove_background,
            "octree_resolution": self.octree_resolution,
            "inference_steps": self.inference_steps,
            "guidance_scale": self.guidance_scale,
            "face_count": self.face_count
        })
        return {'FINISHED'}

    def add_to_queue(self, data: dict):
        generation_queue.append(data)
        global timer_id
        if TimerManager.exists(timer_id):
            return
        TimerManager.add(timer_id, generation_timer)
