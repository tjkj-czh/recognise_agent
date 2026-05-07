"""用地合规提示Agent Demo - 入口文件。

使用方式:
1. 配置环境变量: set ZHIPU_API_KEY=your_key (智谱) 或 set OPENAI_API_KEY=your_key (OpenAI)
2. 安装依赖: pip install -r requirements.txt
3. 运行: python main.py
"""

import json
import sys
import os

# 修复Windows终端编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agent.core import run_agent
from rules.compliance_rules import evaluate_rules


def run_rule_engine_demo(parcel_data: dict):
    """纯规则引擎模式：不依赖大模型，用硬规则直接匹配。"""
    print("\n" + "=" * 60)
    print("【纯规则引擎模式】（无需大模型API）")
    print("=" * 60)
    triggered = evaluate_rules(parcel_data)
    print(f"\n图斑ID: {parcel_data['parcel_id']}")
    print(f"触发规则数: {len(triggered)}\n")

    for t in triggered:
        print(f"  [{t['prompt_type']}] {t['rule_name']}")
        print(f"    {t['prompt_content']}")
        if t.get("require_manual_review"):
            print(f"    >>> 需人工复核")
        print()

    return triggered


def run_llm_agent_demo(parcel_data: dict):
    """大模型Agent模式：通过LangChain编排，大模型调度Skills。"""
    print("\n" + "=" * 60)
    print("【大模型Agent模式】（需配置API Key）")
    print("=" * 60)
    print(f"\n图斑ID: {parcel_data['parcel_id']}")
    print("正在调用大模型分析...\n")

    result = run_agent(parcel_data)
    print("\nAgent输出:")
    print(result.get("output", ""))
    return result


def main():
    # 加载样例数据
    data_path = os.path.join(os.path.dirname(__file__), "data", "sample_input.json")
    with open(data_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print("=" * 60)
    print("  用地合规提示Agent Demo")
    print("  王新林 - 第二组·用地识别智能体")
    print("=" * 60)

    for i, sample in enumerate(samples):
        print(f"\n{'─' * 60}")
        print(f"  样例 {i + 1}: {sample['parcel_id']} ({sample['location']})")
        print(f"  主导地类: {sample['dominant_type']} | 总面积: {sample['total_area_m2']}m²")
        land_desc = ", ".join(f"{lt['type']}({lt['ratio']:.1%})" for lt in sample['land_types'])
        print(f"  地类构成: {land_desc}")
        print(f"{'─' * 60}")

        # 1. 先运行纯规则引擎（无需API）
        triggered = run_rule_engine_demo(sample)

        # 2. 尝试运行大模型Agent模式
        try:
            run_llm_agent_demo(sample)
        except Exception as e:
            print(f"\n大模型Agent模式未启用（{type(e).__name__}）")
            print("如需启用，请配置环境变量:")
            print("  智谱GLM: set ZHIPU_API_KEY=your_key")
            print("  OpenAI:  set OPENAI_API_KEY=your_key")
            print("  切换模型: set LLM_PROVIDER=openai")
            print("\n上方纯规则引擎结果可直接使用。")

    print("\n" + "=" * 60)
    print("  Demo运行完毕")
    print("=" * 60)


if __name__ == "__main__":
    main()
