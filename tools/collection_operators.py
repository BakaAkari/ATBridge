# ATBridge 集合操作符
"""
集合操作符模块

包含集合排序等操作。
"""
import bpy
from bpy.utils import register_class, unregister_class

from ..utils.common import ATOperationError


class CollectionSortOperator(bpy.types.Operator):
    """对选中集合中的子集合按英文字母A-Z排序"""
    bl_idname = "atb.collection_sort"
    bl_label = "Sort Collection"
    bl_description = "Sort child collections alphabetically (A-Z)"
    bl_options = {'REGISTER', 'UNDO'}
    
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to sort",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        try:
            target_collection = None
            
            if self.collection_name:
                target_collection = bpy.data.collections.get(self.collection_name)
            
            if not target_collection:
                if hasattr(context, 'collection') and context.collection:
                    target_collection = context.collection
            
            if not target_collection:
                if hasattr(context, 'id') and context.id and isinstance(context.id, bpy.types.Collection):
                    target_collection = context.id
            
            if not target_collection:
                if context.active_object and context.active_object.users_collection:
                    collections = context.active_object.users_collection
                    if len(collections) >= 1:
                        target_collection = collections[0]
            
            if not target_collection:
                target_collection = context.scene.collection
            
            if not target_collection:
                self.report({'ERROR'}, "无法确定要排序的集合")
                return {'CANCELLED'}
            
            if self._sort_child_collections(target_collection):
                self.report({'INFO'}, f"已对集合 '{target_collection.name}' 的子集合进行排序")
            else:
                self.report({'WARNING'}, f"集合 '{target_collection.name}' 没有需要排序的子集合")
                
            return {'FINISHED'}
            
        except ATOperationError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"排序集合失败: {str(e)}")
            return {'CANCELLED'}
    
    def _sort_child_collections(self, parent_collection):
        """对指定集合的子集合进行排序"""
        if not parent_collection:
            return False
            
        child_collections = list(parent_collection.children)
        
        if len(child_collections) <= 1:
            return False
            
        child_collections.sort(key=lambda x: x.name.lower())
        
        try:
            original_children = list(parent_collection.children)
            
            sorted_names = [c.name for c in child_collections]
            original_names = [c.name for c in original_children]
            
            if sorted_names == original_names:
                return False
            
            for child in original_children:
                parent_collection.children.unlink(child)
            
            for child in child_collections:
                parent_collection.children.link(child)
                
            bpy.context.view_layer.update()
                
            return True
            
        except Exception as e:
            try:
                for child in child_collections:
                    if child.name not in [c.name for c in parent_collection.children]:
                        parent_collection.children.link(child)
            except:
                pass
            raise e


class CollectionContextMenu(bpy.types.Menu):
    """集合右键菜单"""
    bl_idname = "ATB_MT_collection_context_menu"
    bl_label = "Collection Context Menu"

    def draw(self, context):
        layout = self.layout
        layout.separator()
        layout.operator("atb.collection_sort", text="Sort Collection", icon='SORTALPHA')


def collection_context_menu_draw(self, context):
    """在集合右键菜单中添加排序选项"""
    layout = self.layout
    layout.separator()
    
    current_collection = None
    if hasattr(context, 'collection') and context.collection:
        current_collection = context.collection
    elif hasattr(context, 'id') and context.id and isinstance(context.id, bpy.types.Collection):
        current_collection = context.id
    
    op = layout.operator("atb.collection_sort", text="Sort Collection", icon='SORTALPHA')
    if current_collection:
        op.collection_name = current_collection.name


classes = (
    CollectionSortOperator,
    CollectionContextMenu,
)


def register():
    for cls in classes:
        register_class(cls)
    
    bpy.types.OUTLINER_MT_collection.append(collection_context_menu_draw)


def unregister():
    bpy.types.OUTLINER_MT_collection.remove(collection_context_menu_draw)
    
    for cls in reversed(classes):
        unregister_class(cls)
