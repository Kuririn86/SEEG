# SEEG Apptainer 环境

该环境以 `/home/tuoxiaoying/singularity/pytorch_25.10-py3.sif` 为 NVIDIA/CUDA 基础镜像，将 Python 科学计算和 PyTorch 版本对齐到赛事公布环境，并安装本仓库进行训练、测试、解释和 ONNX 导出所需的附加工具。

## 构建可编辑 sandbox

在仓库根目录执行：

```bash
apptainer build --fakeroot --sandbox \
  /home/tuoxiaoying/singularity/seeg_competition_edit \
  containers/seeg_competition.def
```

`seeg_competition_edit/` 是可写目录镜像。后续临时修改使用：

```bash
apptainer exec --fakeroot --writable \
  /home/tuoxiaoying/singularity/seeg_competition_edit bash
```

## 固化为 SIF

```bash
apptainer build --fakeroot --mksquashfs-args '-processors 4' \
  /home/tuoxiaoying/singularity/seeg_competition_cuda.sif \
  /home/tuoxiaoying/singularity/seeg_competition_edit
```

限制 squashfs 并发可避免高核心数主机上的 `Bug in orderer`。原始
`pytorch_25.10-py3.sif` 不会被覆盖。

## 验证

```bash
apptainer exec --nv \
  /home/tuoxiaoying/singularity/seeg_competition_cuda.sif \
  python3 /opt/seeg/container/verify_environment.py --require-cuda

apptainer exec --nv \
  --bind /home/tuoxiaoying/Documents/Research/SEEG:/workspace/SEEG \
  --pwd /workspace/SEEG \
  /home/tuoxiaoying/singularity/seeg_competition_cuda.sif \
  bash -lc 'PYTHONPATH=src python3 -m unittest discover -s tests -v'
```

运行 CUDA 程序必须传递 `--nv`。容器设置了 `PYTHONNOUSERSITE=1`，避免宿主机用户级 Python 包污染镜像内版本。
Matplotlib 和 Numba 缓存被重定向至 `/tmp`，因此只读 SIF 中也可正常导入 MNE。
