# Brazilian E-Commerce Delivery Experience Analytics

**E-commerce Analytics | SQL Data Modeling | Customer Experience | Logistics Performance | Machine Learning**

This project analyzes the Brazilian Olist public e-commerce dataset to understand how logistics, payments, product categories and delivery performance affect customer satisfaction.

The case was designed as a portfolio project outside healthcare to show transferable analytics skills in a commercial marketplace context.

## Business question

How can an e-commerce marketplace identify operational factors that drive poor customer reviews and use them to improve logistics, seller performance and customer experience?

## Dataset

The Olist dataset contains anonymized commercial data from Brazilian marketplace orders between 2016 and 2018.

Main entities used:

- Orders
- Order items
- Payments
- Reviews
- Products
- Sellers
- Customers
- Geolocation reference

## Executive metrics

| Metric | Value |
|---|---:|
| Orders | 99,441 |
| Delivered orders | 96,478 |
| Items | 112,650 |
| Unique customers | 96,096 |
| Sellers | 3,095 |
| Products | 32,951 |
| Total GMV including freight | R$ 15,843,553.24 |
| Average order value | R$ 160.99 |
| Average review score | 4.09 |
| Low review rate, score <= 2 | 14.53% |
| Delivery delay rate | 8.11% |
| Average delivery time | 12.56 days |

## Main findings

- Delivery delay is the strongest signal associated with poor reviews.
- Cross-state deliveries are slower and more expensive than same-state deliveries.
- Same-state deliveries averaged around **7.9 days**, while cross-state deliveries averaged around **15.0 days**.
- Cross-state freight was also higher, with average freight of about **R$ 23.69** versus **R$ 13.46** for same-state deliveries.
- Product categories such as bed bath table, furniture decor and computers accessories combine high sales volume with relatively high low-review rates.
- Credit card is the dominant payment method by transaction volume and payment value.

## Machine learning task

A classification model was built to predict whether an order would receive a low review score, defined as review score <= 2.

| Model | Accuracy | ROC-AUC | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.768 | 0.752 | 0.296 | 0.597 | 0.396 |
| Random Forest | 0.839 | 0.759 | 0.397 | 0.519 | 0.450 |

The target is imbalanced, so recall and precision are more useful than accuracy alone. The model is not intended as a final production model, but as an analytical layer to identify dissatisfaction risk drivers.

## Most relevant features

| Feature | Interpretation |
|---|---|
| delay_days | How late the order was compared with the estimated delivery date |
| delivery_days | Total time between purchase and delivery |
| items_count | Number of items in the order |
| freight | Total freight value |
| product_category_name_english | Product category effect |
| customer_state | Customer location pattern |
| sellers_count | Complexity of multi-seller orders |

## Tools and methods

- Python
- Pandas
- Scikit-learn
- SQL / SQLite-ready analytical queries
- Relational data modeling
- Feature engineering
- Customer experience analytics
- Logistics performance analysis

## Files

```text
projects/olist-ecommerce-experience-analytics/
├── README.md
├── data/
│   ├── executive_summary.csv
│   ├── model_metrics.csv
│   ├── feature_importance.csv
│   ├── same_state_vs_cross_state_delivery.csv
│   ├── top_categories_summary.csv
│   ├── payment_summary.csv
│   └── monthly_orders_revenue.csv
├── scripts/
│   └── olist_experience_model.py
└── sql/
    ├── 01_create_order_mart.sql
    ├── 02_delivery_performance.sql
    └── 03_review_risk_features.sql
```

## Why this project matters

This project shows how marketplace data can be turned into an operational intelligence layer. It connects commercial performance, logistics, seller structure and customer reviews into one analytical view.

It also expands my portfolio beyond healthcare, showing that the same analytical approach used in hospital operations can be applied to e-commerce, customer experience and business performance.
