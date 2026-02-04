const API_BASE = "http://localhost:8000";

const state = {
  view: "year",
  year: null,
  month: null,
  day: null,
  birth: null,
};

const viewLabels = {
  year: "年视图",
  month: "月视图",
  day: "日视图",
  hour: "时视图",
};

const nextViewMap = {
  year: "month",
  month: "day",
  day: "hour",
  hour: null,
};

const prevViewMap = {
  month: "year",
  day: "month",
  hour: "day",
};

const elements = {
  birthDate: document.getElementById("birthDate"),
  birthTime: document.getElementById("birthTime"),
  calendarType: document.getElementById("calendarType"),
  gender: document.getElementById("gender"),
  generateBtn: document.getElementById("generateBtn"),
  heatmapGrid: document.getElementById("heatmapGrid"),
  heatmapStatus: document.getElementById("heatmapStatus"),
  heatmapDefinition: document.getElementById("heatmapDefinition"),
  viewLabel: document.getElementById("viewLabel"),
  backBtn: document.getElementById("backBtn"),
  yearNav: document.getElementById("yearNav"),
  yearDisplay: document.getElementById("yearDisplay"),
  prevYear: document.getElementById("prevYear"),
  nextYear: document.getElementById("nextYear"),
  behaviorNote: document.getElementById("behaviorNote"),
  behaviorList: document.getElementById("behaviorList"),
  birthPillars: document.getElementById("birthPillars"),
};

function chinaNow() {
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  return new Date(utc + 8 * 60 * 60000);
}

function parseChinaIso(iso) {
  const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2})/);
  if (!match) {
    return null;
  }
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(match[4]),
  };
}

function initDefaults() {
  const now = chinaNow();
  state.year = now.getFullYear();
  elements.yearDisplay.textContent = String(state.year);
}

function getBirthInput() {
  const birthDate = elements.birthDate.value;
  const birthTime = elements.birthTime.value;
  if (!birthDate || !birthTime) {
    elements.heatmapStatus.textContent = "请完整填写出生日期与时间。";
    return null;
  }
  return {
    gender: elements.gender.value,
    calendar: elements.calendarType.value,
    birth_date: birthDate,
    birth_time: birthTime,
    is_leap_month: false,
  };
}

function setStatus(message) {
  elements.heatmapStatus.textContent = message;
}

function resetBehavior(message) {
  elements.behaviorList.innerHTML = "";
  elements.behaviorNote.textContent = message;
}

async function responseErrorDetail(response) {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
  } catch (err) {
    // ignore parse errors
  }
  return "后端错误，无法生成结果。";
}

function formatPillar(pillar) {
  if (!pillar) {
    return "—";
  }
  return pillar.label || `${pillar.stem ?? ""}${pillar.branch ?? ""}` || "—";
}

function renderBirthPillars(pillars) {
  if (!elements.birthPillars) {
    return;
  }
  if (!pillars) {
    elements.birthPillars.textContent = "出生四柱：—";
    return;
  }
  const year = formatPillar(pillars.year);
  const month = formatPillar(pillars.month);
  const day = formatPillar(pillars.day);
  const hour = formatPillar(pillars.hour);
  elements.birthPillars.textContent = `出生四柱：年 ${year} · 月 ${month} · 日 ${day} · 时 ${hour}`;
}

function renderHeatmap(cells, view) {
  elements.heatmapGrid.innerHTML = "";
  const keysByView = {
    year: ["big_luck", "year"],
    month: ["big_luck", "year", "month"],
    day: ["big_luck", "year", "month", "day"],
    hour: ["big_luck", "year", "month", "day", "hour"],
  };
  const pillarLabels = {
    big_luck: "大运",
    year: "流年",
    month: "流月",
    day: "流日",
    hour: "流时",
  };
  cells.forEach((cell) => {
    const div = document.createElement("div");
    div.className = "heatmap-cell";
    const color = heatColor(cell.value);
    div.style.background = color;
    const pillarKeys = keysByView[view] ?? [];
    const pillars = cell.pillars ?? {};
    const pillarHtml = pillarKeys
      .map((key) => {
        const label = pillarLabels[key] ?? key;
        const value = formatPillar(pillars[key]);
        return `<div class="pillar-item"><span class="pillar-label">${label}</span><span class="pillar-value">${value}</span></div>`;
      })
      .join("");
    const scores = Array.isArray(cell.ten_god_scores) ? cell.ten_god_scores : [];
    const listHtml = scores.length
      ? scores
          .map(
            (item) =>
              `<div class="ten-god-item"><span class="ten-god-name">${item.label}</span><span class="ten-god-score">${item.score}</span></div>`
          )
          .join("")
      : `<div class="ten-god-empty">未生成十神评分</div>`;
    div.innerHTML = `<strong>${cell.label}</strong><div class="pillar-list">${pillarHtml}</div><div class="ten-god-list">${listHtml}</div>`;
    div.addEventListener("click", () => onCellClick(cell, view));
    elements.heatmapGrid.appendChild(div);
  });
}

function heatColor(value) {
  const hue = 210 - 190 * value;
  const light = 92 - 35 * value;
  return `hsl(${hue}, 70%, ${light}%)`;
}

async function fetchHeatmap() {
  if (!state.birth) {
    setStatus("请先填写出生信息并生成热力图。");
    return;
  }
  setStatus("计算中...");
  const payload = {
    birth: state.birth,
    view: state.view,
    year: state.year,
    month: state.month,
    day: state.day,
  };

  try {
    const response = await fetch(`${API_BASE}/api/analysis/heatmap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const detail = await responseErrorDetail(response);
      throw new Error(detail);
    }
    const data = await response.json();
    renderHeatmap(data.cells, data.view);
    renderBirthPillars(data.birth_pillars);
    if (elements.heatmapDefinition && data.definition) {
      elements.heatmapDefinition.textContent = data.definition;
    }
    updateViewControls();
    setStatus(data.uncertainty_note ?? "");
  } catch (err) {
    elements.heatmapGrid.innerHTML = "";
    updateViewControls();
    setStatus(err?.message || "后端未连接，无法生成热力图。");
    renderBirthPillars(null);
    resetBehavior("无法生成风险提示。");
  }
}

async function fetchBehavior(isoDatetime) {
  if (!state.birth) {
    resetBehavior("请先填写出生信息并生成热力图。");
    return;
  }
  resetBehavior("生成风险提示中...");

  try {
    const response = await fetch(`${API_BASE}/api/analysis/behavior`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        birth: state.birth,
        focus_datetime: isoDatetime,
      }),
    });
    if (!response.ok) {
      const detail = await responseErrorDetail(response);
      throw new Error(detail);
    }
    const data = await response.json();
    elements.behaviorNote.textContent = data.uncertainty_note ?? "";
    const humanMap = {
      "资源获取结构": "资源/资金获取类",
      "约束 / 责任结构": "规则/承诺/职责类",
      "支持 / 缓冲结构": "学习/修复/准备类",
      "输出 / 波动结构": "表达/产出/波动类",
      "竞争 / 内耗结构": "竞争/对抗/消耗类",
    };
    const levelDetail = {
      高: "结构波动更大，承载压力更高",
      中: "结构波动与阻力中等",
      低: "结构阻力较小，波动相对低",
    };
    const groups = {
      low: { title: "宜（风险暴露较低）", items: [] },
      mid: { title: "慎（风险暴露中等）", items: [] },
      high: { title: "忌（风险暴露较高）", items: [] },
    };
    data.prompts.forEach((prompt) => {
      const label = humanMap[prompt.label] ?? prompt.label;
      const level = prompt.risk_level;
      const percent = Number.isFinite(prompt.relative_strength)
        ? ` · 相对占比 ${Math.round(prompt.relative_strength * 100)}%`
        : "";
      const detail = levelDetail[level] ?? `风险暴露${level}`;
      const line = `${label}：${detail}${percent}`;
      if (level === "高") {
        groups.high.items.push(line);
      } else if (level === "中") {
        groups.mid.items.push(line);
      } else {
        groups.low.items.push(line);
      }
    });
    elements.behaviorList.innerHTML = Object.values(groups)
      .map((group) => {
        const items = group.items.length
          ? group.items.map((item) => `<div class="behavior-line">${item}</div>`).join("")
          : '<div class="behavior-empty">暂无</div>';
        return `<li class="behavior-group"><div class="behavior-group-title">${group.title}</div>${items}</li>`;
      })
      .join("");
  } catch (err) {
    resetBehavior(err?.message || "后端未连接，无法生成风险提示。");
  }
}

function onCellClick(cell, currentView) {
  const nextView = nextViewMap[currentView];
  const parsed = parseChinaIso(cell.iso_datetime);
  if (!parsed) {
    setStatus("时间格式异常，无法下钻。");
    return;
  }
  state.year = parsed.year;
  state.month = parsed.month;
  state.day = parsed.day;
  if (nextView) {
    state.view = nextView;
    fetchHeatmap();
    resetBehavior("请下钻到具体时间层级后查看风险提示。");
  } else {
    fetchBehavior(cell.iso_datetime);
  }
}

function updateViewControls() {
  elements.viewLabel.textContent = viewLabels[state.view];
  elements.backBtn.disabled = state.view === "year";
  elements.yearNav.style.display = state.view === "year" ? "flex" : "none";
  elements.yearDisplay.textContent = String(state.year ?? "—");
  if (state.view !== "year") {
    elements.yearDisplay.textContent = "—";
  }
  if (state.view !== "hour") {
    resetBehavior("请下钻到具体时间层级后查看风险提示。");
  }
}

elements.generateBtn.addEventListener("click", () => {
  const birth = getBirthInput();
  if (!birth) {
    return;
  }
  state.birth = birth;
  state.view = "year";
  state.month = null;
  state.day = null;
  fetchHeatmap();
  resetBehavior("请下钻到具体时间层级后查看风险提示。");
});

elements.backBtn.addEventListener("click", () => {
  const prev = prevViewMap[state.view];
  if (!prev) {
    return;
  }
  state.view = prev;
  fetchHeatmap();
});

elements.prevYear.addEventListener("click", () => {
  state.year -= 1;
  fetchHeatmap();
});

elements.nextYear.addEventListener("click", () => {
  state.year += 1;
  fetchHeatmap();
});

initDefaults();
updateViewControls();
