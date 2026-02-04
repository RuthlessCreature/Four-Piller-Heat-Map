# Backend

时间结构热力分析后端（FastAPI + sxtwl）。

## 运行

1. 安装依赖：

```
pip install -r requirements.txt
```

2. 启动服务：

```
uvicorn app.main:app --reload
```

默认端口：`http://localhost:8000`

## 说明

- 仅提供结构强度与风险暴露信号，不输出事件预测或结果承诺。
- 时间计算依赖 `sxtwl`，使用节气换日规则与北京时间。
- 所有结果为相对强度展示，受时间边界与输入精度影响。
