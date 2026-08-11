#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP wrapper for MCP server - 用于 Render 部署
"""

from flask import Flask, request, jsonify
import json
import os
from engine import FishingEngine

app = Flask(__name__)

# 使用持久化存储目录（Render Disk 会挂载到这里）
SAVE_DIR = os.environ.get('SAVE_DIR', '.')
SAVE_FILE = os.path.join(SAVE_DIR, 'fishing_save.json')

# 确保存档目录存在
if SAVE_DIR != '.' and not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR, exist_ok=True)

# 初始化游戏引擎（使用持久化路径）
game_engine = FishingEngine(save_file=SAVE_FILE)


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": "fishing-mcp-server",
        "save_file": SAVE_FILE,
        "save_exists": os.path.exists(SAVE_FILE)
    })


@app.route('/mcp', methods=['GET', 'POST'])
def mcp_endpoint():
    """MCP 请求处理端点（支持 GET 和 POST）"""
    # 处理 GET 请求（用于测试/健康检查）
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "service": "fishing-mcp-server",
            "message": "MCP endpoint is ready. Use POST for JSON-RPC requests."
        })

    # 以下是原有的 POST 处理逻辑
    try:
        request_data = request.get_json()
        method = request_data.get("method")

        if method == "initialize":
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "fishing-game",
                        "version": "1.0.0"
                    }
                }
            })

        elif method == "tools/list":
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "fishing_command",
                            "description": "执行钓鱼游戏指令",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "游戏指令，例如：cast, status, buy basic_worm 5"
                                    }
                                },
                                "required": ["command"]
                            }
                        },
                        {
                            "name": "fishing_new_game",
                            "description": "重新开始新游戏",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "seed": {
                                        "type": "integer",
                                        "description": "随机种子（可选）"
                                    }
                                }
                            }
                        }
                    ]
                }
            })

        elif method == "tools/call":
            params = request_data.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "fishing_command":
                command = arguments.get("command", "")
                result = game_engine.cmd(command)

                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                })

            elif tool_name == "fishing_new_game":
                seed = arguments.get("seed", 0x9e3779b9)
                result = game_engine.new_game(seed)

                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                })

            else:
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }), 404

        else:
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }), 404

    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "id": request_data.get("id", None),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
