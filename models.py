from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# 权限模型
class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # 权限名称
    description = db.Column(db.String(200))  # 权限描述
    
    # 关联角色
    roles = db.relationship('Role', secondary='role_permissions', back_populates='permissions')

# 角色模型
class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # 角色名称
    description = db.Column(db.String(200))  # 角色描述
    
    # 关联用户
    users = db.relationship('User', back_populates='role')
    # 关联权限
    permissions = db.relationship('Permission', secondary='role_permissions', back_populates='roles')

# 角色-权限关联表
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

# 用户模型
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20))  # 手机号
    department = db.Column(db.String(100))  # 所属部门
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)  # 登录失败次数
    locked_until = db.Column(db.DateTime)  # 锁定时间
    last_login_at = db.Column(db.DateTime)  # 最后登录时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联角色
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role', back_populates='users')
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        """检查用户是否有指定权限"""
        if not self.role:
            return False
        # 检查是否有*权限（超级管理员）
        if any(p.name == '*' for p in self.role.permissions):
            return True
        # 检查是否有指定权限
        return any(p.name == permission_name for p in self.role.permissions)
    
    def is_locked(self):
        """检查用户是否被锁定"""
        if self.locked_until:
            return self.locked_until > datetime.utcnow()
        return False
    
    def increment_failed_attempts(self):
        """增加登录失败次数"""
        self.failed_login_attempts += 1
        # 失败5次锁定15分钟
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
    
    def reset_failed_attempts(self):
        """重置登录失败次数"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()

# 版本模型
class Version(db.Model):
    __tablename__ = 'versions'
    
    id = db.Column(db.Integer, primary_key=True)
    software_name = db.Column(db.String(100), nullable=False, index=True)
    version = db.Column(db.String(50), nullable=False)  # v1.0.0
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)  # 文件大小(bytes)
    file_type = db.Column(db.String(10), nullable=False)  # 文件类型：dll, exe, apk
    
    # 核心业务字段
    update_notes = db.Column(db.Text, nullable=False)  # 更新说明（必填）
    test_description = db.Column(db.Text, nullable=False)  # 测试描述
    test_result = db.Column(db.String(20), nullable=False)  # 通过/失败/阻塞
    test_duration = db.Column(db.Integer)  # 用时（秒）
    test_completed_at = db.Column(db.DateTime, nullable=False)  # 测试完成时间
    test_id = db.Column(db.String(50), nullable=False)  # 测试ID
    developer_dri = db.Column(db.String(100), nullable=False)  # 开发负责人
    
    # 操作审计
    uploaded_by = db.Column(db.String(80), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    downloaded_count = db.Column(db.Integer, default=0)
    
    def get_filename(self):
        """返回带版本号的文件名（满足重命名需求）"""
        return f"{self.software_name}_v{self.version}.{self.file_type}"
    
    def get_file_size_mb(self):
        """返回MB格式的文件大小"""
        return round(self.file_size / (1024 * 1024), 2)

# 日志模型
class Log(db.Model):
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 操作用户ID
    username = db.Column(db.String(80), nullable=False)  # 操作用户名（冗余存储，便于查询）
    action = db.Column(db.String(50), nullable=False)  # 操作类型：login, logout, upload, download, etc.
    resource_type = db.Column(db.String(50))  # 资源类型：user, version, file, etc.
    resource_id = db.Column(db.Integer)  # 资源ID
    resource_name = db.Column(db.String(255))  # 资源名称
    ip_address = db.Column(db.String(45))  # 客户端IP地址
    user_agent = db.Column(db.String(255))  # 用户代理
    status = db.Column(db.String(20), nullable=False)  # 操作状态：success, failed, error
    message = db.Column(db.Text)  # 操作详情或错误信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 操作时间
