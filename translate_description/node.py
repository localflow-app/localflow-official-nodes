import re

import requests


def _has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text)) if text else False


def _extract_chinese(text):
    return "".join(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s，。！？、；：""''（）【】《》·…—\-]+", text))


def _extract_english(text):
    return "".join(re.findall(r"[a-zA-Z0-9\s\-_,.;:!?()'\"&+/@#$%^*+=<>~\[\]{}|\\]+", text)).strip()


def _translate_via_llm(text, api_url, api_key, model):
    try:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的软件描述翻译助手。将英文软件描述翻译为简洁准确的中文，只返回翻译结果，不要添加任何解释或标号。",
                },
                {"role": "user", "content": f"翻译以下英文描述为中文：\n{text}"},
            ],
            "temperature": 0.3,
            "max_tokens": 256,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return ""
    except Exception:
        return ""


def execute(self, input_data):
    github_entries = input_data.get("github_entries", [])
    api_url = self.config.get("llm_api_url", "https://api.openai.com/v1/chat/completions")
    api_key = self.config.get("llm_api_key", "")
    model = self.config.get("llm_model", "gpt-4o-mini")

    entries_with_new_desc = []
    translation_count = 0

    for i, entry in enumerate(github_entries):
        report_progress(int(i / len(github_entries) * 100), f"翻译 {entry.get('owner_repo', '')} 描述...")
        github_desc = entry.get("github_description", "")
        existing_desc = entry.get("existing_description", {"en": "", "cn": ""})
        new_en = existing_desc.get("en", "")
        new_cn = existing_desc.get("cn", "")

        if not github_desc:
            entries_with_new_desc.append({
                **entry,
                "new_description": {"en": new_en, "cn": new_cn},
                "desc_action": "skip_empty",
            })
            continue

        github_has_cn = _has_chinese(github_desc)
        github_has_en = bool(_extract_english(github_desc))

        if github_has_cn and github_has_en:
            new_en = _extract_english(github_desc) or new_en
            new_cn = _extract_chinese(github_desc) or new_cn
            action = "both_extracted"
        elif github_has_cn:
            new_cn = github_desc
            if not new_en:
                new_en = github_desc
            action = "cn_direct"
        elif github_has_en:
            new_en = github_desc
            if not new_cn:
                translated = _translate_via_llm(github_desc, api_url, api_key, model)
                if translated:
                    new_cn = translated
                    translation_count += 1
            action = "en_translate"
        else:
            action = "skip_other"

        entries_with_new_desc.append({
            **entry,
            "new_description": {"en": new_en, "cn": new_cn},
            "desc_action": action,
        })

    return {
        **input_data,
        "github_entries": entries_with_new_desc,
        "translation_count": translation_count,
    }
