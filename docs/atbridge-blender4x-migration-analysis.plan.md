---
name: ATBridge-blender4x-migration-analysis
overview: 分析 ATBridge 插件整体架构与兼容逻辑，并规划后续仅支持 Blender 4.x 的改造方向。
todos:
  - id: update-metadata-4x-only
    content: 将插件 bl_info 最低版本调整为 Blender 4.0，并在代码注释中声明仅支持 4.x+。
    status: pending
  - id: clean-version-branches
    content: 删除 ATBridge.py 中所有 <4.x 的版本兼容分支，仅保留 Blender 4.x 可用的节点类型和导入参数。
    status: pending
  - id: verify-4x-api
    content: 逐一对照 Blender 4.x 文档，核实 ShaderNodeMapping、displacement_method、导入操作符参数等 API 是否需要调整。
    status: pending
  - id: refactor-import-structure
    content: 拆分 MS_Init_ImportProcess 的职责，按解析、几何导入、材质/节点构建等模块进行结构化。
    status: pending
  - id: improve-error-handling
    content: 统一异常处理与用户提示，减少裸露的 except Exception 和静默失败。
    status: pending
isProject: false
---

## ATBridge 插件整体架构分析

### 1. 模块划分与职责

- `**ATBridge.py`（核心桥接逻辑）**
  - `**BridgeState**`：
    - 以类属性 + `threading.Lock` 方式模拟全局状态（Alembic 路径、材质列表、导入完成标记、Megascans JSON 数据）。
    - 提供一系列 `get_*/set_*` 与 `reset` 方法，以及端口与 Quixel Bridge 连通性检查工具方法。
  - `**BridgeData` / `BridgeConfig**`：
    - `BridgeData` 是一个 dataclass，用于描述桥接数据结构，但当前代码中几乎未真正发挥“单一结构承载状态”的优势。
    - `BridgeConfig` 定义常量：`HOST`、`PORT`、`BUFFER_SIZE`、`RECONNECT_DELAY`，用于 Socket 通信配置。
  - `**MS_Init_ImportProcess**`（导入流程核心类）：
    - 构造函数中读取 `BridgeState.get_Megascans_DataSet()` 的 JSON 字符串，解析为资产数组，逐个资产处理。
    - 负责：
      - 解析资产元数据（类型、路径、LOD、PBR 工作流、是否散布、是否金属等）。
      - 收集贴图列表 `textureList` / 贴图类型列表 `textureTypes`。
      - 收集几何体列表 `geometryList`（fbx/obj/abc）。
      - 根据渲染引擎（Cycles/Eevee）与 Cycles 设置，决定 `DisplacementSetup`（adaptive/regular）。
      - 调用 `initImportProcess()` 完成：导入几何体、创建材质、布线节点、赋材质、散布/植物特殊处理、位移/法线/凹凸等完整流程。
    - 该类内部再细分多个方法：`ImportGeometry`、`SetupMaterial`、`CreateMaterial`、`CreateTextureNode`、`CreateTextureMultiplyNode`、`CreateNormalNodeSetup`、`CreateDisplacementSetup`、`GiveObjectsMaterial` 等，每个方法大多直接操作 `bpy` API 与节点树。
  - `**QuixelSocketServer**`：
    - 继承 `threading.Thread`，在独立线程上监听 TCP 端口（默认 23333）。
    - 接收到完整数据后调用传入的 `importer` 回调（实际由 `MS_Init_LiveLink` 提供），将数据写入 `BridgeState`。
  - `**MS_Init_LiveLink`（Operator）**：
    - `bpy.types.Operator` 子类，`bl_idname = "bridge.plugin"`，用于启动 Socket 服务器并注册 `bpy.app.timers` 轮询。
    - `execute()` 中：
      - 启动 `QuixelSocketServer(importer=self.importer)`。
      - `bpy.app.timers.register(self.newDataMonitor)` 定时回调。
    - `newDataMonitor()`：检测 `BridgeState.get_Megascans_DataSet()` 是否有数据，有则直接实例化 `MS_Init_ImportProcess()` 触发资产导入。
    - `importer()`：被 Socket 线程调用，将接收到的原始数据串写入 `BridgeState.set_Megascans_DataSet`。
  - `**MS_Init_Abc`（Operator）**：
    - 负责在 Alembic 模式下，根据 `BridgeState` 中记录的 Alembic 路径列表与材质列表，调用 `bpy.ops.wm.alembic_import` 导入，并替换旧材质。
  - `**register/unregister**`：
    - 通过 `classes` 元组统一注册 `MS_Init_LiveLink` 与 `MS_Init_Abc`。
- `**ATBridgeExtend.py`（拓展功能）**
  - `**AT_AddonPreferences`（插件首选项）**：
    - 继承 `AddonPreferences`，`bl_idname` 使用模块名或回退为 `"ATBridge"`，与 `__init__.py` 中 addons 名称匹配。
    - 暴露 `fab_assets_path` 路径设置，默认值为 `"D:/FabAssets"`，用于 Fab ZIP 资源解压与检索。
    - `draw()` 中通过 `get_text` 进行多语言展示，UI 比较简洁。
  - `**ATB_OT_import_zip`（Fab ZIP 导入 Operator）**：
    - 提供一个 `FILE_PATH` 类型的 `filepath` 属性，通过 `invoke()` 弹出文件选择对话框，`execute()` 中执行：
      - 校验是否为 `.zip`，并解析 ZIP 内首个 JSON 描述文件，提取 `id` 等字段。
      - 校验 ZIP 文件名中是否包含该 `id`，增强健壮性。
      - 读取插件首选项中的 `fab_assets_path`，在其中创建目标解压目录并执行 `extractall`。
      - 扫描解压目录，收集所有文件列表，使用 `smart_find_file` / `smart_find_model` 按 `asset_id + map_name/mesh_format` 智能匹配贴图与模型实际路径。
      - 构建与 Quixel Bridge 兼容的 `bridge_asset` 字典结构：
        - `components`：每个贴图统一 type（例如多个 basecolor 同义词统一为 `albedo`），自动推断 `format`。
        - `meshList`：根据扩展名判断 fbx/obj/abc，并填入 `path/format`。
      - 将 `bridge_asset` 封装为单元素数组 JSON 字符串，写入 `BridgeState.set_Megascans_DataSet(json_str)`。
      - 直接调用 `MS_Init_ImportProcess()`，实现“本地 ZIP → Megascans JSON 协议 → 统一导入流程”。
    - `get_fab_assets_path()` 封装了从 `context.preferences.addons[...]` 中安全获取首选项的逻辑。
- `**__init__.py`（插件入口与注册）**（根据子代理分析）
  - 定义 `bl_info`，当前声明 Blender 版本为 `(2, 8, 0)` 起支持。
  - 导入 `ATBridge`, `ATBridgeExtend` 等模块，并在 `register()`/`unregister()` 中集中注册它们的 `register()`。
  - 注册 `load_post` 事件，在 Blender 打开文件后自动尝试建立与 Bridge 的连接或初始化。
  - 给 `TOPBAR_MT_file_import`、`VIEW3D_HT_header` 等菜单/工具栏挂接菜单项与按钮，方便用户手动触发 LiveLink 或 Fab 导入。
- `**utils/translation.py**`（多语言支持）
  - 提供 `get_text` 包装函数，根据当前语言与上下文返回对应文案，用于插件 UI 与提示文字。

### 2. 运行时数据流与调用链

#### 2.1 Quixel Bridge 实时导入流程

- **外部**：Quixel Bridge 通过 TCP 向 Blender 插件绑定的 23333 端口发送 Megascans 资产 JSON。
- **插件内部流转**：
  1. 用户或 `load_post` 自动注册触发 `MS_Init_LiveLink.execute()`；
  2. `MS_Init_LiveLink` 启动 `QuixelSocketServer` 线程并注册 `bpy.app.timers` 回调；
  3. Socket 线程接收完整数据包，调用 `MS_Init_LiveLink.importer(recv_data)`；
  4. `importer()` 将原始 `recv_data` 写入 `BridgeState.set_Megascans_DataSet(...)`；
  5. `bpy.app.timers` 周期性调用 `newDataMonitor()`：
    - 若 `BridgeState.get_Megascans_DataSet()` 非空，则实例化 `MS_Init_ImportProcess()`；
    - `MS_Init_ImportProcess.__init__()` 中解析 JSON、逐资产执行导入。
- **资产导入内部流程（以 `MS_Init_ImportProcess` 为中心）**：
  - 解析 JSON → 收集贴图/网格列表 → 构建 `assetName/materialName` → 
  - `initImportProcess()`：
    - `ImportGeometry()`：调用 `bpy.ops.import_scene.fbx/obj` 或记录 Alembic 路径；
    - `CreateMaterial()`：创建或获取 `bpy.data.materials`；创建节点树基础结构（`Principled BSDF` + Mapping/UV/Value 等）；
    - `SetupMaterial()`：按贴图类型创建 `ShaderNodeTexImage`、`ShaderNodeMix/MixRGB`、`ShaderNodeNormalMap`、`ShaderNodeDisplacement`、`ShaderNodeSeparateColor/RGB` 等，并连接到 BSDF 与 `Material Output`；
    - `ApplyMaterialToGeometry()` / `GiveObjectsMaterial()`：根据资产类型与选择集为对象赋材质；
    - 散布/植物资产则会创建 `empty` 父对象并重建层级。

#### 2.2 Fab ZIP 导入流程

- 用户从菜单或快捷方式触发 `ATB_OT_import_zip`：
  - `invoke()` 检查 Fab 路径是否已设置，否则阻止继续；
  - 文件选择后进入 `execute()`：
    - 校验 ZIP + 解析内部 JSON → 校验 id 与文件名 → 解压到首选项给定目录下；
    - 通过文件名智能匹配生成 Megascans 兼容数据结构 → 写入 `BridgeState` → 直接调用 `MS_Init_ImportProcess()`。
- 两条路径最终都复用同一套导入/材质搭建逻辑，整体设计上是“**协议统一，前端数据源可多样**”。

---

## Blender 版本兼容逻辑梳理

### 1. 明确存在的版本分支

- **OBJ 导入参数差异**（2.92 之前/之后）：`ATBridge.py` 中 `ImportGeometry()`：
  - `bpy.app.version < (2, 92, 0)` 使用 `global_clight_size`；
  - 否则使用 `global_clamp_size`。
- **Cycles `feature_set` 属性兼容**（Blender 5.0 变更）：
  - `MS_Init_ImportProcess.__init__` 内：针对 `self.isCycles` 时：
    - `if hasattr(bpy.context.scene.cycles, 'feature_set'):` 分支处理旧版 Experimetal 自适应置换；
    - `else:` 注释写明“Blender 5.0+ 默认启用自适应置换”。
- `**ShaderNodeMixRGB` → `ShaderNodeMix**`（3.4 以后）：
  - `CreateTextureMultiplyNode()`：
    - `if bpy.app.version >= (3, 4, 0)` 使用 `ShaderNodeMix` + `data_type = 'RGBA'` + `blend_type='MULTIPLY'`；
    - 否则使用旧的 `ShaderNodeMixRGB` 与数值输入槽索引。
- `**ShaderNodeSeparateRGB` → `ShaderNodeSeparateColor**`（3.3 以后）：
  - `CreateDisplacementSetup()`：
    - `if bpy.app.version >= (3, 3, 0)` 使用 `ShaderNodeSeparateColor`；
    - 否则使用 `ShaderNodeSeparateRGB`。
- **BSDF 输入插槽名称变更（Blender 4.0）**：
  - `GetBSDFInputName()`：
    - `if bpy.app.version >= (4, 0, 0)`：
      - `specular` → "Specular IOR Level"；
      - `roughness` → "Roughness"。
    - 否则：
      - `specular` → "Specular"；
      - `roughness` → "Roughness"。
- **注释中遗留的版本条件**：
  - `SetupMaterial()` 中 `opacity` 贴图连接处，注释里还残留早期版本的 input index 条件 `#if bpy.app.version >= (2, 91, 0) else 18`，现在已改为通过名称 `"Alpha"` 连接。
- **插件声明支持的最小版本**：
  - `__init__.py` 的 `bl_info["blender"] = (2, 8, 0)`。

### 2. 可能与 4.x 相关、需验证的 API 使用点

- **节点类型与属性**：
  - `ShaderNodeMapping.vector_type = 'TEXTURE'`：Blender 4.x 中 Mapping 节点重构过，其 `vector_type` 与插槽名称在 UI 上有变动；需要验证该属性在 4.x 是否仍然存在/推荐使用。
  - `self.mat.displacement_method = 'BOTH'`：需要确认 4.x 是否仍支持该枚举值，以及是否推荐通过 `MaterialSettings` 或其他方式配置位移。
- **操作符与上下文**：
  - `bpy.ops.import_scene.fbx/obj` 与 `bpy.ops.wm.alembic_import` 的参数是否在 4.x 有增减；目前使用的参数较少（主要是 `filepath` 及若干布尔参数），一般兼容性较好，但仍建议对照 4.x 官方文档确认。
- **菜单与 UI 挂接**：
  - `TOPBAR_MT_file_import` 与 `VIEW3D_HT_header` 在 4.x 仍然存在，一般问题不大，但如果 Blender UI 结构有变更，需要适配新的菜单或 Panel 位置。

---

## 结构性问题与潜在隐患

### 1. 全局状态与线程模型

- **问题点**：
  - `BridgeState` 使用类属性保存状态，再通过类方法读写，等于“带锁的全局单例”。
  - Socket 线程、Timer 回调、Operator 执行之间共享同一状态：
    - Socket 线程写 `Megascans_DataSet`；
    - Timer 回调读该字段并触发导入；
    - 导入过程中又会写 Alembic 路径/MG 材质列表等。
- **风险**：
  - 虽然加了锁，但缺少更高层级的“状态机”约束，逻辑顺序全靠“先写后读”的约定，出现竞态条件时排查困难。
  - 若未来支持多次并发导入（例如同时触发多个资产流），现有结构不支持“多批次独立状态”。
- **对 Blender 4.x 的影响**：
  - 4.x 本身不会直接破坏这个模型，但为了提升健壮性和可维护性，后续可以考虑：
    - 用一个显式的“任务队列”或“导入 Job 对象”替代扁平全局变量；
    - 明确生命周期：数据接收 → 排队 → 主线程处理 → 完成标记/清理。

### 2. 渲染与材质构建逻辑过于集中

- `**MS_Init_ImportProcess` 职责过重**：
  - 同时负责：
    - JSON 解析、容错与打印日志；
    - 贴图/几何路径收集与列表构建；
    - 场景对象选择、空对象创建、父子层级调整；
    - 材质创建、所有节点的创建与连接；
    - 法线/凹凸/位移的所有逻辑；
    - 特殊资产（scatter/3dplant）的处理。
- **问题**：
  - 几乎所有导入相关逻辑都塞在一个类中，方法间依赖共享的实例字段，耦合度极高。
  - 难以针对单一功能单测或修改；任何版本 API 变更都要在大类内部找到多处散落逻辑。
- **建议**（为后续 4.x 重构准备）：
  - 按职责拆分：例如 `AssetParser`、`GeometryImporter`、`MaterialBuilder`、`NodeGraphBuilder`、`ScatterSetup` 等辅助类或函数模块。
  - 将版本相关判断集中在“适配层”或“兼容 Helper” 中，而不是遍布各处。

### 3. 错误处理与日志

- **当前情况**：
  - 多处使用宽泛的 `except Exception as e: print(...)` 或简单 `pass`，例如：
    - `MS_Init_ImportProcess.__init__`/`initImportProcess`/`ImportGeometry`；
    - `QuixelSocketServer.run`; `MS_Init_LiveLink.newDataMonitor/importer`；
    - `MS_Init_Abc.execute`；
    - `ATB_OT_import_zip.execute` 中虽然打印了 traceback，但仍大量采用宽泛捕获。
- **问题**：
  - 使用者只在 System Console 中看到简单报错文本，缺少明确的用户提示或 UI 反馈（部分地方用了 `self.report`，但并不一致）。
  - 部分异常直接 `pass`，可能导致静默失败。
- **与版本支持的关系**：
  - 当 Blender 4.x 某 API 改动时，如果异常被简单吞掉，很难快速定位是“版本不兼容”还是“数据问题”。
  - 未来聚焦 4.x 时，可以针对 4.x API 异常做更细粒度的报错与降级处理。

### 4. 硬编码常量与平台相关配置

- **端口与主机**：
  - `BridgeConfig.HOST/PORT` 固定为 `localhost:23333`，可以理解为协议约定，但更灵活的做法是：在 Addon Preferences 中开放配置，或至少在 UI 上显示目前使用的端口。
- **Fab 资产路径默认值**：
  - `AT_AddonPreferences.fab_assets_path` 默认 `"D:/FabAssets"`，明显偏向 Windows，且假定 D 盘存在。
  - 在非 Windows 或无 D 盘的环境下容易造成困惑（虽然后续逻辑会要求路径有效）。

### 5. 上下文与 `bpy.context` 使用

- 多处直接使用 `bpy.context.scene.objects`、`bpy.context.active_object`、`bpy.context.scene.render.engine` 等全局上下文：
  - 在典型 GUI 使用中问题不大，但：
    - 在后台渲染（`-b`）或脚本中，context 可能不同或为空，易产生难以复现的错误；
    - 若未来支持在特定区域或多视图中工作，更推荐使用 Operator 的 `context` 参数或从 `depsgraph`/`view_layer` 解析。

### 6. 注释与遗留代码

- 多处被注释掉的大块旧逻辑（例如早期 Bump+Normal 混合逻辑、透明度/Translucency、旧的 BSDF 槽索引判断等）。
- 这些旧片段中往往包含旧版 Blender 的 API 或索引逻辑，如果保留但不说明“仅供参考”，容易在未来维护时被误以为仍可启用。

---

## 与“仅支持 Blender 4.x+” 目标直接相关的问题点

以下内容是“当前为了向下兼容 2.8–3.x 所保留的逻辑”，在明确不再向下兼容时，可以考虑删除或简化：

### 1. 版本分支与兼容代码

- **OBJ 导入分支**：
  - `if bpy.app.version < (2, 92, 0): ... global_clight_size ... else: ... global_clamp_size ...`。
  - 当仅支持 4.x 时，可**直接去掉 `< (2, 92, 0)` 分支，使用新版参数接口即可**。
- `**ShaderNodeMixRGB` / `ShaderNodeSeparateRGB` 兼容**：
  - Blender 4.x 时，`bpy.app.version >= (3, 4, 0)` 与 `>= (3, 3, 0)` 必然为真：
    - 可**去掉 `else` 分支**，统一使用 `ShaderNodeMix` + `data_type='RGBA'`，以及 `ShaderNodeSeparateColor`。
- **BSDF 输入名兼容**：
  - `GetBSDFInputName` 中针对 `< 4.0` 的 "Specular" 等逻辑可以删除，仅保留 4.x 的 "Specular IOR Level" 逻辑。
- **Cycles `feature_set` 检查**：
  - 当前通过 `hasattr` 做运行时兼容，并在注释中提到 Blender 5.0+ 行为。
  - 在仅支持 4.x 时：
    - 可以查阅 4.x 文档，选定一个“唯一正确”的位移配置方式，删除分支与 `hasattr` 检查。
- **注释中旧版 input index 逻辑**：
  - 比如 `Opacity` 部分注释中的 `if bpy.app.version >= (2, 91, 0) else 18` 等，可以彻底移除，防止误导。

### 2. API 使用需要针对 4.x 重新审视

- `**ShaderNodeMapping` 与 displacement**：
  - 4.x 对材质节点系统的升级较大，建议：
    - 明确对齐 4.x 官方推荐的节点/插槽名称和属性，如有废弃字段，直接切换到新的字段。
- **材质设置与渲染属性**：
  - `self.mat.blend_method = 'HASHED'`、`self.mat.displacement_method = 'BOTH'` 等是否在 4.x 仍是最佳实践，需要验证。

### 3. 外围结构可以借机优化

- **bl_info 与文档声明**：
  - `bl_info["blender"]` 调整到 `(4, 0, 0)`，并在说明中删除对 2.8/2.9/3.x 的宣称。
- **删除未使用/冗余的旧代码**：
  - 例如大量注释块、旧版兼容逻辑、过时代码片段。
- **分层与职责拆分**：
  - 借“只支持 4.x”的机会，按照 4.x 的 API 重新梳理节点与导入逻辑，将其拆到更清晰的模块中（特别是材质/节点构建部分）。

---

## 后续仅支持 Blender 4.x 的改造大纲（只做规划，不实施）

- **步骤 1：更新元信息与基础兼容声明**
  - 在 `__init__.py` 中将 `bl_info["blender"]` 最低版本调整为 `(4, 0, 0)`，移除 README/文案中对 2.x/3.x 的兼容描述（用户不要求生成/编辑 README 时只在代码内更新）。
- **步骤 2：清理显式版本分支**
  - 在 `ATBridge.py` 中：
    - 删除 OBJ 导入中 `< 2.92` 的分支，只保留 4.x 可用写法。
    - 删除 `CreateTextureMultiplyNode`/`CreateDisplacementSetup` 中 `< 3.3/3.4` 的旧节点类型分支，只保留 `ShaderNodeMix` 与 `ShaderNodeSeparateColor` 路径。
    - 简化 `GetBSDFInputName` 为仅处理 4.x 的输入名（或改为表驱动映射，并在代码顶部注明“仅适配 4.x”）。
    - 根据官方文档统一 Cycles 位移/`feature_set` 行为，去掉 `hasattr` 兼容逻辑。
- **步骤 3：核对并更新 4.x API 变化点**
  - 集中检查：`ShaderNodeMapping`、材质属性（位移、混合模式）、Alembic/OBJ/FBX 导入操作符参数签名，对照 4.x 文档保证使用当前推荐字段。
- **步骤 4：整理结构与错误处理**
  - 对 `MS_Init_ImportProcess` 进行初步拆分：
    - 将 JSON 解析与数据结构准备提取为独立函数；
    - 将材质/节点构建抽出为 `material_builder`/`node_builder` 模块，方便以后支持更多工作流或渲染引擎；
    - 在线程/Timer 与主线程之间增加更明确的“导入任务对象”，避免多个资产批次状态互相覆盖。
  - 统一异常处理策略：
    - 在 Operator 中尽量使用 `self.report` 提示用户，同时在控制台打印详细堆栈；
    - 删除纯 `except: pass` 的部分。
- **步骤 5：平台与路径相关的小改进**
  - 将 `fab_assets_path` 默认值改为更通用的路径（例如用户主目录下某个子目录），或默认空值，强制用户在首选项中设置，避免与操作系统强绑定。

以上是对当前代码架构、问题点及与 Blender 版本兼容相关内容的详细分析。你确认只支持 4.x 之后，我们可以按上述大纲分步实施改造。