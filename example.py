import WebAPI

username = 'your_username'
password = 'your_password'


# 旧版API
api = WebAPI.WebAPI(username, password)
tid = 2287221
print('api.get_thread_info(tid) :', api.get_thread_info(tid))  # 获取帖子基本信息
print('api.get_reply_page(tid) :', api.get_reply_page(tid))  # 获取单页回复
print('api.get_reply_all(tid) :', api.get_reply_all(tid))  # 获取帖子所有回复，默认限制20页（400楼）
print('api.get_reply_all(tid, 0) :', api.get_reply_all(tid, 0))  # 获取帖子所有回复，显式取消限制
# 除了散水帖，一般帖子很难超过400楼，建议保留默认限制

