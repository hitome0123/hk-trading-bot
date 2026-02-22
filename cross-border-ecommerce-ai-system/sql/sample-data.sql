-- 示例数据 - 跨境电商AI系统
-- 用于演示和测试

-- 插入示例库存数据
INSERT INTO inventory (sku, product_name, available_quantity, in_transit_quantity, supplier_lead_time_days, cost) VALUES
('PROD-A-001', 'Wireless Bluetooth Headphones', 150, 50, 14, 15.99),
('PROD-A-002', 'USB-C Charging Cable', 500, 0, 7, 2.99),
('PROD-A-003', 'Smart Watch Band', 80, 100, 21, 8.50),
('PROD-B-001', 'Portable Phone Charger', 45, 0, 14, 12.00),
('PROD-B-002', 'Screen Protector Pack', 300, 100, 7, 1.50);

-- 插入示例销售历史（过去30天）
INSERT INTO sales_history (sku, order_id, quantity, price, platform, created_at) VALUES
('PROD-A-001', 'AMZ-001', 2, 29.99, 'amazon', CURRENT_TIMESTAMP - INTERVAL '1 day'),
('PROD-A-001', 'EB-001', 1, 29.99, 'ebay', CURRENT_TIMESTAMP - INTERVAL '2 days'),
('PROD-A-002', 'SHOP-001', 5, 5.99, 'shopify', CURRENT_TIMESTAMP - INTERVAL '1 day'),
('PROD-A-003', 'AMZ-002', 3, 15.99, 'amazon', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('PROD-B-001', 'EB-002', 1, 24.99, 'ebay', CURRENT_TIMESTAMP - INTERVAL '5 days');

-- 插入示例订单
INSERT INTO orders (order_id, platform, customer_id, total_amount, currency, status) VALUES
('AMZ-12345', 'amazon', 'CUST-001', 89.97, 'USD', 'pending'),
('EB-67890', 'ebay', 'CUST-002', 54.98, 'USD', 'pending'),
('SHOP-11111', 'shopify', 'CUST-003', 149.99, 'USD', 'processing');

-- 插入示例客户
INSERT INTO customers (customer_id, email, name, language, total_orders, lifetime_value, vip_status) VALUES
('CUST-001', 'john@example.com', 'John Smith', 'en', 5, 450.00, false),
('CUST-002', 'maria@example.com', 'Maria Garcia', 'es', 12, 1250.00, true),
('CUST-003', 'zhang@example.com', 'Zhang Wei', 'zh', 8, 890.00, false);

-- 插入示例价格历史
INSERT INTO price_history (sku, old_price, new_price, adjustment_pct, reasoning, approved) VALUES
('PROD-A-001', 29.99, 27.99, -0.067, 'Competitor price drop detected', true),
('PROD-A-003', 15.99, 17.99, 0.125, 'Increased demand + low inventory', false);

-- 插入示例告警
INSERT INTO inventory_alerts (sku, alert_type, current_stock, recommended_qty, alerts) VALUES
('PROD-B-001', 'reorder', 45, 100, '["CRITICAL: Less than 7 days of stock", "Reorder recommended: 100 units"]'),
('PROD-A-002', 'slow_moving', 500, 0, '["Slow-moving inventory detected"]');
