# SEEG 代码算法设计计划（GitHub 标书基线）

## 1. 技术摘要

本计划将 GitHub 当前已跟踪标书 `CISCNThesis/祈祷一个好头.pdf` 转换为可执行的软件与算法研发路线。正式系统采用“先闭环、后增强”的四级实现：先完成数据接入、合法提交和可复现评分闭环，再建立手工特征基线与共享 TCN 强基线，随后实现质量感知的状态—边界—募集多任务模型，最后仅在患者级验证证明有效时加入时频融合、动态功能图、Top-10 忠实性、蒸馏和量化。

首要交付目标不是一次性实现标书中的全部候选模块，而是尽快形成一条满足赛事硬约束、能够端到端运行并拒绝非法输出的正式链路：

```text
FlyData 资源发现 -> 安全 NPZ 读取 -> 契约与质量检查
-> 确定性预处理 -> 变通道批处理 -> 模型训练/加载
-> 概率、onset、Top-10 推理 -> 全局阈值
-> prediction.csv 全量校验 -> 原子写入 output_path
```

标书提出的核心 QST-DPGNet 被拆为独立、可消融的组件。任何复杂模块只有在患者级或可证明无泄漏的分组验证中稳定改善官方相关指标，且不破坏概率校准、onset、Top-10 稳定性和五小时运行预算时，才进入最终提交模型。

## 2. 基线、范围与解释优先级

### 2.1 需求基线

| 优先级 | 来源 | 用途 |
|---:|---|---|
| 1 | 赛事平台当前页面与运行时资源 | 实际 `source_id`、资源权限、目录和执行环境 |
| 2 | `docs/赛事方资料/3. 复赛结果提交要求.md` | `prediction.csv` 字段、合法性和评分行为 |
| 3 | `reports/赛事算法系统构建规范.md` | 已归纳的输入、输出、平台和样例实测约束 |
| 4 | `CISCNThesis/祈祷一个好头.pdf` | 算法方案、模型结构、训练、推理和消融设计 |
| 5 | `CISCNThesis/example.tex`、`seeg_solution_continuation.tex` | PDF 对应的可检索技术细节 |

本计划锁定的 GitHub PDF 信息为：

- Git 提交：`ec034465dcb8a19fb717db146e94f5c8709fd5e7`
- PDF SHA-256：`8c3bc1e8186624a083763f56766a678109e1dc1797209579c5603f71e0a3de22`
- 页数：39 页

若赛事平台要求与标书设想冲突，以赛事平台和正式提交要求为准。若 GitHub 后续更新标书，应更新本节提交号和文件哈希，并重新执行需求追踪检查。

### 2.2 本次实现范围

必须进入比赛主链路的能力：

- 单包与 17 包两类赛事资源发现；
- 带零字节前缀 NPZ 的安全读取；
- 通道原名、原始索引和有效点掩码全程可追溯；
- `POL DC01`～`POL DC16` 默认排除神经模型和 Top-10；
- 变通道数、变有效长度的批处理；
- 发作概率、统一阈值、onset 和 Top-10 四类结果；
- 官方提交格式的阻断式校验和原子写出；
- 可复现配置、随机种子、模型哈希、端到端计时和简要日志。

条件模块：

- 三维坐标、脑区映射和解剖图仅在赛事提供可靠映射时启用；
- 患者级划分仅在患者 ID 或可信分组到位后启用；否则使用保守的近重复/记录组隔离，并明确验证局限；
- 动态功能图、Top-10 忠实性、蒸馏、剪枝和 INT8 均需通过预注册的保留门槛；
- Integrated Gradients、SmoothGrad 和逐通道遮挡只进入验证或疑难样本复核，不进入默认正式推理。

## 3. 赛事硬约束转换为代码验收条件

| 赛事要求 | 代码责任 | 阻断条件 |
|---|---|---|
| 通过 `FlyData` 读取资源 | `platform/flydata_adapter.py` | 资源不可枚举、训练/测试 ID 冲突或标签对不上文件 |
| 运行时可能是单包或 17 包 | `data/discovery.py` | 依赖固定包名、固定目录深度或字典顺序 |
| 唯一正式文件为 `prediction.csv` | `submission/writer.py` | 输出目录存在多份正式结果或写入未完成文件 |
| 结果覆盖全部且仅覆盖测试 ID | `submission/validator.py` | 缺 ID、多 ID、重复 ID 或顺序不可复现 |
| `prob` 和统一阈值属于 `[0,1]` | `inference/predictor.py`、`evaluation/thresholds.py` | NaN、Inf、越界或表内出现多个阈值 |
| onset 属于 `[0,60)` | `inference/onset.py` | 非有限值、越界或落入 padding 区 |
| 预测阳性必须有 10 个合法通道 | `inference/ranking.py` | 少于 10 个、重复、改名或不属于该样本 |
| 标签由 `prob >= threshold` 推导 | `submission/validator.py` | 另写 `label` 列或使用不同判定逻辑 |
| 代码包不超过 10 MB | 发布脚本与清单 | 打包数据、模型、缓存、图件或第三方归档 |
| 单次运行不超过 5 小时 | `runtime/profiler.py` | 端到端演练没有安全余量或超时后仍写正式结果 |
| 平台 NumPy 为 1.26.4 | 环境约束文件 | 使用 NumPy 2.x 专属接口或安装声明不兼容 |
| 正式阶段不可交互修复 | 单一 CLI 入口 | 依赖 Notebook、GUI、联网下载或人工输入 |

本地评分器实现已知部分：

```text
Score = 0.25*AUC
      + 0.15*F1
      + 0.10*Sensitivity
      + 0.10*Specificity
      + 0.25*ChannelScore
      + 0.15*OnsetScore

OnsetScore = max(0, 1 - MAE_onset / 60)
```

`ChannelScore` 的精确匹配和排序公式尚未由现有赛事资料完整说明，应封装为可替换策略。未知部分不得伪装成官方评分器。

## 4. 目标代码结构

现有 `data`、`analysis`、`visualization` 和 EEGLAB 导出代码继续保留。新增比赛系统建议采用以下结构：

```text
src/seeg_detector/
├── platform/
│   ├── flydata_adapter.py
│   └── runtime.py
├── data/
│   ├── io.py
│   ├── naming.py
│   ├── discovery.py
│   ├── contracts.py
│   ├── labels.py
│   ├── splits.py
│   ├── dataset.py
│   └── collate.py
├── preprocessing/
│   ├── pipeline.py
│   ├── quality.py
│   ├── line_noise.py
│   ├── resample.py
│   ├── reference.py
│   ├── normalize.py
│   └── windowing.py
├── features/
│   ├── handcrafted.py
│   ├── time_domain.py
│   ├── time_frequency.py
│   └── connectivity.py
├── models/
│   ├── outputs.py
│   ├── classical.py
│   ├── shared_tcn.py
│   ├── qst_dpgnet.py
│   ├── encoders.py
│   ├── fusion.py
│   ├── temporal.py
│   ├── graph.py
│   └── heads.py
├── training/
│   ├── engine.py
│   ├── losses.py
│   ├── sampling.py
│   ├── calibration.py
│   ├── checkpoints.py
│   └── reproducibility.py
├── inference/
│   ├── predictor.py
│   ├── aggregation.py
│   ├── onset.py
│   ├── ranking.py
│   └── abstention.py
├── evaluation/
│   ├── classification.py
│   ├── onset.py
│   ├── channels.py
│   ├── competition.py
│   ├── robustness.py
│   └── latency.py
├── submission/
│   ├── schema.py
│   ├── validator.py
│   └── writer.py
└── orchestration/
    ├── train.py
    ├── infer.py
    └── competition.py

configs/
├── competition.toml
├── data/full.toml
├── preprocessing/baseline.toml
├── model/handcrafted.toml
├── model/shared_tcn.toml
├── model/qst_dpgnet.toml
└── experiment/ablations/*.toml

scripts/
├── audit_full_data.py
├── train.py
├── evaluate.py
├── predict.py
└── run_competition.py
```

平台适配层不得渗入模型与评估模块。核心算法只接收普通路径、数据对象和配置，使本地测试不依赖 `flydata`。

## 5. 核心数据契约与接口

### 5.1 原始记录

```python
@dataclass(frozen=True)
class SeegRecord:
    sample_id: str
    signal: np.ndarray              # float32, [channels, samples]
    sampling_rate: float
    valid_samples: int
    raw_channel_ids: tuple[str, ...]
    raw_channel_indices: np.ndarray
```

加载时必须验证：

- `sample_id` 与文件名一致；
- `signal.ndim == 2`；
- 通道元数据长度与 `signal.shape[0]` 一致；
- `0 < valid_samples <= signal.shape[1]`；
- 有效区间可处理且异常数值被显式报告；
- 不启用 pickle。

### 5.2 预处理输出

```python
@dataclass(frozen=True)
class PreparedRecord:
    sample_id: str
    signal: torch.Tensor            # [valid_channels_or_all, time]
    sampling_rate: float
    sample_mask: torch.BoolTensor
    channel_mask: torch.BoolTensor
    channel_roles: tuple[str, ...]
    raw_channel_ids: tuple[str, ...]
    raw_channel_indices: torch.Tensor
    qc_features: torch.Tensor
    transform_metadata: Mapping[str, object]
```

任何滤波、重采样、插值、屏蔽、重参考和归一化操作都要记录参数及原因。模型索引只能是临时索引，输出必须回写 `raw_channel_ids`。

### 5.3 模型输入与统一输出

```python
@dataclass
class SeegBatch:
    waveform: torch.Tensor          # [B, C, T]
    channel_mask: torch.BoolTensor  # [B, C]
    frame_mask: torch.BoolTensor    # [B, K]
    qc_features: torch.Tensor       # [B, C, Q]
    channel_ids: list[tuple[str, ...]]
    sampling_rate: torch.Tensor

@dataclass
class ModelOutput:
    clip_logit: torch.Tensor        # [B]
    state_logits: torch.Tensor      # [B, K]
    onset_logits: torch.Tensor      # [B, K]
    recruitment_logits: torch.Tensor  # [B, C, K]
    channel_scores: torch.Tensor    # [B, C]
    frame_times: torch.Tensor       # [B, K]
    auxiliary: dict[str, torch.Tensor]
```

手工基线、共享 TCN 和 QST-DPGNet 均返回同一 `ModelOutput`。不支持的头可以返回形状合法的中性结果并在能力声明中标记，禁止让不同模型拥有不同提交逻辑。

## 6. 数据与预处理实现计划

### 6.1 资源发现与安全读取

1. 递归解析 `FlyData.load_file(source_id)` 返回树和实际落盘目录。
2. 枚举所有 `label.csv`、`train_*.npz`、`test_*.npz` 及压缩包，不依赖文件顺序。
3. 跨包合并标签并检查 ID 唯一性、文件覆盖、Top-10 合法性。
4. 复用现有 `seeg_detector.data.load_record` 读取普通或带前置零字节的 NPZ。
5. 将审计清单保存为小型 CSV/JSON；正式输出目录不保存波形或中间张量。

### 6.2 通道角色与质量控制

通道角色规则：

- `^POL DC(?:0[1-9]|1[0-6])$` -> `auxiliary_dc`；
- 可解析的普通连续通道 -> `seeg_candidate`；
- `POL E` 等异常名称 -> `special_review`；
- padding -> `invalid`。

每通道至少计算有限值比例、平直率、稳健尺度、峰峰值、削顶/饱和代理、极端跳变率、50/100 Hz 相对背景功率、谱熵和宽带异常。QC 先产生分数和 mask，不依据未确认物理单位设置绝对微伏阈值。

### 6.3 确定性预处理顺序

```text
截取 valid_samples
-> 保留原始映射
-> 通道角色判定
-> 滤波前 QC
-> 屏蔽 DC 与确定坏道
-> 条件式 50 Hz/谐波处理
-> 抗混叠重采样
-> 可选重参考
-> 去中位数 + MAD/IQR 稳健缩放 + clip
-> 滑窗和 mask
```

初始工程配置：

- 主采样率先比较 256 Hz 与 512 Hz；完整数据未证明 100 Hz 以上信息有稳定增益前，以 256 Hz 低成本基线优先；
- 主窗口 4 s、步长 0.5 s；帧间隔约 0.125 s；
- 50 Hz 处理采用可复现窄带方案作为基线，自适应正弦回归作为候选；
- 重参考先保留原参考，稳健 CAR 和相邻双极作为独立消融；
- 双极参考只有在电极轴与相邻编号可信、且能保证官方通道回写语义时才启用。

所有参数必须配置化。上述值是标书初始建议，不是最终固定最优值。

### 6.4 数据划分与泄漏控制

优先级如下：

1. 有可信患者 ID：使用患者级分层交叉验证和独立校准患者集。
2. 无患者 ID、但有连续记录/发作组：按记录组隔离。
3. 两者均无：使用文件哈希、降采样波形指纹、频谱指纹和通道表相似性建立近重复组，再进行组级划分。

任何情况下，相邻窗口、增强版本和同一 NPZ 都不得跨训练与验证。若不能证明患者级隔离，报告只能称为“组级内部验证”，不得声称跨患者泛化。

## 7. 四级模型路线

### 7.1 L0：规则与提交烟雾基线

目标是验证完整 I/O 和评分链路，不追求研究性能。

- 固定或训练集先验概率；
- onset 使用合法占位或简单能量变化规则，仅用于接口验证；
- Top-10 使用质量合格通道的确定性排序；
- 输出必须通过正式校验器。

验收：在本地模拟资源和故障样本上，从资源发现到 `prediction.csv` 全流程稳定运行；相同输入字节级复现相同 CSV。

### 7.2 L1：手工特征强基线

每个通道/窗口提取线长、稳健方差、Hjorth 参数、谱带功率、谱熵、频谱斜率、瞬态率、相对基线变化和简化同步指标。通过通道内统计和掩码聚合得到片段特征，使用 Logistic Regression、LightGBM 或 XGBoost 比较。

用途：

- 检查信号是否存在稳定可学证据；
- 建立概率校准和阈值搜索框架；
- 提供神经网络失败时的低风险回退；
- 为 Top-10 生成可解释的早期变化基线。

### 7.3 L2：共享 TCN 多任务强基线

结构：

```text
每通道共享多尺度 1D 卷积
-> 通道 mask 感知池化
-> 扩张深度可分离 TCN
-> clip/state/onset/recruitment 四头
```

该层先不加入动态图。它直接验证标书最关键的三个假设前提：共享通道编码是否支持变植入布局，帧级状态是否改善分类与 onset，募集头是否能从 Top-10 弱监督中学习有效通道排序。

### 7.4 L3：QST-DPGNet 核心模型

在 L2 上按顺序增加：

1. 时域—时频门控融合；
2. 质量特征门控和质量感知通道池化；
3. 信号驱动的稀疏动态功能图；
4. 状态—边界—募集一致性损失；
5. Top-10 充分性、必要性和扰动稳定性损失。

动态图初版不依赖三维坐标：以编码特征、滞后相关或轻量有向打分构建每节点 Top-k 邻接，并保留自残差。若坐标可靠，再增加静态解剖邻接，并使用显式缺失 mask。

### 7.5 L4：部署模型

以通过联合指标验证的 L2/L3 模型为教师，训练轻量学生模型。候选优化顺序：

1. 混合精度推理；
2. 减少通道嵌入维度、TCN 层数和动态图邻居数；
3. 知识蒸馏；
4. 结构化剪枝；
5. ONNX；
6. 在目标环境支持且联合指标可接受时评估 INT8。

每次压缩后必须重新校准概率，并检查 onset 偏差、Top-10 Jaccard 和端到端时延，不能只比较 AUC。

## 8. 监督信号与联合损失

### 8.1 可用真值边界

赛事训练标签当前明确提供：

- 片段级 `label`；
- 阳性片段 `onset_time`；
- 阳性片段排序 Top-10 通道。

当前没有明确 offset、逐帧状态真值、逐通道募集时间或传播边真值。因此：

- clip 头使用强监督；
- onset 头以标注时间为中心构建窄高斯软标签；
- state 头采用部分标签或多实例约束，不把 onset 后全部帧永久硬标为发作；
- recruitment 头使用 Top-10 排序监督与 onset 邻域伪标签；
- 动态图传播方向只作为辅助表征，不当作有临床真值的监督任务。

### 8.2 分阶段损失

```text
阶段 A：L_clip
阶段 B：L_clip + L_state(partial/MIL) + L_onset
阶段 C：阶段 B + L_recruit(rank) + L_transition
阶段 D：阶段 C + L_fidelity + L_graph_regularization
```

建议实现：

- `L_clip`：加权 BCE 与非对称 Focal 二选一；
- `L_state`：有监督帧用 Focal BCE，可确认区域用 Soft Dice，未知帧通过 mask 排除；
- `L_onset`：高斯软边界 BCE/Focal，并单独记录时间偏差；
- `L_recruit`：Top-10 与非 Top-10 候选的 pairwise/listwise 排序损失；若赛事 Top-10 本身有内部顺序，则保留顺序监督；
- `L_transition`：抑制孤立峰和频繁切换，并约束边界后持续状态证据；
- `L_fidelity`：充分性、必要性、扰动稳定性和目标基数约束，仅在预热后、部分批次启用；
- `L_reg`：权重衰减、动态图稀疏和方向稳定性。

损失权重不以一次实验主观确定。先保证各头独立可学习，再在训练折内按联合目标调整；某辅助损失导致主任务或校准显著退化时退出。

## 9. 训练与校准计划

### 9.1 训练流程

```text
冻结数据清单与分组
-> 拟合训练折预处理统计量
-> 训练 L1/L2 基线
-> 选择候选架构
-> 加入多任务头
-> 加入时频/质量/动态图消融
-> 困难负样本挖掘
-> Top-10 忠实性微调
-> 独立校准集温度缩放
-> 全局阈值搜索
-> 固化模型、配置和哈希
```

默认优化器为 AdamW，配合线性预热、余弦退火、梯度裁剪和早停。采样器同时平衡类别和患者/记录组，不能通过简单复制阳性样本制造相邻窗口泄漏。

增强包括幅值缩放、轻量有色噪声、时间/频带遮挡、随机通道丢弃和轻微基线漂移。改变时间轴的增强必须同步更新 onset 标签；不能可靠更新时不得用于 onset 训练。

### 9.2 概率与阈值

在独立的患者级或组级校准集上执行温度缩放。阈值只能有一个全表值，通过本地复刻的比赛加权指标搜索，同时报告 AUC、F1、Sensitivity、Specificity、onset 和通道指标，不能只优化准确率。

模型内部保留未舍入概率，CSV 中 `prob` 四舍五入至 6 位小数。正式类别、onset 和 Top-10 完整性必须按照序列化后的概率与阈值重新验证，防止临界概率舍入后跨过阈值。

## 10. 推理、onset 与 Top-10 设计

### 10.1 重叠窗口聚合

使用 4 s 窗口和 0.5 s 步长作为初始配置。状态和边界序列以 Hann 或三角中心权重重建；padding 帧权重为零。统一补偿重采样映射、窗口中心和因果滤波延迟。

### 10.2 onset 状态机

```text
重建 state/onset 序列
-> 短尺度中值/高斯平滑
-> 高阈值触发、低阈值维持
-> 最短持续时间检查
-> 边界局部峰与状态上升联合打分
-> 可选单一变化点校正
-> 延迟补偿与 [0, 60) 截断
```

特殊情况：

- 预测阴性：输出赛事建议的 `0.0`；
- 首帧已持续高概率：输出 `0.0`，内部记录左删失；
- 仅 padding 区有高概率：不得触发；
- 多候选发作：按正式规则选择最早满足持续性和边界证据的候选；
- 低置信度：比赛仍需合法输出，内部日志记录置信度和原因。

### 10.3 Top-10 排序

阳性样本在 onset 邻域内计算：

```text
早期募集强度
+ 首次持续募集潜伏期
+ 节律/频谱持续演化
+ 动态图净外流（启用图模型时）
+ 模型募集头分数
- 坏道与伪迹风险
```

各分量先做样本内秩归一化，再按验证集确定的非负权重组合。候选集合只包含合法、质量可用的 SEEG 通道；DC、padding 和确定坏道被排除。并列分数以原始通道顺序或原始索引进行固定次级排序，保证确定性。

若预测阳性但质量合格候选少于 10 个，采用以下顺序扩展：先纳入低置信但非 DC 的普通候选，再纳入 `special_review`；仍不足 10 个时阻断提交并报告数据契约问题，不伪造名称。

## 11. 评估、消融与保留门槛

### 11.1 指标体系

| 目标 | 主指标 | 辅助检查 |
|---|---|---|
| 分类 | AUC、F1、Sensitivity、Specificity | PR-AUC、Brier、ECE、患者/组级分布 |
| onset | MAE、有符号误差、±1 s/±3 s 命中率 | 左删失、假 onset、置信度分层 |
| Top-10 | 官方 ChannelScore（公式确认后） | Hit@k、NDCG、Jaccard、Kendall/Spearman |
| 忠实性 | Top-10 遮挡后 logit 下降 | 仅保留 Top-10 的概率保持率、随机遮挡对照 |
| 鲁棒性 | 通道丢弃、轻噪声、时间偏移后的性能 | 排名稳定性、onset 方差 |
| 部署 | 端到端 P50/P95、总时长、峰值内存/显存 | 单阶段耗时和输出大小 |

所有结果按患者或可信记录组聚合；在患者 ID 不可用时，必须并列报告验证限制。

### 11.2 核心消融顺序

1. L1 手工特征 vs L2 共享 TCN；
2. 单片段头 vs state/onset 多任务头；
3. 时域单分支 vs 时域—时频门控融合；
4. 无质量输入 vs 质量门控；
5. 无图 vs 静态相关图 vs 动态功能图；
6. 仅模型分数 vs onset 感知通道评分；
7. 无忠实性损失 vs 充分性/必要性/稳定性；
8. 256 Hz vs 512 Hz；
9. 原参考 vs 稳健 CAR vs 条件性双极；
10. 教师模型 vs 蒸馏/剪枝/量化模型。

### 11.3 模块保留规则

在查看测试折结果前为每项实验登记：目标指标、允许退化项、重复次数、随机种子和硬件预算。保留模块至少满足：

- 改善超过重复实验或折间随机波动，而非单次最优；
- 不以明显降低 Sensitivity、onset 或 ChannelScore 换取少量 AUC；
- 不显著恶化概率校准；
- 不突破五小时端到端预算；
- 代码复杂度、故障风险和部署收益合理。

不满足时回退到更简单模型。标书中的 H1～H5 均按这一规则接受证伪。

## 12. 测试计划

### 12.1 单元测试

- 普通和零前缀 NPZ；
- 字段缺失、损坏成员、NaN/Inf、非法 `valid_samples`；
- 通道角色、大小写、前导零和 `-Ref` 保真；
- DC、坏道和 padding 不参与模型池化与 Top-10；
- 重采样时间映射、窗口标签和 onset 帧索引；
- 变通道 collate 和 mask；
- 所有损失在空监督、部分监督和全 mask 情况下数值有限；
- onset 输出范围和延迟补偿；
- Top-10 并列分数的确定性；
- CSV schema、全局阈值、ID 覆盖和原子写出。

### 12.2 集成测试

- 单包与 17 包模拟资源树；
- 从训练清单到一个 epoch、校准、推理和提交；
- CPU-only 与单 GPU；
- 不同通道数、采样率、有效长度和候选不足；
- 模型 checkpoint 与配置不匹配时明确失败；
- 中断、磁盘不足和输出目录已有文件时不留下半成品。

### 12.3 防泄漏和回归测试

- 同一文件、近重复记录和相邻窗口不能跨集合；
- 预处理统计量只由训练折拟合；
- 校准和阈值选择不读取测试标签；
- 通道顺序置换后，回写名称仍正确；
- 固定种子下 CSV 字节级一致；
- 每次模型改动运行保存的小型黄金样本回归测试。

## 13. 分阶段实施与交付物

### 阶段 0：环境与契约闭环

实现内容：平台兼容依赖、资源发现、数据契约、提交 schema、校验器、原子写出和单一 CLI。

交付物：

- `constraints-platform.txt` 或等效锁定文件；
- `scripts/run_competition.py`；
- 输入和提交单元测试；
- L0 合法提交样例。

退出条件：模拟单包和 17 包均能生成合法、确定性的完整 CSV；非法输入不会静默继续。

### 阶段 1：数据审计与传统基线

实现内容：完整数据清单、分组/近重复检查、确定性预处理、L1 特征基线、阈值和已知评分复刻。

交付物：版本化审计报告、划分清单、特征配置、基线结果和端到端计时。

退出条件：能够解释每个输入变换和每个输出字段；验证结果不存在已知切片泄漏。

### 阶段 2：共享 TCN 多任务基线

实现内容：变通道 batch、共享多尺度编码器、TCN、clip/state/onset/recruitment 四头、部分监督和重叠推理。

交付物：L2 checkpoint、训练曲线、校准参数、onset 状态机和 Top-10 排序器。

退出条件：四类输出全部来自统一模型链路；相较 L1 的收益在分组验证中可重复。

### 阶段 3：QST-DPGNet 增强

实现内容：时频融合、质量门控、动态功能图、一致性和忠实性损失。

交付物：逐模块消融表、快速排序与离线遮挡对照、鲁棒性测试。

退出条件：只有通过联合保留门槛的模块进入候选正式模型；其余通过配置关闭。

### 阶段 4：部署优化与沙箱演练

实现内容：蒸馏/剪枝/ONNX/量化候选、缓存和批量推理、故障注入、五小时预算演练。

交付物：最终 checkpoint/哈希、生产配置、代码包清单、时延与资源报告、作品说明。

退出条件：目标环境完整运行有安全余量；输出目录只有一个经重读验证的 `prediction.csv`。

### 阶段 5：提交冻结

冻结代码提交、依赖、配置、随机种子、模型文件及哈希。仅允许修复阻断提交的缺陷；任何模型或预处理变化都必须重新执行校准、完整验证和端到端演练。

## 14. 配置与可复现性

每次实验至少记录：

- Git commit 与 dirty 状态；
- 数据资源 ID、清单哈希和划分哈希；
- Python/NumPy/PyTorch/CUDA 版本；
- 完整配置和随机种子；
- 预处理统计量与阈值；
- 模型 checkpoint SHA-256；
- 训练、校准、推理和写出时长；
- 分类、onset、Top-10、鲁棒性和资源指标；
- 启用/关闭的条件模块及原因。

配置加载后执行 schema 校验，未知键默认报错，避免拼写错误被静默忽略。生产日志不得包含原始波形、患者信息或大数组。

## 15. 当前阻断项与需确认事项

### 开发前必须解决

1. 将 `pyproject.toml` 的 NumPy 约束调整为兼容平台 1.26.4，并建立平台版本测试环境。
2. 获取平台实际 `source_id` 和正式资源目录样例。
3. 确认是否提供患者 ID、记录组或其他可用于隔离的标识。
4. 核验训练 Top-10 是否具有严格顺序语义。

### 不阻断基础开发，但会影响最终实现

1. ChannelScore 的精确公式；
2. onset 的标注定义、评分对象和容忍规则；
3. 信号单位、参考电极、硬件滤波和通道命名含义；
4. 两套数据的测试 ID 是否一致；
5. RAR 在生产环境中的展开方式；
6. GPU、CPU、内存、磁盘和 DataLoader 的实际配额；
7. 是否提供坐标、脑区标签、CT/MRI 或专家 SOZ 信息。

上述问题均采用“接口预留 + 保守默认 + 显式日志”处理，不用未经证实的推测固化算法。

## 16. 标书到代码的追踪矩阵

| 标书设计 | 代码模块 | 首次落地阶段 | 验证方式 |
|---|---|---:|---|
| 数据审计与泄漏排查 | `data/contracts.py`、`data/splits.py` | 0～1 | 哈希/指纹、元数据探针、组级隔离测试 |
| 质量感知预处理 | `preprocessing/quality.py`、`pipeline.py` | 1 | 滤波前后 QC、坏道注入测试 |
| 多尺度时域编码 | `models/encoders.py` | 2 | L1/L2 对照和频带/时域敏感性 |
| 时频门控融合 | `features/time_frequency.py`、`models/fusion.py` | 3 | 时域单支 vs 融合消融 |
| 变通道建模 | `data/collate.py`、mask 感知池化 | 2 | 通道置换、缺失与 padding 测试 |
| 动态功能图 | `features/connectivity.py`、`models/graph.py` | 3 | 无图/静态/动态图患者级消融 |
| 帧级状态与边界头 | `models/heads.py` | 2 | onset MAE、偏差和持续性 |
| 通道募集头 | `models/heads.py`、`inference/ranking.py` | 2 | Top-10/NDCG、早期性和稳定性 |
| Top-10 忠实性 | `training/losses.py` | 3 | 遮挡、仅保留 Top-10、随机对照 |
| 概率校准 | `training/calibration.py` | 1～2 | Brier、ECE、可靠性曲线 |
| onset 后处理 | `inference/aggregation.py`、`onset.py` | 2 | 单阈值/滞回/校正消融 |
| 轻量化部署 | `models` 导出与运行时工具 | 4 | 联合指标、P50/P95、五小时演练 |
| 条件性空间映射 | 独立 `spatial/` 包（数据到位后） | 条件阶段 | 坐标完整性、配准误差、接点级验证 |

## 17. 完成定义

代码算法设计完成并可进入正式提交，必须同时满足：

- 四类赛事输出均有可训练、可推理、可校验的实现；
- 正式 CSV 全量覆盖测试集，字段和通道名称严格合法；
- 数据划分、预处理、校准和阈值不存在已知泄漏；
- DC、坏道和 padding 不影响模型池化或 Top-10；
- 模型在变通道、异常输入和 CPU-only 情况下有明确行为；
- 所有启用的复杂模块有患者级或可信组级消融证据；
- 概率、onset 和 Top-10 在压缩后重新验证；
- 完整流程在目标环境五小时限制内留有安全余量；
- 配置、代码、数据清单、模型和结果均可由哈希追溯；
- `Dataset/`、`SecRnd/`、模型权重、缓存和正式数据未进入 Git。

在这些条件满足前，任何单次高分都只视为实验结果，不视为可提交的算法系统。
