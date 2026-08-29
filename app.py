import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="多平台电商经营分析看板", layout="wide")

st.title("多平台电商经营对比分析 (拼多多 vs 京东 vs 抖音)")
st.caption("基于订单主表与用户画像，深度对比不同平台模式下的客单价、GMV 及数据质量。")


def run_sql(query, params=()):
    with sqlite3.connect("ecommerce.db") as conn:
        return pd.read_sql_query(query, conn, params=params)


# 侧边栏选择
st.sidebar.header("全局筛选")
selected_platforms = st.sidebar.multiselect(
    "选择分析平台", ["pinduoduo", "jd", "douyin"], default=["pinduoduo", "jd", "douyin"]
)

tab1, tab2, tab3 = st.tabs(["经营总览与平台对比", "地域分析", "数据质量"])

# ---------------- Tab 1: 平台差异化对比 ----------------
with tab1:
    st.subheader("三大平台核心指标对比")

    # SQL 统计各平台 GMV、订单数、客单价
    plat_str = "','" .join(selected_platforms)
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

    # 4 列展示整体数据
    c1, c2, c3 = st.columns(3)
    c1.metric("筛选平台总GMV", f"¥{df_plat['总GMV'].sum():,.2f}")
    c2.metric("总有效订单数", f"{df_plat['订单量'].sum():,} 单")
    c3.metric(
        "最高客单价平台",
        df_plat.sort_values("客单价", ascending=False).iloc[0]["平台"]
        if not df_plat.empty
        else "N/A",
    )

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        # 平台 GMV 占比饼图
        fig_pie = px.pie(
            df_plat,
            values="总GMV",
            names="平台",
            title="各平台 GMV 贡献占比",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        # 平台客单价对比柱状图
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
        "💡 **洞察结论**：京东凭借 3C 家电优势保持较高的**平均客单价**；拼多多以低客单价走量，具备极高的**订单量与走量能力**；抖音直播带货客单价介于两者之间。"
    )
    st.dataframe(df_plat, use_container_width=True)

# ---------------- Tab 2: 地域分析 ----------------
with tab2:
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

# ---------------- Tab 3: 数据质量 ----------------
with tab3:
    st.subheader("数据质量检查板")
    if st.button("执行完整数据质量检查", type="primary"):
        check_sql = """
            SELECT '订单主键重复' AS 检查项, COUNT(order_id) - COUNT(DISTINCT order_id) AS 异常数 FROM orders
            UNION ALL
            SELECT '用户主键重复', COUNT(user_id) - COUNT(DISTINCT user_id) FROM users
            UNION ALL
            SELECT '订单找不到用户', COUNT(o.order_id) FROM orders o LEFT JOIN users u ON o.user_id = u.user_id WHERE u.user_id IS NULL
        """
        df_check = run_sql(check_sql)
        df_check["结果"] = df_check["异常数"].apply(
            lambda x: "通过" if x == 0 else "未通过"
        )
        st.dataframe(df_check, use_container_width=True, hide_index=True)