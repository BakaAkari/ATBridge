import bpy

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