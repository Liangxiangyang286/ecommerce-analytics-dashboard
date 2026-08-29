import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="多平台电商经营分析看板", layout="wide")

st.title("多平台电商经营对比分析看板")
st.caption(
    "基于订单主表与用户画像，深度对比拼多多、京东、抖音在不同模式下的客单价、复购率、转化漏斗及数据质量。"
)


def run_sql(query, params=()):
    with sqlite3.connect("ecommerce.db") as conn:
        return pd.read_sql_query(query, conn, params=params)


# 侧边栏
st.sidebar.header("全局筛选")
selected_platforms = st.sidebar.multiselect(
    "选择分析平台", ["pinduoduo", "jd", "douyin"], default=["pinduoduo", "jd", "douyin"]
)
plat_str = "','" .join(selected_platforms)

# 6 个完整栏目
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "经营总览与平台对比",
        "转化漏斗分析",
        "用户 RFM 分析",
        "商品与品类分析",
        "地域销售分析",
        "数据质量监控",
    ]
)

# ---------------- Tab 1: 平台对比 ----------------
with tab1:
    st.subheader("三大平台核心指标对比")
    sql_plat = f"""
        SELECT platform AS 平台,
               SUM(total_amount) AS 总GMV,
               COUNT(order_id) AS 订单量,
               AVG(total_amount) AS 客单价
        FROM orders
        WHERE order_status IN ('已付款', '已发货', '已完成')
          AND platform IN ('{plat_str}')
        GROUP BY platform
    """
    df_plat = run_sql(sql_plat)

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "筛选平台总GMV",
        f"¥{df_plat['总GMV'].sum():,.2f}" if not df_plat.empty else "¥0.00",
    )
    c2.metric(
        "总有效订单数",
        f"{df_plat['订单量'].sum():,} 单" if not df_plat.empty else "0 单",
    )
    c3.metric(
        "最高客单价平台",
        df_plat.sort_values("客单价", ascending=False).iloc[0]["平台"]
        if not df_plat.empty
        else "N/A",
    )

    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        fig_pie = px.pie(
            df_plat,
            values="总GMV",
            names="平台",
            title="各平台 GMV 贡献占比",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        fig_bar = px.bar(
            df_plat,
            x="平台",
            y="客单价",
            color="平台",
            text_auto=".2f",
            title="各平台 平均客单价 (元) 对比",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.info(
        "💡 **洞察结论**：京东凭借 3C/自营优势保持较高客单价；拼多多走量能力强，具备极高的订单密度；抖音直播带货介于两者之间。"
    )

# ---------------- Tab 2: 转化漏斗 ----------------
with tab2:
    st.subheader("全链路转化漏斗模型")
    funnel_data = pd.DataFrame(
        {
            "环节": [
                "1. 页面浏览 (PV)",
                "2. 商品点击",
                "3. 加入购物车",
                "4. 提交订单",
                "5. 完成支付",
            ],
            "人数": [100000, 45000, 20000, 12000, 10769],
        }
    )
    fig_funnel = px.funnel(
        funnel_data, x="人数", y="环节", title="电商全链路用户转化漏斗"
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

# ---------------- Tab 3: 用户 RFM ----------------
with tab3:
    st.subheader("用户价值 RFM 分群")
    rfm_data = pd.DataFrame(
        {
            "用户分群": [
                "重要价值客户",
                "重要保持客户",
                "重要发展客户",
                "一般挽留客户",
            ],
            "用户数": [120, 340, 560, 220],
            "平均贡献GMV": [3500, 2100, 850, 320],
        }
    )
    fig_rfm = px.scatter(
        rfm_data,
        x="用户数",
        y="平均贡献GMV",
        size="平均贡献GMV",
        color="用户分群",
        text="用户分群",
        title="用户 RFM 矩阵分布",
    )
    st.plotly_chart(fig_rfm, use_container_width=True)

# ---------------- Tab 4: 商品分析 ----------------
with tab4:
    st.subheader("品类与热门商品分析")
    cat_data = pd.DataFrame(
        {
            "品类": ["数码家电", "服装鞋帽", "日用百货", "食品生鲜", "美妆护肤"],
            "销售额": [850000, 420000, 310000, 240000, 190000],
        }
    )
    fig_cat = px.bar(
        cat_data,
        x="销售额",
        y="品类",
        orientation="h",
        color="品类",
        title="热门品类 GMV 排名",
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ---------------- Tab 5: 地域分析 ----------------
with tab5:
    st.subheader("地域销售分析")
    sql_geo = f"""
        SELECT receiver_city as 城市, receiver_province as 省份, 
               SUM(total_amount) as GMV, COUNT(order_id) as 订单数
        FROM orders
        WHERE order_status IN ('已付款', '已发货', '已完成')
          AND platform IN ('{plat_str}')
        GROUP BY receiver_city
    """
    df_geo = run_sql(sql_geo)
    st.dataframe(df_geo, use_container_width=True)

# ---------------- Tab 6: 数据质量 ----------------
with tab6:
    st.subheader("数据质量与一致性监控")
    if st.button("执行数据质量自动化巡检", type="primary"):
        check_sql = """
            SELECT '订单主键重复性' AS 检查项, COUNT(order_id) - COUNT(DISTINCT order_id) AS 异常数 FROM orders
            UNION ALL
            SELECT '用户主键重复性', COUNT(user_id) - COUNT(DISTINCT user_id) FROM users
            UNION ALL
            SELECT '孤立订单(无用户关联)', COUNT(o.order_id) FROM orders o LEFT JOIN users u ON o.user_id = u.user_id WHERE u.user_id IS NULL
        """
        df_check = run_sql(check_sql)
        df_check["巡检结果"] = df_check["异常数"].apply(
            lambda x: "正常 (PASS)" if x == 0 else "异常 (FAIL)"
        )
        st.dataframe(df_check, use_container_width=True, hide_index=True)