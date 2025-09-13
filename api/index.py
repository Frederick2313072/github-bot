import os
import hmac
import hashlib
import json
import time
import base64
import requests
from flask import Flask, request, abort
from datetime import datetime

app = Flask(__name__)

GITHUB_SECRET = os.environ.get('GITHUB_SECRET')
FEISHU_WEBHOOK_URL = os.environ.get('FEISHU_WEBHOOK_URL')
FEISHU_SECRET = os.environ.get('FEISHU_SECRET')

# 检查必要的环境变量
if not FEISHU_WEBHOOK_URL:
    print("错误：未设置 FEISHU_WEBHOOK_URL 环境变量")
    print("请在 Vercel 项目设置中添加 FEISHU_WEBHOOK_URL 环境变量")

def verify_github_signature(req):
    """验证 GitHub Webhook 签名"""
    if not GITHUB_SECRET:
        return True
    
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return False
    
    sha_name, signature_hex = signature.split('=', 1)
    if sha_name != 'sha256':
        return False
    
    mac = hmac.new(GITHUB_SECRET.encode('utf-8'), msg=request.data, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_hex)

def gen_sign(timestamp, secret):
    """生成飞书签名"""
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def format_commit_message(commit):
    """格式化提交信息，添加图标和样式"""
    import re

    message = commit.get("message", "无提交信息").split('\n')[0]
    author = commit.get("author", {}).get("name", "未知作者")

    # 为提交者添加@符号并加粗
    author_display = f"**@{author}**" if author != "未知作者" else author

    # 使用正则表达式匹配提交类型，包括带括号的格式
    commit_type_match = re.match(r'^(\w+)(\([^)]*\))?:\s', message.lower())

    if commit_type_match:
        commit_type = commit_type_match.group(1)

        # 根据提交类型添加图标
        if commit_type == 'feat':
            icon = "✨"
            type_label = "特性"
        elif commit_type == 'fix':
            icon = "🐛"
            type_label = "修复"
        elif commit_type == 'docs':
            icon = "📚"
            type_label = "文档"
        elif commit_type == 'style':
            icon = "💅"
            type_label = "样式"
        elif commit_type == 'refactor':
            icon = "♻️"
            type_label = "重构"
        elif commit_type == 'test':
            icon = "🧪"
            type_label = "测试"
        elif commit_type == 'chore':
            icon = "🔧"
            type_label = "杂项"
        elif commit_type == 'perf':
            icon = "⚡"
            type_label = "性能"
        elif commit_type == 'ci':
            icon = "🚀"
            type_label = "CI"
        elif commit_type == 'build':
            icon = "📦"
            type_label = "构建"
        elif commit_type == 'revert':
            icon = "⏪"
            type_label = "回滚"
        else:
            icon = "📝"
            type_label = "其他"
    elif message.lower().startswith('merge'):
        icon = "🔀"
        type_label = "合并"
    else:
        icon = "📝"
        type_label = "其他"

    return f"{icon} **{type_label}** {message}", author_display

def send_to_feishu(card_json):
    """发送消息到飞书"""
    if not FEISHU_WEBHOOK_URL:
        print("错误：FEISHU_WEBHOOK_URL 环境变量未设置，无法发送消息")
        return False
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msg_type": "interactive",
        "card": card_json
    }
    
    if FEISHU_SECRET:
        timestamp = int(time.time())
        sign = gen_sign(timestamp, FEISHU_SECRET)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    
    try:
        response = requests.post(FEISHU_WEBHOOK_URL, headers=headers, json=payload)
        response.raise_for_status()
        print("消息已成功发送到飞书:", response.json())
        return True
    except requests.exceptions.RequestException as e:
        print(f"发送消息到飞书时出错: {e}")
        return False

def handle_push_event(payload):
    """处理 push 事件"""
    repo_name = payload['repository']['full_name']
    ref = payload.get("ref", "未知分支") 
    branch_name = ref.split("/")[-1] if ref else "未知分支"
    
    pusher_name = payload.get("pusher", {}).get("name", "未知推送者")
    
    commits = payload.get("commits", [])
    if not commits:
        head_commit = payload.get("head_commit")
        if head_commit:
            commit_message = head_commit.get("message", "无提交信息 (可能为创建/删除分支)")
            commit_url = head_commit.get("url", "#")
            commit_author = head_commit.get("author", {}).get("name", pusher_name)
        else:
            commit_message = "无具体代码变更 (例如：分支创建/删除)"
            commit_url = payload.get("compare", "#")
            commit_author = pusher_name
    else:
        # 处理多个提交的情况
        if len(commits) == 1:
            # 单个提交时使用格式化函数
            single_commit = commits[0]
            formatted_message, author_display = format_commit_message(single_commit)
            commit_message = formatted_message
            commit_url = single_commit.get("url", "#")
            commit_author = author_display
        else:
            # 多个提交时，展示所有提交信息
            commit_details = []
            # 收集所有不同的提交者
            unique_authors = set()
            for commit in commits:
                author = commit.get("author", {}).get("name", "未知作者")
                if author and author != "未知作者":
                    unique_authors.add(author)

            for i, commit in enumerate(commits, 1):
                formatted_message, author_display = format_commit_message(commit)
                commit_details.append(f"{i}. {author_display}: {formatted_message}")

            commit_message = "\\n".join(commit_details)
            commit_url = payload.get("compare", "#")  # 使用compare URL查看所有变更

            # 提交者显示为逗号分隔的名字列表
            if unique_authors:
                authors_list = [f"**@{author}**" for author in unique_authors]
                commit_author = ", ".join(authors_list)
            else:
                commit_author = "未知提交者"

    # --- 构建消息卡片 ---
    card_elements = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"📦 **仓库**: {repo_name}"}
        },
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"🌿 **分支**: {branch_name}"}
        },
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"👤 **提交者**: {commit_author}"}
        }
    ]

    # 处理提交信息显示
    if len(commits) <= 1:
        # 单个提交的情况
        card_elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"💬 **信息**: {commit_message}"}
        })
        card_elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔗 查看提交详情"},
                    "type": "default",
                    "url": commit_url
                }
            ]
        })
    else:
        # 多个提交的情况
        card_elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"✨ **总提交数**: {len(commits)}"}
        })

        # 限制显示的提交数量，避免卡片过长
        max_display_commits = 10
        displayed_commits = commits[:max_display_commits]

        # 添加提交列表
        for i, commit in enumerate(displayed_commits, 1):
            formatted_message, author_display = format_commit_message(commit)
            card_elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"  {i}. {author_display}: {formatted_message}"}
            })

        # 如果有更多提交，显示省略信息
        if len(commits) > max_display_commits:
            remaining = len(commits) - max_display_commits
            card_elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"  ... 还有{remaining}个提交"}
            })

        # 添加查看所有变更的按钮
        compare_url_from_payload = payload.get("compare")
        if compare_url_from_payload:
            card_elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔍 查看所有变更"},
                        "type": "default",
                        "url": compare_url_from_payload
                    }
                ]
            })
    
    card_elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": "💾 请及时拉取最新数据 git pull origin main"}
    })
    
    # 完整的消息卡片JSON对象
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "GitHub 项目更新通知"},
            "template": "blue"
        },
        "elements": card_elements
    }
    
    send_to_feishu(card)

def handle_issues_event(payload):
    """处理 issues 事件"""
    action = payload['action']
    issue = payload['issue']
    repo_name = payload['repository']['full_name']
    user = payload['sender']['login']
    
    action_map = {
        'opened': '创建',
        'closed': '关闭',
        'reopened': '重新打开',
        'assigned': '分配',
        'unassigned': '取消分配'
    }
    
    action_text = action_map.get(action, action)
    
    color_map = {
        'opened': 'green',
        'closed': 'red',
        'reopened': 'orange'
    }
    
    template_color = color_map.get(action, 'blue')
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template_color,
            "title": {"content": f"🐛 [{repo_name}] Issue {action_text}", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"**标题:** {issue['title']}\\n**操作人:** {user}\\n**Issue #:** {issue['number']}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**描述:** {(issue['body'] or '无描述')[:200]}{'...' if issue['body'] and len(issue['body']) > 200 else ''}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "查看 Issue", "tag": "plain_text"},
                        "type": "primary",
                        "url": issue['html_url']
                    }
                ]
            }
        ]
    }
    send_to_feishu(card)

def handle_pull_request_event(payload):
    """处理 pull request 事件"""
    action = payload['action']
    pr = payload['pull_request']
    repo_name = payload['repository']['full_name']
    user = payload['sender']['login']
    
    action_map = {
        'opened': '创建',
        'closed': '关闭',
        'merged': '合并',
        'reopened': '重新打开',
        'review_requested': '请求审查'
    }
    
    action_text = action_map.get(action, action)
    
    color_map = {
        'opened': 'green',
        'closed': 'red',
        'merged': 'purple'
    }
    
    template_color = color_map.get(action, 'blue')
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template_color,
            "title": {"content": f"🔀 [{repo_name}] Pull Request {action_text}", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"**标题:** {pr['title']}\\n**操作人:** {user}\\n**PR #:** {pr['number']}\\n**分支:** {pr['head']['ref']} → {pr['base']['ref']}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**描述:** {(pr['body'] or '无描述')[:200]}{'...' if pr['body'] and len(pr['body']) > 200 else ''}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "查看 PR", "tag": "plain_text"},
                        "type": "primary",
                        "url": pr['html_url']
                    }
                ]
            }
        ]
    }
    send_to_feishu(card)

def handle_release_event(payload):
    """处理 release 事件"""
    action = payload['action']
    release = payload['release']
    repo_name = payload['repository']['full_name']
    
    if action == 'published':
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "purple",
                "title": {"content": f"🎉 [{repo_name}] 新版本发布", "tag": "plain_text"}
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**版本:** {release['tag_name']}\\n**名称:** {release['name']}\\n**发布人:** {release['author']['login']}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"**发布说明:**\\n{(release['body'] or '无发布说明')[:300]}{'...' if release['body'] and len(release['body']) > 300 else ''}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"content": "查看发布", "tag": "plain_text"},
                            "type": "primary",
                            "url": release['html_url']
                        }
                    ]
                }
            ]
        }
        send_to_feishu(card)

@app.route('/', methods=['GET'])
def health_check():
    """健康检查接口"""
    config_status = {
        'FEISHU_WEBHOOK_URL': '已配置' if FEISHU_WEBHOOK_URL else '未配置',
        'GITHUB_SECRET': '已配置' if GITHUB_SECRET else '未配置',
        'FEISHU_SECRET': '已配置' if FEISHU_SECRET else '未配置'
    }
    
    return {
        'status': 'ok' if FEISHU_WEBHOOK_URL else 'error',
        'message': 'GitHub-飞书机器人运行正常' if FEISHU_WEBHOOK_URL else '缺少必要的环境变量配置',
        'config': config_status,
        'timestamp': datetime.now().isoformat()
    }

@app.route('/', methods=['POST'])
def webhook_handler():
    """接收 Webhook 请求的入口"""
    # 检查环境变量
    if not FEISHU_WEBHOOK_URL:
        error_msg = "错误：FEISHU_WEBHOOK_URL 环境变量未配置"
        print(error_msg)
        return error_msg, 500
    
    # 验证签名
    if not verify_github_signature(request):
        abort(401, '无效签名')
    
    # 获取事件类型和数据
    event_type = request.headers.get('X-GitHub-Event')
    
    try:
        payload = request.get_json()
        if payload is None:
            error_msg = "错误：无法解析 JSON 数据"
            print(error_msg)
            return error_msg, 400
            
        print(f"收到 GitHub 事件: {event_type}")
        print(f"事件数据键: {list(payload.keys()) if payload else 'None'}")
        
        # 处理不同类型的事件
        if event_type == 'push':
            if 'repository' not in payload or 'pusher' not in payload:
                print("Push 事件数据不完整")
                return "Push 事件数据不完整", 400
            handle_push_event(payload)
        elif event_type == 'issues':
            if 'issue' not in payload or 'action' not in payload:
                print("Issues 事件数据不完整")
                return "Issues 事件数据不完整", 400
            handle_issues_event(payload)
        elif event_type == 'pull_request':
            if 'pull_request' not in payload or 'action' not in payload:
                print("Pull Request 事件数据不完整")
                return "Pull Request 事件数据不完整", 400
            handle_pull_request_event(payload)
        elif event_type == 'release':
            if 'release' not in payload or 'action' not in payload:
                print("Release 事件数据不完整")
                return "Release 事件数据不完整", 400
            handle_release_event(payload)
        elif event_type == 'ping':
            print("收到 GitHub Webhook ping 事件")
            return "Webhook 配置成功！", 200
        else:
            print(f"未处理的事件类型: {event_type}")
            return f"未处理的事件类型: {event_type}", 200
            
    except Exception as e:
        error_msg = f"处理事件时发生错误: {str(e)}"
        print(error_msg)
        print(f"错误详情: {type(e).__name__}")
        return error_msg, 500
    
    return 'OK', 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
