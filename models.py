from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Version(db.Model):
    __tablename__ = 'versions'
    
    id = db.Column(db.Integer, primary_key=True)
    software_name = db.Column(db.String(100), nullable=False, index=True)
    version = db.Column(db.String(50), nullable=False)  # v1.0.0
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)  # 文件大小(bytes)
    
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
        return f"{self.software_name}_v{self.version}.dll"
    
    def get_file_size_mb(self):
        """返回MB格式的文件大小"""
        return round(self.file_size / (1024 * 1024), 2)
