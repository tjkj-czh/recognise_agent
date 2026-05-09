-- 用户权限管理表
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(100),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'locked')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, resource, action)
);

-- 土地供应信息表
CREATE TABLE IF NOT EXISTS land_supplies (
    id SERIAL PRIMARY KEY,
    resource_id VARCHAR(100) NOT NULL,
    transfer_no VARCHAR(100) NOT NULL,
    district VARCHAR(50) NOT NULL,
    land_use_type VARCHAR(100) NOT NULL,
    area_sqm NUMERIC(15, 2) NOT NULL,
    area_mu NUMERIC(15, 2) NOT NULL,
    plot_ratio NUMERIC(5, 2),
    starting_price NUMERIC(15, 2),
    transaction_price NUMERIC(15, 2),
    transaction_date DATE,
    estimated_date DATE,
    transaction_stage VARCHAR(50) NOT NULL,
    system_type VARCHAR(50) NOT NULL,
    longitude NUMERIC(10, 6) NOT NULL,
    latitude NUMERIC(10, 6) NOT NULL,
    plot_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_permissions_role ON permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_land_supplies_district ON land_supplies(district);
CREATE INDEX IF NOT EXISTS idx_land_supplies_stage ON land_supplies(transaction_stage);
CREATE INDEX IF NOT EXISTS idx_land_supplies_coords ON land_supplies(longitude, latitude);
