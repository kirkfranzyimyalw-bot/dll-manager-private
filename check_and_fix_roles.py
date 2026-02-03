from app import app, db
from models import Role, Permission

with app.app_context():
    # 定义正确的角色配置
    correct_roles = [
        {
            'code': 'role_super_admin',
            'name': '超级管理员',
            'description': '超级管理员 (Super Admin)',
            'permissions': ['*']
        },
        {
            'code': 'role_admin',
            'name': '管理员',
            'description': '管理员 (Administrator)',
            'permissions': [
                'system:config', 'user:*', 'role:assign', 
                'file:edit_remark', 'file:download', 'file:view', 
                'file:details', 'stats:view', 'audit:view'
            ]
        },
        {
            'code': 'role_tester',
            'name': '测试群组',
            'description': '测试群组 (QA / Tester)',
            'permissions': [
                'file:upload', 'file:download', 'file:delete_own', 
                'file:edit_metadata', 'file:edit_remark', 'file:view', 
                'file:details', 'file:share', 'stats:view', 'audit:view'
            ]
        },
        {
            'code': 'role_ops',
            'name': '运维群组',
            'description': '运维群组 (Operations)',
            'permissions': [
                'file:download', 'file:delete_own', 'file:edit_metadata', 
                'file:edit_remark', 'file:view', 'file:details', 
                'file:share', 'stats:view', 'audit:view'
            ]
        },
        {
            'code': 'role_visitor',
            'name': '访客群组',
            'description': '访客群组 (Visitor)',
            'permissions': [
                'file:edit_remark', 'file:view', 'stats:view', 'audit:view'
            ]
        }
    ]
    
    # 获取所有权限
    all_permissions = {p.name: p for p in Permission.query.all()}
    
    # 检查和修复每个角色
    for role_config in correct_roles:
        # 查找角色
        role = Role.query.filter_by(name=role_config['code']).first()
        
        if role:
            # 更新角色信息
            role.description = role_config['description']
            
            # 清除现有权限
            role.permissions = []
            
            # 添加正确的权限
            for perm_name in role_config['permissions']:
                if perm_name in all_permissions:
                    role.permissions.append(all_permissions[perm_name])
            
            db.session.commit()
            print(f'✅ 修复角色: {role_config["name"]} ({role_config["code"]})')
            print(f'   权限: {" ".join(role_config["permissions"])}')
        else:
            # 创建新角色
            new_role = Role(
                name=role_config['code'],
                description=role_config['description']
            )
            
            # 添加权限
            for perm_name in role_config['permissions']:
                if perm_name in all_permissions:
                    new_role.permissions.append(all_permissions[perm_name])
            
            db.session.add(new_role)
            db.session.commit()
            print(f'✅ 创建角色: {role_config["name"]} ({role_config["code"]})')
            print(f'   权限: {" ".join(role_config["permissions"])}')
    
    # 显示最终结果
    print('\n=== 最终角色配置 ===')
    for role in Role.query.filter(Role.name.in_([r['code'] for r in correct_roles])).all():
        perm_names = [p.name for p in role.permissions]
        print(f'\n{role.description}:')
        print(f'  角色代码: {role.name}')
        print(f'  权限: {" ".join(perm_names)}')
