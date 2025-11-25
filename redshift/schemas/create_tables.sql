-- Drop existing table if exists
DROP TABLE IF EXISTS sales_fact;

-- Create sales fact table
CREATE TABLE sales_fact (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255),
    category VARCHAR(100),
    order_date DATE NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2),
    sales_amount DECIMAL(12, 2),
    revenue DECIMAL(12, 2),
    year INT,
    month INT,
    quarter INT,
    region VARCHAR(50),
    processed_timestamp TIMESTAMP,
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT positive_amount CHECK (sales_amount > 0)
)
DISTSTYLE KEY
DISTKEY (customer_id)
SORTKEY (order_date);

-- Create indexes for faster queries
CREATE INDEX idx_order_date ON sales_fact(order_date);
CREATE INDEX idx_product_id ON sales_fact(product_id);
CREATE INDEX idx_customer_id ON sales_fact(customer_id);

-- Create aggregated views for analytics
CREATE VIEW monthly_revenue AS
SELECT 
    year,
    month,
    category,
    SUM(revenue) as total_revenue,
    COUNT(DISTINCT order_id) as order_count,
    COUNT(DISTINCT customer_id) as unique_customers,
    AVG(sales_amount) as avg_order_value
FROM sales_fact
GROUP BY year, month, category;

-- Create customer analytics view
CREATE VIEW customer_analytics AS
SELECT 
    customer_id,
    COUNT(order_id) as total_orders,
    SUM(revenue) as lifetime_value,
    AVG(sales_amount) as avg_order_value,
    MAX(order_date) as last_order_date,
    DATEDIFF(day, MAX(order_date), CURRENT_DATE) as days_since_last_order
FROM sales_fact
GROUP BY customer_id;
