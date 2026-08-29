import sqlite3
import numpy as np
import pandas as pd

# 连接数据库
conn = sqlite3.connect("ecommerce.db")
np.random.seed(42)

n = 12000
dates = pd.date_range("2025-01-01", "2026-12-28", freq="h")
cities = ["南京", "杭州", "上海", "西安", "广州", "北京", "成都", "重庆", "深圳", "武汉"]
provinces = ["江苏", "浙江", "上海", "陕西", "广东", "北京", "四川", "重庆", "广东", "湖北"]
city_prov_map = dict(zip(cities, provinces))

# 区分三大平台的偏好
platforms = np.random.choice(["pinduoduo", "jd", "douyin"], n, p=[0.4, 0.3, 0.3])
amounts = []

for p in platforms:
    if p == "pinduoduo":
        # 拼多多：低客单价（均值 35 元）
        amounts.append(np.round(np.random.gamma(2, 15) + 5, 2))
    elif p == "jd":
        # 京东：高客单价（均值 450 元）
        amounts.append(np.round(np.random.gamma(3, 120) + 50, 2))
    else:
        # 抖音：中等客单价（均值 150 元）
        amounts.append(np.round(np.random.gamma(2.5, 50) + 20, 2))

chosen_cities = np.random.choice(cities, n)

df_orders = pd.DataFrame(
    {
        "order_id": [f"ORD{i:06d}" for i in range(1, n + 1)],
        "user_id": [f"USR{np.random.randint(1000, 3000):04d}" for _ in range(n)],
        "platform": platforms,
        "total_amount": amounts,
        "order_status": np.random.choice(
            ["已付款", "已发货", "已完成", "已退款"], n, p=[0.4, 0.3, 0.2, 0.1]
        ),
        "receiver_city": chosen_cities,
        "receiver_province": [city_prov_map[c] for c in chosen_cities],
        "created_at": np.random.choice(dates, n),
    }
)
df_orders.to_sql("orders", conn, if_exists="replace", index=False)

df_users = pd.DataFrame(
    {
        "user_id": [f"USR{i:04d}" for i in range(1000, 3000)],
        "register_city": np.random.choice(cities, 2000),
    }
)
df_users.to_sql("users", conn, if_exists="replace", index=False)

conn.close()
print("新版的 拼多多/京东/抖音 差异化数据库 ecommerce.db 生成成功！")