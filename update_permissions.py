from app import app, db
from models import Role, Permission

with app.app_context():
    # 定义要创建的权限
    permissions_to_create = [
        # 系统权限
        {'name': 'system:config', 'description': '系统配置'}, 
        
        # 用户管理权限
        {'name': 'user:*', 'description': '用户管理'}, 
        {'name': 'role:assign', 'description': '分配角色'}, 
        
        # 文件权限
        {'name': 'file:edit_remark', 'description': '编辑文件备注'}, 
        {'name': 'file:download', 'description': '下载文件'}, 
        {'name': 'file:view', 'description': '浏览文件'}, 
        {'name': 'file:details', 'description': '查看Hash等详情'}, 
        {'name': 'file:upload', 'description': '上传文件'}, 
        {'name': 'file:delete_own', 'description': '删除自己上传的'}, 
        {'name': 'file:edit_metadata', 'description': '编辑文件属性-仅自有'}, 
        {'name': 'file:share', 'description': '生成分享链接'}, 
        
        # 统计和审计权限
        {'name': 'stats:view', 'description': '查看统计'}, 
        {'name': 'audit:view', 'description': '查看审计'}, 
        
        # 所有权限（特殊标记）
        {'name': '*', 'description': '所有权限 (系统最高权限)'} 
    ]
    
    # 创建权限
    created_permissions = {}
    for perm_data in permissions_to_create:
        existing_perm = Permission.query.filter_by(name=perm_data['name']).first()
        if not existing_perm:
            new_perm = Permission(
                name=perm_data['name'],
                description=perm_data['description']
            )
            db.session.add(new_perm)
            db.session.flush()
            created_permissions[perm_data['name']] = new_perm
            print(f'✅ 创建权限: {perm_data["name"]}')
        else:
            created_permissions[perm_data['name']] = existing_perm
            print(f'⚠️  权限已存在: {perm_data["name"]}')
    
    db.session.commit()
    
    # 分配权限给角色
    # 获取所有角色
    roles = {
        'role_super_admin': Role.query.filter_by(name='role_super_admin').first(),
        'role_admin': Role.query.filter_by(name='role_admin').first(),
        'role_ops': Role.query.filter_by(name='role_ops').first(),
        'role_tester': Role.query.filter_by(name='role_tester').first(),
        'role_visitor': Role.query.filter_by(name='role_visitor').first()
    }
    
    # 定义角色权限分配
    role_permissions = {
        'role_super_admin': ['*'],  # 所有权限
        'role_admin': [
            'system:config', 'user:*', 'role:assign', 
            'file:edit_remark', 'file:download', 'file:view', 
            'file:details', 'stats:view', 'audit:view'
        ],
        'role_ops': [
            'file:upload', 'file:download', 'file:delete_own', 
            'file:edit_metadata', 'file:edit_remark', 'file:view', 
            'file:details', 'file:share', 'stats:view', 'audit:view'
        ],
        'role_tester': [
            'file:download', 'file:delete_own', 'file:edit_metadata', 
            'file:edit_remark', 'file:view', 'file:details', 
            'file:share', 'stats:view', 'audit:view'
        ],
        'role_visitor': [
            'file:edit_remark', 'file:view', 'stats:view', 'audit:view'
        ]
    }
    
    # 分配权限
    for role_name, perm_names in role_permissions.items():
        role = roles.get(role_name)
        if role:
            # 清空现有权限
            role.permissions = []
            
            # 添加新权限
            for perm_name in perm_names:
                if perm_name in created_permissions:
                    role.permissions.append(created_permissions[perm_name])
            
            db.session.commit()
            print(f'✅ 分配权限给角色: {role_name}')
    
    # 显示最终结果
    print('\n最终权限分配:')
    for role_name, role in roles.items():
        if role:
            perm_names = [p.name for p in role.permissions]
            print(f'\n{role.description}:')
            print(f'  权限: {" ".join(perm_names)}')
