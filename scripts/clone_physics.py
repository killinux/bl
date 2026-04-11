"""
Clone / extract / apply MMD rigid body + joint physics between mmd_tools models.

Use cases:
  1. 直接从一个已加载的 target mmd_root 克隆到另一个 (两边都在场景里)
  2. 从 target mmd_root 抽取 JSON 模板文件, 日后复用 (不需要再次加载 target)
  3. 从 JSON 模板文件应用到 dst mmd_root

运行方式 (Blender 内 py console 或 exec):
    import sys; sys.path.insert(0, '/opt/mywork/mytest/bl/scripts')
    import importlib, clone_physics; importlib.reload(clone_physics)
    clone_physics.clone_in_scene('Test Converted', 'Purifier Inase 18 None')
    # or
    clone_physics.extract_to_json('Purifier Inase 18 None', '/tmp/physics_template.json')
    clone_physics.apply_from_json('Test Converted', '/tmp/physics_template.json')

注意:
- 用 bone 名匹配, 目标有但 dst armature 没有的骨会被跳过
- size 按 dst/src 骨长比自动缩放 (处理 1.25x 身材差)
- 位置 / 旋转按 bone local frame 做 retarget, 保证几何合理
- 仍然需要在 apply 之后跑 mmd_tools.build_rig 激活物理
"""
import bpy
import json
import os
from collections import defaultdict

SHAPE_IDX = {'SPHERE': 0, 'BOX': 1, 'CAPSULE': 2}


def _get_mmd_model(root_name_or_obj):
    from mmd_tools.core.model import Model as MMDModel
    root = bpy.data.objects[root_name_or_obj] if isinstance(root_name_or_obj, str) else root_name_or_obj
    return MMDModel(root), root


def _bone_world_rest(arm, name):
    return arm.matrix_world @ arm.data.bones[name].matrix_local


def extract(src_root_name):
    """从场景里一个 mmd_root 抽取完整 physics 描述, 返回 dict (JSON-able)."""
    src_model, src_root = _get_mmd_model(src_root_name)
    src_arm = src_model.armature()

    rigids = []
    rigid_name_to_idx = {}
    for i, sr in enumerate(src_model.rigidBodies()):
        bname = sr.mmd_rigid.bone
        if not bname or bname not in src_arm.data.bones:
            rigids.append(None)  # placeholder so indices line up for joint refs
            continue
        sb_mat = _bone_world_rest(src_arm, bname)
        # store rigid pose in the BONE's local frame (so it can be re-projected onto any armature)
        rigid_local_mat = sb_mat.inverted() @ sr.matrix_world
        src_bone_length = src_arm.data.bones[bname].length
        rigid_entry = {
            'idx': i,
            'name_j': sr.mmd_rigid.name_j or sr.name,
            'name_e': sr.mmd_rigid.name_e,
            'bone': bname,
            'shape': sr.mmd_rigid.shape,
            'type': sr.mmd_rigid.type,
            'size': list(sr.mmd_rigid.size),
            'size_per_bone_length': [s / src_bone_length for s in sr.mmd_rigid.size] if src_bone_length > 1e-6 else list(sr.mmd_rigid.size),
            'local_matrix': [list(row) for row in rigid_local_mat],
            'collision_group_number': sr.mmd_rigid.collision_group_number,
            'collision_group_mask': list(sr.mmd_rigid.collision_group_mask),
            'friction': sr.rigid_body.friction,
            'mass': sr.rigid_body.mass,
            'angular_damping': sr.rigid_body.angular_damping,
            'linear_damping': sr.rigid_body.linear_damping,
            'bounce': sr.rigid_body.restitution,
        }
        rigids.append(rigid_entry)
        rigid_name_to_idx[sr.name] = i

    # joints: need to reference rigid indices. The joint's transform is stored
    # relative to rigid_a's world frame (same retarget strategy).
    joints = []
    for sj in src_model.joints():
        rbc = sj.rigid_body_constraint
        a = rbc.object1
        b = rbc.object2
        if a is None or b is None:
            continue
        ai = rigid_name_to_idx.get(a.name)
        bi = rigid_name_to_idx.get(b.name)
        if ai is None or bi is None:
            continue
        if rigids[ai] is None or rigids[bi] is None:
            continue
        joint_local_mat = a.matrix_world.inverted() @ sj.matrix_world
        mj = sj.mmd_joint
        joints.append({
            'name_j': mj.name_j or sj.name.replace('J.', ''),
            'name_e': mj.name_e,
            'rigid_a_idx': ai,
            'rigid_b_idx': bi,
            'local_matrix_in_a': [list(row) for row in joint_local_mat],
            'maximum_location': [rbc.limit_lin_x_upper, rbc.limit_lin_y_upper, rbc.limit_lin_z_upper],
            'minimum_location': [rbc.limit_lin_x_lower, rbc.limit_lin_y_lower, rbc.limit_lin_z_lower],
            'maximum_rotation': [rbc.limit_ang_x_upper, rbc.limit_ang_y_upper, rbc.limit_ang_z_upper],
            'minimum_rotation': [rbc.limit_ang_x_lower, rbc.limit_ang_y_lower, rbc.limit_ang_z_lower],
            'spring_angular': list(sj.mmd_joint.spring_angular),
            'spring_linear': list(sj.mmd_joint.spring_linear),
        })

    # also record src model's size (height) so apply() can pick a global scale hint
    head_bone = src_arm.data.bones.get('頭')
    ankle_bone = src_arm.data.bones.get('足首.L')
    body_height = None
    if head_bone and ankle_bone:
        body_height = float((_bone_world_rest(src_arm, '頭').to_translation()
                             - _bone_world_rest(src_arm, '足首.L').to_translation()).z)

    return {
        'version': 1,
        'source': src_root_name if isinstance(src_root_name, str) else src_root.name,
        'body_height_m': body_height,
        'rigids': rigids,
        'joints': joints,
    }


def apply(dst_root_name, data, *, rescale_by_bone_length=True):
    """把 extract() 的结果应用到 dst mmd_root. 返回 (n_rigids, n_joints, n_skipped)."""
    from mathutils import Matrix
    dst_model, dst_root = _get_mmd_model(dst_root_name)
    dst_arm = dst_model.armature()
    dst_bone_names = set(dst_arm.data.bones.keys())

    rigid_idx_to_obj = {}
    skipped_bones = []

    for entry in data['rigids']:
        if entry is None:
            continue
        bname = entry['bone']
        if bname not in dst_bone_names:
            skipped_bones.append(bname)
            continue
        db_mat = _bone_world_rest(dst_arm, bname)
        rigid_local_mat = Matrix(entry['local_matrix'])
        new_mat = db_mat @ rigid_local_mat

        dbl = dst_arm.data.bones[bname].length
        if rescale_by_bone_length and 'size_per_bone_length' in entry:
            new_size = tuple(s * dbl for s in entry['size_per_bone_length'])
        else:
            new_size = tuple(entry['size'])

        nr = dst_model.createRigidBody(
            shape_type=SHAPE_IDX[entry['shape']],
            location=new_mat.to_translation(),
            rotation=new_mat.to_euler(),
            size=new_size,
            dynamics_type=int(entry['type']),
            name=entry['name_j'],
            name_e=entry.get('name_e'),
            bone=bname,
            friction=entry.get('friction'),
            mass=entry.get('mass'),
            angular_damping=entry.get('angular_damping'),
            linear_damping=entry.get('linear_damping'),
            bounce=entry.get('bounce'),
            collision_group_number=entry.get('collision_group_number'),
            collision_group_mask=entry.get('collision_group_mask'),
        )
        rigid_idx_to_obj[entry['idx']] = nr

    n_joints = 0
    for j in data['joints']:
        ai = j['rigid_a_idx']
        bi = j['rigid_b_idx']
        if ai not in rigid_idx_to_obj or bi not in rigid_idx_to_obj:
            continue
        na = rigid_idx_to_obj[ai]
        nb = rigid_idx_to_obj[bi]
        joint_local_mat = Matrix(j['local_matrix_in_a'])
        new_jmat = na.matrix_world @ joint_local_mat
        dst_model.createJoint(
            name=j['name_j'],
            name_e=j.get('name_e'),
            location=new_jmat.to_translation(),
            rotation=new_jmat.to_euler(),
            rigid_a=na,
            rigid_b=nb,
            maximum_location=tuple(j['maximum_location']),
            minimum_location=tuple(j['minimum_location']),
            maximum_rotation=tuple(j['maximum_rotation']),
            minimum_rotation=tuple(j['minimum_rotation']),
            spring_angular=tuple(j['spring_angular']),
            spring_linear=tuple(j['spring_linear']),
        )
        n_joints += 1

    return len(rigid_idx_to_obj), n_joints, skipped_bones


def clone_in_scene(dst_root_name, src_root_name, *, build=True):
    """场景里 src -> dst 一步完成, 返回诊断 dict."""
    data = extract(src_root_name)
    n_r, n_j, skipped = apply(dst_root_name, data)
    if build:
        for o in bpy.data.objects: o.select_set(False)
        dst_root = bpy.data.objects[dst_root_name]
        dst_root.select_set(True)
        bpy.context.view_layer.objects.active = dst_root
        bpy.ops.mmd_tools.build_rig()
    return {'rigids': n_r, 'joints': n_j, 'skipped_bones': skipped}


def extract_to_json(src_root_name, json_path):
    data = extract(src_root_name)
    os.makedirs(os.path.dirname(json_path) or '.', exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n_rigids = sum(1 for r in data['rigids'] if r is not None)
    return {'path': json_path, 'rigids': n_rigids, 'joints': len(data['joints'])}


def apply_from_json(dst_root_name, json_path, *, build=True):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    n_r, n_j, skipped = apply(dst_root_name, data)
    if build:
        for o in bpy.data.objects: o.select_set(False)
        dst_root = bpy.data.objects[dst_root_name]
        dst_root.select_set(True)
        bpy.context.view_layer.objects.active = dst_root
        bpy.ops.mmd_tools.build_rig()
    return {'rigids': n_r, 'joints': n_j, 'skipped_bones': skipped, 'template': json_path}
