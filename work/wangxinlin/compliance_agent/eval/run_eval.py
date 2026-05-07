"""用地合规提示Agent - 评测运行脚本。

使用方式:
  python eval/run_eval.py            # 运行全部评测
  python eval/run_eval.py --category normal    # 只跑正常样本
  python eval/run_eval.py --verbose            # 详细输出每个样本结果

输出:
  - 终端打印评测报告摘要和明细
  - 生成 eval/eval_report.json 详细结果文件
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from rules.compliance_rules import evaluate_rules
from web.report_builder import build_report

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))


def load_samples(category_filter=None):
    path = os.path.join(EVAL_DIR, "eval_samples.json")
    with open(path, "r", encoding="utf-8") as f:
        samples = json.load(f)
    if category_filter:
        samples = [s for s in samples if s["category"] == category_filter]
    return samples


def run_single(sample):
    parcel_data = sample["input"]
    try:
        triggered = evaluate_rules(parcel_data)
        report = build_report(parcel_data, triggered)
        triggered_ids = sorted([r["rule_id"] for r in triggered])
    except Exception as e:
        return {
            "sample_id": sample["sample_id"],
            "status": "error",
            "error": str(e),
            "triggered_rules": [],
            "risk_level": "ERROR",
            "manual_review": False,
        }

    expected_ids = sorted(sample["expected_rules"])
    rules_match = triggered_ids == expected_ids
    risk_match = report["overall_risk_level"] == sample["expected_risk_level"]
    review_match = (len(report["manual_review_items"]) > 0) == sample["expected_manual_review"]
    passed = rules_match and risk_match and review_match

    # 漏判 / 误判分析
    missed = [r for r in expected_ids if r not in triggered_ids]
    extra = [r for r in triggered_ids if r not in expected_ids]

    return {
        "sample_id": sample["sample_id"],
        "category": sample["category"],
        "category_label": sample["category_label"],
        "description": sample["description"],
        "status": "pass" if passed else "fail",
        "triggered_rules": triggered_ids,
        "expected_rules": expected_ids,
        "rules_match": rules_match,
        "missed_rules": missed,
        "extra_rules": extra,
        "risk_level": report["overall_risk_level"],
        "expected_risk_level": sample["expected_risk_level"],
        "risk_match": risk_match,
        "manual_review": len(report["manual_review_items"]) > 0,
        "expected_manual_review": sample["expected_manual_review"],
        "review_match": review_match,
        "adversarial_note": sample.get("adversarial_note", ""),
    }


def run_eval(category_filter=None, verbose=False):
    samples = load_samples(category_filter)
    results = [run_single(s) for s in samples]

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = total - passed

    # 分类统计
    cat_stats = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0})
    for r in results:
        cat = r["category"]
        cat_stats[cat]["total"] += 1
        if r["status"] == "pass":
            cat_stats[cat]["pass"] += 1
        else:
            cat_stats[cat]["fail"] += 1

    # 错误分类法统计
    error_types = defaultdict(int)
    for r in results:
        if r["status"] == "fail":
            if not r["rules_match"]:
                if r["missed_rules"]:
                    error_types["规则漏判"] += 1
                if r["extra_rules"]:
                    error_types["规则误判"] += 1
            if not r["risk_match"]:
                error_types["风险等级错误"] += 1
            if not r.get("review_match", True):
                error_types["人工复核判断错误"] += 1

    # 规则覆盖率
    rule_hit = defaultdict(lambda: {"expected": 0, "triggered": 0})
    for s, r in zip(samples, results):
        for rid in s["expected_rules"]:
            rule_hit[rid]["expected"] += 1
            if rid in r["triggered_rules"]:
                rule_hit[rid]["triggered"] += 1

    # 打印报告
    print("\n" + "=" * 70)
    print("  用地合规提示Agent - 评测报告")
    print("  王新林 · 第二组 · 用地识别智能体")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print(f"\n总通过率: {passed}/{total} ({passed/total*100:.1f}%)\n")

    print("【分类统计】")
    cat_order = ["normal", "boundary", "abnormal", "adversarial", "robustness"]
    for cat in cat_order:
        if cat in cat_stats:
            s = cat_stats[cat]
            label = {"normal": "正常", "boundary": "边界", "abnormal": "异常",
                     "adversarial": "对抗", "robustness": "鲁棒性"}[cat]
            rate = s["pass"] / s["total"] * 100 if s["total"] else 0
            print(f"  {label}样本: {s['pass']}/{s['total']} ({rate:.0f}%)")

    if error_types:
        print("\n【错误分类统计】")
        for etype, cnt in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"  {etype}: {cnt}次")

    print("\n【规则覆盖率】")
    for rid in sorted(rule_hit.keys()):
        s = rule_hit[rid]
        rate = s["triggered"] / s["expected"] * 100 if s["expected"] else 0
        print(f"  {rid}: {s['triggered']}/{s['expected']} ({rate:.0f}%)")

    if verbose or failed > 0:
        print("\n【失败样本明细】")
        for r in results:
            if r["status"] == "fail":
                print(f"\n  [{r['sample_id']}] {r['category_label']}")
                print(f"    描述: {r['description']}")
                print(f"    预期规则: {r['expected_rules']}")
                print(f"    实际规则: {r['triggered_rules']}")
                if r["missed_rules"]:
                    print(f"    漏判规则: {r['missed_rules']}")
                if r["extra_rules"]:
                    print(f"    误判规则: {r['extra_rules']}")
                print(f"    预期风险: {r['expected_risk_level']} | 实际风险: {r['risk_level']}")
                if r.get("adversarial_note"):
                    print(f"    对抗说明: {r['adversarial_note']}")

    if verbose:
        print("\n【全部样本明细】")
        for r in results:
            mark = "PASS" if r["status"] == "pass" else "FAIL"
            print(f"  [{mark}] {r['sample_id']} ({r['category_label']}) "
                  f"规则:{r['triggered_rules']} 风险:{r['risk_level']}")

    # 保存详细结果
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total": total, "passed": passed, "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
        },
        "category_stats": dict(cat_stats),
        "error_types": dict(error_types),
        "rule_coverage": {k: dict(v) for k, v in rule_hit.items()},
        "results": results,
    }

    report_path = os.path.join(EVAL_DIR, "eval_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {report_path}")

    return report_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="用地合规提示Agent评测")
    parser.add_argument("--category", default=None,
                        choices=["normal", "boundary", "abnormal", "adversarial", "robustness"],
                        help="只跑指定类别的样本")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="打印每个样本的详细结果")
    args = parser.parse_args()

    run_eval(category_filter=args.category, verbose=args.verbose)
