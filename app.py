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

SAVE_DIR = os.environ.get('SAVE_DIR', '.')
SAVE_FILE = os.path.join(SAVE_DIR, 'fishing_save.json')

if SAVE_DIR != '.' and not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR, exist_ok=True)

game_engine = FishingEngine(save_file=SAVE_FILE)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "fishing-mcp-server",
        "save_file": SAVE_FILE,
        "save_exists": os.path.exists(SAVE_FILE)
    })


# 注意：这里只有唯一一个 '/mcp' 路由，且支持 GET 和 POST
@app.route('/mcp', methods=['GET', 'POST'])
def mcp_endpoint():
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "service": "fishing-mcp-server",
            "message": "MCP endpoint is ready. Use POST for JSON-RPC requests."
        })

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
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
