import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, g
import jwt
from werkzeug.utils import secure_filename
from config import Config
from models import db, Version, User, Role, Permission

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

# JWT配置
app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(hours=24)

# 生成JWT token
def generate_token(user_id):
    """生成JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

# 验证JWT token
def verify_token(token):
    """验证JWT token"""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# 获取当前用户
def get_current_user():
    """获取当前用户"""
    token = request.cookies.get('token') or request.headers.get('Authorization')
    if token:
        if 'Bearer ' in token:
            token = token.replace('Bearer ', '')
        user_id = verify_token(token)
        if user_id:
            return User.query.get(user_id)
    return None

# 权限验证装饰器
def require_permission(permission_name):
    """权限验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash('❌ 请先登录！', 'error')
                return redirect(url_for('login'))
            
            if not user.has_permission(permission_name):
                flash('❌ 权限不足！', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 登录验证装饰器
def require_login():
    """登录验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash('❌ 请先登录！', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 上下文处理器，将函数暴露给模板
@app.context_processor
def inject_functions():
    """将函数暴露给模板"""
    return {
        'get_current_user': get_current_user
    }

# 记录操作日志
def log_operation(user, action, resource_type=None, resource_id=None, resource_name=None, status='success', message=None):
    """记录操作日志"""
    from models import Log
    
    log = Log(
        user_id=user.id if user else None,
        username=user.username if user else 'anonymous',
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status=status,
        message=message
    )
    
    try:
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Log error: {str(e)}")
        # 日志记录失败不应影响主流程，所以这里只是记录错误，不抛出异常

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        try:
            # 验证必填字段
            required_fields = ['username', 'email', 'password', 'full_name']
            for field in required_fields:
                if not request.form.get(field, '').strip():
                    flash(f'❌ "{field}" 为必填项！', 'error')
                    return redirect(request.url)
            
            # 强密码策略验证（最小8位）
            password = request.form['password']
            if len(password) < 8:
                flash('❌ 密码长度必须至少8位！', 'error')
                return redirect(request.url)
            
            # 验证用户名是否已存在
            if User.query.filter_by(username=request.form['username'].strip()).first():
                flash('❌ 用户名已存在！', 'error')
                return redirect(request.url)
            
            # 验证邮箱是否已存在
            if User.query.filter_by(email=request.form['email'].strip()).first():
                flash('❌ 邮箱已存在！', 'error')
                return redirect(request.url)
            
            # 创建用户
            user = User(
                username=request.form['username'].strip(),
                email=request.form['email'].strip(),
                full_name=request.form['full_name'].strip()
            )
            user.set_password(request.form['password'])
            
            # 分配默认角色（普通用户）
            default_role = Role.query.filter_by(name='user').first()
            if default_role:
                user.role_id = default_role.id
            
            db.session.add(user)
            db.session.commit()
            
            # 记录注册日志
            log_operation(user, 'register', 'user', user.id, user.username, 'success', f'用户 {user.username} 注册成功')
            
            flash('✅ 注册成功！请登录。', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f"Register error: {str(e)}")
            flash(f'❌ 注册失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('register.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        try:
            # 验证必填字段
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash('❌ 用户名和密码为必填项！', 'error')
                return redirect(request.url)
            
            # 验证用户
            user = User.query.filter_by(username=username).first()
            if not user:
                # 记录登录失败日志
                log_operation(None, 'login', 'user', None, username, 'failed', f'用户 {username} 登录失败：用户名或密码错误')
                flash('❌ 用户名或密码错误！', 'error')
                return redirect(request.url)
            
            # 检查用户是否被锁定
            if user.is_locked():
                flash('❌ 账号已被锁定，请15分钟后再试！', 'error')
                return redirect(url_for('login'))
            
            # 检查用户状态
            if not user.is_active:
                # 记录登录失败日志
                log_operation(user, 'login', 'user', user.id, user.username, 'failed', f'用户 {user.username} 登录失败：账号已被禁用')
                flash('❌ 账号已被禁用！', 'error')
                return redirect(url_for('login'))
            
            # 验证密码
            if not user.check_password(password):
                # 增加登录失败次数
                user.increment_failed_attempts()
                db.session.commit()
                
                # 记录登录失败日志
                log_operation(user, 'login', 'user', user.id, user.username, 'failed', f'用户 {user.username} 登录失败：用户名或密码错误')
                flash('❌ 用户名或密码错误！', 'error')
                return redirect(request.url)
            
            # 重置登录失败次数并更新最后登录时间
            user.reset_failed_attempts()
            db.session.commit()
            
            # 生成token
            token = generate_token(user.id)
            
            # 设置cookie
            response = redirect(url_for('index'))
            response.set_cookie('token', token, max_age=86400)
            
            # 记录登录成功日志
            log_operation(user, 'login', 'user', user.id, user.username, 'success', f'用户 {user.username} 登录成功')
            
            flash(f'✅ 登录成功！欢迎回来，{user.full_name}', 'success')
            return response
            
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash(f'❌ 登录失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('login.html')

# 登出路由
@app.route('/logout')
def logout():
    """用户登出"""
    # 获取当前用户
    user = get_current_user()
    
    # 记录登出日志
    if user:
        log_operation(user, 'logout', 'user', user.id, user.username, 'success', f'用户 {user.username} 登出成功')
    
    response = redirect(url_for('login'))
    response.delete_cookie('token')
    flash('✅ 登出成功！', 'success')
    return response

# 用户信息维护路由
@app.route('/user/profile', methods=['GET', 'POST'])
def user_profile():
    """用户信息维护"""
    # 获取当前用户
    token = request.cookies.get('token')
    if not token:
        flash('❌ 请先登录！', 'error')
        return redirect(url_for('login'))
    
    user_id = verify_token(token)
    if not user_id:
        flash('❌ 登录已过期，请重新登录！', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('❌ 用户不存在！', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # 更新用户信息
            user.full_name = request.form.get('full_name', '').strip()
            user.email = request.form.get('email', '').strip()
            
            # 如果修改密码
            password = request.form.get('password', '').strip()
            if password:
                user.set_password(password)
            
            db.session.commit()
            
            # 记录个人信息更新日志
            log_operation(user, 'update_profile', 'user', user.id, user.username, 'success', f'用户 {user.username} 更新个人信息成功')
            
            flash('✅ 个人信息更新成功！', 'success')
            return redirect(request.url)
            
        except Exception as e:
            app.logger.error(f"Update profile error: {str(e)}")
            flash(f'❌ 更新失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('profile.html', user=user)

@app.route('/')
def index():
    """显示最新20个版本"""
    versions = Version.query.order_by(Version.uploaded_at.desc()).limit(20).all()
    return render_template('index.html', versions=versions)

@app.route('/upload', methods=['GET', 'POST'])
@require_login()
def upload():
    """处理文件上传"""
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
            file = request.files['file']
            if not file or not file.filename:
                flash('❌ 未选择文件！', 'error')
                return redirect(request.url)
            
            # 获取文件类型
            file_ext = file.filename.lower().split('.')[-1]
            # 支持的文件类型
            supported_types = ['dll', 'exe', 'apk', 'so', 'jar']
            if file_ext not in supported_types:
                supported_extensions = ', '.join([f'.{ext}' for ext in supported_types])
                flash(f'❌ 仅支持 {supported_extensions} 文件上传！', 'error')
                return redirect(request.url)
            
            # 文件头校验（扩展名+文件头双重校验）
            def check_file_header(file, expected_ext):
                """检查文件头是否与扩展名匹配"""
                # 保存当前文件位置
                current_pos = file.tell()
                try:
                    # 读取文件头
                    header = file.read(12)
                    # 重置文件位置
                    file.seek(current_pos)
                    
                    if expected_ext in ['dll', 'exe']:
                        # DLL和EXE文件头：MZ
                        return header.startswith(b'MZ')
                    elif expected_ext == 'apk':
                        # APK文件头：PK（ZIP格式）
                        return header.startswith(b'PK')
                    elif expected_ext == 'so':
                        # SO文件头：ELF
                        return header.startswith(b'\x7fELF')
                    elif expected_ext == 'jar':
                        # JAR文件头：PK（ZIP格式）
                        return header.startswith(b'PK')
                    return True
                except:
                    # 重置文件位置
                    file.seek(current_pos)
                    return False
            
            # 验证文件头
            if not check_file_header(file, file_ext):
                flash(f'❌ 文件类型与扩展名不匹配！', 'error')
                return redirect(request.url)
            
            # ClamAV病毒扫描（占位符）
            # 实际部署时，需要安装ClamAV并配置clamd服务
            # if not scan_file_for_viruses(file):
            #     flash('❌ 文件检测到病毒，上传失败！', 'error')
            #     return redirect(request.url)
            
            # 保存文件（标准化命名）
            software_name = secure_filename(request.form['software_name'].strip())
            version = request.form['version'].strip().replace('v', '')
            
            # 1. 自动建文件夹：为每个软件创建单独的文件夹
            software_folder = os.path.join(app.config['UPLOAD_FOLDER_CURRENT'], software_name)
            os.makedirs(software_folder, exist_ok=True)
            
            # 2. 旧文件重命名：检查是否存在同名文件
            filename = f"{software_name}_v{version}.{file_ext}"
            file_path = os.path.join(software_folder, filename)
            
            # 如果文件已存在，重命名旧文件
            if os.path.exists(file_path):
                old_filename = f"{software_name}_v{version}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_ext}"
                old_file_path = os.path.join(software_folder, old_filename)
                os.rename(file_path, old_file_path)
                app.logger.info(f"旧文件重命名: {filename} -> {old_filename}")
            
            # 保存文件
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # 3. 版本自动解析：这里可以集成文件版本解析逻辑
            # 目前使用用户输入的版本号，后续可以扩展为自动解析
            # version = parse_file_version(file_path, file_ext) or version
            
            # 获取当前用户
            current_user = get_current_user()
            uploaded_by = current_user.username if current_user else 'admin'
            
            # 创建数据库记录
            new_version = Version(
                software_name=software_name,
                version=version,
                file_path=file_path,
                file_size=file_size,
                file_type=file_ext,
                update_notes=request.form['update_notes'].strip(),
                test_description=request.form['test_description'].strip(),
                test_result=request.form['test_result'].strip(),
                test_duration=int(request.form.get('test_duration', 0) or 0),
                test_completed_at=datetime.fromisoformat(request.form['test_completed_at']),
                test_id=request.form['test_id'].strip(),
                developer_dri=request.form['developer_dri'].strip(),
                uploaded_by=uploaded_by
            )
            
            db.session.add(new_version)
            db.session.commit()
            
            # 记录上传日志
            log_operation(current_user, 'upload', 'version', new_version.id, f'{software_name} v{version}', 'success', f'用户 {current_user.username} 上传文件 {software_name} v{version}.{file_ext} 成功')
            
            flash(f'✅ {software_name} v{version} 上传成功！', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            app.logger.error(f"Upload error: {str(e)}")
            flash(f'❌ 上传失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

def archive_old_versions(software_name):
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
@require_login()
def download(version_id):
    """下载文件"""
    version = Version.query.get_or_404(version_id)
    
    # 更新下载计数
    version.downloaded_count += 1
    db.session.commit()
    
    # 获取当前用户
    current_user = get_current_user()
    user_name = current_user.username if current_user else 'admin'
    
    # 记录审计日志
    app.logger.info(f"Download: {version.software_name} v{version.version} ({version.file_type}) by {user_name}")
    
    # 记录下载日志
    log_operation(current_user, 'download', 'version', version.id, f'{version.software_name} v{version.version}', 'success', f'用户 {user_name} 下载文件 {version.software_name} v{version.version}.{version.file_type} 成功')
    
    # 根据文件类型设置mimetype
    mimetype_map = {
        'dll': 'application/octet-stream',
        'exe': 'application/x-msdownload',
        'apk': 'application/vnd.android.package-archive'
    }
    mimetype = mimetype_map.get(version.file_type, 'application/octet-stream')
    
    return send_file(
        version.file_path,
        as_attachment=True,
        download_name=version.get_filename(),
        mimetype=mimetype
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
                  app.config['UPLOAD_FOLDER_HISTORY']]:
        if not os.path.exists(folder) or not os.access(folder, os.W_OK):
            storage_status = f"error: {folder} not writable"
    
    return jsonify({
        'status': 'healthy' if db_status == 'ok' and storage_status == 'ok' else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'storage': storage_status,
        'version': '1.0.0'
    })

# 数据分析路由
@app.route('/analytics')
@require_login()
def analytics():
    """数据分析页面"""
    # 获取当前用户
    user = get_current_user()
    
    # 获取版本数据
    versions = Version.query.order_by(Version.uploaded_at.desc()).all()
    
    # 准备图表数据
    # 1. 版本趋势数据（按月份）
    version_trend = {}
    for v in versions:
        month = v.uploaded_at.strftime('%Y-%m')
        if month not in version_trend:
            version_trend[month] = 0
        version_trend[month] += 1
    
    # 2. 测试结果统计
    test_results = {'通过': 0, '失败': 0, '阻塞': 0}
    for v in versions:
        if v.test_result in test_results:
            test_results[v.test_result] += 1
    
    # 3. 文件类型分布
    file_types = {}
    for v in versions:
        if v.file_type not in file_types:
            file_types[v.file_type] = 0
        file_types[v.file_type] += 1
    
    # 4. 下载量统计（前10个版本）
    top_downloads = Version.query.order_by(Version.downloaded_count.desc()).limit(10).all()
    
    # 5. 文件大小分布
    file_sizes = []
    for v in versions:
        file_sizes.append({
            'name': f"{v.software_name} v{v.version}",
            'size': v.get_file_size_mb()
        })
    
    return render_template('analytics.html', 
                           user=user,
                           version_trend=version_trend,
                           test_results=test_results,
                           file_types=file_types,
                           top_downloads=top_downloads,
                           file_sizes=file_sizes)

# API：获取数据分析数据
@app.route('/api/analytics')
@require_login()
def api_analytics():
    """API：获取数据分析数据"""
    # 获取版本数据
    versions = Version.query.order_by(Version.uploaded_at.desc()).all()
    
    # 准备图表数据
    # 1. 版本趋势数据（按月份）
    version_trend = {}
    for v in versions:
        month = v.uploaded_at.strftime('%Y-%m')
        if month not in version_trend:
            version_trend[month] = 0
        version_trend[month] += 1
    
    # 2. 测试结果统计
    test_results = {'通过': 0, '失败': 0, '阻塞': 0}
    for v in versions:
        if v.test_result in test_results:
            test_results[v.test_result] += 1
    
    # 3. 文件类型分布
    file_types = {}
    for v in versions:
        if v.file_type not in file_types:
            file_types[v.file_type] = 0
        file_types[v.file_type] += 1
    
    # 4. 下载量统计（前10个版本）
    top_downloads = []
    for v in Version.query.order_by(Version.downloaded_count.desc()).limit(10).all():
        top_downloads.append({
            'name': f"{v.software_name} v{v.version}",
            'downloads': v.downloaded_count
        })
    
    return jsonify({
        'version_trend': version_trend,
        'test_results': test_results,
        'file_types': file_types,
        'top_downloads': top_downloads
    })

# 用户管理路由
@app.route('/admin/users')
@require_login()
def user_management():
    """用户管理页面"""
    # 获取当前用户
    current_user = get_current_user()
    if not current_user or not current_user.has_permission('manage_users'):
        flash('❌ 权限不足！', 'error')
        return redirect(url_for('index'))
    
    # 获取所有用户
    users = User.query.all()
    
    return render_template('user_management.html', users=users)

# 角色管理路由
@app.route('/admin/roles')
@require_login()
def role_management():
    """角色管理页面"""
    # 获取当前用户
    current_user = get_current_user()
    if not current_user or not current_user.has_permission('manage_roles'):
        flash('❌ 权限不足！', 'error')
        return redirect(url_for('index'))
    
    # 获取所有角色
    roles = Role.query.all()
    
    return render_template('role_management.html', roles=roles)

def init_db():
    """初始化数据库（首次运行时调用）"""
    with app.app_context():
        db.create_all()
        print("✅ 数据库初始化成功！")
        print(f"   - 数据库存储: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("   - 表已创建: versions, users, roles, permissions, logs")
        
        # 创建默认角色和权限
        try:
            # 创建默认权限
            default_permissions = [
                Permission(name='upload', description='上传文件'),
                Permission(name='download', description='下载文件'),
                Permission(name='view_analytics', description='查看数据分析'),
                Permission(name='manage_users', description='管理用户'),
                Permission(name='manage_roles', description='管理角色'),
            ]
            for perm in default_permissions:
                if not Permission.query.filter_by(name=perm.name).first():
                    db.session.add(perm)
            
            # 创建默认角色
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin', description='管理员')
                db.session.add(admin_role)
            
            user_role = Role.query.filter_by(name='user').first()
            if not user_role:
                user_role = Role(name='user', description='普通用户')
                db.session.add(user_role)
            
            db.session.commit()
            
            # 为角色分配权限
            # 管理员角色分配所有权限
            for perm in default_permissions:
                if perm not in admin_role.permissions:
                    admin_role.permissions.append(perm)
            
            # 普通用户分配基本权限
            basic_permissions = ['upload', 'download', 'view_analytics']
            for perm in default_permissions:
                if perm.name in basic_permissions and perm not in user_role.permissions:
                    user_role.permissions.append(perm)
            
            db.session.commit()
            print("✅ 默认角色和权限创建成功！")
        except Exception as e:
            app.logger.error(f"初始化默认角色和权限失败: {str(e)}")
            db.session.rollback()

# 添加上下文处理器，让get_current_user在模板中可用
@app.context_processor
def inject_user():
    return dict(get_current_user=get_current_user)

if __name__ == '__main__':
    # 首次运行时初始化数据库
    init_db()
    
    port = 5001
    
    print("\n" + "="*60)
    print("✅ DLL版本管理系统启动成功！")
    print("="*60)
    print(f"🌍 访问地址: http://192.168.66.213:{port}")
    print(f"📤 上传页面: http://192.168.66.213:{port}/upload")
    print(f"📊 数据分析: http://192.168.66.213:{port}/analytics")
    print(f"🔍 API端点: http://192.168.66.213:{port}/api/versions")
    print(f"🔧 健康检查: http://192.168.66.213:{port}/health")
    print(f"👤 个人信息: http://192.168.66.213:{port}/user/profile")
    print(f"🔑 登录页面: http://192.168.66.213:{port}/login")
    print("="*60)

    # 生产环境应使用gunicorn，此处仅开发用
    app.run(host='0.0.0.0', port=port, debug=False)
