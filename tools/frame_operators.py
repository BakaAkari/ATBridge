# ATBridge 帧控制操作符
"""
帧控制操作符模块

包含帧设置和语言切换操作。
"""
import bpy
from bpy.utils import register_class, unregister_class


def stop_playback(scene):
    """停止播放回调"""
    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=False)
    print("Stop Loop")


def start_playback(scene):
    """开始播放回调"""
    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=True)
    print("Start Loop")


class FrameStartOperator(bpy.types.Operator):
    """设置开始帧"""
    bl_idname = "atb.frame_set_start"
    bl_label = "SetStartFrame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        try:
            actscene = bpy.context.scene
            bpy.data.scenes[actscene.name].frame_start = bpy.data.scenes[actscene.name].frame_current
            self.report({'INFO'}, f"开始帧设为 {actscene.frame_current}")
        except Exception as exc:
            print(str(exc) + " | Error in execute function of SetStartFrame")
        return {"FINISHED"}


class FrameEndOperator(bpy.types.Operator):
    """设置结束帧"""
    bl_idname = "atb.frame_set_end"
    bl_label = "SetEndFrame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        try:
            actscene = bpy.context.scene
            bpy.data.scenes[actscene.name].frame_end = bpy.data.scenes[actscene.name].frame_current
            self.report({'INFO'}, f"结束帧设为 {actscene.frame_current}")
        except Exception as exc:
            print(str(exc) + " | Error in execute function of SetEndFrame")
        return {"FINISHED"}


class FrameLoopOperator(bpy.types.Operator):
    """设置循环播放"""
    bl_idname = "atb.frame_toggle_loop"
    bl_label = "StopLoop"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        frame_change = bpy.app.handlers.frame_change_pre
        actscene = bpy.context.scene

        if stop_playback not in frame_change:
            stop_playback(bpy.data.scenes[actscene.name])
            frame_change.append(stop_playback)
            self.report({'INFO'}, "循环播放已禁用")
        elif stop_playback in frame_change:
            start_playback(bpy.data.scenes[actscene.name])
            del frame_change[-1]
            self.report({'INFO'}, "循环播放已启用")

        print(list(frame_change))
        return {'FINISHED'}


class LanguageToggleOperator(bpy.types.Operator):
    """切换语言"""
    bl_idname = "atb.ui_toggle_language"
    bl_label = "Toggle Language"
    bl_description = "Toggle between Chinese and English"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            viewlanguage = context.preferences.view.language
            prefview = context.preferences.view
            
            if viewlanguage == "en_US":
                current_lang = "English"
                target_lang = "中文"
                try:
                    context.preferences.view.language = "zh_CN"
                except:
                    try:
                        context.preferences.view.language = "zh_HANS"
                    except:
                        context.preferences.view.language = "zh_TW"
                prefview.use_translate_new_dataname = False
            else:
                current_lang = "中文"
                target_lang = "English"
                context.preferences.view.language = "en_US"
            
            print(f"ATBridge语言切换: {current_lang} → {target_lang}")
            self.report({'INFO'}, f"Language switched: {current_lang} → {target_lang}")
            
            for area in context.screen.areas:
                area.tag_redraw()
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch language: {str(e)}")
            print(f"ATBridge: Error in language toggle: {e}")
            return {'CANCELLED'}


classes = (
    FrameStartOperator,
    FrameEndOperator,
    FrameLoopOperator,
    LanguageToggleOperator,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
