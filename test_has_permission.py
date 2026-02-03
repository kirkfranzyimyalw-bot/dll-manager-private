from app import app, db
from models import User, Role

with app.app_context():
    # 查找Admin用户
    admin_user = User.query.filter_by(username='Admin').first()
    
    if admin_user:
        # 测试各种权限检查
        test_permissions = [
            'manage_users',
            'manage_roles',
            'file:upload',
            'file:download',
            'system:config'
        ]
        
        print('Admin用户权限测试:')
        for perm in test_permissions:
            result = admin_user.has_permission(perm)
            print(f'  {perm}: {"✅" if result else "❌"}')
        
        # 特别测试manage_users权限
        if admin_user.has_permission('manage_users'):
            print('\n✅ Admin用户通过manage_users权限检查，可以看到管理链接')
        else:
            print('\n❌ Admin用户未通过manage_users权限检查，无法看到管理链接')
    else:
        print('⚠️ Admin用户不存在')
