"""Phase 1 openai_compat.py chat/raw pattern, adapted 2026-11-11.

Transport is injected, so contract tests need no SDK installation or network.
The application factory never constructs live clients in this release. Keep
that gate outside these transport-only adapters; an enabled registry flag is
not authorization. Native Anthropic shares the same normalized result contract.
"""


class OpenAICompatibleAdapter:
    def __init__(self, entry, transport):
        self.entry = entry
        self.transport = transport

    def get_provider_info(self):
        return dict(provider=self.entry.provider_type, model=self.entry.model_id,
                    registry_id=self.entry.id, base_url=self.entry.base_url)

    def chat_raw(self, messages, max_tokens=2000, temperature=0, timeout=None):
        options = dict(model=self.entry.model_id, messages=messages, max_tokens=max_tokens, temperature=temperature)
        if timeout is not None:
            options['timeout'] = timeout
        if self.entry.capabilities.json_mode:
            options['response_format'] = {'type': 'json_object'}
        response = self.transport.chat.completions.create(**options)
        choice = response.choices[0]
        return dict(text=choice.message.content or '', stop_reason=choice.finish_reason, content=None)

    def chat(self, messages, max_tokens=2000, temperature=0, timeout=None):
        return self.chat_raw(messages, max_tokens, temperature, timeout)['text']


class AnthropicAdapter(OpenAICompatibleAdapter):
    def chat_raw(self, messages, max_tokens=2000, temperature=0, timeout=None):
        options = dict(model=self.entry.model_id, max_tokens=max_tokens,
            messages=[m for m in messages if m['role'] != 'system'],
            system='\n'.join(m['content'] for m in messages if m['role'] == 'system'))
        if timeout is not None:
            options['timeout'] = timeout
        response = self.transport.messages.create(**options)
        content = [block.model_dump() for block in response.content]
        return dict(text=''.join(block.get('text', '') for block in content if block['type'] == 'text'),
                    stop_reason=response.stop_reason, content=content)
