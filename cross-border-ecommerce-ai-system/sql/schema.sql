-- 跨境电商AI系统数据库Schema
-- PostgreSQL 14+

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100),
    total_amount DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending',
    ai_recommendations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_platform ON orders(platform);

-- 库存表
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(255),
    available_quantity INT DEFAULT 0,
    in_transit_quantity INT DEFAULT 0,
    reserved_quantity INT DEFAULT 0,
    supplier_lead_time_days INT DEFAULT 14,
    reorder_point INT,
    safety_stock INT,
    warehouse_location VARCHAR(100),
    cost DECIMAL(10, 2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_sku ON inventory(sku);
CREATE INDEX idx_inventory_available ON inventory(available_quantity);

-- 销售历史表
CREATE TABLE IF NOT EXISTS sales_history (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) NOT NULL,
    order_id VARCHAR(100),
    quantity INT NOT NULL,
    price DECIMAL(10, 2),
    platform VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sales_sku_date ON sales_history(sku, created_at);
CREATE INDEX idx_sales_created_at ON sales_history(created_at);

-- 价格历史表
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) NOT NULL,
    old_price DECIMAL(10, 2),
    new_price DECIMAL(10, 2),
    adjustment_pct DECIMAL(5, 3),
    reasoning TEXT,
    approved BOOLEAN DEFAULT false,
    approved_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_price_sku_date ON price_history(sku, created_at);

-- 采购订单表
CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(100) UNIQUE,
    sku VARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    unit_cost DECIMAL(10, 2),
    total_cost DECIMAL(10, 2),
    supplier VARCHAR(100),
    status VARCHAR(50) DEFAULT 'draft',
    reason TEXT,
    forecast_demand INT,
    expected_delivery_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(100)
);

CREATE INDEX idx_po_status ON purchase_orders(status);
CREATE INDEX idx_po_sku ON purchase_orders(sku);

-- 库存告警表
CREATE TABLE IF NOT EXISTS inventory_alerts (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    current_stock INT,
    recommended_qty INT,
    alerts JSONB,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_sku ON inventory_alerts(sku);
CREATE INDEX idx_alerts_type ON inventory_alerts(alert_type);
CREATE INDEX idx_alerts_acknowledged ON inventory_alerts(acknowledged);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(100),
    execution_id VARCHAR(100),
    order_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    user_id VARCHAR(100),
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_workflow ON audit_logs(workflow_id);
CREATE INDEX idx_audit_execution ON audit_logs(execution_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);

-- 性能指标表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100) UNIQUE,
    workflow_id VARCHAR(100),
    duration_ms INT,
    items_processed INT,
    success_count INT,
    error_count INT,
    review_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_workflow ON performance_metrics(workflow_id);
CREATE INDEX idx_metrics_created_at ON performance_metrics(created_at);

-- 客户信息表
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    language VARCHAR(10) DEFAULT 'en',
    preferred_contact VARCHAR(50),
    lifetime_value DECIMAL(10, 2),
    total_orders INT DEFAULT 0,
    vip_status BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_vip ON customers(vip_status);

-- 客服工单表
CREATE TABLE IF NOT EXISTS support_tickets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100),
    customer_id VARCHAR(100),
    subject VARCHAR(255),
    message TEXT,
    sentiment_score DECIMAL(3, 2),
    escalated BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'open',
    assigned_to VARCHAR(100),
    ai_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_tickets_status ON support_tickets(status);
CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
CREATE INDEX idx_tickets_escalated ON support_tickets(escalated);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表添加更新时间触发器
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_support_tickets_updated_at BEFORE UPDATE ON support_tickets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
