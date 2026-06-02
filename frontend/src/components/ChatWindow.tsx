import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import type { Message } from '../types';

interface Props {
  messages: Message[];
}

export default function ChatWindow({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Smooth-scroll to the newest message whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">
      {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
      <div ref={bottomRef} />
    </div>
  );
}
