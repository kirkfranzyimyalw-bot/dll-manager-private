from app import app, db
from models import User, Role

with app.app_context():
    # 查找Admin用户
    admin_user = User.query.filter_by(username='Admin').first()
    
    if admin_user:
        # 查找role_super_admin角色
        super_admin_role = Role.query.filter_by(name='role_super_admin').first()
        
        if super_admin_role:
            # 更新用户角色
            admin_user.role_id = super_admin_role.id
            db.session.commit()
            print(f'✅ 将Admin用户角色更改为: role_super_admin')
        else:
            print('⚠️  role_super_admin角色不存在')
    else:
        print('⚠️  Admin用户不存在')
    
    # 再次尝试删除admin角色
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        users_with_role = User.query.filter_by(role_id=admin_role.id).all()
        
        if not users_with_role:
            db.session.delete(admin_role)
            db.session.commit()
            print('✅ 删除角色: admin')
        else:
            print(f'⚠️  角色 admin 仍有 {len(users_with_role)} 个用户使用，无法删除')
    
    # 显示最终角色列表
    print('\n最终角色列表:')
    for role in Role.query.all():
        print(f'- {role.name}: {role.description}')
