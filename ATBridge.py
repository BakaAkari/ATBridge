import json
import os
import socket
import threading
import time
import bpy
from dataclasses import dataclass, field
from typing import List, Optional

from bpy.utils import register_class, unregister_class

# 数据管理器类，替代全局变量
class BridgeState:
    _lock = threading.Lock()
    _MG_AlembicPath = []
    _MG_Material = []
    _MG_ImportComplete = False
    _Megascans_DataSet = None
    # 移除 _last_bridge_connect 及相关方法

    @classmethod
    def get_MG_AlembicPath(cls):
        with cls._lock:
            return cls._MG_AlembicPath

    @classmethod
    def set_MG_AlembicPath(cls, value):
        with cls._lock:
            cls._MG_AlembicPath = value

    @classmethod
    def get_MG_Material(cls):
        with cls._lock:
            return cls._MG_Material

    @classmethod
    def set_MG_Material(cls, value):
        with cls._lock:
            cls._MG_Material = value

    @classmethod
    def get_MG_ImportComplete(cls):
        with cls._lock:
            return cls._MG_ImportComplete

    @classmethod
    def set_MG_ImportComplete(cls, value):
        with cls._lock:
            cls._MG_ImportComplete = value

    @classmethod
    def get_Megascans_DataSet(cls):
        with cls._lock:
            return cls._Megascans_DataSet

    @classmethod
    def set_Megascans_DataSet(cls, value):
        with cls._lock:
            cls._Megascans_DataSet = value

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._MG_AlembicPath = []
            cls._MG_Material = []
            cls._MG_ImportComplete = False
            cls._Megascans_DataSet = None

    @staticmethod
    def check_port_available(host='localhost', port=23333, timeout=2):
        """
        检查端口是否可用（未被占用/堵塞）。
        返回 True 表示端口可用，False 表示端口被占用或不可用。
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.bind((host, port))
            s.close()
            return True
        except OSError:
            return False

    @staticmethod
    def check_quixel_bridge_connectivity(host='localhost', port=23333, timeout=2):
        """
        使用握手协议检测与 Quixel Bridge 的通信连通性。
        尝试连接端口，发送 b'ping'，若收到响应则认为连通。
        返回 True 表示连通，False 表示不通。
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.sendall(b'ping')
            resp = s.recv(1024)
            s.close()
            if resp:
                return True
            else:
                return False
        except Exception:
            return False

@dataclass
class BridgeData:
    megascans_dataset: Optional[str] = None
    mg_material: List = field(default_factory=list)
    mg_alembic_path: List = field(default_factory=list)
    mg_import_complete: bool = False

class BridgeConfig:
    HOST = 'localhost'
    PORT = 23333
    BUFFER_SIZE = 8192  # 4096 * 2
    RECONNECT_DELAY = 3

class MS_Init_ImportProcess():

    # This initialization method create the data structure to process our assets
    # later on in the initImportProcess method. The method loops on all assets
    # that have been sent by Bridge.
    def __init__(self):
        print("[ATBridge] Initialized import class...")
        try:
            self.TexCount = 0
            # Check if there's any incoming data
            if BridgeState.get_Megascans_DataSet() != None:

                BridgeState.set_MG_AlembicPath([])
                BridgeState.set_MG_Material([])
                BridgeState.set_MG_ImportComplete(False)

                self.json_Array = json.loads(BridgeState.get_Megascans_DataSet())
                print(f"[ATBridge] 解析到资产数量: {len(self.json_Array)}")

                # Start looping over each asset in the self.json_Array list
                for js in self.json_Array:

                    self.json_data = js
                    print(f"[ATBridge] 当前资产: {json.dumps(js, ensure_ascii=False)[:500]} ...")

                    self.selectedObjects = []

                    self.IOR = 1.45
                    self.assetType = self.json_data["type"]
                    self.assetPath = self.json_data["path"] if "path" in self.json_data else None
                    self.assetID = self.json_data["id"]
                    self.isMetal = bool(self.json_data.get("category", "") == "Metal")
                    # Workflow setup.
                    self.isHighPoly = bool(self.json_data.get("activeLOD", "") == "high")
                    self.activeLOD = self.json_data.get("activeLOD", None)
                    self.minLOD = self.json_data.get("minLOD", None)
                    self.RenderEngine = bpy.context.scene.render.engine.lower()  # Get the current render engine. i.e. blender_eevee or cycles
                    self.Workflow = self.json_data.get('pbrWorkflow', 'specular')
                    self.DisplacementSetup = 'adaptive'  #regular
                    self.isCycles = bool(self.RenderEngine == 'cycles')
                    self.isScatterAsset = self.CheckScatterAsset() if hasattr(self, 'CheckScatterAsset') else False
                    self.textureList = []
                    self.isBillboard = self.CheckIsBillboard() if hasattr(self, 'CheckIsBillboard') else False
                    self.ApplyToSelection = False
                    self.isSpecularWorkflow = False
                    self.isAlembic = False

                    self.NormalSetup = False
                    self.BumpSetup = False

                    # if "workflow" in self.json_data.keys():
                    #     self.isSpecularWorkflow = bool(self.json_data["workflow"] == "specular")

                    if "applyToSelection" in self.json_data.keys():
                        self.ApplyToSelection = bool(self.json_data["applyToSelection"])

                    if self.isCycles:
                        # Blender 5.0+ 移除了 feature_set 属性，默认支持自适应置换
                        if hasattr(bpy.context.scene.cycles, 'feature_set'):
                            if bpy.context.scene.cycles.feature_set == 'EXPERIMENTAL':
                                self.DisplacementSetup = 'adaptive'
                        else:
                            # Blender 5.0+ 默认启用自适应置换
                            self.DisplacementSetup = 'adaptive'

                    texturesListName = "components"
                    if self.isBillboard:
                        texturesListName = "components"

                    # Get a list of all available texture maps. item[1] returns the map type (albedo, normal, etc...).
                    self.textureTypes = [obj.get("type", "unknown") for obj in self.json_data.get(texturesListName, [])]
                    self.textureList = []

                    for idx, obj in enumerate(self.json_data.get(texturesListName, [])):
                        print(f"[ATBridge] 贴图对象[{idx}]: {obj}")
                        try:
                            texFormat = obj["format"]
                            texType = obj["type"]
                            texPath = obj["path"]
                        except Exception as e:
                            print(f"[ATBridge] 贴图对象缺少关键字段: {e}, 对象内容: {obj}")
                            raise
                        # Replace diffuse texture type with albedo so we don't have to add more conditions to handle diffuse map.
                        if texType == "diffuse" and "albedo" not in self.textureTypes:
                            texType = "albedo"
                            self.textureTypes.append("albedo")
                            self.textureTypes.remove("diffuse")

                        # Normal / Bump setup checks
                        if texType == "normal":
                            self.NormalSetup = True
                        if texType == "bump":
                            self.BumpSetup = True

                        self.textureList.append((texFormat, texType, texPath))

                    # Create a tuple list of all the 3d meshes  available.
                    # This tuple is composed of (meshFormat, meshPath)
                    self.geometryList = []
                    for idx, obj in enumerate(self.json_data.get("meshList", [])):
                        print(f"[ATBridge] 模型对象[{idx}]: {obj}")
                        try:
                            meshFormat = obj["format"]
                            meshPath = obj["path"]
                        except Exception as e:
                            print(f"[ATBridge] 模型对象缺少关键字段: {e}, 对象内容: {obj}")
                            raise
                        self.geometryList.append((meshFormat, meshPath))

                    # Create name of our asset. Multiple conditions are set here
                    # in order to make sure the asset actually has a name and that the name
                    # is short enough for us to use it. We compose a name with the ID otherwise.
                    if "name" in self.json_data.keys():
                        self.assetName = self.json_data["name"].replace(" ", "_")
                    else:
                        self.assetName = os.path.basename(self.json_data["path"]).replace(" ", "_")
                    if len(self.assetName.split("_")) > 2:
                        self.assetName = "_".join(self.assetName.split("_")[:-1])

                    self.materialName = self.assetName + '_' + self.assetID
                    self.colorSpaces = ["sRGB", "Non-Color", "Linear"]

                    # Initialize the import method to start building our shader and import our geometry
                    self.initImportProcess()
                    print("Imported asset from " + self.assetName + " Quixel Bridge")

            if len(BridgeState.get_MG_AlembicPath()) > 0:
                BridgeState.set_MG_ImportComplete(True)
        except Exception as e:
            print("Megascans Plugin Error initializing the import process. Error: ", str(e))

        BridgeState.set_Megascans_DataSet(None)

    # this method is used to import the geometry and create the material setup.
    def initImportProcess(self):
        try:
            if len(self.textureList) >= 1:

                if (self.ApplyToSelection and self.assetType not in ["3dplant", "3d"]):
                    self.CollectSelectedObjects()

                self.ImportGeometry()
                self.CreateMaterial()
                self.ApplyMaterialToGeometry()
                if (self.isScatterAsset and len(self.selectedObjects) > 1):
                    self.ScatterAssetSetup()
                elif (self.assetType == "3dplant" and len(self.selectedObjects) > 1):
                    self.PlantAssetSetup()

                self.SetupMaterial()
                self.GiveObjectsMaterial()

                if self.isAlembic:
                    BridgeState.get_MG_Material().append(self.mat)

        except Exception as e:
            print("Megascans Plugin Error while importing textures/geometry or setting up material. Error: ", str(e))

    def ImportGeometry(self):
        self.ImportGeo = True
        try:
            # Import geometry
            abcPaths = []
            if len(self.geometryList) >= 1:
                for obj in self.geometryList:
                    meshPath = obj[1]
                    meshFormat = obj[0]

                    if meshFormat.lower() == "fbx":
                        bpy.ops.import_scene.fbx(filepath=meshPath)
                        # get selected objects
                        obj_objects = [o for o in bpy.context.scene.objects if o.select_get()]
                        self.selectedObjects += obj_objects

                    elif meshFormat.lower() == "obj":
                        if bpy.app.version < (2, 92, 0):
                            bpy.ops.import_scene.obj(filepath=meshPath, use_split_objects=True, use_split_groups=True,
                                                     global_clight_size=1.0)
                        else:
                            bpy.ops.import_scene.obj(filepath=meshPath, use_split_objects=True, use_split_groups=True,
                                                     global_clamp_size=1.0)
                        # get selected objects
                        obj_objects = [o for o in bpy.context.scene.objects if o.select_get()]
                        self.selectedObjects += obj_objects

                    elif meshFormat.lower() == "abc":
                        self.isAlembic = True
                        abcPaths.append(meshPath)

            if self.isAlembic:
                BridgeState.get_MG_AlembicPath().append(abcPaths)
        except Exception as e:
            print("Megascans Plugin Error while importing textures/geometry or setting up material. Error: ", str(e))

    def dump(self, obj):
        for attr in dir(obj):
            print("obj.%s = %r" % (attr, getattr(obj, attr)))

    def CollectSelectedObjects(self):
        try:
            sceneSelectedObjects = [o for o in bpy.context.scene.objects if o.select_get()]
            for obj in sceneSelectedObjects:
                if obj.type == "MESH":
                    self.selectedObjects.append(obj)
        except Exception as e:
            print("Megascans Plugin Error::CollectSelectedObjects::", str(e))

    def ApplyMaterialToGeometry(self):
        for obj in self.selectedObjects:
            # assign material to obj
            obj.active_material = self.mat

    def CheckScatterAsset(self):
        if ('scatter' in self.json_data['categories'] or 'scatter' in self.json_data['tags'] or 'cmb_asset' in
                self.json_data['categories'] or 'cmb_asset' in self.json_data['tags']):
            return True
        return False

    def CheckIsBillboard(self):
        # Use billboard textures if importing the Billboard LOD.
        if (self.assetType == "3dplant"):
            if (self.activeLOD == self.minLOD):
                return True
        return False

    #Add empty parent for the scatter assets.
    def ScatterAssetSetup(self):
        bpy.ops.object.empty_add(type='ARROWS')
        emptyRefList = [o for o in bpy.context.scene.objects if o.select_get() and o not in self.selectedObjects]
        for scatterParentObject in emptyRefList:
            scatterParentObject.name = self.assetID + "_" + self.assetName
            for obj in self.selectedObjects:
                obj.parent = scatterParentObject
            break

    #Add empty parent for plants.
    def PlantAssetSetup(self):
        bpy.ops.object.empty_add(type='ARROWS')
        emptyRefList = [o for o in bpy.context.scene.objects if o.select_get() and o not in self.selectedObjects]
        for plantParentObject in emptyRefList:
            plantParentObject.name = self.assetID + "_" + self.assetName
            for obj in self.selectedObjects:
                obj.parent = plantParentObject
            break

    # def AddModifiersToGeomtry(self, geo_list, mat):
    #     for obj in geo_list:
    #         # assign material to obj
    #         bpy.ops.object.modifier_add(type='SOLIDIFY')

    #Shader setups for all asset types. Some type specific functionality is also handled here.
    def SetupMaterial(self):
        if "albedo" in self.textureTypes:
            if "ao" in self.textureTypes:
                self.CreateTextureMultiplyNode("albedo", "ao", -250, 320, -640, 460, -640, 200, 0, 1, True,
                                               0)  #设置Color和AO的操作在该函数内
                self.TexCount += 2
            # print("have AO")
            else:
                ColorNode = self.CreateTextureNode("albedo", -640, 460, 0, True, 'Base Color')
                self.TexCount += 1
                ColorNode.name = "Color Tex Node"
            # print("have color")

        if self.isSpecularWorkflow:
            if "specular" in self.textureTypes:
                self.CreateTextureNode("specular", -640, 460 - (self.TexCount * 260), 0, True, self.GetBSDFInputName('specular'))
                self.TexCount += 1

            if "gloss" in self.textureTypes:
                glossNode = self.CreateTextureNode("gloss", -640, -60)
                invertNode = self.CreateGenericNode("ShaderNodeInvert", -250, 60)
                # Add glossNode to invertNode connection
                self.mat.node_tree.links.new(invertNode.inputs[1], glossNode.outputs[0])
                # Connect roughness node to the material parent node.
                self.mat.node_tree.links.new(self.nodes.get(self.parentName).inputs[self.GetBSDFInputName('roughness')], invertNode.outputs[0])
                self.TexCount += 1
            elif "roughness" in self.textureTypes:
                self.CreateTextureNode("roughness", -640, 460 - (self.TexCount * 260), 1, True, self.GetBSDFInputName('roughness'))
                self.TexCount += 1
        else:
            if "metalness" in self.textureTypes:
                MetalNode = self.CreateTextureNode("metalness", -640, 460 - (self.TexCount * 260), 1, True, 'Metallic')
                self.TexCount += 1
                MetalNode.name = "Metallic Tex Node"

            if "roughness" in self.textureTypes:
                RoughNode = self.CreateTextureNode("roughness", -640, 460 - (self.TexCount * 260), 1, True, 'Roughness')
                self.TexCount += 1
                RoughNode.name = "Roughness Tex Node"
            elif "gloss" in self.textureTypes:
                glossNode = self.CreateTextureNode("gloss", -640, 460 - (self.TexCount * 260))
                glossNode.name = "Gloss Tex Node"
                invertNode = self.CreateGenericNode("ShaderNodeInvert", -250, 60)
                # Add glossNode to invertNode connection
                self.mat.node_tree.links.new(invertNode.inputs[1], glossNode.outputs[0])
                # Connect roughness node to the material parent node.
                self.mat.node_tree.links.new(self.nodes.get(self.parentName).inputs[self.GetBSDFInputName('roughness')], invertNode.outputs[0])
                self.TexCount += 1

        if "opacity" in self.textureTypes:
            OpacityNode = self.CreateTextureNode("opacity", -640, 460 - (self.TexCount * 260), 1, True,
                                                 'Alpha')  #if bpy.app.version >= (2, 91, 0) else 18)
            OpacityNode.name = "Opacity Tex Node"
            self.mat.blend_method = 'HASHED'
            self.TexCount += 1

        # if "translucency" in self.textureTypes:
        #     self.CreateTextureNode("translucency", -640, 460-(self.TexCount*260), 1, True, '')
        #     self.TexCount += 1
        elif "transmission" in self.textureTypes:
            TransmissionNode = self.CreateTextureNode("transmission", -640, 460 - (self.TexCount * 260), 1, True,
                                                      'Transmission Weight')
            self.TexCount += 1
            TransmissionNode.name = "Transmission Tex Node"
        # If HIGH POLY selected > use normal_bump and no displacement
        # If LODs selected > use corresponding LODs normal + displacement
        # if self.isHighPoly:
        #     self.BumpSetup = False
        if "normal" in self.textureTypes:
            self.CreateNormalNodeSetup(True, 5)
            self.TexCount += 1

        if "displacement" in self.textureTypes:  #and not self.isHighPoly:
            DisplacementNode = self.CreateDisplacementSetup(True)
            self.TexCount += 1
        # DisplacementNode.name = "Displacement Tex Node"

    # print(self.TexCount)

    def CreateMaterial(self):
        self.mat = (bpy.data.materials.get(self.materialName) or bpy.data.materials.new(self.materialName))
        self.mat.use_nodes = True
        self.nodes = self.mat.node_tree.nodes
        self.parentName = "Principled BSDF"
        self.materialOutputName = "Material Output"

        # self.mat.node_tree.nodes[self.parentName].distribution = 'MULTI_GGX'
        # self.mat.node_tree.nodes[self.parentName].inputs[4].default_value = 1 if self.isMetal else 0 # Metallic value
        # # self.mat.node_tree.nodes[self.parentName].inputs[14].default_value = self.IOR

        self.mappingNode = None

        if self.assetType not in ["3d", "3dplant"]:
            # Create mapping node.
            self.mappingNode = self.CreateGenericNode("ShaderNodeMapping", -1950, 0)
            self.mappingNode.vector_type = 'TEXTURE'
            self.reroute = self.CreateGenericNode("NodeReroute", -1200, 0)
            # Create texture coordinate node.
            texCoordNode = self.CreateGenericNode("ShaderNodeTexCoord", -2150, -0)
            floatNode = self.CreateGenericNode("ShaderNodeValue", -2150, -250)
            floatNode.name = 'Tiling Scale'
            floatNode.outputs[0].default_value = 1.0
            # Connect texCoordNode to the mappingNode
            if self.assetType == "surface":
                self.mat.node_tree.links.new(self.mappingNode.inputs['Vector'], texCoordNode.outputs['UV'])
                self.mat.node_tree.links.new(self.reroute.inputs[0], self.mappingNode.outputs[0])

                self.mat.node_tree.links.new(self.mappingNode.inputs['Scale'], floatNode.outputs['Value'])
            if self.assetType == "3d":
                self.mat.node_tree.links.new(self.mappingNode.inputs['Vector'], texCoordNode.outputs['UV'])
                self.mat.node_tree.links.new(self.reroute.inputs[0], self.mappingNode.outputs[0])
            if self.assetType == "atlas":
                self.mat.node_tree.links.new(self.mappingNode.inputs['Vector'], texCoordNode.outputs['UV'])
                self.mat.node_tree.links.new(self.reroute.inputs[0], self.mappingNode.outputs[0])

    def CreateTextureNode(self, textureType, PosX, PosY, colorspace=1, connectToMaterial=False, MaterialInputIdent=''):
        texturePath = self.GetTexturePath(textureType)
        textureNode = self.CreateGenericNode('ShaderNodeTexImage', PosX, PosY)
        textureNode.image = bpy.data.images.load(texturePath)
        textureNode.show_texture = True
        textureNode.image.colorspace_settings.name = self.colorSpaces[colorspace]  # "sRGB", "Non-Color", "Linear"

        if self.assetType == "surface":
            textureNode.projection = "FLAT"

        if textureType in ["albedo", "specular", "translucency"]:
            if self.GetTextureFormat(textureType) in "exr":
                textureNode.image.colorspace_settings.name = self.colorSpaces[2]  # "sRGB", "Non-Color", "Linear"

        if connectToMaterial:
            self.ConnectNodeToMaterial(MaterialInputIdent, textureNode)
        # If it is Cycles render we connect it to the mapping node.
        if self.assetType not in ["3d", "3dplant"]:
            self.mat.node_tree.links.new(textureNode.inputs['Vector'], self.reroute.outputs[0])
        return textureNode

    def CreateTextureMultiplyNode(self, aTextureType, bTextureType, PosX, PosY, aPosX, aPosY, bPosX, bPosY, aColorspace,
                                  bColorspace, connectToMaterial, materialInputIndex):
        # Blender 3.4+ 使用 ShaderNodeMix 替代 ShaderNodeMixRGB
        if bpy.app.version >= (3, 4, 0):
            multiplyNode = self.CreateGenericNode('ShaderNodeMix', PosX, PosY)
            multiplyNode.data_type = 'RGBA'  # 设置为颜色模式
            multiplyNode.blend_type = 'MULTIPLY'
            multiplyNode.inputs['Factor'].default_value = 1.0
        else:
            multiplyNode = self.CreateGenericNode('ShaderNodeMixRGB', PosX, PosY)
            multiplyNode.blend_type = 'MULTIPLY'
            multiplyNode.inputs[0].default_value = 1
        
        #Setup A and B nodes
        ColorNode = self.CreateTextureNode(aTextureType, aPosX, aPosY, aColorspace)
        ColorNode.name = "Color Tex Node"

        if self.assetType == "surface":
            ColorNode.projection = "FLAT"

        AONode = self.CreateTextureNode(bTextureType, bPosX, bPosY, bColorspace)
        AONode.name = "AO Tex Node"

        if self.assetType == "surface":
            AONode.projection = "FLAT"

        # 连接 albedo 和 ao 节点到 multiply 节点
        if bpy.app.version >= (3, 4, 0):
            self.mat.node_tree.links.new(multiplyNode.inputs['A'], ColorNode.outputs['Color'])
            self.mat.node_tree.links.new(multiplyNode.inputs['B'], AONode.outputs['Color'])
        else:
            self.mat.node_tree.links.new(multiplyNode.inputs['Color1'], ColorNode.outputs['Color'])
            self.mat.node_tree.links.new(multiplyNode.inputs['Color2'], AONode.outputs['Color'])

        if connectToMaterial:
            self.ConnectNodeToMaterial(materialInputIndex, multiplyNode)

        return multiplyNode

    def CreateNormalNodeSetup(self, connectToMaterial, materialInputIndex):

        bumpNode = None
        normalNode = None
        bumpMapNode = None
        normalMapNode = None

        # if self.NormalSetup and self.BumpSetup:
        #     bumpMapNode = self.CreateTextureNode("bump", -640, -180)
        #     normalMapNode = self.CreateTextureNode("normal", -640, -650)
        #     bumpNode = self.CreateGenericNode("ShaderNodeBump", -250, -350)
        #     bumpNode.inputs[0].default_value = 0.1
        #     normalNode = self.CreateGenericNode("ShaderNodeNormalMap", -640, -500)
        #     # Add normalMapNode to normalNode connection
        #     self.mat.node_tree.links.new(normalNode.inputs[1], normalMapNode.outputs[0])
        #     # Add bumpMapNode and normalNode connection to the bumpNode
        #     self.mat.node_tree.links.new(bumpNode.inputs[2], bumpMapNode.outputs[0])
        #     if (2, 81, 0) > bpy.app.version:
        #         self.mat.node_tree.links.new(bumpNode.inputs[3], normalNode.outputs[0])
        #     else:
        #         self.mat.node_tree.links.new(bumpNode.inputs[5], normalNode.outputs[0])
        #     # Add bumpNode connection to the material parent node
        #     if connectToMaterial:
        #         self.ConnectNodeToMaterial(materialInputIndex, bumpNode)
        if self.NormalSetup:
            normalMapNode = self.CreateTextureNode("normal", -640, 460 - (self.TexCount * 260))
            normalNode = self.CreateGenericNode("ShaderNodeNormalMap", -250, -250)
            normalMapNode.name = "Normal Tex Node"

            if self.assetType == "surface":
                normalMapNode.projection = "FLAT"

            # Add normalMapNode to normalNode connection
            self.mat.node_tree.links.new(normalNode.inputs['Color'], normalMapNode.outputs['Color'])
            # Add normalNode connection to the material parent node
            if connectToMaterial:
                self.ConnectNodeToMaterial(materialInputIndex, normalNode)
        elif self.BumpSetup:
            bumpMapNode = self.CreateTextureNode("bump", -640, 460 - (self.TexCount * 260))
            bumpNode = self.CreateGenericNode("ShaderNodeBump", -250, -250)

            if self.assetType == "surface":
                bumpMapNode.projection = "FLAT"

            bumpNode.inputs[0].default_value = 0.1
            # Add bumpMapNode and normalNode connection to the bumpNode
            self.mat.node_tree.links.new(bumpNode.inputs[2], bumpMapNode.outputs[0])
            # Add bumpNode connection to the material parent node
            if connectToMaterial:
                self.ConnectNodeToMaterial(materialInputIndex, bumpNode)

    def CreateDisplacementSetup(self, connectToMaterial):
        if self.DisplacementSetup == "adaptive":
            # Add vector>displacement map node
            displacementNode = self.CreateGenericNode("ShaderNodeDisplacement", 10, -400)
            displacementNode.inputs[2].default_value = 0.1
            displacementNode.inputs[1].default_value = 0.5
            # Add converter>RGB Separator node
            if bpy.app.version >= (3, 3, 0):
                RGBSplitterNode = self.CreateGenericNode("ShaderNodeSeparateColor", -250, -550)
            else:
                RGBSplitterNode = self.CreateGenericNode("ShaderNodeSeparateRGB", -250, -550)
            # Import normal map and normal map node setup.
            displacementMapNode = self.CreateTextureNode("displacement", -640, 460 - (self.TexCount * 260))
            displacementMapNode.name = "Displacement Tex Node"
            #创建置换强度控制节点
            floatNode = self.CreateGenericNode("ShaderNodeValue", -250, -650)
            floatNode.name = 'Bump Strength'
            floatNode.outputs[0].default_value = 0.1

            if self.assetType == "surface":
                displacementMapNode.projection = "FLAT"

            # Add displacementMapNode to RGBSplitterNode connection
            self.mat.node_tree.links.new(RGBSplitterNode.inputs[0], displacementMapNode.outputs[0])
            # Add RGBSplitterNode to displacementNode connection
            self.mat.node_tree.links.new(displacementNode.inputs[0], RGBSplitterNode.outputs[0])
            # Add normalNode connection to the material output displacement node
            self.mat.node_tree.links.new(displacementNode.inputs['Scale'], floatNode.outputs[0])

            if connectToMaterial:
                self.mat.node_tree.links.new(self.nodes.get(self.materialOutputName).inputs[2],
                                             displacementNode.outputs[0])
                self.mat.displacement_method = 'BOTH'

        if self.DisplacementSetup == "regular":
            pass
        # print(self.TexCount)

    def ConnectNodeToMaterial(self, MaterialInputIdent, textureNode):
        self.mat.node_tree.links.new(self.nodes.get(self.parentName).inputs[MaterialInputIdent], textureNode.outputs[0])

    def CreateGenericNode(self, nodeName, PosX, PosY):
        genericNode = self.nodes.new(nodeName)
        genericNode.location = (PosX, PosY)
        return genericNode

    def GetTexturePath(self, textureType):
        for item in self.textureList:
            if item[1] == textureType:
                path = item[2]
                # 如果是网络路径（UNC），直接返回原始路径
                if path.startswith("\\\\"):
                    return path
                # 否则替换为正斜杠
                return path.replace("\\", "/")

    def GetTextureFormat(self, textureType):
        for item in self.textureList:
            if item[1] == textureType:
                return item[0].lower()

    def GetBSDFInputName(self, input_type):
        """Handle Blender 4.0+ BSDF input changes"""
        if bpy.app.version >= (4, 0, 0):
            if input_type == 'specular':
                return "Specular IOR Level"
            if input_type == 'roughness':
                return "Roughness"
        else:
            if input_type == 'specular':
                return "Specular" if bpy.app.version >= (2, 80, 0) else 5 # Actually just name "Specular" usually works in 2.8+, but let's stick to simple names
                # In old code it used index 5. 5 is Specular in 2.8-3.x
                return 5
            if input_type == 'roughness':
                return 9
        return input_type

    #========================================================================================================================
    def GiveObjectsMaterial(self):
        act_obj = bpy.context.active_object
        if act_obj is not None and act_obj.type == "MESH":
            print(self.assetType)
            if self.assetType == "surface":
                qui_mat = bpy.data.materials[self.materialName]
                act_obj.active_material = qui_mat
            if self.assetType == "atlas":
                qui_mat = bpy.data.materials[self.materialName]
                act_obj.active_material = qui_mat


#========================================================================================================================

class QuixelSocketServer(threading.Thread):
    def __init__(self, host='localhost', port=23333, importer=None):
        super().__init__()
        self.host = host
        self.port = port
        self.importer = importer  # 资产导入处理函数
        self.daemon = True
        self.running = True
        self.server = None

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                self.server = server
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((self.host, self.port))
                server.listen(5)
                while self.running:
                    try:
                        client, addr = server.accept()
                        with client:
                            data = b''
                            while True:
                                chunk = client.recv(8192)
                                if not chunk:
                                    break
                                data += chunk
                            if data and self.importer:
                                # 移除 BridgeState.update_last_bridge_connect()
                                self.importer(data)
                    except Exception as e:
                        print(f'QuixelSocketServer error: {e}')
        except Exception as e:
            print(f'QuixelSocketServer main error: {e}')

    def stop(self):
        self.running = False
        # 触发一次连接以退出阻塞的accept
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.close()
        except Exception:
            pass


class MS_Init_LiveLink(bpy.types.Operator):
    bl_idname = "bridge.plugin"
    bl_label = "Megascans Plugin"
    socketCount = 0

    def execute(self, context):
        try:
            BridgeState.set_Megascans_DataSet(None)
            self.server_thread = QuixelSocketServer(importer=self.importer)
            self.server_thread.start()
            bpy.app.timers.register(self.newDataMonitor)
            return {'FINISHED'}
        except Exception as e:
            print("Megascans Plugin Error starting blender plugin. Error: ", str(e))
            return {"FAILED"}

    def newDataMonitor(self):
        try:
            if BridgeState.get_Megascans_DataSet() != None:
                MS_Init_ImportProcess()
                BridgeState.set_Megascans_DataSet(None)
        except Exception as e:
            print("Megascans Plugin Error starting blender plugin (newDataMonitor). Error: ", str(e))
            return {"FAILED"}
        return 1.0

    def importer(self, recv_data):
        try:
            BridgeState.set_Megascans_DataSet(recv_data)
        except Exception as e:
            print("Megascans Plugin Error starting blender plugin (importer). Error: ", str(e))
            return {"FAILED"}

    def __del__(self):
        if hasattr(self, 'server_thread') and self.server_thread:
            self.server_thread.stop()


class MS_Init_Abc(bpy.types.Operator):
    bl_idname = "ms_livelink_abc.py"
    bl_label = "Import ABC"

    def execute(self, context):

        try:
            if BridgeState.get_MG_ImportComplete():

                assetMeshPaths = BridgeState.get_MG_AlembicPath()
                assetMaterials = BridgeState.get_MG_Material()

                if len(assetMeshPaths) > 0 and len(assetMaterials) > 0:

                    materialIndex = 0
                    old_materials = []
                    for meshPaths in assetMeshPaths:
                        for meshPath in meshPaths:
                            bpy.ops.wm.alembic_import(filepath=meshPath, as_background_job=False)
                            for o in bpy.context.scene.objects:
                                if o.select_get():
                                    old_materials.append(o.active_material)
                                    o.active_material = assetMaterials[materialIndex]

                        materialIndex += 1

                    for mat in old_materials:
                        try:
                            if mat is not None:
                                bpy.data.materials.remove(mat)
                        except:
                            pass

                    BridgeState.set_MG_AlembicPath([])
                    BridgeState.set_MG_Material([])
                    BridgeState.set_MG_ImportComplete(False)

            return {'FINISHED'}
        except Exception as e:
            print("Megascans Plugin Error starting MS_Init_Abc. Error: ", str(e))
            return {"CANCELLED"}


class testpreferences(bpy.types.AddonPreferences):
    bl_idname = "test perferences"

    def draw(self, context):
        layout = self.layout

classes = (
    MS_Init_LiveLink,
    MS_Init_Abc,
)

def register():
    global classes
    for cls in classes:
        register_class(cls)


def unregister():
    global classes
    for cls in classes:
        unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
