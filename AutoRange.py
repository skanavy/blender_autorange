import math

import bpy

from bpy.props import BoolProperty
from bpy.props import EnumProperty
from bpy.utils import register_class, unregister_class
from bpy.app.handlers import persistent

bl_info = {
    "name": "AutoRange",
    "author": "Demian Karpunov",
    "version": (0, 3),
    "blender": (3, 1, 2),
    "location": "Timeline -> Use AutoRange",
    "description": "Automatically set frame range by active object animation",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Scene",
    "support": "TESTING"
}

""" LOCALS """

RANGE_UPDATE = False  # Prevents looping


class AutoRange(bpy.types.Operator):
    """Automatically set frame range with active object animation"""
    bl_idname = "scene.auto_range"
    bl_label = "Auto Range"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Define scene and properties
        scene = context.scene

        if scene.autorange_type == 'SCENE':
            l = full_range()
            scene.frame_start = l[0]
            scene.frame_end = l[-1]
            return {"FINISHED"}

        obj = context.active_object
        if scene.autorange_type == 'CAM':
            obj = scene.camera
            if not obj:
                self.report({"WARNING"}, "Active scene camera required")
                return {"FINISHED"}

        if not obj:
            self.report({"WARNING"}, "Active object required")
            return {"FINISHED"}

        anim_data = obj.animation_data
        if not anim_data or not anim_data.action:
            self.report({"WARNING"}, "Animation required")
            return {"FINISHED"}

        # Find action range
        action = anim_data.action
        start, end = action.frame_range

        self.report({"DEBUG"}, f"Frame range: {start}-{end}")
        start, end = round(start), round(end)

        if (end - start) <= 1:
            keyframes = get_keyframes(obj)
            start, end = keyframes[0], keyframes[-1]
            self.report({"DEBUG"}, f"Frame range actually one {start}-{end} frame")

        # Set frame range
        if not all([scene.frame_start == start, scene.frame_end == end]):
            self.report({"INFO"}, f"Set frame range {start}-{end}")
            scene.frame_start = start
            scene.frame_end = end
        return {"FINISHED"}


class AutoRangePanel(bpy.types.Panel):
    bl_label = "AutoRange"
    bl_idname = "TIME_PT_AutoRange"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "HEADER"
    bl_ui_units_x = 8

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.active = scene.autorange_enabled

        col = layout.column(heading="AutoRange by animation from")
        col.prop(scene, "autorange_type", text="Type", icon="OBJECT_DATA")


def full_range():
    if bpy.data.actions:
        action_list = []
        for action in bpy.data.actions:
            action_list.append(action.frame_range)

        keys = []
        for sublist in action_list:
            for item in sublist:
                keys.append(item)
        keys = sorted(set(keys))

        return keys


def get_keyframes(obj: bpy.types.Object):
    keyframes = []
    anim_data = obj.animation_data
    if not anim_data or not anim_data.action:
        return keyframes

    for fcu in anim_data.action.fcurves:
        for keyframe in fcu.keyframe_points:
            x, y = keyframe.co
            if x not in keyframes:
                keyframes.append((math.ceil(x)))
    return keyframes


def update_frame_range(scene: bpy.types.Scene):
    if not scene.autorange_enabled:
        return

    bpy.ops.scene.auto_range("EXEC_DEFAULT")


@persistent
def update_frame_range_handler(scene: bpy.types.Scene):
    global RANGE_UPDATE
    if RANGE_UPDATE:
        return

    RANGE_UPDATE = True
    update_frame_range(scene)
    RANGE_UPDATE = False


def draw_autorange_feature(self, context: bpy.types.Context):
    scene = context.scene
    layout = self.layout

    layout.separator()

    row = layout.row(align=True)
    row.prop(scene, "autorange_enabled", text="AutoRange", toggle=True, icon="PREVIEW_RANGE")
    sub = row.row(align=True)
    sub.active = scene.autorange_enabled
    sub.popover(
        panel="TIME_PT_AutoRange",
        text=""
    )


def item_callback(self, context):
    return (
        ('OB', 'Object', "", "OBJECT_DATA", 0),
        ('CAM', 'Camera', "", "VIEW_CAMERA", 0),
        ('SCENE', 'Scene', "", "SCENE_DATA", 0),
    )


""" REGISTER """


def register():
    bpy.types.Scene.autorange_enabled = BoolProperty(
        name="Activate AutoRange",
        description="AutoRange frames",
        default=False
    )

    bpy.types.Scene.autorange_type = EnumProperty(
        items=item_callback,
        name="AutoRange type",
        description="choose type",
        default=None,
        options={'ANIMATABLE'},
        update=None,
        get=None,
        set=None
    )

    register_class(AutoRange)
    register_class(AutoRangePanel)

    bpy.app.handlers.depsgraph_update_pre.append(update_frame_range_handler)

    bpy.types.TIME_MT_editor_menus.append(draw_autorange_feature)


def unregister():
    bpy.types.TIME_MT_editor_menus.remove(draw_autorange_feature)

    if update_frame_range_handler in bpy.app.handlers.depsgraph_update_pre:
        bpy.app.handlers.depsgraph_update_pre.remove(update_frame_range_handler)

    unregister_class(AutoRangePanel)
    unregister_class(AutoRange)

    del bpy.types.Scene.autorange_acamera_enabled
    del bpy.types.Scene.autorange_enabled


if __name__ == "__main__":
    register()
