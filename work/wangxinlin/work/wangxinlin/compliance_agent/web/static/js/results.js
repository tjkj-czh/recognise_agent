document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("resultContent");
  if (!container) return;

  let report = null;
  try {
    report = JSON.parse(localStorage.getItem("latestComplianceReport") || "null");
  } catch (e) {
    console.warn("读取缓存分析结果失败:", e);
  }

  if (!report) {
    container.innerHTML = '<p class="placeholder">暂无分析结果，请先到“地图分析”页面提交或点击图斑触发分析。</p>';
    return;
  }

  container.innerHTML = buildReportHtml(report);
});

function buildReportHtml(report) {
  let html = `<div class="result-header">
    <div class="parcel-id">${report.parcel_id || "-"}</div>
    <div class="parcel-meta">${report.summary ? report.summary.split("。")[0] : ""}</div>
    <span class="risk-badge risk-badge-${report.overall_risk_level}">${report.overall_risk_level || "无特殊关注"}</span>
  </div>`;

  if (report.summary) {
    html += `<div class="result-section">
      <div class="result-section-title">摘要</div>
      <p class="summary-text">${report.summary}</p>
    </div>`;
  }

  if (report.auto_judgments?.length) {
    html += `<div class="result-section">
      <div class="result-section-title attention">自动判断 (${report.auto_judgments.length})</div>`;
    report.auto_judgments.forEach((text) => {
      html += `<div class="rule-card" data-type="关注">${text}</div>`;
    });
    html += `</div>`;
  }

  if (report.suspected_prompts?.length) {
    html += `<div class="result-section">
      <div class="result-section-title suspected">疑似提示 (${report.suspected_prompts.length})</div>`;
    report.suspected_prompts.forEach((text) => {
      html += `<div class="rule-card" data-type="疑似">${text}</div>`;
    });
    html += `</div>`;
  }

  if (report.manual_review_items?.length) {
    html += `<div class="result-section">
      <div class="result-section-title review">人工复核项 (${report.manual_review_items.length})</div>`;
    report.manual_review_items.forEach((item) => {
      const priClass = item.priority === "高" ? "high" : "medium";
      html += `<div class="rule-card review-card" data-type="建议复核">
        <span class="review-priority ${priClass}">${item.priority}优先</span>${item.item}
        <div class="review-reason">${item.reason}</div>
      </div>`;
    });
    html += `</div>`;
  }

  if (report.generated_at) {
    html += `<div class="generated-at">生成时间: ${report.generated_at}</div>`;
  }

  return html;
}
