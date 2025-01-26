import bpy
import numpy as np
import os
import subprocess
import importlib

def messagebox(message="", title="WARNING", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)

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

def convert_blender_image_to_pil(tex_node):
    try:
        from PIL import Image
    except:
        # 如果导入失败，打印错误信息并跳过导入
        messagebox(message="PIL library not installed. Install it on the plugin settings page", title="WARNING", icon='INFO')
        pass

    blender_image = tex_node.image
    width, height = blender_image.size
    pixels = np.array(blender_image.pixels).reshape(height, width, 4)
    pil_image = Image.fromarray((pixels * 255).astype(np.uint8))
    return pil_image

def OpenSysDir(NewORMTexPath):
    print(NewORMTexPath)
    if os.name == 'nt':  # Windows
        subprocess.run(['explorer', os.path.dirname(NewORMTexPath)])
    elif os.name == 'posix':  # Linux or macOS
        subprocess.run(['xdg-open', os.path.dirname(NewORMTexPath)])
#===========================================================================================================
# Bridge流程
#===========================================================================================================
def BridgeSavePILImage(blend_file_directory, BID, TexNode, pil_image):
    NewTexPath = os.path.join(blend_file_directory, "Merge Tex", BID, TexNode.image.name)
    os.path.exists(os.path.dirname(NewTexPath)) or os.makedirs(os.path.dirname(NewTexPath))
    pil_image.save(NewTexPath) 
    pass
    
def BridgePILMergeCol(BID, ColNodeList):
    try:
        from PIL import Image
    except:
        # 如果导入失败，打印错误信息并跳过导入
        messagebox(message="PIL library not installed. Install it on the plugin settings page", title="WARNING", icon='INFO')
        pass

    for colnode in ColNodeList:
        if colnode.name == "Color Tex Node":
            ColTex = Image.open(colnode.image.filepath)
            TexName = colnode.image.name
        elif colnode.name == "Opacity Tex Node":
            OpacityTex = Image.open(colnode.image.filepath)
            
    if len(ColNodeList) > 1:
        NewColTex = Image.merge("RGBA", (ColTex.split()[0], ColTex.split()[1], ColTex.split()[2], OpacityTex.split()[0]))
    else:
        NewColTex = Image.merge("RGB", (ColTex.split()[0], ColTex.split()[1], ColTex.split()[2]))
    
    blend_file_path = bpy.data.filepath
    if blend_file_path:
        blend_file_directory = os.path.dirname(blend_file_path)
        NewColTexPath = os.path.join(blend_file_directory, "Merge Tex", BID, TexName)
        os.path.exists(os.path.dirname(NewColTexPath)) or os.makedirs(os.path.dirname(NewColTexPath))
        NewColTex.save(NewColTexPath)
        # print(NewColTexPath)
    else:
        messagebox("Please save the file first", "Warning", "ERROR")
    
def BridgePILMergeORM(BID, ORMNodeList):
    AOTex = None
    RoughnessTex = None
    MetalnessTex = None
    try:
        from PIL import Image
    except:
        # 如果导入失败，打印错误信息并跳过导入
        messagebox(message="PIL library not installed. Install it on the plugin settings page", title="WARNING", icon='INFO')
        pass

    for ORMNode in ORMNodeList:
        if ORMNode.name == "AO Tex Node":
            AOTex = Image.open(ORMNode.image.filepath)
        if ORMNode.name == "Roughness Tex Node":
            RoughnessTex = Image.open(ORMNode.image.filepath)
            TexName = ORMNode.image.name.replace("Roughness", "ORM")
        if ORMNode.name == "Metalness Tex Node":
            MetalnessTex = Image.open(ORMNode.image.filepath)
            
    if RoughnessTex:
        if AOTex:
            if MetalnessTex:
                NewORMTex = Image.merge("RGB", (AOTex.split()[0], RoughnessTex.split()[0], MetalnessTex.split()[0]))
            else:
                NewORMTex = Image.merge("RGB", (AOTex.split()[0], RoughnessTex.split()[0], Image.new('L', RoughnessTex.size, 0)))
        else:
            NewORMTex = Image.merge("RGB", (Image.new('L', RoughnessTex.size, 256), RoughnessTex.split()[0], Image.new('L', RoughnessTex.size, 0)))
    else:
        pass
            
    blend_file_path = bpy.data.filepath
    if blend_file_path:
        blend_file_directory = os.path.dirname(blend_file_path)
        
        NewORMTexPath = os.path.join(blend_file_directory, "Merge Tex", BID, TexName)
        os.path.exists(os.path.dirname(NewORMTexPath)) or os.makedirs(os.path.dirname(NewORMTexPath))
        NewORMTex.save(NewORMTexPath)
        return NewORMTexPath
    else:
        messagebox("Please save the file first", "Warning", "ERROR")

def OrganizeImages(BID, NrmNodeList, DisNodeList):
    blend_file_path = bpy.data.filepath
    blend_file_directory = os.path.dirname(blend_file_path)
    
    if blend_file_path:
        for NrmNode in NrmNodeList:
            if NrmNode.name == "Normal Tex Node":
                NrmTex = convert_blender_image_to_pil(NrmNode)
                BridgeSavePILImage(blend_file_directory, BID, NrmNode, NrmTex)
        
        # for DisNode in DisNodeList:
        #     if DisNode.name == "Displacement Tex Node":
        #         DisTex = convert_blender_image_to_pil(DisNode)
        #         save_pil_image(blend_file_directory, BID, DisNode, DisTex)
#===========================================================================================================
# 手动流程
#===========================================================================================================
def ManualPILMergeCol(ManualColNodeList):
    wm = bpy.context.window_manager
    blend_file_path = bpy.data.filepath
    blend_file_directory = os.path.dirname(blend_file_path)
    try:
        from PIL import Image
    except:
        # 如果导入失败，打印错误信息并跳过导入
        messagebox(message="PIL library not installed. Install it on the plugin settings page", title="WARNING", icon='INFO')
        pass

    if len(ManualColNodeList) > 1:
        for colnode in ManualColNodeList:
            if colnode.image.name == wm.atbprops.col_tex_name:
                if os.path.isabs(colnode.image.filepath):
                    ColTex = Image.open(blend_file_directory + os.path.abspath(colnode.image.filepath))
                else:
                    ColTex = Image.open(os.path.abspath(colnode.image.filepath))
            elif colnode.name == wm.atbprops.opa_tex_name:
                if os.path.isabs(colnode.image.filepath):
                    OpaTex = Image.open(blend_file_directory + os.path.abspath(colnode.image.filepath))
                    print(colnode)
                else:
                    OpaTex = Image.open(os.path.abspath(colnode.image.filepath))
                    print(colnode)
                    
            # print(ColTex)
            # print(OpaTex)
        
    # elif len(ManualColNodeList) == 1:
    #     colnode = ManualColNodeList[0]
    #     if os.path.isabs(colnode.image.filepath):
    #         ColTex = Image.open(blend_file_directory + os.path.abspath(colnode.image.filepath))
    #         OpaTex = Image.new('L', ColTex.size, 256)
    #     else:
    #         ColTex = Image.open(colnode.image.filepath)
    #         OpaTex = Image.new('L', ColTex.size, 256)
    #         print(OpaTex)
        
        return
            
    # if len(ColNodeList) > 1:
    #     NewColTex = Image.merge("RGBA", (ColTex.split()[0], ColTex.split()[1], ColTex.split()[2], OpacityTex.split()[0]))
    # else:
    #     NewColTex = Image.merge("RGB", (ColTex.split()[0], ColTex.split()[1], ColTex.split()[2]))
    
    # blend_file_path = bpy.data.filepath
    # if blend_file_path:
    #     blend_file_directory = os.path.dirname(blend_file_path)
    #     NewColTexPath = os.path.join(blend_file_directory, "Merge Tex", BID, TexName)
    #     os.path.exists(os.path.dirname(NewColTexPath)) or os.makedirs(os.path.dirname(NewColTexPath))
    #     NewColTex.save(NewColTexPath)
    #     # print(NewColTexPath)
    # else:
    #     messagebox("Please save the file first", "Warning", "ERROR")
