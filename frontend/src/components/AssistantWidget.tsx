import { useState } from 'react';
import { Bot, X, Send } from 'lucide-react';
import { useAssistantChat, useAssistantSuggestions } from '../hooks/queries';
import type { ChatResponse } from '../types/models';

interface Msg {
  role: 'user' | 'bot';
  text: string;
  mode?: string;
}

export default function AssistantWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Msg[]>([]);
  const chat = useAssistantChat();
  const { data: sugg } = useAssistantSuggestions();

  const send = (text: string) => {
    if (!text.trim() || chat.isPending) return;
    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');
    chat.mutate(text, {
      onSuccess: (res: ChatResponse) =>
        setMessages((m) => [...m, { role: 'bot', text: res.answer, mode: res.mode }]),
      onError: () =>
        setMessages((m) => [
          ...m,
          { role: 'bot', text: 'Sorry, something went wrong. Try again.' },
        ]),
    });
  };

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-on-primary shadow-lg shadow-primary/30 transition-transform hover:scale-105"
        title="Ask PashuSafe AI"
      >
        {open ? <X className="h-6 w-6" /> : <Bot className="h-7 w-7" />}
      </button>

      {open && (
        <div className="fixed bottom-24 right-6 z-40 flex h-[520px] w-96 flex-col overflow-hidden rounded-3xl border border-outline-variant/40 bg-surface-container-lowest shadow-2xl">
          <div className="bg-primary px-5 py-4 text-on-primary">
            <p className="font-display font-bold">PashuSafe Assistant</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-primary-fixed">
              {sugg?.mode === 'claude' ? 'Claude-powered · live farm data' : 'Offline mode · live farm data'}
            </p>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto p-4">
            {messages.length === 0 && (
              <p className="mt-8 px-4 text-center text-sm text-on-surface-variant">
                Ask about withdrawals, violations, drug usage, risk predictions or sensor alerts.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-sm ${
                  m.role === 'user'
                    ? 'ml-auto bg-secondary-container font-medium text-on-secondary-container'
                    : 'bg-surface-container text-on-surface'
                }`}
              >
                {m.text}
                {m.mode === 'offline' && (
                  <span className="mt-1 block font-mono text-[9px] uppercase tracking-widest text-outline">
                    offline rule-based answer
                  </span>
                )}
              </div>
            ))}
            {chat.isPending && (
              <div className="w-16 rounded-2xl bg-surface-container px-3 py-2 text-sm text-outline">…</div>
            )}
          </div>

          {sugg && messages.length < 4 && (
            <div className="flex flex-wrap gap-1 border-t border-outline-variant/30 px-3 pt-2">
              {sugg.suggestions.slice(0, 4).map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full bg-surface-container px-2.5 py-1 text-[11px] font-medium text-on-surface-variant hover:bg-surface-container-high"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex gap-2 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask something…"
              className="flex-1 rounded-full border-none bg-surface-container-high px-4 py-2.5 text-sm text-on-surface outline-none transition-all placeholder:text-outline focus:ring-2 focus:ring-secondary"
            />
            <button
              type="submit"
              disabled={chat.isPending}
              className="rounded-xl bg-primary px-3.5 text-on-primary transition-colors hover:bg-primary-container disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
