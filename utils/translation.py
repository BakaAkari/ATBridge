# ATBridge 翻译系统
import bpy
from typing import Dict, Optional

class ATBridgeTranslationManager:
    """ATBridge翻译管理器"""
    
    def __init__(self):
        self._translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """加载翻译数据"""
        return {
            # 面板标题
            "ATBridge": {"en_US": "ATBridge", "zh": "ATBridge"},
            "Bridge Tools": {"en_US": "Bridge Tools", "zh": "Bridge工具"},
            "Import Tools": {"en_US": "Import Tools", "zh": "导入工具"},
            "Tools": {"en_US": "Tools", "zh": "工具"},
            "Physics": {"en_US": "Physics", "zh": "物理"},
            "Node Tools": {"en_US": "Node Tools", "zh": "节点工具"},
            
            # 操作按钮
            "Import Fab Asset": {"en_US": "Import Fab Asset", "zh": "导入Fab资产"},
            "Import ZIP": {"en_US": "Import ZIP", "zh": "导入ZIP"},
            "Clean Model": {"en_US": "Clean Model", "zh": "清理模型"},
            "Physics Simulation": {"en_US": "Physics Simulation", "zh": "物理模拟"},
            "Rename": {"en_US": "Rename", "zh": "重命名"},
            "Clean Attributes": {"en_US": "Clean Attributes", "zh": "清理属性"},
            "Resize to Texture": {"en_US": "Resize to Texture", "zh": "按纹理调整大小"},
            "Reload Images": {"en_US": "Reload Images", "zh": "重载图像"},
            "Add Subdivision": {"en_US": "Add Subdivision", "zh": "添加细分"},
            "Toggle Projection": {"en_US": "Toggle Projection", "zh": "切换投影"},
            "Import UE PBR": {"en_US": "Import UE PBR", "zh": "导入UE PBR"},
            "Calculate": {"en_US": "Calculate", "zh": "计算"},
            "Apply": {"en_US": "Apply", "zh": "应用"},
            "Stop": {"en_US": "Stop", "zh": "停止"},
            "Sort Collection": {"en_US": "Sort Collection", "zh": "排序集合"},
            "Set Start Frame": {"en_US": "Set Start Frame", "zh": "设置开始帧"},
            "Set End Frame": {"en_US": "Set End Frame", "zh": "设置结束帧"},
            "Toggle Loop": {"en_US": "Toggle Loop", "zh": "切换循环"},
            "Toggle Language": {"en_US": "Toggle Language", "zh": "切换语言"},
            
            # 属性标签
            "Fab Assets Path": {"en_US": "Fab Assets Path", "zh": "Fab资产路径"},
            "Extract Path": {"en_US": "Extract Path", "zh": "解压路径"},
            "Socket Port": {"en_US": "Socket Port", "zh": "Socket端口"},
            "Collision Shape": {"en_US": "Collision Shape", "zh": "碰撞形状"},
            "Collision Margin": {"en_US": "Collision Margin", "zh": "碰撞边距"},
            "Friction": {"en_US": "Friction", "zh": "摩擦力"},
            "Time Scale": {"en_US": "Time Scale", "zh": "时间缩放"},
            "Solver Iterations": {"en_US": "Solver Iterations", "zh": "求解器迭代"},
            "Restitution": {"en_US": "Restitution", "zh": "弹性"},
            "Split Impulse": {"en_US": "Split Impulse", "zh": "分离冲量"},
            "Use Custom Colliders": {"en_US": "Use Custom Colliders", "zh": "使用自定义碰撞体"},
            "Custom Colliders": {"en_US": "Custom Colliders", "zh": "自定义碰撞体"},
            
            # 状态信息
            "Import Complete": {"en_US": "Import Complete", "zh": "导入完成"},
            "Import Failed": {"en_US": "Import Failed", "zh": "导入失败"},
            "ATBridge Settings:": {"en_US": "ATBridge Settings:", "zh": "ATBridge设置:"},
            "Fab Assets Configuration:": {"en_US": "Fab Assets Configuration:", "zh": "Fab资产配置:"},
            "Specify the path to extract Fab ZIP assets": {"en_US": "Specify the path to extract Fab ZIP assets", "zh": "指定解压Fab ZIP资产的路径"},
            "Select Fab Assets ZIP file to import assets": {"en_US": "Select Fab Assets ZIP file to import assets", "zh": "选择Fab资产ZIP文件以导入资产"},
        }
    
    def get_text(self, key: str, context: Optional[bpy.types.Context] = None) -> str:
        """获取翻译后的文本"""
        if context is None:
            context = bpy.context
        
        # 获取当前语言设置
        current_lang = context.preferences.view.language
        is_chinese = current_lang not in ["en_US"]
        
        # 从翻译字典获取文本
        if key in self._translations:
            lang_key = "zh" if is_chinese else "en_US"
            return self._translations[key].get(lang_key, key)
        
        # 如果没有找到翻译，返回原文本
        return key
    
    def add_translation(self, key: str, en_text: str, zh_text: str):
        """动态添加翻译"""
        self._translations[key] = {"en_US": en_text, "zh": zh_text}


# 全局翻译管理器实例
_translation_manager = ATBridgeTranslationManager()

def get_text(key: str, context: Optional[bpy.types.Context] = None) -> str:
    """获取翻译文本的便捷函数"""
    return _translation_manager.get_text(key, context)

def add_translation(key: str, en_text: str, zh_text: str):
    """添加翻译的便捷函数"""
    _translation_manager.add_translation(key, en_text, zh_text)
