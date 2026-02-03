from app import app, db
from models import Role, Permission

with app.app_context():
    # 定义修正后的角色配置
    corrected_roles = [
        {
            'code': 'role_super_admin',
            'permissions': ['*']
        },
        {
            'code': 'role_admin',
            'permissions': [
                'system:config', 'user:*', 'role:assign', 
                'file:edit_remark', 'file:edit_metadata', 'file:download', 
                'file:view', 'file:details', 'stats:view', 'audit:view'
            ]
        },
        {
            'code': 'role_tester',
            'permissions': [
                'file:upload', 'file:download', 'file:view', 'file:details', 
                'file:delete_own', 'file:edit_metadata', 'file:edit_remark', 
                'file:share', 'stats:view', 'audit:view'
            ]
        },
        {
            'code': 'role_ops',
            'permissions': [
                'file:edit_remark', 'file:download', 'file:view', 'file:details'
            ]
        },
        {
            'code': 'role_visitor',
            'permissions': [
                'file:edit_remark', 'file:view', 'stats:view'
            ]
        }
    ]
    
    # 获取所有权限
    all_permissions = {p.name: p for p in Permission.query.all()}
    
    # 更新每个角色的权限
    for role_config in corrected_roles:
        # 查找角色
        role = Role.query.filter_by(name=role_config['code']).first()
        
        if role:
            # 清除现有权限
            role.permissions = []
            
            # 添加修正后的权限
            for perm_name in role_config['permissions']:
                if perm_name in all_permissions:
                    role.permissions.append(all_permissions[perm_name])
            
            db.session.commit()
            print(f'✅ 更新角色权限: {role_config["code"]}')
            print(f'   新权限: {" ".join(role_config["permissions"])}')
        else:
            print(f'⚠️  角色不存在: {role_config["code"]}')
    
    # 显示最终结果
    print('\n=== 最终角色配置 (修正版) ===')
    for role_config in corrected_roles:
        role = Role.query.filter_by(name=role_config['code']).first()
        if role:
            perm_names = [p.name for p in role.permissions]
            print(f'\n{role.description}:')
            print(f'  角色代码: {role.name}')
            print(f'  权限: {" ".join(perm_names)}')
