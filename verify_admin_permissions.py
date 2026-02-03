from app import app, db
from models import User, Role

with app.app_context():
    # 查找Admin用户
    admin_user = User.query.filter_by(username='Admin').first()
    
    if admin_user:
        # 查找用户角色
        user_role = Role.query.get(admin_user.role_id)
        
        if user_role:
            print(f'Admin用户角色: {user_role.name}')
            print(f'角色描述: {user_role.description}')
            
            # 检查权限
            perm_names = [p.name for p in user_role.permissions]
            print(f'拥有的权限: {" ".join(perm_names)}')
            
            if '*' in perm_names:
                print('✅ Admin用户拥有超级管理员权限')
            else:
                print('⚠️ Admin用户没有超级管理员权限')
        else:
            print('⚠️ Admin用户没有分配角色')
    else:
        print('⚠️ Admin用户不存在')
