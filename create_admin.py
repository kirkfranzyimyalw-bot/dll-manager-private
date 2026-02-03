from app import app, db
from models import User, Role

with app.app_context():
    # 查找或创建admin角色
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='管理员')
        db.session.add(admin_role)
        db.session.commit()
    
    # 查找或创建admin用户
    admin_user = User.query.filter_by(username='Admin').first()
    if not admin_user:
        admin_user = User(
            username='Admin',
            email='admin@example.com',
            phone='13800138000',
            department='IT',
            is_active=True
        )
        admin_user.set_password('Rikaipdm-12345...')
        admin_user.role = admin_role
        db.session.add(admin_user)
        db.session.commit()
        print('✅ 管理员用户创建成功！')
    else:
        # 更新现有管理员用户的密码
        admin_user.set_password('Rikaipdm-12345...')
        db.session.commit()
        print('✅ 管理员用户密码更新成功！')
    
    print(f'管理员用户: {admin_user.username}')
    print(f'所属角色: {admin_user.role.name if admin_user.role else "无"}')
    print(f'是否激活: {admin_user.is_active}')
