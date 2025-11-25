-- Top 10 best-selling products
SELECT 
    product_name,
    category,
    COUNT(order_id) as order_count,
    SUM(revenue) as total_revenue,
    AVG(sales_amount) as avg_order_value
FROM sales_fact
GROUP BY product_name, category
ORDER BY total_revenue DESC
LIMIT 10;

-- Monthly revenue trend
SELECT 
    year,
    month,
    SUM(revenue) as monthly_revenue,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(order_id) as total_orders
FROM sales_fact
GROUP BY year, month
ORDER BY year DESC, month DESC;

-- Customer segmentation (RFM - Recency, Frequency, Monetary)
SELECT 
    customer_id,
    DATEDIFF(day, MAX(order_date), CURRENT_DATE) as recency_days,
    COUNT(order_id) as frequency,
    SUM(revenue) as monetary_value,
    CASE 
        WHEN SUM(revenue) > 1000 THEN 'High Value'
        WHEN SUM(revenue) > 500 THEN 'Medium Value'
        ELSE 'Low Value'
    END as customer_segment
FROM sales_fact
GROUP BY customer_id
ORDER BY monetary_value DESC;

-- Regional performance
SELECT 
    region,
    COUNT(order_id) as total_orders,
    SUM(revenue) as total_revenue,
    AVG(sales_amount) as avg_order_value,
    COUNT(DISTINCT customer_id) as unique_customers
FROM sales_fact
GROUP BY region
ORDER BY total_revenue DESC;
