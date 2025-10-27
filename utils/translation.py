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
            
            # 操作按钮
            "Import Fab Asset": {"en_US": "Import Fab Asset", "zh": "导入Fab资产"},
            "Import ZIP": {"en_US": "Import ZIP", "zh": "导入ZIP"},
            "Clean Model": {"en_US": "Clean Model", "zh": "清理模型"},
            "Physics Simulation": {"en_US": "Physics Simulation", "zh": "物理模拟"},
            
            # 属性标签
            "Fab Assets Path": {"en_US": "Fab Assets Path", "zh": "Fab资产路径"},
            "Extract Path": {"en_US": "Extract Path", "zh": "解压路径"},
            "Socket Port": {"en_US": "Socket Port", "zh": "Socket端口"},
            
            # 状态信息
            "Import Complete": {"en_US": "Import Complete", "zh": "导入完成"},
            "Import Failed": {"en_US": "Import Failed", "zh": "导入失败"},
            "ATBridge Settings:": {"en_US": "ATBridge Settings:", "zh": "ATBridge设置:"},
            "Fab Assets Configuration:": {"en_US": "Fab Assets Configuration:", "zh": "Fab资产配置:"},
            "Extract Path": {"en_US": "Extract Path", "zh": "解压路径"},
            "Fab Assets Path": {"en_US": "Fab Assets Path", "zh": "Fab资产路径"},
            "Specify the path to extract Fab ZIP assets": {"en_US": "Specify the path to extract Fab ZIP assets", "zh": "指定解压Fab ZIP资产的路径"},
            "Import Fab Asset": {"en_US": "Import Fab Asset", "zh": "导入Fab资产"},
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
