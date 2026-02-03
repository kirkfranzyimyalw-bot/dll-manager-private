from app import app, db
from models import Role, User

with app.app_context():
    # 要删除的角色名称
    roles_to_delete = ['admin', 'user']
    
    for role_name in roles_to_delete:
        # 查找角色
        role = Role.query.filter_by(name=role_name).first()
        
        if role:
            # 检查是否有用户使用此角色
            users_with_role = User.query.filter_by(role_id=role.id).all()
            
            if users_with_role:
                print(f'⚠️  角色 {role_name} 仍有 {len(users_with_role)} 个用户使用，无法删除')
            else:
                # 删除角色
                db.session.delete(role)
                db.session.commit()
                print(f'✅ 删除角色: {role_name}')
        else:
            print(f'⚠️  角色 {role_name} 不存在')
    
    # 显示剩余的角色
    print('\n剩余角色:')
    for role in Role.query.all():
        print(f'- {role.name}: {role.description}')
