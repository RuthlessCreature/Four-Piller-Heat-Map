# Four-Piller-Heat-Map

时间结构热力分析系统（非算命 / 非事件预测）。

## 项目定位

- 基于中国八字（四柱）的时间结构分析
- 只呈现结构强度与风险暴露，不给出吉凶或结果承诺
- 短周期仅放大/减弱，不反转长周期结构

## 功能概览

- 输入出生信息（公历/农历、日期、时间、性别）
- 生成热力图并按 年 → 月 → 日 → 时 下钻
- 输出行为风险提示（仅结构风险暴露）

## 目录结构

- backend/ FastAPI + sxtwl 后端
- frontend/ 原生 HTML/CSS/JS 前端
- prompts/ 系统与 UI 约束提示词

## 启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

默认端口：`http://localhost:8000`

### 2. 启动前端

建议使用静态服务器（避免 file:// 跨域限制）：

```bash
cd frontend
python -m http.server 5173
```

浏览器访问：`http://localhost:5173`

## 使用说明

- 默认时区：中国标准时间（UTC+8）
- 时间计算使用 sxtwl（寿星万年历），以节气为准
- 不提供自定义节气/算法选项
- 建议下钻到“时视图”后再查看行为风险提示

## 免责声明

- 输出为时间结构相对强度展示
- 不预测具体事件，不提供结果保证
- 仅用于结构理解与风险识别
