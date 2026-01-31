import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from config import Config
from models import db, Version

app = Flask(__name__)
app.config.from_object(Config)

# 初始化数据库
db.init_app(app)

# 创建上传目录（确保权限正确）
for folder in [app.config['UPLOAD_FOLDER_TESTING'], 
               app.config['UPLOAD_FOLDER_CURRENT'],
               app.config['UPLOAD_FOLDER_HISTORY']]:
    os.makedirs(folder, exist_ok=True)
    os.chmod(folder, 0o755)  # 确保web服务器可写

@app.route('/')
def index():
    """显示最新20个版本"""
    versions = Version.query.order_by(Version.uploaded_at.desc()).limit(20).all()
    return render_template('index.html', versions=versions)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """处理DLL上传"""
    if request.method == 'POST':
        try:
            # 验证必填字段
            required_fields = ['software_name', 'version', 'update_notes', 
                              'test_description', 'test_result', 'test_completed_at',
                              'test_id', 'developer_dri']
            
            for field in required_fields:
                if not request.form.get(field, '').strip():
                    flash(f'❌ "{field}" 为必填项！', 'error')
                    return redirect(request.url)
            
            # 验证文件
            file = request.files['dll_file']
            if not file or not file.filename:
                flash('❌ 未选择文件！', 'error')
                return redirect(request.url)
            
            if not file.filename.lower().endswith('.dll'):
                flash('❌ 仅支持 .dll 文件上传！', 'error')
                return redirect(request.url)
            
            # 保存文件（标准化命名）
            software_name = secure_filename(request.form['software_name'].strip())
            version = request.form['version'].strip().replace('v', '')
            
            # 生成唯一文件名: software_v1.2.3.dll
            filename = f"{software_name}_v{version}.dll"
            file_path = os.path.join(app.config['UPLOAD_FOLDER_CURRENT'], filename)
            
            # 保存文件
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # 创建数据库记录
            new_version = Version(
                software_name=software_name,
                version=version,
                file_path=file_path,
                file_size=file_size,
                update_notes=request.form['update_notes'].strip(),
                test_description=request.form['test_description'].strip(),
                test_result=request.form['test_result'].strip(),
                test_duration=int(request.form.get('test_duration', 0) or 0),
                test_completed_at=datetime.fromisoformat(request.form['test_completed_at']),
                test_id=request.form['test_id'].strip(),
                developer_dri=request.form['developer_dri'].strip(),
                uploaded_by='admin'  # TODO: 集成用户认证
            )
            
            db.session.add(new_version)
            db.session.commit()
            
            # 移动历史版本
            self._archive_old_versions(software_name)
            
            flash(f'✅ {software_name} v{version} 上传成功！', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            app.logger.error(f"Upload error: {str(e)}")
            flash(f'❌ 上传失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

def _archive_old_versions(self, software_name):
    """归档旧版本：保留最新版在current，其余移到history"""
    # 获取该软件的所有版本（按时间排序）
    versions = Version.query.filter_by(software_name=software_name)\
                           .order_by(Version.uploaded_at.desc()).all()
    
    if len(versions) > 1:
        # 除最新版外，其余都归档
        for version in versions[1:]:
            old_path = version.file_path
            if app.config['UPLOAD_FOLDER_CURRENT'] in old_path:
                # 移动到历史目录
                filename = os.path.basename(old_path)
                new_path = os.path.join(app.config['UPLOAD_FOLDER_HISTORY'], filename)
                
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                    version.file_path = new_path
                    db.session.commit()

@app.route('/download/<int:version_id>')
def download(version_id):
    """下载DLL文件"""
    version = Version.query.get_or_404(version_id)
    
    # 更新下载计数
    version.downloaded_count += 1
    db.session.commit()
    
    # 记录审计日志
    app.logger.info(f"Download: {version.software_name} v{version.version} by admin")
    
    return send_file(
        version.file_path,
        as_attachment=True,
        download_name=version.get_filename(),
        mimetype='application/octet-stream'
    )

@app.route('/api/versions')
def api_versions():
    """API：获取所有版本数据"""
    versions = Version.query.order_by(Version.uploaded_at.desc()).all()
    return jsonify([{
        'id': v.id,
        'software': v.software_name,
        'version': v.version,
        'test_result': v.test_result,
        'test_id': v.test_id,
        'developer_dri': v.developer_dri,
        'file_size_mb': v.get_file_size_mb(),
        'uploaded_at': v.uploaded_at.strftime('%Y-%m-%d %H:%M'),
        'downloaded_count': v.downloaded_count
    } for v in versions])

@app.route('/health')
def health_check():
    """健康检查端点（用于监控）"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # 检查存储目录
    storage_status = "ok"
    for folder in [app.config['UPLOAD_FOLDER_TESTING'], 
                  app.config['UPLOAD_FOLDER_CURRENT'],
                  app.config['UPLOAD_BUCKET_HISTORY']]:
        if not os.path.exists(folder) or not os.access(folder, os.W_OK):
            storage_status = f"error: {folder} not writable"
    
    return jsonify({
        'status': 'healthy' if db_status == 'ok' and storage_status == 'ok' else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'storage': storage_status,
        'version': '1.0.0'
    })

def init_db():
    """初始化数据库（首次运行时调用）"""
    with app.app_context():
        db.create_all()
        print("✅ 数据库初始化成功！")
        print(f"   - 数据库存储: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("   - 表已创建: versions")

if __name__ == '__main__':
    # 首次运行时初始化数据库
    init_db()
    
    print("\n" + "="*60)
    print("✅ DLL版本管理系统启动成功！")
    print("="*60)
    print(f"🌍 访问地址: http://192.168.66.213:5000")
    print(f"📤 上传页面: http://192.168.66.213:5000/upload")
    print(f"🔍 API端点: http://192.168.66.213:5000/api/versions")
    print(f"🔧 健康检查: http://192.168.66.213:5000/health")
    print("="*60)
    
    # 生产环境应使用gunicorn，此处仅开发用
    app.run(host='0.0.0.0', port=5000, debug=False)
