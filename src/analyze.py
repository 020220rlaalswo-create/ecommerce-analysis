"""Reproducible Olist customer, sales, payment and delivery analysis.

Usage: python src/analyze.py --data-dir data/raw --out-dir outputs
Outputs: order_level.csv, monthly_sales.csv, category_sales.csv,
         customer_rfm.csv, kpis.json and seven PNG charts.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

FILES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "categories": "product_category_name_translation.csv",
}
DATES = ["order_purchase_timestamp", "order_approved_at",
         "order_delivered_carrier_date", "order_delivered_customer_date",
         "order_estimated_delivery_date"]


def load(data_dir):
    missing = [f for f in FILES.values() if not (data_dir / f).is_file()]
    if missing:
        raise FileNotFoundError("Missing CSV files: " + ", ".join(missing))
    frames = {k: pd.read_csv(data_dir / file) for k, file in FILES.items()}
    for col in DATES:
        frames["orders"][col] = pd.to_datetime(frames["orders"][col], errors="coerce")
    if frames["orders"]["order_id"].duplicated().any():
        raise ValueError("order_id must be unique in orders")
    if frames["customers"]["customer_id"].duplicated().any():
        raise ValueError("customer_id must be unique in customers")
    return frames


def prepare(frames):
    orders = frames["orders"].merge(
        frames["customers"][["customer_id", "customer_unique_id", "customer_state"]],
        on="customer_id", how="left", validate="many_to_one"
    )
    # Items and payments are one-to-many relative to orders.
    item_agg = frames["items"].groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        item_revenue=("price", "sum"),
        freight_total=("freight_value", "sum")
    )
    pay_agg = frames["payments"].groupby("order_id", as_index=False).agg(
        payment_total=("payment_value", "sum"),
        payment_records=("payment_value", "size")
    )
    # Multiple review records may exist: one average score per order.
    review_agg = frames["reviews"].groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean")
    )
    order_level = (orders.merge(item_agg, on="order_id", how="left", validate="one_to_one")
                   .merge(pay_agg, on="order_id", how="left", validate="one_to_one")
                   .merge(review_agg, on="order_id", how="left", validate="one_to_one"))
    order_level["delivery_days"] = (
        order_level["order_delivered_customer_date"] -
        order_level["order_purchase_timestamp"]).dt.total_seconds() / 86400
    order_level["delivery_delay_days"] = (
        order_level["order_delivered_customer_date"] -
        order_level["order_estimated_delivery_date"]).dt.total_seconds() / 86400
    order_level["is_late"] = order_level["delivery_delay_days"] > 0
    order_level["purchase_month"] = order_level["order_purchase_timestamp"].dt.to_period("M").astype(str)
    # Reject time-inconsistent delivery records only for delivery metrics.
    order_level.loc[order_level["delivery_days"] < 0, "delivery_days"] = np.nan
    assert len(order_level) == len(orders), "Join multiplied orders"
    return order_level


def business_tables(f, order_level):
    # Completed-order sales analysis; product revenue excludes freight.
    delivered = order_level[order_level["order_status"] == "delivered"].copy()
    monthly = delivered.groupby("purchase_month", as_index=False).agg(
        orders=("order_id", "nunique"),
        product_revenue=("item_revenue", "sum"),
        payment_total=("payment_total", "sum"),
        avg_order_item_value=("item_revenue", "mean"),
        late_rate=("is_late", "mean"),
    ).sort_values("purchase_month")
    items = f["items"].merge(
        f["products"][["product_id", "product_category_name"]],
        on="product_id", how="left", validate="many_to_one"
    ).merge(f["categories"], on="product_category_name", how="left", validate="many_to_one")
    items = items[items["order_id"].isin(set(delivered["order_id"]))]
    items["category"] = items["product_category_name_english"].fillna(
        items["product_category_name"]).fillna("unknown")
    category = items.groupby("category", as_index=False).agg(
        product_revenue=("price", "sum"), units=("order_item_id", "size"),
        orders=("order_id", "nunique")
    ).sort_values("product_revenue", ascending=False)
    # Cohort/returning metrics are limited to observed customer order history.
    observed = delivered.dropna(subset=["customer_unique_id", "order_purchase_timestamp"])
    customer = observed.groupby("customer_unique_id", as_index=False).agg(
        order_count=("order_id", "nunique"),
        monetary=("item_revenue", "sum"),
        last_purchase=("order_purchase_timestamp", "max"),
        first_purchase=("order_purchase_timestamp", "min")
    )
    anchor = observed["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    customer["recency_days"] = (anchor - customer["last_purchase"]).dt.days
    customer["repeat_customer"] = customer["order_count"] >= 2
    customer["first_cohort"] = customer["first_purchase"].dt.to_period("M").astype(str)
    return delivered, monthly, category, customer


def make_charts(order_level, delivered, monthly, category, customer, out_dir):
    plt.style.use("seaborn-v0_8-whitegrid")
    def save(name):
        plt.tight_layout()
        plt.savefig(out_dir / name, dpi=150, bbox_inches="tight")
        plt.close()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(monthly["purchase_month"], monthly["product_revenue"], marker="o")
    ax.set(title="Monthly product revenue (delivered)", xlabel="Purchase month", ylabel="BRL")
    ax.tick_params(axis="x", rotation=65)
    save("01_monthly_revenue.png")
    fig, ax = plt.subplots(figsize=(9, 6))
    top = category.head(12).iloc[::-1]
    ax.barh(top["category"], top["product_revenue"])
    ax.set(title="Top 12 categories by product revenue", xlabel="BRL")
    save("02_category_revenue.png")
    fig, ax = plt.subplots(figsize=(8, 5))
    status = order_level["order_status"].value_counts()
    ax.bar(status.index, status.values)
    ax.set(title="Order statuses (all orders)", ylabel="Orders")
    ax.tick_params(axis="x", rotation=45)
    save("03_order_status.png")
    fig, ax = plt.subplots(figsize=(8, 5))
    valid = delivered["delivery_days"].dropna()
    ax.hist(valid, bins=45)
    ax.set(title="Delivery time (delivered orders)", xlabel="Days", ylabel="Orders")
    save("04_delivery_days.png")
    fig, ax = plt.subplots(figsize=(8, 5))
    rates = delivered.dropna(subset=["order_delivered_customer_date",
                                     "order_estimated_delivery_date"]).groupby(
        "customer_state")["is_late"].agg(["mean", "size"])
    rates = rates[rates["size"] >= 100].sort_values("mean", ascending=False).head(15)
    ax.bar(rates.index, rates["mean"] * 100)
    ax.set(title="Late delivery by customer state (n>=100)", ylabel="Late delivery %")
    save("05_late_delivery_states.png")
    fig, ax = plt.subplots(figsize=(7, 5))
    c = customer["repeat_customer"].value_counts().reindex([False, True], fill_value=0)
    ax.bar(["One order", "2+ orders"], c.values)
    ax.set(title="Observed customer purchase frequency", ylabel="Customers")
    save("06_repeat_customers.png")
    fig, ax = plt.subplots(figsize=(8, 5))
    valid = delivered.dropna(subset=["review_score", "delivery_delay_days"]).copy()
    valid["late"] = valid["delivery_delay_days"] > 0
    vals = valid.groupby("late")["review_score"].mean().reindex([False, True])
    ax.bar(["On time / early", "Late"], vals.values)
    ax.set(title="Average review score by delivery punctuality",
           ylabel="Review score", ylim=(0, 5))
    save("07_review_vs_lateness.png")


def run(data_dir, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    f = load(data_dir)
    orders = prepare(f)
    delivered, monthly, category, customers = business_tables(f, orders)
    delivery_sample = delivered.dropna(
        subset=["order_delivered_customer_date", "order_estimated_delivery_date"])
    metrics = {
        "all_orders": int(len(orders)),
        "delivered_orders": int(len(delivered)),
        "unique_delivered_customers": int(len(customers)),
        "product_revenue_brl": round(float(delivered["item_revenue"].sum()), 2),
        "payment_total_brl": round(float(delivered["payment_total"].sum()), 2),
        "mean_delivery_days": round(float(delivered["delivery_days"].mean()), 2),
        "late_delivery_rate": round(float(delivery_sample["is_late"].mean()), 4),
        "late_delivery_denominator": int(len(delivery_sample)),
        "observed_repeat_customer_rate": round(float(customers["repeat_customer"].mean()), 4),
        "repeat_customer_denominator": int(len(customers)),
    }
    orders.to_csv(out_dir / "order_level.csv", index=False)
    monthly.to_csv(out_dir / "monthly_sales.csv", index=False)
    category.to_csv(out_dir / "category_sales.csv", index=False)
    customers.to_csv(out_dir / "customer_rfm.csv", index=False)
    (out_dir / "kpis.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    make_charts(orders, delivered, monthly, category, customers, out_dir)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = p.parse_args()
    run(args.data_dir, args.out_dir)
