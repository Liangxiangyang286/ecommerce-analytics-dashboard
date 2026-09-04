# 多平台电商经营分析看板 (E-commerce Analytics Dashboard)

[![Streamlit App](https://static.streamlit.io/badge-svg.svg)](https://liangxiangyang286-ecommerce-analytics.streamlit.app)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

全栈式多平台电商数据分析看板，基于 **Python + Streamlit + Plotly + SQLite** 架构搭建。针对多渠道（拼多多、京东、抖音等）运营场景，提供从宏观经营大盘到微观用户价值（RFM）与转化漏斗的精细化数据分析支持。

**🔗 在线交互体验**：[https://liangxiangyang286-ecommerce-analytics.streamlit.app](https://liangxiangyang286-ecommerce-analytics.streamlit.app)

---

## 💡 核心业务模块

* **经营大盘 (Overview)**：实时监控 GMV、订单总量、客单价及退款率等核心 KPI 指标，支持时间颗粒度与跨平台对比。
* **渠道与品类分析 (Channel & Category)**：解构各电商平台的 GMV 贡献占比与品类销售分布，定位高产出渠道。
* **用户价值 RFM 模型 (RFM Customer Analysis)**：基于 Recency（近度）、Frequency（频度）、Monetary（额度）算法，将用户切分为高价值核心客群、潜力客群与流失风险客群。
* **转化漏斗分析 (Conversion Funnel)**：全链路分析“浏览 - 下单 - 支付 - 完成”转化流失率，定位环节瓶颈。

---

## 🛠️ 技术栈与架构

* **前端交互与可视化**：`Streamlit`, `Plotly Express`
* **数据处理与计算**：`Pandas`, `NumPy`
* **数据存储**：`SQLite3`
* **项目结构**：
  ```text
  ├── app.py              # Streamlit 仪表盘主程序入口
  ├── scripts/
  │   └── init_db.py      # 数据库初始化与清洗脚本
  ├── requirements.txt    # 依赖环境配置
  └── README.md           # 项目说明文档
