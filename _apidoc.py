"""
I am apiDoc history file.
"""

# apiPermission

"""
@apiDefine admin 管理员权限
没有权限则返回错误码1101
"""

# apiGroup

"""
@apiDefine admin_Admin Admin API - 管理员
"""

"""
@apiDefine admin_Ext Admin Extensions
"""

# apiParam

"""
@apiDefine paginate
@apiParam [page] 第几页
@apiParam [per_page] 每页几条
"""

# apiSuccess

"""
@apiDefine admin_obj
@apiSuccess (admin对象) {Number} id ID
@apiSuccess (admin对象) {String} create_time 创建时间
@apiSuccess (admin对象) {String} update_time 更新时间
@apiSuccess (admin对象) {String} uuid UUID
@apiSuccess (admin对象) {String/Null} last_login_time 最近登录时间
@apiSuccess (admin对象) {String} last_login_ip 最近登录IP
@apiSuccess (admin对象) {String} username 用户名
"""

# apiError

"""
@apiDefine e1103
@apiError (错误码) 1103 Forbidden
"""

"""
@apiDefine e1104
@apiError (错误码) 1104 Not Found
"""

"""
@apiDefine e1201
@apiError (错误码) 1201 url参数不完整
"""

"""
@apiDefine e1202
@apiError (错误码) 1202 url参数值错误
"""

"""
@apiDefine e1203
@apiError (错误码) 1203 json数据不完整
"""

"""
@apiDefine e1204
@apiError (错误码) 1204 json数据类型错误
"""

"""
@apiDefine e1205
@apiError (错误码) 1205 json数据值错误
"""

"""
@apiDefine e1301
@apiError (错误码) 1301 用户名错误
"""

"""
@apiDefine e1302
@apiError (错误码) 1302 密码错误
"""

"""
@apiDefine e1303
@apiError (错误码) 1303 密码长度不符合要求
"""
