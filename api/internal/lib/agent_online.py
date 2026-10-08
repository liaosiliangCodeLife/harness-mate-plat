'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //按会话心跳判断智能体是否在线
* @File: agent_online.py
* @Time: 2026/10/07 16:58:00
* @All Rights Reserve By Brtc
'''

from datetime import timedelta

from internal.extension.database_extension import db
from internal.lib.helper import utc_now
from internal.model import Conversation

# 会话心跳超过该秒数视为离线
ONLINE_TTL_SECONDS = 90


def is_online(agent_id) -> bool:
    """
    * @Author Leon-liao
    * @Function: is_online(agent_id)
    * @Description //判断智能体名下是否有未删除且 90 秒内仍在线的会话
    * @Date :2026/10/07 16:58:00
    * @Param: agent_id: 智能体主键，UUID 或可被查询比较的值
    * @return：存在这样的会话返回 True，否则返回 False
    """
    if agent_id is None or agent_id == "":
        return False
    deadline = utc_now() - timedelta(seconds=ONLINE_TTL_SECONDS)
    existed = db.session.query(Conversation.id).filter(
        Conversation.agent_id == agent_id,
        Conversation.deleted_at.is_(None),
        Conversation.status == 1,
        Conversation.online_at >= deadline,
    ).first()
    return existed is not None
