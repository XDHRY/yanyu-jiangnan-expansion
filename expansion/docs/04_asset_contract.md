# 资产、实例与完成状态

asset_id表示可复用资产种类，例如JNX_A001；instance_id表示摆放实例，例如JNX_D02_BLD_004。二者不可混用。同一资产可以实例化几十次，但这不增加独立资产种类数。

建议manifest字段：schema_version、task_id、asset_id、name_cn、status、source_file、generator_entry、parameters、seed、variant、units、up_axis、nominal_bounds、actual_bounds、origin、sockets、materials、lods、collision、preview_files、limitations。所有不存在的产物写null或单独planned，不写虚假路径冒充成功。

socket由name、type、position_local、direction_local、tolerance_m、compatible_families组成。记录端点归属与是否已接通。模型相连后仍能追踪原任务和版本，合并对象时保留源ID映射。

planned：只有规格；blockout：已经运行生成初版形体；implemented：任务要求的细节已在文件中实现；validated：实际运行及对应检查已有证据。单写Python文件处于framework阶段，不自动提升96张任务卡。

交付模型可编辑，层级命名清楚，原点和单位正确。近景模型的开口、厚度、背面需要真实几何；概念图和贴图不算完成模型。低模替代件可用于未完成项，但manifest必须明确proxy_for及限制。
