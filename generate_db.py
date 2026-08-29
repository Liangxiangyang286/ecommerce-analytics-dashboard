import sqlite3
import numpy as np
import pandas as pd

conn = sqlite3.connect("ecommerce.db")
np.random.seed(42)

# 1. 生成 50,000 条订单数据 (2025-2026年)
n = 50000
dates = pd.date_range("2025-01-01", "2026-12-31", freq="h")
chosen_dates = np.random.choice(dates, n)

cities = ["南京", "杭州", "上海", "西安", "广州", "北京", "成都", "重庆", "深圳", "武汉"]
provinces = ["江苏", "浙江", "上海", "陕西", "广东", "北京", "四川", "重庆", "广东", "湖北"]
city_prov_map = dict(zip(cities, provinces))

platforms = np.random.choice(["pinduoduo", "jd", "douyin"], n, p=[0.4, 0.3, 0.3])
categories = ["数码家电", "服饰鞋包", "日用百货", "美妆护肤", "食品生鲜"]
chosen_cats = np.random.choice(categories, n, p=[0.2, 0.25, 0.3, 0.15, 0.1])

amounts = []
for p, c in zip(platforms, chosen_cats):
    base = 50 if p == "pinduoduo" else (300 if p == "jd" else 120)
    cat_mult = 3.5 if c == "数码家电" else (1.5 if c == "美妆护肤" else 1.0)
    val = np.round(np.random.exponential(scale=base * cat_mult) + 15, 2)
    amounts.append(val)

chosen_cities = np.random.choice(cities, n)

df_orders = pd.DataFrame({
    "order_id": [f"ORD{i:06d}" for i in range(1, n + 1)],
    "user_id": [f"USR{np.random.randint(1000, 8000):04d}" for _ in range(n)],
    "platform": platforms,
    "category": chosen_cats,
    "total_amount": amounts,
    "order_status": np.random.choice(["已付款", "已发货", "已完成", "已退款"], n, p=[0.35, 0.3, 0.25, 0.1]),
    "receiver_city": chosen_cities,
    "receiver_province": [city_prov_map[c] for c in chosen_cities],
    "created_at": chosen_dates
})
df_orders.to_sql("orders", conn, if_exists="replace", index=False)

# 2. 生成用户数据
df_users = pd.DataFrame({
    "user_id": [f"USR{i:04d}" for i in range(1000, 8000)],
    "register_city": np.random.choice(cities, 7000),
    "user_level": np.random.choice(["注册会员", "黄金会员", "钻石会员"], 7000, p=[0.6, 0.3, 0.1])
})
df_users.to_sql("users", conn, if_exists="replace", index=False)

conn.close()
print("🎉 50,000条大容量商业级数据生成成功！")