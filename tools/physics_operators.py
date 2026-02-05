# ATBridge 物理操作符
"""
物理操作符模块

包含刚体物理模拟相关操作。
"""
import bpy
from bpy.utils import register_class, unregister_class
from mathutils import Matrix

from ..config import PhysicsSettings
from ..utils.translation import get_text
from ..utils.common import ATOperationError, validate_object_selection


# 模块级别状态存储（用于在操作符实例间共享数据）
_physics_state = {
    'selected_objects': [],      # 物理模拟的目标对象列表
    'deselected_objects': [],    # 临时取消选择的碰撞体对象
    'fps': 0,
    'frame_start': 0,
    'frame_end': 0,
    'frame_current': 0,
    'world_enabled': True,
    'use_split_impulse': True,
    'world_time_scale': 1.0,
    'solver_iterations': 10,
    'is_running': False,         # 模拟是否运行中
}


def get_atprops(context):
    """安全获取 atprops 属性"""
    wm = context.window_manager
    if not hasattr(wm, 'atb_props'):
        raise AttributeError(
            "WindowManager 缺少 'atb_props' 属性。"
            "请确保插件已正确注册。"
        )
    if wm.atb_props is None:
        raise AttributeError(
            "WindowManager.atb_props 为 None。"
            "请确保插件已正确初始化。"
        )
    return wm.atb_props


def add_shrink_modifier(obj, strength):
    """添加或更新收缩/膨胀修改器"""
    mod_name = "ATB_Physics_Shrink"
    mod = obj.modifiers.get(mod_name)
    if not mod:
        mod = obj.modifiers.new(name=mod_name, type='DISPLACE')
    
    mod.strength = strength
    mod.mid_level = 0.0
    return mod


def remove_shrink_modifier(obj):
    """移除收缩/膨胀修改器"""
    mod_name = "ATB_Physics_Shrink"
    mod = obj.modifiers.get(mod_name)
    if mod:
        obj.modifiers.remove(mod)


def _remove_passive_bodies(context):
    """移除被动刚体（模块级函数）"""
    global _physics_state
    atprops = get_atprops(context)
    active_object = context.active_object

    objects_to_process = []
    if atprops.physics_use_custom_colliders:
        for item in atprops.physics_custom_colliders:
            if item.obj:
                objects_to_process.append(item.obj)
    else:
        objects_to_process = [obj for obj in context.visible_objects if not obj.select_get() and obj.type == "MESH"]

    for obj in objects_to_process:
        try:
            context.view_layer.objects.active = obj
            if obj.rigid_body is not None:
                bpy.ops.rigidbody.object_remove()
        except:
            pass

    context.view_layer.objects.active = active_object


def stop_physics_and_apply(context):
    """
    停止物理模拟并应用结果（模块级函数）
    
    这个函数可以从 modal 的 exit_modal 或 execute 的停止分支调用。
    确保无论通过 ESC 还是按钮点击停止，行为完全一致。
    """
    global _physics_state
    
    # 如果没有在运行，直接返回
    if not _physics_state['is_running']:
        return
    
    atprops = get_atprops(context)
    wm = context.window_manager
    
    # 停止动画播放
    if context.screen.is_animation_playing:
        bpy.ops.screen.animation_play()
    
    # 更新视图层以获取最新的物理位置
    context.view_layer.update()
    
    # 应用物理结果
    active_object = context.active_object
    
    for obj in _physics_state['selected_objects']:
        try:
            if obj and obj.name in bpy.data.objects:
                context.view_layer.objects.active = obj
                
                # 移除收缩修改器
                remove_shrink_modifier(obj)
                
                # 应用视觉变换（将物理模拟位置应用到对象变换）
                bpy.ops.object.visual_transform_apply()
                
                # 移除刚体
                if obj.rigid_body:
                    bpy.ops.rigidbody.object_remove()
        except Exception as e:
            print(f"应用物理到 {obj.name} 失败: {e}")
    
    context.view_layer.objects.active = active_object
    
    # 恢复场景设置
    context.scene.render.fps = _physics_state['fps']
    context.scene.frame_start = _physics_state['frame_start']
    context.scene.frame_end = _physics_state['frame_end']
    context.scene.frame_current = _physics_state['frame_current']
    
    if context.scene.rigidbody_world:
        context.scene.rigidbody_world.enabled = _physics_state['world_enabled']
        context.scene.rigidbody_world.use_split_impulse = _physics_state['use_split_impulse']
        context.scene.rigidbody_world.time_scale = _physics_state['world_time_scale']
        context.scene.rigidbody_world.solver_iterations = _physics_state['solver_iterations']

    # 移除被动刚体
    _remove_passive_bodies(context)

    # 清理所有可见物体的收缩修改器
    for obj in context.visible_objects:
        if obj.type == 'MESH':
            remove_shrink_modifier(obj)

    # 恢复选择
    for obj in _physics_state['deselected_objects']:
        if obj:
            try:
                obj.select_set(True)
            except:
                pass

    wm.progress_end()
    
    # 重置运行状态
    _physics_state['is_running'] = False
    atprops.running_physics_calculation = False
    
    # 清空全局状态
    _physics_state['selected_objects'] = []
    _physics_state['deselected_objects'] = []
    
    bpy.ops.ed.undo_push(message="Calc Physics")


class PhysicsCalculateOperator(bpy.types.Operator):
    """计算物理模拟"""
    bl_idname = "atb.physics_calculate"
    bl_label = "Calculate Physics"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        # 只有在未运行时才允许启动
        global _physics_state
        return not _physics_state['is_running']

    def add_passive_bodies(self, context, add):
        """添加或移除被动刚体"""
        atprops = get_atprops(context)
        active_object = context.active_object

        objects_to_process = []
        if atprops.physics_use_custom_colliders:
            for item in atprops.physics_custom_colliders:
                if item.obj:
                    objects_to_process.append(item.obj)
        else:
            objects_to_process = [obj for obj in context.visible_objects if not obj.select_get() and obj.type == "MESH"]

        for obj in objects_to_process:
            context.view_layer.objects.active = obj
            if add and obj.rigid_body == None:
                bpy.ops.rigidbody.object_add()
                obj.rigid_body.friction = atprops.physics_friction
                obj.rigid_body.use_margin = True
                
                safety_margin = 0.001
                target_margin = atprops.physics_collision_margin
                physics_margin = safety_margin
                displace_strength = target_margin - physics_margin
                
                add_shrink_modifier(obj, displace_strength)
                
                obj.rigid_body.collision_margin = physics_margin
                obj.rigid_body.restitution = atprops.physics_restitution
                obj.rigid_body.type = "PASSIVE"
                obj.rigid_body.collision_shape = atprops.physics_collision_shape
            elif not add and obj.rigid_body != None:
                bpy.ops.rigidbody.object_remove()

        context.view_layer.objects.active = active_object

    def invoke(self, context, event):
        global _physics_state
        try:
            selected_objects = validate_object_selection(context, min_count=1, obj_type='MESH')
            
            # 保存选中对象引用到全局状态（供停止时使用）
            _physics_state['selected_objects'] = list(selected_objects)
            _physics_state['is_running'] = True

            wm = context.window_manager
            atprops = get_atprops(context)
            wm.modal_handler_add(self)
            atprops.running_physics_calculation = True
            
            _physics_state['deselected_objects'] = []
            if atprops.physics_use_custom_colliders:
                for item in atprops.physics_custom_colliders:
                    if item.obj and item.obj.select_get():
                        item.obj.select_set(False)
                        _physics_state['deselected_objects'].append(item.obj)

            if context.scene.rigidbody_world == None:
                bpy.ops.rigidbody.world_add()

            scene = context.scene
            _physics_state['fps'] = scene.render.fps
            _physics_state['frame_start'] = scene.frame_start
            _physics_state['frame_end'] = scene.frame_end
            _physics_state['frame_current'] = scene.frame_current
            _physics_state['world_enabled'] = scene.rigidbody_world.enabled
            _physics_state['use_split_impulse'] = scene.rigidbody_world.use_split_impulse
            _physics_state['world_time_scale'] = scene.rigidbody_world.time_scale
            _physics_state['solver_iterations'] = scene.rigidbody_world.solver_iterations

            scene.rigidbody_world.time_scale = atprops.physics_time_scale
            scene.render.fps = PhysicsSettings.DEFAULT_FPS
            scene.frame_start = 0
            scene.frame_end = PhysicsSettings.MAX_SIMULATION_FRAMES
            scene.frame_current = 0
            scene.rigidbody_world.enabled = True
            scene.rigidbody_world.use_split_impulse = atprops.physics_split_impulse
            scene.rigidbody_world.solver_iterations = max(1, int(atprops.physics_solver_iterations))

            self.add_passive_bodies(context, True)
            bpy.ops.atb.physics_add_active()
            bpy.ops.screen.animation_play()

            tot = scene.frame_end
            wm.progress_begin(0, tot)
            
            self.report({'INFO'}, f"开始物理模拟 ({len(selected_objects)} 个对象)")
            return {"RUNNING_MODAL"}
            
        except ATOperationError as e:
            self.report({'ERROR'}, str(e))
            return {"CANCELLED"}
        except Exception as e:
            self.report({'ERROR'}, f"启动物理模拟失败: {str(e)}")
            return {"CANCELLED"}

    def modal(self, context, event):
        """模态操作循环"""
        global _physics_state
        wm = context.window_manager
        
        # 检查退出条件：ESC键、达到最大帧数、或已经被停止（通过按钮点击）
        if event.type in {"ESC"} or context.scene.frame_current >= PhysicsSettings.MAX_SIMULATION_FRAMES:
            # ESC 或帧数达到限制，直接调用停止并应用
            stop_physics_and_apply(context)
            return {"FINISHED"}
        
        # 检查是否已经被停止（通过按钮点击 execute 调用 stop_physics_and_apply）
        if not _physics_state['is_running']:
            # 已经被停止，直接退出
            return {"FINISHED"}
        
        wm.progress_update(context.scene.frame_current)
        return {"PASS_THROUGH"}


class PhysicsAddActiveOperator(bpy.types.Operator):
    """为选中对象添加主动物理属性"""
    bl_idname = "atb.physics_add_active"
    bl_label = "Add physics to Assets"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            selected_objects = validate_object_selection(context, min_count=1, obj_type='MESH')
            
            atprops = get_atprops(context)
            active_object = context.active_object
            processed_count = 0
            failed_objects = []
            
            for obj in selected_objects:
                try:
                    context.view_layer.objects.active = obj
                    bpy.ops.rigidbody.object_add()
                    obj.rigid_body.friction = atprops.physics_friction
                    obj.rigid_body.use_margin = True
                    
                    safety_margin = 0.001
                    target_margin = atprops.physics_collision_margin
                    physics_margin = safety_margin
                    displace_strength = target_margin - physics_margin
                    
                    add_shrink_modifier(obj, displace_strength)
                    obj.rigid_body.collision_margin = physics_margin
                    obj.rigid_body.restitution = atprops.physics_restitution
                    obj.rigid_body.collision_shape = atprops.physics_collision_shape
                    processed_count += 1
                except Exception as e:
                    failed_objects.append(f"{obj.name}: {str(e)}")
            
            context.view_layer.objects.active = active_object
            
            if processed_count > 0:
                self.report({'INFO'}, f"成功为 {processed_count} 个对象添加物理属性")
            
            if failed_objects:
                error_msg = "添加物理属性失败的对象:\n" + "\n".join(failed_objects[:3])
                if len(failed_objects) > 3:
                    error_msg += f"\n... 还有 {len(failed_objects) - 3} 个对象失败"
                self.report({'WARNING'}, error_msg)

            return {'FINISHED'}
            
        except ATOperationError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"添加物理属性失败: {str(e)}")
            return {'CANCELLED'}


class PhysicsApplyOperator(bpy.types.Operator):
    """应用物理模拟结果"""
    bl_idname = "atb.physics_apply"
    bl_label = "Apply physics to Assets"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            selected_objects = validate_object_selection(context, min_count=1, obj_type='MESH')
            
            active_object = context.active_object
            obj_transformation = []
            processed_count = 0
            failed_objects = []
            
            context.view_layer.update()

            for obj in selected_objects:
                obj_transformation.append({
                    "obj": obj, 
                    "matrix_world": Matrix(obj.matrix_world)
                })

            for data in obj_transformation:
                try:
                    obj = bpy.data.objects[data["obj"].name]
                    context.view_layer.objects.active = obj
                    
                    remove_shrink_modifier(obj)
                    bpy.ops.object.visual_transform_apply()
                    
                    if obj.rigid_body:
                        bpy.ops.rigidbody.object_remove()
                    
                    obj.matrix_world = data["matrix_world"]
                    processed_count += 1
                    
                except Exception as e:
                    failed_objects.append(f"{data['obj'].name}: {str(e)}")

            context.view_layer.objects.active = active_object
            
            if processed_count > 0:
                self.report({'INFO'}, f"成功应用物理到 {processed_count} 个对象")
            
            if failed_objects:
                error_msg = "应用物理失败的对象:\n" + "\n".join(failed_objects[:3])
                if len(failed_objects) > 3:
                    error_msg += f"\n... 还有 {len(failed_objects) - 3} 个对象失败"
                self.report({'WARNING'}, error_msg)

            return {'FINISHED'}
            
        except ATOperationError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"应用物理失败: {str(e)}")
            return {'CANCELLED'}


class PhysicsGetCustomCollidersOperator(bpy.types.Operator):
    """将选中的Mesh对象添加到自定义碰撞体列表"""
    bl_idname = "atb.physics_get_custom_colliders"
    bl_label = "Get Selected Colliders"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects
        
    def execute(self, context):
        atprops = get_atprops(context)
        added_count = 0
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                exists = False
                for item in atprops.physics_custom_colliders:
                    if item.obj == obj:
                        exists = True
                        break
                
                if not exists:
                    item = atprops.physics_custom_colliders.add()
                    item.obj = obj
                    added_count += 1
        
        if added_count > 0:
            self.report({'INFO'}, f"Added {added_count} objects to colliders list")
        else:
            self.report({'WARNING'}, "No new mesh objects added")
            
        return {'FINISHED'}


class PhysicsClearCustomCollidersOperator(bpy.types.Operator):
    """清空自定义碰撞体列表"""
    bl_idname = "atb.physics_clear_custom_colliders"
    bl_label = "Clear Colliders"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        atprops = get_atprops(context)
        atprops.physics_custom_colliders.clear()
        self.report({'INFO'}, "Colliders list cleared")
        return {'FINISHED'}


class PhysicsRemoveCustomColliderOperator(bpy.types.Operator):
    """移除选中的自定义碰撞体"""
    bl_idname = "atb.physics_remove_custom_collider"
    bl_label = "Remove Collider"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        try:
            atprops = get_atprops(context)
            return len(atprops.physics_custom_colliders) > 0
        except:
            return False
    
    def execute(self, context):
        atprops = get_atprops(context)
        index = atprops.physics_custom_collider_index
        
        if 0 <= index < len(atprops.physics_custom_colliders):
            atprops.physics_custom_colliders.remove(index)
            if index >= len(atprops.physics_custom_colliders):
                atprops.physics_custom_collider_index = len(atprops.physics_custom_colliders) - 1
                
        return {'FINISHED'}


classes = (
    PhysicsCalculateOperator,
    PhysicsAddActiveOperator,
    PhysicsApplyOperator,
    PhysicsGetCustomCollidersOperator,
    PhysicsClearCustomCollidersOperator,
    PhysicsRemoveCustomColliderOperator,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
