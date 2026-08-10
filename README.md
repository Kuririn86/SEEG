# 基于 SEEG 的癫痫发作状态智能检测

本仓库用于开发“基于 SEEG 的癫痫发作状态智能检测”竞赛方案与算法系统，包括技术方案、CISCN LaTeX 标书、科研图件、数据读取与质量检查代码。当前已建立可复现的数据探索骨架；训练与推理模块仍待赛事完整数据和患者映射到位后实现。

## 当前版本

当前评审基线为 **V3 评委可读版**。V3 将方案收敛为“预处理—时域卷积与 STFT—门控融合—TCN—状态、概率、onset 和 Top-10 输出”主线，将动态图、小波、空间坐标和脑区映射降为验证后或数据具备时启用的条件模块。

| 文件 | 用途 |
|---|---|
| [`CISCNThesis/祈祷一个好头_v3.pdf`](CISCNThesis/祈祷一个好头_v3.pdf) | 当前中文标书成品 |
| [`CISCNThesis/SEEG_proposal_v3.pdf`](CISCNThesis/SEEG_proposal_v3.pdf) | 与中文成品对应的 ASCII 文件名副本 |
| [`CISCNThesis/example_v3.tex`](CISCNThesis/example_v3.tex) | V3 主 LaTeX 文件 |
| [`CISCNThesis/seeg_solution_continuation_v3.tex`](CISCNThesis/seeg_solution_continuation_v3.tex) | V3 后续章节 |
| [`CISCNThesis/cumcmthesis_v3.cls`](CISCNThesis/cumcmthesis_v3.cls) | V3 文档类与版式设置 |
| [`CISCNThesis/修改说明_v3.md`](CISCNThesis/修改说明_v3.md) | V3 修改原则、图件清单和编译说明 |
| [`SEEG癫痫发作状态智能检测算法方案_ACEHolix.md`](SEEG癫痫发作状态智能检测算法方案_ACEHolix.md) | 完整技术方案与论证依据 |
| [`reports/赛事算法系统构建规范.md`](reports/赛事算法系统构建规范.md) | 赛事规范、样例检查结论、输入处理、输出评分、沙箱部署和系统结构 |
| [`reports/代码算法设计计划_GitHub标书版.md`](reports/代码算法设计计划_GitHub标书版.md) | 以 GitHub 标书为基线的代码模块、模型路线、接口、测试、里程碑和验收计划 |

V3 是面向评委阅读的精简重构，不要求与完整技术方案逐字一致。无后缀版本和 V2 文件作为历史版本保留。

## 目录结构

```text
SEEG/
├── README.md
├── AGENTS.md
├── SEEG癫痫发作状态智能检测算法方案.md
├── SEEG癫痫发作状态智能检测算法方案_ACEHolix.md
├── CISCNThesis/
│   ├── example_v3.tex
│   ├── seeg_solution_continuation_v3.tex
│   ├── cumcmthesis_v3.cls
│   ├── 祈祷一个好头_v3.pdf
│   ├── 修改说明_v3.md
│   └── tmp/pdfs/seeg_figures_zh_final_v3/
├── src/seeg_detector/       # 可复用算法代码
│   ├── data/                # NPZ 兼容读取与字段校验
│   ├── analysis/            # 数据描述与质量检查
│   ├── visualization/       # SEEG 波形与科研图件
│   ├── preprocessing/       # 预处理（待实现）
│   ├── models/              # 模型（待实现）
│   ├── training/            # 训练与患者级划分（待实现）
│   ├── evaluation/          # 指标和提交格式（待实现）
│   └── inference/           # 状态/onset/Top-10 推理（待实现）
├── configs/                 # 数据、模型、训练和推理配置
├── scripts/                 # 可复现命令行入口
├── notebooks/               # 数据探索与实验 notebook
├── tests/                   # 数据泄漏、读取和格式测试
├── assets/figures/          # 可追踪的正式图件
├── reports/                 # 数据描述等可追踪报告
├── Dataset/                 # 本地赛题数据，不提交 Git
└── SecRnd/                  # 本地赛题/支持资料，不提交 Git
```

`CISCNThesis/tmp/pdfs/seeg_figures_zh_final_v3/` 保存 V3 图件的 Python、TikZ、SVG、PDF、PNG 和 TIFF 版本。修改图件时应优先编辑源文件并重新生成，不直接修改 PDF。

## 算法开发环境

建议使用 Python 3.10 或更新版本。在仓库根目录创建环境并安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

样例数据存在一项兼容性问题：多数 NPZ 文件带有零字节前缀，不能直接用 `numpy.load(path)`。项目内的 `seeg_detector.data.load_record` 使用安全的 ZIP/NPY 成员读取方式，并始终禁用 pickle。

生成数据描述和波形图：

```bash
PYTHONPATH=src python3 scripts/describe_sample_data.py
PYTHONPATH=src python3 scripts/plot_sample_waveforms.py
```

输出分别位于 `reports/sample_data_description.md`、`reports/sample_file_profile.csv` 和 `assets/figures/sample_waveforms_onset.{png,svg,pdf}`。

计算阳性样例的 onset 对齐生理特征，并生成记录级结果表与科学图件：

```bash
PYTHONPATH=src python3 scripts/analyze_onset_features.py
```

分析报告位于 `reports/onset_feature_analysis.md`，原始结果表位于 `reports/onset_features/`；该样例分析以记录为独立单位，不把通道或滑窗当作独立样本。

第二轮进一步加入多通道招募、lead–lag 外流和动态网络特征，并执行网络窗与严重线噪通道敏感性分析：

```bash
PYTHONPATH=src python3 scripts/analyze_propagation_sensitivity.py
PYTHONPATH=src python3 scripts/analyze_onset_features_round2.py
```

第二轮报告位于 `reports/onset_feature_analysis_round2.md`，共比较第一轮 17 项与新增 16 项传播特征。

运行基础测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 阶段 0：赛事契约闭环

算法系统已开始按[代码算法设计计划](reports/代码算法设计计划_GitHub标书版.md)实施。当前阶段提供平台隔离的数据发现、NPZ metadata 轻量读取、预测数据契约、阻断式提交校验、原子写出和统一非交互入口。

使用本地样例执行全阴性的契约烟雾测试：

```bash
PYTHONPATH=src python3 scripts/run_competition.py \
  --data-root Dataset/sampleData \
  --output-dir /tmp/seeg-stage0-output \
  --smoke-baseline
```

该命令只验证资源发现、测试 ID 覆盖、通道元数据和 `prediction.csv` 格式，不代表已训练模型或算法性能。接入赛事完整资源后可增加 `--strict-full-data`，要求每一行训练标签均有对应 NPZ。在赛事平台中改用 `--source-id`，输出路径由 `FlyData.output_path()` 提供。

## 样例数据 M0 试训练

本地样例只有 20 个有标签训练文件和 4 个无标签测试文件。以下命令训练布局无关的手工时域—频带特征逻辑回归基线，使用相同通道 ID 序列作为患者映射缺失时的保守分组代理，执行留一组折外评估，并为无标签测试文件生成合法的 `prediction.csv`：

```bash
PYTHONPATH=src python3 scripts/train_sample_baseline.py \
  --data-root Dataset/sampleData \
  --output-dir outputs/sample_baseline_trial
```

输出包括模型、逐样本折外预测、指标 JSON、报告和测试预测。赛事材料尚未公开 ChannelScore 的精确排序公式，因此报告只提供明确标记的重合率与 rank-aware 代理分；无标签 `test_*` 文件不能计算平台测试分，20 个样例上的折外结果也不能外推为正式赛性能。

赛事环境版本约束见 [`constraints-platform.txt`](constraints-platform.txt)，其中 NumPy 固定为平台公布的 1.26.4；项目安装声明也已取消对 NumPy 2.x 的依赖。

## 导出到 EEGLAB

将本地现有训练样例批量导出为 EEGLAB 原生 `.set` 文件：

```bash
PYTHONPATH=src python3 scripts/export_eeglab.py
```

默认输出到 `outputs/eeglab_sample/`。阳性记录包含类型为 `seizure_onset` 的 `EEG.event` 和 `EEG.urevent`；事件位置按 EEGLAB 的 1 基采样点约定计算为 `onset_time * EEG.srate + 1`。阴性记录的事件表为空。幅值数据保持 `float32`，不重参考、不滤波、不降采样。`POL DC01`–`POL DC16` 作为设备辅助 DC 输入保留但标记为 `MISC`，`POL ACxx` 与其他脑电候选通道标记为 `SEEG`；神经模型输入默认排除 DC 通道。

EEGLAB 的通道检查会自动移除部分标签开头的 `EEG ` 前缀。为保留赛事官方通道 ID，完整原名同时写入 `EEG.chanlocs.original_label` 和 `EEG.etc.original_channel_ids`，原始零基通道索引写入 `EEG.chanlocs.raw_index`。

导出单个记录或同时导出测试集：

```bash
PYTHONPATH=src python3 scripts/export_eeglab.py --sample-id train_000027
PYTHONPATH=src python3 scripts/export_eeglab.py --split all
```

在 MATLAB 中加载并查看 marker：

```matlab
[ALLEEG, EEG, CURRENTSET, ALLCOM] = eeglab;
EEG = pop_loadset('filename', 'train_000027.set', ...
    'filepath', fullfile(pwd, 'outputs', 'eeglab_sample'));
EEG = eeg_checkset(EEG, 'eventconsistency');
pop_eegplot(EEG, 1, 1, 1);
```

橙色或彩色竖线即 `seizure_onset` marker。`scripts/validate_eeglab_exports.m` 可批量加载目录中的全部 `.set` 并复核事件时间。

## 编译 V3 标书

需要 Python 3 和 XeLaTeX。在 `CISCNThesis/` 目录执行：

```bash
python3 tmp/pdfs/seeg_figures_zh_final_v3/text_flow_with_placeholders_v1.py
xelatex -output-directory=tmp/pdfs/seeg_figures_zh_final_v3 tmp/pdfs/seeg_figures_zh_final_v3/onset-v3.tex
xelatex -interaction=nonstopmode -halt-on-error example_v3.tex
xelatex -interaction=nonstopmode -halt-on-error example_v3.tex
xelatex -interaction=nonstopmode -halt-on-error example_v3.tex
```

连续编译三次用于更新目录、引用和页码。编译完成后应人工检查中文字体、公式、表格宽度、图件清晰度、交叉引用和空白页。

## 提交前检查

在仓库根目录执行：

```bash
git diff --check
rg -n 'TO''DO|FIX''ME|T''BD' --glob '*.md'
rg -n '^(<<<<<<<|=======|>>>>>>>)' --glob '*.md' --glob '*.tex'
git status --short
```

涉及正文时还应使用 `git diff --word-diff` 核对措辞；涉及 LaTeX 或图件时必须检查新生成的 PDF。任何性能数字均应注明患者级数据划分、指标定义、数据来源和运行硬件。

## 数据与版本管理

- `Dataset/`、`SecRnd/`、模型权重、缓存、实验输出和第三方压缩包仅限本地使用，不应提交。
- 新的大版本使用独立后缀，并配套 `修改说明_<version>.md`；不要覆盖旧版标书。
- Top-10 表示模型判定的重要记录通道，不能直接等同于临床 SOZ、EZ 或手术靶点。
- 未经真实患者级实验验证，不写入推测性的精度、时延或泛化结论。

详细协作规则见 [`AGENTS.md`](AGENTS.md)。
