#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : router.py
"""
from dataclasses import dataclass

from flask import Flask, Blueprint
from injector import inject

from internal.handler import (
    UploadFileHandler,
    OAuthHandler,
    AccountHandler,
    AuthHandler,
    ServerHandler,
    AgentHandler,
    ConversationHandler,
    MessageHandler,
)


@inject
@dataclass
class Router:
    """路由"""
    upload_file_handler: UploadFileHandler
    oauth_handler: OAuthHandler
    account_handler: AccountHandler
    auth_handler: AuthHandler
    server_handler: ServerHandler
    agent_handler: AgentHandler
    conversation_handler: ConversationHandler
    message_handler: MessageHandler

    def register_router(self, app: Flask):
        """注册路由"""
        # 1.创建一个蓝图
        bp = Blueprint("llmops", __name__, url_prefix="")

        # 2.上传文件模块
        bp.add_url_rule("/upload-files/file", methods=["POST"], view_func=self.upload_file_handler.upload_file)
        bp.add_url_rule("/upload-files/image", methods=["POST"], view_func=self.upload_file_handler.upload_image)
        bp.add_url_rule("/open-api/upload-file", methods=["POST"], view_func=self.upload_file_handler.upload_open_file)

        # 3.授权认证模块
        bp.add_url_rule(
            "/oauth/<string:provider_name>",
            view_func=self.oauth_handler.provider,
        )
        bp.add_url_rule(
            "/oauth/authorize/<string:provider_name>",
            methods=["POST"],
            view_func=self.oauth_handler.authorize,
        )
        bp.add_url_rule(
            "/auth/password-login",
            methods=["POST"],
            view_func=self.auth_handler.password_login,
        )
        bp.add_url_rule(
            "/auth/logout",
            methods=["POST"],
            view_func=self.auth_handler.logout,
        )
        bp.add_url_rule(
            "/auth/register-code",
            methods=["POST"],
            view_func=self.auth_handler.send_register_code,
        )
        bp.add_url_rule(
            "/auth/register",
            methods=["POST"],
            view_func=self.auth_handler.register,
        )

        # 4.账号设置模块
        bp.add_url_rule("/account", view_func=self.account_handler.get_current_user)
        bp.add_url_rule("/account/password", methods=["POST"], view_func=self.account_handler.update_password)
        bp.add_url_rule("/account/name", methods=["POST"], view_func=self.account_handler.update_name)
        bp.add_url_rule("/account/avatar", methods=["POST"], view_func=self.account_handler.update_avatar)

        # 5.WS 网关模块
        bp.add_url_rule("/open-api/server", view_func=self.server_handler.get_open_server)
        bp.add_url_rule("/open-api/servers", view_func=self.server_handler.get_open_servers)

        # 6.智能体模块
        bp.add_url_rule("/agents", view_func=self.agent_handler.get_agents_with_page)
        bp.add_url_rule("/agents", methods=["POST"], view_func=self.agent_handler.create_agent)
        bp.add_url_rule("/agents/<string:agent_id>", view_func=self.agent_handler.get_agent)
        bp.add_url_rule(
            "/agents/<string:agent_id>",
            methods=["POST"],
            view_func=self.agent_handler.update_agent,
        )
        bp.add_url_rule(
            "/agents/<string:agent_id>/delete",
            methods=["POST"],
            view_func=self.agent_handler.delete_agent,
        )
        bp.add_url_rule(
            "/agent/generate-id",
            methods=["GET"],
            view_func=self.agent_handler.generate_agent_id,
        )

        # 7.会话模块
        bp.add_url_rule(
            "/agents/<string:agent_id>/conversations",
            view_func=self.conversation_handler.get_conversations_with_page,
        )
        bp.add_url_rule(
            "/agents/<string:agent_id>/conversations",
            methods=["POST"],
            view_func=self.conversation_handler.create_conversation,
        )
        bp.add_url_rule(
            "/agents/<string:agent_id>/conversations/<string:conversation_id>",
            methods=["POST"],
            view_func=self.conversation_handler.update_conversation,
        )
        bp.add_url_rule(
            "/agents/<string:agent_id>/conversations/<string:conversation_id>/delete",
            methods=["POST"],
            view_func=self.conversation_handler.delete_conversation,
        )

        # 8.消息模块
        bp.add_url_rule(
            "/agents/<string:agent_id>/conversations/<string:conversation_id>/messages",
            view_func=self.message_handler.get_messages_with_page,
        )
        bp.add_url_rule(
            "/agents/<string:agent_id>/conversations/<string:conversation_id>/messages",
            methods=["POST"],
            view_func=self.message_handler.create_message,
        )

        # 9.在应用上注册蓝图
        app.register_blueprint(bp)
