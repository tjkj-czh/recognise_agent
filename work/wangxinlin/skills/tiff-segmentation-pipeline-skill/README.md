# tiff-segmentation-pipeline-skill

按 `DazhuangSkill-Creator-main` 标准封装的项目技能，用于 recognise_agent 的 TIFF 上传 → 切片准备 → 分割识别 → 矢量结果核验与绘制联调。

## 目录
- `SKILL.md`：技能主体（规则 + 工作流程）
- `config.yaml`：默认参数
- `references/`：接口契约、排障、测评规范
- `assets/output-format.md`：输出模板
- `scripts/`：执行与测评脚本
- `evals/trigger-eval-set.json`：触发测评集

## 快速使用
```bash
py -3 scripts/run_pipeline.py --base-url http://127.0.0.1:5000 --tiff "D:/data/demo.tif"
```

## 校验
```bash
py -3 ../DazhuangSkill-Creator-main/scripts/quick_validate.py . --strict
```
