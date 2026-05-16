# Olist E-commerce Customer Experience & Logistics Analytics

**E-commerce Analytics | Customer Experience | Logistics Performance | SQL Modeling | Machine Learning**

This project analyzes the Brazilian Olist public e-commerce dataset to understand how delivery performance, freight cost, product category, seller location and payment behavior affect customer satisfaction.

Unlike the healthcare projects in this portfolio, this case focuses on **marketplace operations**, **commercial analytics** and **customer experience intelligence**.

## Business question

What operational and commercial factors are most associated with poor customer experience in a Brazilian marketplace?

## Dataset

The Olist dataset contains approximately 100k orders from 2016 to 2018, distributed across multiple relational tables:

- Orders
- Order items
- Payments
- Reviews
- Customers
- Sellers
- Products
- Product category translation
- Geolocation

## Project angle

The project connects three layers of analysis:

1. **Operational performance** — delivery time, delays, freight, seller-customer distance.
2. **Customer experience** — review score, low-rating rate and written comments.
3. **Predictive analytics** — model to estimate the probability of a low review.

## Key metrics from initial analysis

| Metric | Value |
|---|---:|
| Total orders | 99,441 |
| Delivered orders | 96,478 |
| Order items | 112,650 |
| Reviews | 99,224 |
| Sellers | 3,095 |
| Customers | 99,441 |
| Total product revenue | R$ 13.59M |
| Total freight value | R$ 2.25M |
| Average review score | 4.09 |
| Delivered late rate | 8.1% |
| Average delivery time | 12.6 days |
| Median delivery time | 10.2 days |

## Customer satisfaction findings

| Segment | Average review score | Low review rate |
|---|---:|---:|
| On-time deliveries | 4.29 | 9.2% |
| Late deliveries | 2.57 | 54.0% |

Late delivery is one of the strongest operational signals associated with poor customer experience.

## Distance and logistics findings

Estimated seller-customer distance was calculated using geolocation ZIP code prefixes.

| Distance range | Orders | Avg. delivery days | Late rate | Avg. review score | Avg. freight |
|---|---:|---:|---:|---:|---:|
| 0–50 km | 11,729 | 6.2 | 6.5% | 4.28 | R$ 13.15 |
| 50–200 km | 12,892 | 8.0 | 6.2% | 4.29 | R$ 15.67 |
| 200–500 km | 30,255 | 12.1 | 7.4% | 4.15 | R$ 21.88 |
| 500–1000 km | 25,744 | 14.3 | 8.4% | 4.11 | R$ 24.16 |
| 1000–2000 km | 9,744 | 18.0 | 10.8% | 4.05 | R$ 33.08 |
| 2000+ km | 5,610 | 21.2 | 13.7% | 3.98 | R$ 39.86 |

Longer distances are associated with higher freight values, longer delivery times and slightly lower review scores.

## Low-review prediction model

Target variable:

```text
low_review = 1 if review_score <= 2, else 0
```

Baseline models tested:

| Model | Accuracy | ROC-AUC | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.810 | 0.755 | 0.347 | 0.557 | 0.428 |
| Random Forest | 0.836 | 0.761 | 0.395 | 0.536 | 0.455 |

The model is not designed as a final production classifier. Its purpose is to identify useful operational drivers of dissatisfaction.

## Most relevant predictive features

| Feature | Interpretation |
|---|---|
| item_count | Multi-item orders may have more fulfillment complexity |
| delay_days | Delay beyond estimated delivery date strongly affects satisfaction |
| product_category_name_english | Some product categories are more prone to low ratings |
| delivery_days | Longer delivery time impacts customer experience |
| late_delivery | Binary delay flag with strong business meaning |
| carrier_handoff_days | Time until seller/carrier processing affects downstream delivery |
| seller_count | Multi-seller orders can increase complexity |
| seller_customer_km | Distance affects time, freight and service experience |

## Suggested dashboard pages

1. **Executive Overview**
   - GMV, freight, orders, review score, late delivery rate
2. **Customer Experience**
   - Review score by delivery status, category, state and payment type
3. **Logistics Performance**
   - Delivery time, delay days, freight ratio and seller-customer distance
4. **Seller Performance**
   - Seller clusters by late rate, review score and revenue
5. **Risk Monitor**
   - Probability of low review by order profile

## Tools and stack

This project is designed to expand the portfolio stack beyond healthcare analytics:

| Layer | Tools |
|---|---|
| Data modeling | SQL, DuckDB, relational joins |
| Analytics | Python, Pandas, Polars-ready structure |
| Visualization | Plotly, Streamlit dashboard concept |
| Machine Learning | Scikit-learn, classification, feature importance |
| Geospatial analysis | Haversine distance, geolocation ZIP prefixes |
| NLP extension | Review text analysis, TF-IDF, sentiment/topic extraction |
| Portfolio delivery | GitHub, README, reproducible scripts |

## Methodology

1. Import and validate all Olist relational tables.
2. Build an order-level analytical table.
3. Join orders, items, payments, reviews, customers, sellers, products and geolocation.
4. Engineer operational features: delivery days, delay days, freight ratio, seller-customer distance.
5. Analyze dissatisfaction drivers using reviews and operational metrics.
6. Train baseline models to predict low review probability.
7. Translate findings into dashboard and business recommendations.

## Business recommendations

- Monitor late orders as a direct customer experience risk.
- Track seller-customer distance and freight ratio as logistics pressure indicators.
- Segment low reviews by product category to detect product quality or expectation issues.
- Create seller performance scorecards combining delivery reliability and review quality.
- Use low-review prediction as an early warning layer, not as an isolated decision tool.

## Next steps

- Build a Streamlit dashboard with interactive filters.
- Add DuckDB SQL models for reproducible relational analysis.
- Add NLP analysis over review comments.
- Create seller segmentation using clustering.
- Deploy a lightweight dashboard and connect it to the portfolio site.
