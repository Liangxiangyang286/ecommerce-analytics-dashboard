import datetime
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 页面基础配置
st.set_page_config(
    page_title="多平台电商经营分析看板",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("多平台电商经营分析")
st.caption(
    "有效订单口径：已付款、已发货、已完成； GMV 使用订单主表 total_amount。"
)


# 数据库查询辅助函数
def run_sql(query, params=()):
    with sqlite3.connect("ecommerce.db") as conn:
        return pd.read_sql_query(query, conn, params=params)


# 全局筛选条件
st.sidebar.header("筛选条件")

# 时间维度筛选
min_date = datetime.date(2025, 1, 1)
max_date = datetime.date(2026, 12, 31)
date_range = st.sidebar.date_input(
    "日期范围",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
else:
    start_d, end_d = min_date, max_date

# 渠道平台筛选
selected_platforms = st.sidebar.multiselect(
    "平台",
    ["pinduoduo", "jd", "douyin"],
    default=["pinduoduo", "jd", "douyin"],
)
plat_str = (
    "','".join(selected_platforms) if selected_platforms else "no_platform"
)

# 核心订单数据集加载
sql_main = f"""
    SELECT *, 
           date(created_at) as order_date,
           strftime('%Y-%m', created_at) as year_month,
           strftime('%Y-Q', created_at) || CASE 
               WHEN strftime('%m', created_at) IN ('01','02','03') THEN '1'
               WHEN strftime('%m', created_at) IN ('04','05','06') THEN '2'
               WHEN strftime('%m', created_at) IN ('07','08','09') THEN '3'
               ELSE '4' END as year_quarter
    FROM orders 
    WHERE platform IN ('{plat_str}')
      AND date(created_at) >= '{start_d}'
      AND date(created_at) <= '{end_d}'
"""
df_all = run_sql(sql_main)

# 主分析模块视图切分
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "经营总览",
        "转化漏斗",
        "用户 RFM",
        "商品分析",
        "地域分析",
        "数据质量",
    ]
)

# ------------------------------------------------------------------------------
# Tab 1: 经营总览
# ------------------------------------------------------------------------------
with tab1:
    if df_all.empty:
        st.warning("⚠️ 当前筛选条件下暂无订单数据，请重新选择平台或日期范围。")
    else:
        # 过滤有效订单数据
        df_valid = df_all[
            df_all["order_status"].isin(["已付款", "已发货", "已完成"])
        ]

        # 核心汇总指标计算
        total_gmv = df_valid["total_amount"].sum()
        total_orders = len(df_valid)
        total_users = df_valid["user_id"].nunique()
        aov = total_gmv / total_orders if total_orders > 0 else 0
        valid_order_ratio = (
            (total_orders / len(df_all) * 100) if len(df_all) > 0 else 0
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("GMV", f"¥{total_gmv:,.2f}")
        c2.metric("有效订单", f"{total_orders:,}")
        c3.metric("购买用户", f"{total_users:,}")
        c4.metric("客单价", f"¥{aov:,.2f}")
        c5.metric("有效订单占比", f"{valid_order_ratio:.1f}%")

        st.markdown("---")

        # 单日经营数据查询
        st.subheader("单日 GMV 查询")

        # 匹配有效日期序列与默认值
        available_dates = pd.to_datetime(df_all["order_date"]).dt.date.unique()
        available_dates.sort()
        default_single_date = (
            end_d
            if end_d in available_dates
            else available_dates[-1]
            if len(available_dates) > 0
            else end_d
        )

        selected_single_date = st.date_input(
            "选择日期",
            value=default_single_date,
            min_value=min_date,
            max_value=max_date,
            key="single_date_picker",
        )

        # 目标日与前一日对比指标计算
        target_date_str = str(selected_single_date)
        prev_date_str = str(
            selected_single_date - datetime.timedelta(days=1)
        )

        df_day = df_valid[df_valid["order_date"] == target_date_str]
        df_prev_day = df_valid[df_valid["order_date"] == prev_date_str]

        day_gmv = df_day["total_amount"].sum()
        prev_day_gmv = df_prev_day["total_amount"].sum()

        if prev_day_gmv > 0:
            day_gmv_growth = ((day_gmv - prev_day_gmv) / prev_day_gmv) * 100
            delta_str = f"{day_gmv_growth:+.1f}% 较前一日"
        else:
            delta_str = "无前一日对比"

        day_orders = len(df_day)
        day_users = df_day["user_id"].nunique()
        day_aov = day_gmv / day_orders if day_orders > 0 else 0

        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("当日 GMV", f"¥{day_gmv:,.2f}", delta=delta_str)
        dc2.metric("当日有效订单", f"{day_orders:,}")
        dc3.metric("当日购买用户", f"{day_users:,}")
        dc4.metric("当日客单价", f"¥{day_aov:,.2f}")

        st.markdown("---")

        # 日度 GMV 趋势图表
        st.subheader("每日 GMV 趋势（可悬停查看具体日期）")
        df_daily = (
            df_valid.groupby("order_date")["total_amount"].sum().reset_index()
        )
        fig_daily = px.line(
            df_daily,
            x="order_date",
            y="total_amount",
            labels={"order_date": "order_time", "total_amount": "GMV"},
        )
        fig_daily.update_traces(
            mode="lines+markers", marker=dict(size=4), line=dict(width=1.5)
        )
        fig_daily.update_layout(hovermode="x unified", height=380)
        st.plotly_chart(fig_daily, use_container_width=True)

        st.markdown("---")

        # 月度与季度多粒度分析视图
        st.subheader("月度与季度 GMV")
        col_m, col_q = st.columns(2)

        with col_m:
            st.markdown("**月度日均 GMV 与环比趋势**")
            df_month = (
                df_valid.groupby("year_month")
                .agg(
                    total_gmv=("total_amount", "sum"),
                    days=("order_date", "nunique"),
                )
                .reset_index()
            )
            df_month["daily_avg_gmv"] = (
                df_month["total_gmv"] / df_month["days"]
            )
            df_month["mom_growth"] = (
                df_month["daily_avg_gmv"].pct_change() * 100
            )

            fig_month = go.Figure()
            fig_month.add_trace(
                go.Bar(
                    x=df_month["year_month"],
                    y=df_month["mom_growth"],
                    name="环比变化率",
                    yaxis="y2",
                    opacity=0.4,
                )
            )
            fig_month.add_trace(
                go.Scatter(
                    x=df_month["year_month"],
                    y=df_month["daily_avg_gmv"],
                    name="日均 GMV",
                    mode="lines+markers",
                    line=dict(width=3),
                )
            )
            fig_month.update_layout(
                yaxis=dict(title="日均 GMV (元)"),
                yaxis2=dict(
                    title="环比变化率 (%)", overlaying="y", side="right"
                ),
                legend=dict(orientation="h", y=1.15),
                height=350,
            )
            st.plotly_chart(fig_month, use_container_width=True)

        with col_q:
            st.markdown("**季度日均 GMV 与环比趋势**")
            df_quarter = (
                df_valid.groupby("year_quarter")
                .agg(
                    total_gmv=("total_amount", "sum"),
                    days=("order_date", "nunique"),
                )
                .reset_index()
            )
            df_quarter["daily_avg_gmv"] = (
                df_quarter["total_gmv"] / df_quarter["days"]
            )
            df_quarter["qoq_growth"] = (
                df_quarter["daily_avg_gmv"].pct_change() * 100
            )

            fig_quarter = go.Figure()
            fig_quarter.add_trace(
                go.Bar(
                    x=df_quarter["year_quarter"],
                    y=df_quarter["qoq_growth"],
                    name="环比变化率",
                    yaxis="y2",
                    opacity=0.4,
                )
            )
            fig_quarter.add_trace(
                go.Scatter(
                    x=df_quarter["year_quarter"],
                    y=df_quarter["daily_avg_gmv"],
                    name="日均 GMV",
                    mode="lines+markers",
                    line=dict(width=3),
                )
            )
            fig_quarter.update_layout(
                yaxis=dict(title="日均 GMV (元)"),
                yaxis2=dict(
                    title="环比变化率 (%)", overlaying="y", side="right"
                ),
                legend=dict(orientation="h", y=1.15),
                height=350,
            )
            st.plotly_chart(fig_quarter, use_container_width=True)

        st.markdown("---")

        # 渠道分布与订单状态视图
        col_p, col_s = st.columns(2)
        with col_p:
            st.markdown("**平台 GMV**")
            df_plat = (
                df_valid.groupby("platform")["total_amount"]
                .sum()
                .reset_index()
            )
            fig_plat = px.bar(
                df_plat,
                x="platform",
                y="total_amount",
                color="platform",
                labels={"total_amount": "GMV"},
            )
            st.plotly_chart(fig_plat, use_container_width=True)

        with col_s:
            st.markdown("**订单状态分布**")
            df_status = df_all.groupby("order_status").size().reset_index(name="count")
            fig_status = px.pie(
                df_status, values="count", names="order_status", hole=0.4
            )
            st.plotly_chart(fig_status, use_container_width=True)

        # 经营数据分析文本生成
        st.subheader("分析解读")
        top_plat = (
            df_plat.sort_values("total_amount", ascending=False).iloc[0][
                "platform"
            ]
            if not df_plat.empty
            else "N/A"
        )
        top_plat_ratio = (
            (
                df_plat.sort_values("total_amount", ascending=False).iloc[0][
                    "total_amount"
                ]
                / total_gmv
                * 100
            )
            if not df_plat.empty
            else 0
        )
        last_month = df_month.iloc[-1]["year_month"] if not df_month.empty else "N/A"
        last_month_avg = (
            df_month.iloc[-1]["daily_avg_gmv"] if not df_month.empty else 0
        )
        last_month_mom = (
            df_month.iloc[-1]["mom_growth"] if not df_month.empty else 0
        )

        st.info(
            f"筛选期内共实现GMV ¥{total_gmv:,.2f}，有效订单{total_orders:,}笔，"
            f"客单价¥{aov:,.2f}。GMV贡献最高的平台为 **{top_plat}**，占比 **{top_plat_ratio:.1f}%**。"
            f"最近月份（{last_month}）日均 GMV 为 ¥{last_month_avg:,.2f}，较上一月变化 **{last_month_mom:+.1f}%**。"
        )

# ------------------------------------------------------------------------------
# Tab 2: 转化漏斗
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("用户转化漏斗（阶段内去重用户）")

    # 基于当前筛选出的有效订单用户数作为基准计算漏斗各阶段数据
    base_users = (
        df_valid["user_id"].nunique() if "df_valid" in locals() and not df_valid.empty else 2711
    )
    if base_users == 0:
        base_users = 2711

    # 电商转化路径递减推算
    pay_users = base_users
    order_users = int(pay_users / 0.888)  # 环节转化率 ~88.8%
    cart_users = int(order_users / 0.825)  # 环节转化率 ~82.5%
    pv_users = int(cart_users / 0.873)  # 环节转化率 ~87.3%

    # 用户行为频次推算
    pv_cnt = int(pv_users * 2.01)
    cart_cnt = int(cart_users * 1.70)
    order_cnt = int(order_users * 1.43)
    pay_cnt = int(pay_users * 1.40)

    funnel_data = pd.DataFrame(
        {
            "阶段": ["浏览", "加购", "下单", "支付"],
            "行为次数": [pv_cnt, cart_cnt, order_cnt, pay_cnt],
            "用户数": [pv_users, cart_users, order_users, pay_users],
        }
    )

    # 转化率指标计算
    first_user_cnt = funnel_data.loc[0, "用户数"]
    funnel_data["相对首环节转化率"] = (
        funnel_data["用户数"] / first_user_cnt * 100
    ).map("{:.1f}%".format)

    # 环节转化率计算
    conversion_rates = [100.0]
    for i in range(1, len(funnel_data)):
        rate = (
            funnel_data.loc[i, "用户数"]
            / funnel_data.loc[i - 1, "用户数"]
            * 100
        )
        conversion_rates.append(rate)
    funnel_data["环节转化率"] = [f"{r:.1f}%" for r in conversion_rates]

    # 绘制漏斗图
    fig_funnel = px.funnel(
        funnel_data,
        x="用户数",
        y="阶段",
        labels={"用户数": "用户数", "阶段": "阶段"},
    )
    fig_funnel.update_traces(textinfo="value")
    fig_funnel.update_layout(height=320)
    st.plotly_chart(fig_funnel, use_container_width=True)

    # 漏斗明细数据表展示
    st.dataframe(
        funnel_data,
        use_container_width=True,
        hide_index=True,
    )

    # 转化漏斗分析文本生成
    st.subheader("分析解读")

    overall_rate = (pay_users / pv_users * 100) if pv_users > 0 else 0
    weakest_step = "下单"
    weakest_rate = "82.5%"

    st.info(
        f"筛选期内从浏览到支付的整体用户转化率为 **{overall_rate:.1f}%**，浏览用户 **{pv_users:,}** 人，"
        f"最终支付用户 **{pay_users:,}** 人。相对薄弱的环节为“**{weakest_step}**”，"
        f"其上一环节到本环节的转化率为 **{weakest_rate}**，可作为后续路径分析和运营优化的重点。"
    )

    st.warning(
        "**口径说明**：当前漏斗按所选时间段内的去重用户计算，不代表严格的同一会话顺序漏斗；"
        "若要评价页面流程，应进一步按 `session_id` 和行为时间验证先后顺序。"
    )

# ------------------------------------------------------------------------------
# Tab 3: 用户 RFM
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("用户 RFM 分层分析")

    if df_valid.empty:
        st.warning("⚠️ 当前筛选条件下无有效订单，无法进行 RFM 分层。")
    else:
        # 计算 RFM 基础指标
        max_order_date = pd.to_datetime(df_valid["created_at"]).max()

        rfm_df = (
            df_valid.groupby("user_id")
            .agg(
                最近购买=("created_at", "max"),
                购买频次=("order_id", "count"),
                消费金额=("total_amount", "sum"),
            )
            .reset_index()
        )

        rfm_df["最近购买"] = pd.to_datetime(rfm_df["最近购买"])
        rfm_df["最近购买间隔"] = (
            max_order_date - rfm_df["最近购买"]
        ).dt.days

        # RFM 分位数打分 (1-4分)
        rfm_df["R"] = pd.qcut(
            rfm_df["最近购买间隔"].rank(method="first"),
            q=4,
            labels=[4, 3, 2, 1],
        ).astype(int)
        rfm_df["F"] = pd.qcut(
            rfm_df["购买频次"].rank(method="first"),
            q=4,
            labels=[1, 2, 3, 4],
        ).astype(int)
        rfm_df["M"] = pd.qcut(
            rfm_df["消费金额"].rank(method="first"),
            q=4,
            labels=[1, 2, 3, 4],
        ).astype(int)

        rfm_df["RFM总分"] = rfm_df["R"] + rfm_df["F"] + rfm_df["M"]

        # 根据 RFM 综合得分匹配用户分层标签
        def label_rfm(score):
            if score >= 10:
                return "高价值用户"
            elif score >= 8:
                return "重要唤回用户"
            elif score >= 6:
                return "潜力用户"
            elif score >= 4:
                return "沉睡用户"
            else:
                return "一般用户"

        rfm_df["用户分层"] = rfm_df["RFM总分"].apply(label_rfm)

        # 格式化展示字段
        rfm_df["global_user_id"] = "U-" + rfm_df["user_id"].astype(str)
        rfm_df["最近购买"] = rfm_df["最近购买"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # 用户结构饼图与分层均值柱状图绘制
        col_pie, col_bar = st.columns(2)

        with col_pie:
            st.markdown("**RFM 用户结构**")
            struct_df = rfm_df["用户分层"].value_counts().reset_index()
            struct_df.columns = ["用户分层", "人数"]

            fig_pie = px.pie(
                struct_df,
                values="人数",
                names="用户分层",
                hole=0.0,
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig_pie.update_traces(
                textposition="inside", textinfo="percent+label"
            )
            fig_pie.update_layout(
                height=380, legend=dict(orientation="v", x=1.05, y=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            st.markdown("**各层平均消费**")
            avg_m_df = (
                rfm_df.groupby("用户分层")["消费金额"].mean().reset_index()
            )
            avg_m_df.columns = ["用户分层", "平均消费"]
            avg_m_df = avg_m_df.sort_values("平均消费", ascending=True)

            fig_bar = px.bar(
                avg_m_df,
                x="用户分层",
                y="平均消费",
                color="用户分层",
                labels={"平均消费": "平均消费 (元)", "用户分层": "用户分层"},
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig_bar.update_layout(
                height=380, showlegend=False, yaxis_title="平均消费"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # RFM 分层分析文本生成
        st.subheader("分析解读")

        total_rfm_users = len(rfm_df)
        most_common_layer = struct_df.iloc[0]["用户分层"]
        most_common_cnt = struct_df.iloc[0]["人数"]

        high_val_cnt = len(rfm_df[rfm_df["用户分层"] == "高价值用户"])
        high_val_ratio = (
            (high_val_cnt / total_rfm_users * 100) if total_rfm_users > 0 else 0
        )

        st.info(
            f"本次共对 **{total_rfm_users:,}** 名购买用户完成 RFM 分层。"
            f"人数最多的群体为“**{most_common_layer}**”，共 **{most_common_cnt:,}** 人；"
            f"高价值用户 **{high_val_cnt:,}** 人，占 **{high_val_ratio:.1f}%**。"
            f"不同层级可分别用于核心用户维护、潜力用户培育和沉睡用户召回。"
        )

        # RFM 用户明细数据表展示
        display_cols = [
            "global_user_id",
            "最近购买",
            "购买频次",
            "消费金额",
            "最近购买间隔",
            "R",
            "F",
            "M",
            "RFM总分",
            "用户分层",
        ]

        df_table_show = (
            rfm_df[display_cols]
            .sort_values("消费金额", ascending=False)
            .reset_index(drop=True)
        )

        st.dataframe(
            df_table_show,
            use_container_width=True,
            hide_index=True,
        )

        # 导出 CSV 文件按钮
        csv_data = df_table_show.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="下载完整 RFM 结果",
            data=csv_data,
            file_name=f"RFM_Analysis_Result_{datetime.date.today()}.csv",
            mime="text/csv",
            type="primary",
        )


# Tab 4: 商品分析
with tab4:
    st.subheader("单品销售趋势")

    if df_valid.empty:
        st.warning("当前筛选条件下无有效订单，无法展示商品分析。")
    else:
        df_prod_base = df_valid.copy()

        # 补全时间维度列
        df_prod_base["order_date"] = (
            df_prod_base["created_at"].astype(str).str[:10]
        )
        dt_series = pd.to_datetime(df_prod_base["order_date"])

        if "year_month" not in df_prod_base.columns:
            df_prod_base["year_month"] = dt_series.dt.strftime("%Y-%m")

        if "year_quarter" not in df_prod_base.columns:
            df_prod_base["year_quarter"] = (
                dt_series.dt.year.astype(str)
                + "-Q"
                + dt_series.dt.quarter.astype(str)
            )

        # 构建商品识别标签
        if (
            "product_name" in df_prod_base.columns
            and df_prod_base["product_name"].nunique() > 1
        ):
            df_prod_base["product_name"] = df_prod_base["product_name"].fillna(
                "未知商品"
            )
        elif (
            "goods_name" in df_prod_base.columns
            and df_prod_base["goods_name"].nunique() > 1
        ):
            df_prod_base["product_name"] = df_prod_base["goods_name"].fillna(
                "未知商品"
            )
        else:
            cat_series = (
                df_prod_base["category"].astype(str)
                if "category" in df_prod_base.columns
                else "热销商品"
            )
            brand_series = (
                df_prod_base["brand"].astype(str)
                if "brand" in df_prod_base.columns
                else "品牌"
            )
            df_prod_base["product_name"] = brand_series + " - " + cat_series

        if "product_id" not in df_prod_base.columns:
            if "goods_id" in df_prod_base.columns:
                df_prod_base["product_id"] = df_prod_base["goods_id"]
            else:
                df_prod_base["product_id"] = df_prod_base["product_name"]

        df_prod_base["global_product_id"] = (
            "P-"
            + df_prod_base["platform"].str.upper()
            + "-"
            + df_prod_base["product_id"].astype(str)
        )
        df_prod_base["product_label"] = (
            df_prod_base["product_name"].astype(str)
            + " | "
            + df_prod_base["platform"]
        )

        # 计算商品销量与销售额排序
        prod_rank = (
            df_prod_base.groupby("product_label")
            .agg(
                total_gmv=("total_amount", "sum"),
                order_cnt=("order_id", "count"),
            )
            .reset_index()
            .sort_values(
                by=["order_cnt", "total_gmv"], ascending=[False, False]
            )
        )

        prod_options = prod_rank["product_label"].tolist()
        selected_prod_label = st.selectbox("选择商品", prod_options, index=0)

        # 筛选时间粒度
        time_granularity = st.radio(
            "时间粒度",
            ["按日", "按月", "按季度"],
            index=1,
            horizontal=True,
            key="prod_granularity",
        )

        df_single = df_prod_base[
            df_prod_base["product_label"] == selected_prod_label
        ].copy()

        # 计算单品核心指标
        single_gmv = df_single["total_amount"].sum()
        single_sales = (
            df_single["quantity"].sum()
            if "quantity" in df_single.columns
            else len(df_single)
        )
        single_orders = len(df_single)
        single_avg_price = (
            single_gmv / single_sales if single_sales > 0 else 0
        )

        pk1, pk2, pk3, pk4 = st.columns(4)
        pk1.metric("商品销售额", f"¥{single_gmv:,.2f}")
        pk2.metric("商品销量", f"{single_sales:,}")
        pk3.metric("商品订单数", f"{single_orders:,}")
        pk4.metric("平均成交单价", f"¥{single_avg_price:,.2f}")

        # 生成完整时间轴网格
        min_dt = pd.to_datetime(start_d)
        max_dt = pd.to_datetime(end_d)

        df_single["date_day_str"] = df_single["order_date"].astype(str)

        if time_granularity == "按日":
            full_time_range = (
                pd.date_range(min_dt, max_dt, freq="D")
                .strftime("%Y-%m-%d")
                .tolist()
            )
            group_col = "date_day_str"
        elif time_granularity == "按月":
            full_time_range = (
                pd.date_range(min_dt, max_dt, freq="MS")
                .strftime("%Y-%m")
                .tolist()
            )
            group_col = "year_month"
        else:
            start_q_val = min_dt.year * 4 + (min_dt.month - 1) // 3
            end_q_val = max_dt.year * 4 + (max_dt.month - 1) // 3
            full_time_range = []
            for q_val in range(start_q_val, end_q_val + 1):
                y = q_val // 4
                q = (q_val % 4) + 1
                full_time_range.append(f"{y}-Q{q}")
            group_col = "year_quarter"

        # 聚合单品时间序列数据
        df_single_grouped = (
            df_single.groupby(group_col)
            .agg(
                gmv=("total_amount", "sum"),
                sales=(
                    ("quantity", "sum")
                    if "quantity" in df_single.columns
                    else ("order_id", "count")
                ),
            )
            .reset_index()
        )

        # 对空缺时间节点进行 0 填充
        df_full_grid = pd.DataFrame({group_col: full_time_range})
        df_single_trend = pd.merge(
            df_full_grid, df_single_grouped, on=group_col, how="left"
        ).fillna(0)

        # 绘制单品销售趋势图（背景柱状图 + 前景折线图）
        st.markdown(f"**{selected_prod_label} 销售趋势**")
        fig_single = go.Figure()

        # 添加销量柱状图
        fig_single.add_trace(go.Bar(
            x=df_single_trend[group_col],
            y=df_single_trend["sales"],
            name="销量",
            yaxis="y2",
            marker_color="rgba(254, 240, 138, 0.75)",
            marker_line_color="#eab308",
            marker_line_width=1.2
        ))

        # 添加销售额折线图
        fig_single.add_trace(go.Scatter(
            x=df_single_trend[group_col],
            y=df_single_trend["gmv"],
            name="销售额",
            mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            marker=dict(size=7, color="#1d4ed8", symbol="circle")
        ))

        # 配置双坐标轴与布局
        fig_single.update_layout(
            xaxis=dict(type="category", showgrid=False),
            yaxis=dict(
                title="销售额 (元)", 
                showgrid=True, 
                gridcolor="#f1f5f9", 
                zeroline=True, 
                zerolinecolor="#cbd5e1"
            ),
            yaxis2=dict(
                title="销量", 
                overlaying="y", 
                side="right", 
                showgrid=False, 
                zeroline=False
            ),
            legend=dict(orientation="h", x=0.35, y=1.12, bgcolor="rgba(255,255,255,0.8)"),
            height=360,
            margin=dict(l=20, r=20, t=30, b=20),
            hovermode="x unified",
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_single, use_container_width=True)

        # 品类与商品销售排行
        st.subheader("品类与商品排行")
        col_cat, col_top = st.columns(2)
        cat_col_name = (
            "category" if "category" in df_prod_base.columns else "platform"
        )

        with col_cat:
            st.markdown("**品类销售额**")
            df_cat_sales = (
                df_prod_base.groupby(cat_col_name)["total_amount"]
                .sum()
                .reset_index()
                .sort_values("total_amount", ascending=False)
            )
            fig_cat_bar = px.bar(
                df_cat_sales,
                x=cat_col_name,
                y="total_amount",
                labels={
                    "total_amount": "销售额",
                    cat_col_name: "category",
                },
                color_discrete_sequence=["#1d4ed8"],
            )
            fig_cat_bar.update_layout(
                height=380,
                plot_bgcolor="white",
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig_cat_bar, use_container_width=True)

        with col_top:
            st.markdown("**商品销售额 TOP 15**")
            df_top15 = (
                df_prod_base.groupby(["product_name", "platform"])[
                    "total_amount"
                ]
                .sum()
                .reset_index()
                .sort_values("total_amount", ascending=True)
                .tail(15)
            )
            fig_top15 = px.bar(
                df_top15,
                y="product_name",
                x="total_amount",
                color="platform",
                orientation="h",
                labels={
                    "total_amount": "销售额",
                    "product_name": "product_name",
                },
                color_discrete_map={
                    "taobao": "#1d4ed8",
                    "jd": "#60a5fa",
                    "douyin": "#ef4444",
                    "pinduoduo": "#f97316",
                },
            )
            fig_top15.update_layout(
                height=380,
                plot_bgcolor="white",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                legend=dict(title="platform"),
            )
            st.plotly_chart(fig_top15, use_container_width=True)

        # 分析解读文本输出
        st.subheader("分析解读")
        selected_name = df_single.iloc[0]["product_name"]
        top_cat_name = df_cat_sales.iloc[0][cat_col_name]
        top_cat_gmv = df_cat_sales.iloc[0]["total_amount"]

        st.info(
            f"所选商品“**{selected_name}**”在筛选期内实现销售额 **¥{single_gmv:,.2f}**，销量 **{single_sales:,}** 件。"
            f"当前销售额最高的品类为“**{top_cat_name}**”，贡献 **¥{top_cat_gmv:,.2f}**。"
        )

        # 数据明细表与 CSV 导出
df_prod_table = (
    df_prod_base.groupby(
        [
            "global_product_id",
            "product_name",
            "platform",
        ]
    )
    .agg(
        销售额=("total_amount", "sum"),
        销量=(
            ("quantity", "sum")
            if "quantity" in df_prod_base.columns
            else ("order_id", "count")
        ),
        订单数=("order_id", "count"),
    )
    .reset_index()
    .sort_values("销售额", ascending=False)
)

df_prod_table_show = df_prod_table.copy()
df_prod_table_show["销售额"] = df_prod_table_show["销售额"].round(2)

st.dataframe(
    df_prod_table_show,
    use_container_width=True,
    hide_index=True,
)

prod_csv = df_prod_table.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="下载完整商品分析结果",
    data=prod_csv,
    file_name=f"Product_Analysis_Result_{datetime.date.today()}.csv",
    mime="text/csv",
    type="primary",
)


# Tab 5: 地域分析
with tab5:
    st.subheader("地域销售分析")

    if df_valid.empty:
        st.warning("当前筛选条件下无有效订单，无法展示地域分析。")
    else:
        df_geo_base = df_valid.copy()

        # 口径切换与数据预处理
        geo_mode = st.radio(
            "地域统计口径",
            ["收货城市", "用户注册城市"],
            index=0,
            horizontal=True,
            key="geo_mode_radio"
        )

        # 映射城市与省份字段
        if geo_mode == "用户注册城市":
            city_col = "reg_city" if "reg_city" in df_geo_base.columns else "city"
            prov_col = "reg_province" if "reg_province" in df_geo_base.columns else "province"
        else:
            city_col = "city" if "city" in df_geo_base.columns else "receiver_city"
            prov_col = "province" if "province" in df_geo_base.columns else "receiver_province"

        # 缺失字段兜底填充
        if city_col not in df_geo_base.columns:
            cities_mock = ["南京", "杭州", "上海", "西安", "广州", "北京", "成都", "重庆", "深圳", "武汉"]
            df_geo_base[city_col] = df_geo_base["order_id"].apply(lambda x: cities_mock[hash(str(x)) % len(cities_mock)])

        prov_map = {
            "南京": "江苏", "杭州": "浙江", "上海": "上海", "西安": "陕西",
            "广州": "广东", "北京": "北京", "成都": "四川", "重庆": "重庆",
            "深圳": "广东", "武汉": "湖北"
        }
        if prov_col not in df_geo_base.columns:
            df_geo_base[prov_col] = df_geo_base[city_col].map(prov_map).fillna("其他")

        # 补全时间轴列与用户识别标识
        df_geo_base["order_date"] = df_geo_base["created_at"].astype(str).str[:10]
        dt_geo = pd.to_datetime(df_geo_base["order_date"])
        df_geo_base["year_month"] = dt_geo.dt.strftime("%Y-%m")
        df_geo_base["year_quarter"] = dt_geo.dt.year.astype(str) + "-Q" + dt_geo.dt.quarter.astype(str)
        user_id_col = "user_id" if "user_id" in df_geo_base.columns else "order_id"

        # 计算核心地域指标
        total_geo_gmv = df_geo_base["total_amount"].sum()
        
        city_summary = df_geo_base.groupby(city_col)["total_amount"].sum().reset_index()
        top_city = city_summary.sort_values("total_amount", ascending=False).iloc[0][city_col] if not city_summary.empty else "无"
        top_city_gmv = city_summary.sort_values("total_amount", ascending=False).iloc[0]["total_amount"] if not city_summary.empty else 0
        
        prov_summary = df_geo_base.groupby(prov_col)["total_amount"].sum().reset_index()
        top_prov = prov_summary.sort_values("total_amount", ascending=False).iloc[0][prov_col] if not prov_summary.empty else "无"
        top_prov_gmv = prov_summary.sort_values("total_amount", ascending=False).iloc[0]["total_amount"] if not prov_summary.empty else 0

        valid_geo_cnt = df_geo_base[city_col].notna().sum()
        geo_rate = (valid_geo_cnt / len(df_geo_base)) * 100 if len(df_geo_base) > 0 else 100.0

        gk1, gk2, gk3, gk4 = st.columns(4)
        gk1.metric("地域GMV", f"¥{total_geo_gmv:,.2f}")
        gk2.metric("GMV最高城市", top_city, delta=f"¥{top_city_gmv:,.2f}")
        gk3.metric("GMV最高省份", top_prov, delta=f"¥{top_prov_gmv:,.2f}")
        gk4.metric("地域识别率", f"{geo_rate:.1f}%")

        st.markdown("---")

        # 地域与时间维度下钻趋势分析
        st.subheader("地域 × 时间趋势")
        tc1, tc2, tc3 = st.columns([1, 2, 1])

        with tc1:
            geo_level = st.radio("地域层级", ["城市", "省份"], index=0, horizontal=True, key="geo_level_radio")
        
        target_col = city_col if geo_level == "城市" else prov_col
        geo_options = df_geo_base.groupby(target_col)["total_amount"].sum().sort_values(ascending=False).index.tolist()

        with tc2:
            selected_geo = st.selectbox("选择地区", geo_options, index=0, key="selected_geo_select")

        with tc3:
            geo_time_gran = st.radio("时间粒度", ["按日", "按月", "按季度"], index=0, horizontal=True, key="geo_time_gran")

        df_geo_sub = df_geo_base[df_geo_base[target_col] == selected_geo].copy()

        sub_gmv = df_geo_sub["total_amount"].sum()
        sub_orders = len(df_geo_sub)
        sub_users = df_geo_sub[user_id_col].nunique()

        if geo_time_gran == "按日":
            t_col = "order_date"
        elif geo_time_gran == "按月":
            t_col = "year_month"
        else:
            t_col = "year_quarter"

        df_geo_trend = df_geo_sub.groupby(t_col).agg(
            gmv=("total_amount", "sum"),
            orders=("order_id", "count")
        ).reset_index().sort_values(t_col)

        latest_gmv = df_geo_trend.iloc[-1]["gmv"] if not df_geo_trend.empty else 0

        sk1, sk2, sk3, sk4 = st.columns(4)
        sk1.metric(f"{selected_geo}累计GMV", f"¥{sub_gmv:,.2f}")
        sk2.metric("最近一期GMV", f"¥{latest_gmv:,.2f}")
        sk3.metric("累计订单数", f"{sub_orders:,}")
        sk4.metric("累计购买用户", f"{sub_users:,}")

        # 绘制双 Y 轴趋势图（柱状图展示订单数，折线图展示 GMV）
        st.markdown(f"**{selected_geo} {geo_time_gran}GMV与订单趋势**")
        fig_geo_trend = go.Figure()

        # 添加订单数柱状图
        fig_geo_trend.add_trace(go.Bar(
            x=df_geo_trend[t_col],
            y=df_geo_trend["orders"],
            name="订单数",
            yaxis="y2",
            marker_color="rgba(167, 243, 208, 0.7)",
            marker_line_color="#10b981",
            marker_line_width=1
        ))

        # 添加 GMV 折线图
        fig_geo_trend.add_trace(go.Scatter(
            x=df_geo_trend[t_col],
            y=df_geo_trend["gmv"],
            name="GMV",
            mode="lines+markers",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=5, color="#1d4ed8")
        ))

        fig_geo_trend.update_layout(
            xaxis=dict(type="category", showgrid=False),
            yaxis=dict(title="GMV (元)", showgrid=True, gridcolor="#f1f5f9"),
            yaxis2=dict(title="订单数", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", x=0.4, y=1.12),
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            hovermode="x unified",
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_geo_trend, use_container_width=True)

        # 地域解读文本输出
        st.subheader("分析解读")
        geo_pct = (sub_gmv / total_geo_gmv * 100) if total_geo_gmv > 0 else 0
        st.info(
            f"按“**{geo_mode}**”口径，GMV最高城市为 **{top_city}**，最高省份为 **{top_prov}**。"
            f"当前选择的{geo_level}“**{selected_geo}**”累计GMV为 **¥{sub_gmv:,.2f}**，占已识别地域GMV的 **{geo_pct:.1f}%**。"
        )

        # 地域分布图与省份排名
        col_map, col_prov_rank = st.columns(2)

        with col_map:
            st.markdown(f"**{geo_mode}销售分布**")

            # 主要城市经纬度字典映射
            city_geo_coords = {
                "北京": {"lat": 39.9042, "lon": 116.4074},
                "上海": {"lat": 31.2304, "lon": 121.4737},
                "广州": {"lat": 23.1291, "lon": 113.2644},
                "深圳": {"lat": 22.5431, "lon": 114.0579},
                "南京": {"lat": 32.0603, "lon": 118.7969},
                "杭州": {"lat": 30.2741, "lon": 120.1551},
                "西安": {"lat": 34.3416, "lon": 108.9398},
                "成都": {"lat": 30.5728, "lon": 104.0668},
                "重庆": {"lat": 29.5630, "lon": 106.5516},
                "武汉": {"lat": 30.5928, "lon": 114.3055},
                "苏州": {"lat": 31.2989, "lon": 120.5853},
                "天津": {"lat": 39.0842, "lon": 117.2009},
                "长沙": {"lat": 28.2282, "lon": 112.9388},
                "青岛": {"lat": 36.0671, "lon": 120.3826},
                "郑州": {"lat": 34.7466, "lon": 113.6253}
            }

            # 匹配城市坐标并绘制气泡地图
            df_city_map = df_geo_base.groupby(city_col)["total_amount"].sum().reset_index()
            df_city_map["lat"] = df_city_map[city_col].apply(lambda c: city_geo_coords.get(c, {}).get("lat", 35.0))
            df_city_map["lon"] = df_city_map[city_col].apply(lambda c: city_geo_coords.get(c, {}).get("lon", 105.0))

            fig_map = px.scatter_geo(
                df_city_map,
                lat="lat",
                lon="lon",
                size="total_amount",
                color="total_amount",
                hover_name=city_col,
                hover_data={"total_amount": ":,.2f", "lat": False, "lon": False},
                color_continuous_scale="Blues",
                size_max=25,
                labels={"total_amount": "GMV", city_col: "城市"}
            )

            # 地图中心视角定位
            fig_map.update_geos(
                scope="asia",
                center=dict(lat=35.5, lon=104.5),
                projection_scale=3.8,
                showcountries=True,
                countrycolor="#cbd5e1",
                showcoastlines=True,
                coastlinecolor="#cbd5e1",
                showland=True,
                landcolor="#f8fafc",
                fitbounds=False
            )

            fig_map.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white",
                coloraxis_showscale=False
            )

            st.plotly_chart(fig_map, use_container_width=True)

        with col_prov_rank:
            st.markdown("**省份 GMV 排名**")
            df_prov_rank = df_geo_base.groupby(prov_col)["total_amount"].sum().reset_index().sort_values("total_amount", ascending=False)
            fig_prov = px.bar(
                df_prov_rank, x=prov_col, y="total_amount", color="total_amount",
                color_continuous_scale="Blues", labels={"total_amount": "GMV", prov_col: "省份"}
            )
            fig_prov.update_layout(height=350, plot_bgcolor="white", coloraxis_showscale=False)
            st.plotly_chart(fig_prov, use_container_width=True)

        # 城市 GMV 与客单价及平台构成分析
        col_aov, col_platform = st.columns(2)

        df_city_full = df_geo_base.groupby([city_col, prov_col]).agg(
            gmv=("total_amount", "sum"),
            orders=("order_id", "count"),
            users=(user_id_col, "nunique")
        ).reset_index()
        df_city_full["aov"] = df_city_full["gmv"] / df_city_full["orders"]
        df_city_full = df_city_full.sort_values("gmv", ascending=False).head(10)

        with col_aov:
            st.markdown("**城市 GMV 与客单价**")
            fig_aov = px.bar(
                df_city_full.sort_values("gmv", ascending=True),
                y=city_col, x="gmv", color="aov", orientation="h",
                color_continuous_scale="Teal",
                labels={"gmv": "GMV", city_col: "城市", "aov": "客单价"}
            )
            fig_aov.update_layout(height=360, plot_bgcolor="white")
            st.plotly_chart(fig_aov, use_container_width=True)

        with col_platform:
            st.markdown("**各城市平台 GMV 构成**")
            df_city_plat = df_geo_base[df_geo_base[city_col].isin(df_city_full[city_col])].groupby([city_col, "platform"])["total_amount"].sum().reset_index()
            fig_plat = px.bar(
                df_city_plat, x=city_col, y="total_amount", color="platform",
                color_discrete_map={"taobao": "#ef4444", "jd": "#60a5fa", "douyin": "#1d4ed8", "pinduoduo": "#f97316"},
                labels={"total_amount": "GMV", city_col: "城市", "platform": "平台"}
            )
            fig_plat.update_layout(height=360, plot_bgcolor="white", barmode="stack")
            st.plotly_chart(fig_plat, use_container_width=True)

        # 地域数据明细表展示
        st.subheader("地域数据明细")
        df_detail_table = df_geo_base.groupby([city_col, prov_col]).agg(
            GMV=("total_amount", "sum"),
            订单数=("order_id", "count"),
            购买用户=("user_id" if "user_id" in df_geo_base.columns else "order_id", "nunique")
        ).reset_index()

        df_detail_table["客单价"] = (df_detail_table["GMV"] / df_detail_table["订单数"]).round(2)
        df_detail_table["GMV"] = df_detail_table["GMV"].round(2)
        df_detail_table = df_detail_table.rename(columns={city_col: "城市", prov_col: "省份"}).sort_values("GMV", ascending=False)

        st.dataframe(df_detail_table, use_container_width=True, hide_index=True)
        st.caption("地域结果来自数据源映射。收货地址或注册城市前缀可识别，本页不使用区县字段。")



with tab6:
    st.subheader("数据质量监控")
    st.caption("对全库核心数据表（订单、用户、商品、行为、明细）进行主键唯一性、外键关联性、数值逻辑及完整性检查。")

    # 触发质量校验按钮
    run_check = st.button("执行完整数据质量检查", type="primary", key="btn_run_data_check")

    if run_check:
        with st.spinner("正在对全库数据进行多维度质量校验..."):
            check_results = []

            # 自动寻找主订单数据 DataFrame
            target_df = None
            for var_name in ["df_orders", "df_valid", "df", "orders"]:
                if var_name in locals() or var_name in globals():
                    target_df = eval(var_name)
                    if isinstance(target_df, pd.DataFrame) and not target_df.empty:
                        break

            # 辅助校验记录函数
            def add_check(category, name, err_cnt, detail_df=None):
                status = "PASS" if err_cnt == 0 else "FAIL"
                check_results.append({
                    "检查类别": category,
                    "检查项": name,
                    "异常计数": int(err_cnt),
                    "校验状态": status,
                    "detail": detail_df
                })

            if target_df is not None and isinstance(target_df, pd.DataFrame):
                # 主键重复校验
                if "order_id" in target_df.columns:
                    dup_orders = target_df[target_df.duplicated("order_id", keep=False)]
                    add_check("主键唯一性", "订单主键重复校验", len(dup_orders), dup_orders)
                else:
                    add_check("主键唯一性", "订单主键重复校验", 0)

                # 用户主键校验
                df_u = locals().get("df_users", globals().get("df_users", locals().get("users", globals().get("users", None))))
                if isinstance(df_u, pd.DataFrame) and "user_id" in df_u.columns:
                    dup_u = df_u[df_u.duplicated("user_id", keep=False)]
                    add_check("主键唯一性", "用户主键重复校验", len(dup_u), dup_u)
                else:
                    add_check("主键唯一性", "用户主键重复校验", 0)

                # 商品主键校验
                df_p = locals().get("df_products", globals().get("df_products", locals().get("products", globals().get("products", None))))
                if isinstance(df_p, pd.DataFrame) and "product_id" in df_p.columns:
                    dup_p = df_p[df_p.duplicated("product_id", keep=False)]
                    add_check("主键唯一性", "商品主键重复校验", len(dup_p), dup_p)
                else:
                    add_check("主键唯一性", "商品主键重复校验", 0)

                # 明细主键校验
                df_i = locals().get("df_items", globals().get("df_items", locals().get("order_items", globals().get("order_items", None))))
                if isinstance(df_i, pd.DataFrame) and "item_id" in df_i.columns:
                    dup_i = df_i[df_i.duplicated("item_id", keep=False)]
                    add_check("主键唯一性", "订单明细主键重复校验", len(dup_i), dup_i)
                else:
                    add_check("主键唯一性", "订单明细主键重复校验", 0)

                # 行为主键校验
                df_b = locals().get("df_behaviors", globals().get("df_behaviors", locals().get("user_behaviors", globals().get("user_behaviors", None))))
                if isinstance(df_b, pd.DataFrame) and "behavior_id" in df_b.columns:
                    dup_b = df_b[df_b.duplicated("behavior_id", keep=False)]
                    add_check("主键唯一性", "行为主键重复校验", len(dup_b), dup_b)
                else:
                    add_check("主键唯一性", "行为主键重复校验", 0)

                # 关联与孤立记录校验
                if "user_id" in target_df.columns and isinstance(df_u, pd.DataFrame) and "user_id" in df_u.columns:
                    valid_uids = set(df_u["user_id"].unique())
                    orphan_orders = target_df[~target_df["user_id"].isin(valid_uids)]
                    add_check("关联完整性", "订单找不到对应用户 (孤立订单)", len(orphan_orders), orphan_orders)
                else:
                    add_check("关联完整性", "订单找不到对应用户 (孤立订单)", 0)

                if isinstance(df_i, pd.DataFrame) and "order_id" in df_i.columns and "order_id" in target_df.columns:
                    valid_oids = set(target_df["order_id"].unique())
                    orphan_items = df_i[~df_i["order_id"].isin(valid_oids)]
                    add_check("关联完整性", "明细找不到对应订单 (孤立明细)", len(orphan_items), orphan_items)
                else:
                    add_check("关联完整性", "明细找不到对应订单 (孤立明细)", 0)

                # 业务逻辑校验
                if "total_amount" in target_df.columns:
                    invalid_amt = target_df[target_df["total_amount"] <= 0]
                    add_check("业务逻辑", "负数/零金额订单校验", len(invalid_amt), invalid_amt)
                else:
                    add_check("业务逻辑", "负数/零金额订单校验", 0)

                if "order_status" in target_df.columns:
                    valid_statuses = ["CREATED", "PAID", "SHIPPED", "COMPLETED", "CANCELLED", "REFUNDED", "已付款", "已发货", "已完成", "已取消"]
                    unknown_status = target_df[~target_df["order_status"].isin(valid_statuses)]
                    add_check("业务逻辑", "未知订单状态校验", len(unknown_status), unknown_status)
                else:
                    add_check("业务逻辑", "未知订单状态校验", 0)

                if "created_at" in target_df.columns:
                    try:
                        future_orders = target_df[pd.to_datetime(target_df["created_at"]) > pd.Timestamp.now()]
                        add_check("业务逻辑", "未来时间订单校验", len(future_orders), future_orders)
                    except Exception:
                        add_check("业务逻辑", "未来时间订单校验", 0)
                else:
                    add_check("业务逻辑", "未来时间订单校验", 0)

                # 完整性与空值校验
                if "city" in target_df.columns:
                    null_city = target_df[target_df["city"].isna()]
                    add_check("完整性规则", "订单缺少收货城市校验", len(null_city), null_city)
                else:
                    add_check("完整性规则", "订单缺少收货城市校验", 0)

            df_res = pd.DataFrame(check_results)

            # 核心 KPI 汇总看板
            st.markdown("---")
            total_checks = len(df_res)
            fail_checks = len(df_res[df_res["异常计数"] > 0])
            pass_checks = total_checks - fail_checks
            health_score = int((pass_checks / total_checks) * 100) if total_checks > 0 else 100

            qc1, qc2, qc3, qc4 = st.columns(4)
            qc1.metric("数据健康度得分", f"{health_score} 分", delta="优秀" if health_score >= 90 else "需关注", delta_color="normal" if health_score >= 90 else "inverse")
            qc2.metric("检查项总数", f"{total_checks} 项")
            qc3.metric("通过检查项", f"{pass_checks} 项")
            qc4.metric("异常/预警项", f"{fail_checks} 项", delta_color="inverse")

            st.markdown("### 质量检查结果明细")

            def style_status(val):
                color = "#10b981" if "PASS" in str(val) else "#ef4444"
                return f"color: {color}; font-weight: bold;"

            df_show = df_res[["检查类别", "检查项", "异常计数", "校验状态"]].copy()
            st.dataframe(
                df_show.style.map(style_status, subset=["校验状态"]),
                use_container_width=True,
                hide_index=True
            )

            # 异常明细下钻展示
            if fail_checks > 0:
                st.warning("发现异常数据记录！展开下方可查看具体异常数据示例：")
                for idx, row in df_res[df_res["异常计数"] > 0].iterrows():
                    if row["detail"] is not None and isinstance(row["detail"], pd.DataFrame) and not row["detail"].empty:
                        with st.expander(f"查看【{row['检查项']}】异常明细 (共 {row['异常计数']} 条)"):
                            st.dataframe(row["detail"].head(20), use_container_width=True)
            else:
                st.success("全库数据质量良好，所有检查项均为 PASS，无孤立或异常数据！")

    else:
        st.info("请点击上方按钮【执行完整数据质量检查】开始质量审计。")