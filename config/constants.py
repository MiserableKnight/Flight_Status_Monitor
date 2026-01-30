"""
技术常量定义

说明：
- 这些是代码级常量，开发者维护，用户通常不需要修改
- 业务配置（如飞机号、调度时间）请在 config/config.ini 中配置
"""

# 浏览器连接
DEFAULT_BROWSER_PORT = 9222

# 登录超时配置
MAX_LOGIN_WAIT_SECONDS = 90  # 登录流程最大等待时间
LOGIN_CHECK_INTERVAL = 0.5  # 页面状态检测间隔（秒）
TARGET_PAGE_LOAD_TIMEOUT = 15  # 目标页面加载超时（秒）

# 备份管理
DEFAULT_BACKUP_KEEP_COUNT = 2  # 默认保留备份文件数量

# 数据刷新
QUICK_REFRESH_WAIT = 2  # 快速刷新模式等待时间（秒）
NORMAL_REFRESH_WAIT = 3  # 正常刷新等待时间（秒）
