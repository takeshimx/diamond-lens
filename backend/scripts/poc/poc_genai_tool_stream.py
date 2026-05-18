"""
POC: google-genai SDK の tool_use + streaming 動作確認。
ChatOrchestrator 実装前に SDK の挙動（特に stream 中の function_call 検出方法）を把握する。
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# プロジェクトルート直下の .env を明示的に読み込む（既存サービスと同じパターン）
# scripts/poc/poc_genai_tool_stream.py → 3 階層上がプロジェクトルート
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


def main():
    api_key = os.getenv("GEMINI_API_KEY_V2")
    if not api_key:
        raise RuntimeError(
            f"GEMINI_API_KEY_V2 が見つかりません。.env (探索パス: {_env_path}) を確認してください。"
        )
    client = genai.Client(api_key=api_key)

    # 最小限のダミー tool（実 BQ には触らない）
    add_tool = types.FunctionDeclaration(
        name="add_two_numbers",
        description="2 つの整数の和を返す",
        parameters={
            "type": "OBJECT",
            "properties": {
                "a": {"type": "INTEGER"},
                "b": {"type": "INTEGER"},
            },
            "required": ["a", "b"],
        },
    )

    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[add_tool])],
        system_instruction="あなたは計算アシスタント。必ず add_two_numbers ツールを使って答えること。",
        temperature=0,
    )

    contents = [
        types.Content(role="user", parts=[types.Part(text="3 と 5 を足すといくつ？")]),
    ]

    for iteration in range(3):
        print(f"\n===== iteration {iteration} =====")
        stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        function_calls = []
        full_text = ""
        for chunk_idx, chunk in enumerate(stream):
            for cand in (chunk.candidates or []):
                for part in (cand.content.parts or []):
                    if part.function_call:
                        print(f"[chunk={chunk_idx}] function_call: name={part.function_call.name}, args={dict(part.function_call.args or {})}")
                        function_calls.append(part.function_call)
                    elif part.text:
                        print(f"[chunk={chunk_idx}] text: {part.text!r}")
                        full_text += part.text

        if not function_calls:
            print(f"\n--- DONE (final text: {full_text}) ---")
            break

        # assistant の function_call を contents に追加
        contents.append(types.Content(
            role="model",
            parts=[types.Part(function_call=fc) for fc in function_calls],
        ))
        # tool_response を追加
        for fc in function_calls:
            args = dict(fc.args or {})
            result = args["a"] + args["b"]
            contents.append(types.Content(
                role="user",
                parts=[types.Part(function_response=types.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                ))],
            ))


if __name__ == "__main__":
    main()
