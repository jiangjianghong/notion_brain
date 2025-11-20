import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from tools import (
    get_lasted_change_page_id,
    wrap_url,
    wrap_text,
    change_block,
    search_pages,
    get_page_properties,
    get_blocks,
    clear_rich_text,
    append_text,
    append_page_mention,
    finish_rich_text
)

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL").replace("/chat/completions", "")
)

# 定义可用的工具函数
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_lasted_change_page_id",
            "description": "获取 Notion 中最近修改的页面 ID 列表，按最后编辑时间降序排序",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_size": {
                        "type": "integer",
                        "description": "要返回的页面数量，默认为 10"
                    }
                },
                "required": ["page_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_pages",
            "description": "根据关键词搜索 Notion 中的页面或数据库，返回包含标题、ID、类型和最后编辑时间的结果列表。支持模糊搜索和精确匹配。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词。如果为空字符串 ''，则返回所有页面（按最后编辑时间排序）。支持页面标题的模糊匹配。"
                    },
                    "obj_type": {
                        "type": "string",
                        "description": "要搜索的对象类型。'page' 表示页面，'database' 表示数据库。默认为 'page'。",
                        "enum": ["page", "database"],
                        "default": "page"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回的结果数量上限，范围 1-100。默认为 10。",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_properties",
            "description": "获取指定 Notion 页面的详细属性信息，包括标题、属性、创建时间等",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion 页面的 ID"
                    }
                },
                "required": ["page_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_blocks",
            "description": "获取指定页面或块的子块内容（最多 100 条），可选择是否递归获取所有嵌套子块",
            "parameters": {
                "type": "object",
                "properties": {
                    "block_id": {
                        "type": "string",
                        "description": "Notion 块或页面的 ID"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归获取所有嵌套的子块，默认为 false"
                    }
                },
                "required": ["block_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_text",
            "description": "添加文本内容到 rich_text 缓冲区。必须按照最终在 Notion 中显示的顺序依次调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "文本内容，使用 \\n 表示换行"
                    },
                    "bold": {
                        "type": "boolean",
                        "description": "是否加粗显示，默认为 false"
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_page_mention",
            "description": "添加页面引用（mention）到 rich_text 缓冲区。页面引用会在 Notion 中显示为可点击的页面链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "要引用的 Notion 页面 ID"
                    }
                },
                "required": ["page_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish_rich_text",
            "description": "完成 rich_text 构建并返回完整列表。在添加完所有内容元素后，必须调用此函数来完成构建过程。这是最后一步。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# 函数映射
available_functions = {
    "get_lasted_change_page_id": get_lasted_change_page_id,
    "search_pages": search_pages,
    "get_page_properties": get_page_properties,
    "get_blocks": get_blocks,
    "append_text": append_text,
    "append_page_mention": append_page_mention,
    "finish_rich_text": finish_rich_text,
}


def run_agent(user_prompt: str, max_iterations: int = 50):
    """
    运行智能体，根据用户提示生成 rich_text

    Args:
        user_prompt: 用户的需求描述
        max_iterations: 最大迭代次数，防止无限循环

    Returns:
        生成的 rich_text 列表
    """
    # 自动清空缓冲区，开始新的构建
    clear_rich_text()

    messages = [
        {
            "role": "system",
            "content": """你是一个 Notion 助手。你的职责是根据用户的问题，收集信息并构建 rich_text 格式的回答，最终显示在 Notion block 中。

            ## 可用工具

            **【数据获取工具】**
            1. `search_pages(keyword, obj_type, limit)` - 搜索 Notion 页面或数据库
            - keyword: 搜索关键词，空字符串 '' 返回所有页面
            - obj_type: 'page' 或 'database'
            - limit: 返回数量（1-100）

            2. `get_lasted_change_page_id(page_size)` - 获取最近修改的页面 ID 列表

            3. `get_page_properties(page_id)` - 获取页面的详细属性（标题、属性、创建时间等）

            4. `get_blocks(block_id, recursive)` - 获取页面或块的内容
            - block_id: 页面或块 ID
            - recursive: 是否递归获取子块（true/false）

            **【内容构建工具】**
            5. `append_text(text, bold)` - 添加文本内容
            - text: 文本内容，使用 \\n 表示换行
            - bold: 是否加粗（true/false）

            6. `append_page_mention(page_id)` - 添加页面引用链接
            - page_id: 要引用的页面 ID

            7. `finish_rich_text()` - **完成构建，返回最终结果**（必须是最后一步）

            ## 工作流程（严格遵守）

            **阶段 1：数据收集**
            - 根据用户问题，使用数据获取工具收集必要信息
            - 可能需要多次调用不同工具来获取完整信息
            - 注意工具调用的参数和返回值，不要遗漏任何细节

            **阶段 2：内容构建（核心）**
            按照最终在 Notion 中的显示顺序，依次调用 append_* 函数：
            1. 使用 `append_text()` 添加标题、描述、说明文字
            2. 使用 `append_page_mention()` 添加页面引用
            3. 使用 `append_text()` 添加换行符、分隔符、后续文字
            4. 重复以上步骤，直到所有内容添加完毕

            **阶段 3：完成构建**
            - 确认所有内容已添加后，调用 `finish_rich_text()`
            - 这是最后一步，调用后任务完成

            ## 示例工作流

            **用户问题：**"显示最近修改的 3 个页面"

            **执行步骤：**
            ```
            1. get_lasted_change_page_id(3)  → 获取 [id1, id2, id3]

            2. append_text("最近修改的页面：\\n\\n", bold=true)  → 添加标题

            3. append_text("• ", bold=false)  → 添加列表标记
            4. append_page_mention(id1)       → 添加第1个页面引用
            5. append_text("\\n", bold=false) → 换行

            6. append_text("• ", bold=false)  → 添加列表标记
            7. append_page_mention(id2)       → 添加第2个页面引用
            8. append_text("\\n", bold=false) → 换行

            9. append_text("• ", bold=false)  → 添加列表标记
            10. append_page_mention(id3)      → 添加第3个页面引用
            11. append_text("\\n", bold=false) → 换行

            12. finish_rich_text()            → 完成构建
            ```

            ## 关键规则

            **必须遵守：**
            1. ✅ **永远不要直接返回文本给用户** - 必须使用 append_* 工具构建
            2. ✅ **按显示顺序调用** - 从上到下、从左到右依次添加内容
            3. ✅ **内容要完整** - 不要只添加标题就结束，要添加完整的回答
            4. ✅ **最后必须调用 finish_rich_text()** - 否则内容不会返回
            5. ✅ **使用 \\n 换行** - 使用 \\n\\n 创建段落间距

            **格式建议：**
            - 标题和重点内容使用 `bold=true`
            - 列表项使用 `• ` 或 `1. ` 等标记
            - 页面引用后通常需要换行
            - 内容要清晰、结构化，方便阅读
            - 如果回答是基于最近修改的页面或搜索结果，务必引用具体页面

            **常见错误（避免）：**
            ❌ 只调用一次 append_text 就调用 finish_rich_text
            ❌ 调用 finish_rich_text 后继续添加内容
            ❌ 不调用 finish_rich_text 就结束
            ❌ 直接返回文本内容而不使用工具

            记住：你的目标是构建一个**完整、格式美观**的 rich_text 列表，确保用户能在 Notion 中获得高质量的回答！"""
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    iteration = 0
    rich_text_result = None

    while iteration < max_iterations:
        iteration += 1
        print(f"\n=== 迭代 {iteration} ===")

        # 调用 OpenAI API
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        # 检查是否需要调用工具
        tool_calls = response_message.tool_calls

        if not tool_calls:
            # 没有工具调用，说明已完成
            print("智能体完成")
            break

        # 执行工具调用
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"调用函数: {function_name}")
            print(f"参数: {function_args}")

            if function_name in available_functions:
                function_to_call = available_functions[function_name]

                # 调用函数
                try:
                    function_response = function_to_call(**function_args)

                    # 将函数响应转换为字符串
                    if isinstance(function_response, (dict, list)):
                        function_response_str = json.dumps(function_response, ensure_ascii=False)
                    else:
                        function_response_str = str(function_response)

                    print(f"函数返回: {function_response_str[:200]}...")

                    # 将函数响应添加到消息中
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response_str
                    })

                    # 如果是 finish_rich_text，提取最终的 rich_text
                    if function_name == "finish_rich_text" and isinstance(function_response, dict):
                        rich_text_result = function_response.get("rich_text", [])
                        print(f"\n✓ Rich text 构建完成，共 {len(rich_text_result)} 个元素")

                except Exception as e:
                    print(f"函数调用错误: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {str(e)}"
                    })

    return rich_text_result


def generate_rich_text(prompt: str):
    """
    根据提示生成 rich_text 并更新 Notion block

    Args:
        prompt: 用户的需求描述
    """
    print(f"用户需求: {prompt}\n")

    # 运行智能体
    rich_text = run_agent(prompt)

    if rich_text:
        print("\n=== 生成的 Rich Text ===")
        print(json.dumps(rich_text, indent=2, ensure_ascii=False))

        # 更新 Notion block
        print("\n=== 更新 Notion Block ===")
        change_block(rich_text)
        print("✓ 已成功更新 Notion block")
    else:
        print("未能生成 rich_text")

    return rich_text


def ask_question(question: str):
    """
    向智能体提问，自动搜索相关信息并生成 rich_text 格式的回答

    Args:
        question: 用户的问题

    Returns:
        生成的 rich_text 列表
    """
    print(f"问题: {question}\n")

    # 运行智能体
    rich_text = run_agent(question)

    if rich_text:
        print("\n=== 生成的回答（Rich Text） ===")
        print(json.dumps(rich_text, indent=2, ensure_ascii=False))

        # 更新 Notion block
        print("\n=== 更新到 Notion Block ===")
        change_block(rich_text)
        print("✓ 回答已更新到 Notion")
    else:
        print("未能生成回答")

    return rich_text


if __name__ == "__main__":
    # 示例 1：生成包含最近修改页面的 rich_text
    # prompt = """
    # 请帮���生成一个 rich_text，内容如下：
    # 1. 先显示粗体文本 "最近修改的页面："
    # 2. 获取最近 5 个修改的页面
    # 3. 为每个页面创建一个换行，然后显示页面的 mention 链接
    # 4. 最后显示文本 "以上是最近的更新"
    # """
    # generate_rich_text(prompt)

    # 示例 2：向智能体提问
    ask_question("先根据用户最近更新的页面，列出3-5个页面,只需最终要给用户一个建议，语言幽默风趣")
