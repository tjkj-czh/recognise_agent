/* === 评测页面交互逻辑 === */

const CAT_LABELS = {
  normal: "正常", boundary: "边界", abnormal: "异常",
  adversarial: "对抗", robustness: "鲁棒性"
};

let allSamples = [];
let evalResults = null;
let currentFilter = "all";
let selectedSampleId = null;

document.addEventListener("DOMContentLoaded", () => {
  loadSamples();
  initFilters();
  document.getElementById("runAllBtn").addEventListener("click", () => runEval());
  document.getElementById("runCatBtn").addEventListener("click", () => runEval(currentFilter));
});

function loadSamples() {
  fetch("/api/eval/samples")
    .then(r => r.json())
    .then(data => {
      allSamples = data;
      document.getElementById("sampleCount").textContent = data.length;
      renderSampleList();
    });
}

function initFilters() {
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.cat;
      renderSampleList();
      document.getElementById("runCatBtn").disabled = currentFilter === "all";
    });
  });
}

function renderSampleList() {
  const container = document.getElementById("sampleList");
  const filtered = currentFilter === "all"
    ? allSamples
    : allSamples.filter(s => s.category === currentFilter);

  container.innerHTML = filtered.map(s => `
    <div class="sample-item ${s.sample_id === selectedSampleId ? 'active' : ''}"
         data-id="${s.sample_id}" onclick="selectSample('${s.sample_id}')">
      <div class="sid">${s.sample_id}</div>
      <div class="sdesc">${s.description}</div>
      <div class="stags">
        <span class="tag-chip cat-${s.category}">${s.category_label}</span>
        ${s.tags.slice(0, 2).map(t => `<span class="tag-chip">${t}</span>`).join("")}
      </div>
    </div>
  `).join("");
}

function selectSample(sampleId) {
  selectedSampleId = sampleId;
  renderSampleList();
  renderDetail(sampleId);
}

function renderDetail(sampleId) {
  const panel = document.getElementById("detailPanel");
  const sample = allSamples.find(s => s.sample_id === sampleId);
  if (!sample) return;

  let resultHtml = "";
  if (evalResults) {
    const r = evalResults.results.find(x => x.sample_id === sampleId);
    if (r) {
      resultHtml = `
        <div class="detail-card">
          <div class="detail-header">
            <span class="dh-id">评测结果</span>
            ${r.passed
              ? '<span class="pass-badge">PASS</span>'
              : '<span class="fail-badge">FAIL</span>'}
          </div>
          <div class="detail-body">
            <table>
              <tr><th>触发规则</th><td>${r.triggered_rules.join(", ") || "无"}</td></tr>
              <tr><th>预期规则</th><td>${r.expected_rules.join(", ") || "无"}</td></tr>
              <tr><th>规则匹配</th><td>${r.rules_match ? "是" : "否"}</td></tr>
              <tr><th>实际风险</th><td>${r.risk_level}</td></tr>
              <tr><th>预期风险</th><td>${r.expected_risk_level}</td></tr>
              <tr><th>风险匹配</th><td>${r.risk_match ? "是" : "否"}</td></tr>
            </table>
            ${r.adversarial_note ? `<div class="note-box">对抗说明: ${r.adversarial_note}</div>` : ""}
          </div>
        </div>`;
    }
  }

  panel.innerHTML = `
    <div class="detail-card">
      <div class="detail-header">
        <span class="dh-id">${sample.sample_id}</span>
        <span class="tag-chip cat-${sample.category}">${sample.category_label}</span>
      </div>
      <div class="detail-body">
        <table>
          <tr><th>描述</th><td>${sample.description}</td></tr>
          <tr><th>图斑ID</th><td>${sample.parcel_id}</td></tr>
          <tr><th>主导地类</th><td>${sample.dominant_type}</td></tr>
          <tr><th>预期规则</th><td>${sample.expected_rules.join(", ") || "无"}</td></tr>
          <tr><th>预期风险</th><td>${sample.expected_risk_level}</td></tr>
          <tr><th>标签</th><td>${sample.tags.map(t => `<span class="tag-chip">${t}</span>`).join(" ")}</td></tr>
        </table>
      </div>
    </div>
    ${resultHtml}
  `;
}

function runEval(category) {
  const btn = document.getElementById("runAllBtn");
  btn.disabled = true;
  btn.textContent = "评测中...";

  fetch("/api/eval/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category: category || null }),
  })
    .then(r => r.json())
    .then(data => {
      evalResults = data;
      renderSummary(data);
      if (selectedSampleId) renderDetail(selectedSampleId);
    })
    .catch(err => alert("评测失败: " + err.message))
    .finally(() => {
      btn.disabled = false;
      btn.textContent = "运行全部评测";
    });
}

function renderSummary(data) {
  const panel = document.getElementById("summaryPanel");
  panel.style.display = "block";

  const grid = document.getElementById("summaryGrid");
  const catHtml = Object.entries(data.category_stats).map(([cat, s]) => `
    <div class="stat-card">
      <div class="stat-val">${s.passed}/${s.total}</div>
      <div class="stat-label">${s.label}样本</div>
    </div>
  `).join("");

  grid.innerHTML = `
    <div class="stat-card ${data.passed === data.total ? 'pass' : 'fail'}">
      <div class="stat-val">${data.pass_rate}%</div>
      <div class="stat-label">总通过率</div>
    </div>
    <div class="stat-card pass">
      <div class="stat-val">${data.passed}</div>
      <div class="stat-label">通过</div>
    </div>
    <div class="stat-card ${data.total - data.passed > 0 ? 'fail' : ''}">
      <div class="stat-val">${data.total - data.passed}</div>
      <div class="stat-label">失败</div>
    </div>
    ${catHtml}
  `;
}
