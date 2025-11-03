import { useEffect, useState } from 'react';
import { DataPacket_Kind, RemoteParticipant } from 'livekit-client';
import { useRoomContext } from '@livekit/components-react';
import type { ReceivedChatMessage } from '@livekit/components-react';

export function useDataMessages(): ReceivedChatMessage[] {
  const room = useRoomContext();
  const [dataMessages, setDataMessages] = useState<ReceivedChatMessage[]>([]);

  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant?: RemoteParticipant,
      kind?: DataPacket_Kind
    ) => {
      if (kind !== DataPacket_Kind.RELIABLE) return;

      try {
        const decoder = new TextDecoder();
        const message = decoder.decode(payload);

        // Try to parse as JSON, fallback to plain text
        let parsedMessage: { message?: string } | { message: string };
        try {
          parsedMessage = JSON.parse(message);
        } catch {
          parsedMessage = { message };
        }

        const chatMessage: ReceivedChatMessage = {
          id: `data-${Date.now()}-${Math.random()}`,
          timestamp: Date.now(),
          message: parsedMessage.message || message,
          from: participant || room.localParticipant,
        };

        setDataMessages((prev) => [...prev, chatMessage]);
      } catch (error) {
        console.error('Failed to process data message:', error);
      }
    };

    room.on('dataReceived', handleDataReceived);

    return () => {
      room.off('dataReceived', handleDataReceived);
    };
  }, [room]);

  return dataMessages;
}