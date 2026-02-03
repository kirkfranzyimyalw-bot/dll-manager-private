from app import app, db
from models import User, Role, Permission

with app.app_context():
    # 查找Admin用户
    admin_user = User.query.filter_by(username='Admin').first()
    print('Admin用户:', admin_user)
    
    if admin_user:
        print('用户角色:', admin_user.role.name if admin_user.role else '无')
        print('是否有manage_users权限:', admin_user.has_permission('manage_users'))
        print('是否有manage_roles权限:', admin_user.has_permission('manage_roles'))
    
    # 查找所有权限
    permissions = Permission.query.all()
    print('\n所有权限:')
    for perm in permissions:
        print(f'- {perm.name}: {perm.description}')
    
    # 查找admin角色
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        print('\nAdmin角色权限:')
        for perm in admin_role.permissions:
            print(f'- {perm.name}')
