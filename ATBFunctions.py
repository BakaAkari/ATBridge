import bpy
import numpy as np
# from PIL import Image


def messagebox(text="", title="WARNING", icon='ERROR'):
    def draw(self):
        self.layout.label(text=text)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def translationui(self, context):
    layout = self.layout
    # row = layout.row(align=True)
    if context.preferences.view.language == "en_US":
        buttonname = "Switch CH"
    else:
        buttonname = "切换英文"
    layout.operator(operator="object.translation", text=buttonname)
    # layout.operator(operator="object.translationoperation")

    # return super().draw(context)


def stop_playback(scene):
    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=False)
    print("Stop Loop")


def start_playback(scene):
    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=True)
    print("Start Loop")


def setframe(self, context):
    try:
        layout = self.layout
        layout.operator("object.setstartframe", text=r"Start", emboss=True, depress=False, icon_value=0)
        layout.operator("object.setendframe", text=r"End", emboss=True, depress=False, icon_value=0)
        layout.operator("object.stoploop", text=r"Set Loop", emboss=True, depress=False, icon_value=0)

    except Exception as exc:
        print(str(exc) + " | Error in Dopesheet Ht Header when adding to menu")


# def load_image_as_numpy_array(filepath):
#     # Load the image using PIL
#     img = Image.open(filepath).convert('L')  # Convert to grayscale
#     return np.array(img)


# def save_numpy_array_as_image(array, filepath):
#     # Convert the NumPy array back to an image and save it
#     img = Image.fromarray(array)
#     img.save(filepath)


# def merge_images(image_a_path, image_b_path):
#     # Load images as numpy arrays
#     image_a = load_image_as_numpy_array(image_a_path)
#     image_b = load_image_as_numpy_array(image_b_path)

#     # Check if the images have the same dimensions
#     if image_a.shape != image_b.shape:
#         raise ValueError("Image dimensions do not match.")

#     # Create an empty array for the merged image
#     merged_image = np.zeros((image_a.shape[0], image_a.shape[1], 3), dtype=np.uint8)

#     # Assign the R channel to image A and the G channel to image B
#     merged_image[..., 0] = image_a  # Red channel
#     merged_image[..., 1] = image_b  # Green channel
#     # Blue channel remains zero
