from app import app, db
from models import Role, Permission

with app.app_context():
    # 定义要创建的角色
    roles_to_create = [
        {
            'code': 'role_super_admin',
            'name': '超级管理员',
            'description': '超级管理员 (Super Admin)',
            'permissions': ['upload', 'download', 'view_analytics', 'manage_users', 'manage_roles']
        },
        {
            'code': 'role_admin',
            'name': '管理员',
            'description': '管理员 (Administrator)',
            'permissions': ['upload', 'download', 'view_analytics', 'manage_users', 'manage_roles']
        },
        {
            'code': 'role_tester',
            'name': '测试群组',
            'description': '测试群组 (QA / Tester)',
            'permissions': ['download', 'view_analytics']
        },
        {
            'code': 'role_ops',
            'name': '运维群组',
            'description': '运维群组 (Operations)',
            'permissions': ['upload', 'download', 'view_analytics']
        },
        {
            'code': 'role_visitor',
            'name': '访客群组',
            'description': '访客群组 (Visitor)',
            'permissions': ['view_analytics']
        }
    ]
    
    # 获取所有权限
    all_permissions = {p.name: p for p in Permission.query.all()}
    
    # 创建角色
    for role_data in roles_to_create:
        # 检查角色是否已存在
        existing_role = Role.query.filter_by(name=role_data['name']).first()
        if not existing_role:
            # 创建新角色
            new_role = Role(
                name=role_data['code'],
                description=role_data['description']
            )
            db.session.add(new_role)
            db.session.flush()  # 获取ID但不提交
            
            # 分配权限
            for perm_name in role_data['permissions']:
                if perm_name in all_permissions:
                    new_role.permissions.append(all_permissions[perm_name])
            
            db.session.commit()
            print(f'✅ 创建角色: {role_data["name"]} ({role_data["code"]})')
        else:
            print(f'⚠️  角色已存在: {role_data["name"]}')
    
    # 显示所有角色
    print('\n所有角色:')
    for role in Role.query.all():
        perm_names = [p.name for p in role.permissions]
        print(f'- {role.name}: {role.description}')
        print(f'  权限: {", ".join(perm_names) if perm_names else "无"}')
