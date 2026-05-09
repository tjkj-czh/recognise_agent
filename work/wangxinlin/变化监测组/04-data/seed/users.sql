-- 初始化角色
INSERT INTO roles (name, description) VALUES
('admin', '系统管理员，拥有全部权限'),
('monitor', '监测员，可执行监测任务和查看数据'),
('guest', '访客，仅可查看公开数据')
ON CONFLICT (name) DO NOTHING;

-- 初始化权限
INSERT INTO permissions (role_id, resource, action)
SELECT id, 'all', 'all' FROM roles WHERE name = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (role_id, resource, action)
SELECT id, 'land-supply', 'read' FROM roles WHERE name = 'monitor'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (role_id, resource, action)
SELECT id, 'monitoring', 'execute' FROM roles WHERE name = 'monitor'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (role_id, resource, action)
SELECT id, 'land-supply', 'read' FROM roles WHERE name = 'guest'
ON CONFLICT DO NOTHING;

-- 初始化测试用户
-- admin password: admin123
-- monitor password: monitor123
-- guest password: guest123
INSERT INTO users (username, password_hash, real_name, role_id, status) VALUES
('admin', '$2b$10$qmpfbyprScvFsIafmtSGKubonH6NRajOValLJZSaK4eI7QtTdLBbW', '系统管理员', (SELECT id FROM roles WHERE name = 'admin'), 'active'),
('monitor', '$2b$10$Th.If9HwoWagnS/repwLfuR.ifEEhm04Qfri0K2Wkia8JoryfDc/G', '监测员', (SELECT id FROM roles WHERE name = 'monitor'), 'active'),
('guest', '$2b$10$.EMF.0u8RoTu1OnR5xJDq.mrgRPcFECSfRv1On3OGoMlvGRt7waje', '访客', (SELECT id FROM roles WHERE name = 'guest'), 'active')
ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash;
