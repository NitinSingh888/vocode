from __future__ import annotations

import asyncio
import json
from fastapi import WebSocket

from vocode.streaming.models.audio import AudioEncoding
from vocode.streaming.models.transcript import TranscriptEvent
from vocode.streaming.models.websocket import AudioMessage, TranscriptMessage
from vocode.streaming.output_device.base_output_device import BaseOutputDevice
from vocode.streaming.utils.create_task import asyncio_create_task_with_done_error_log


class WebsocketOutputDevice(BaseOutputDevice):
    def __init__(self, ws: WebSocket, sampling_rate: int, audio_encoding: AudioEncoding):
        super().__init__(sampling_rate, audio_encoding)
        self.ws = ws
        self.active = False
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    def start(self):
        self.active = True
        self.process_task = asyncio_create_task_with_done_error_log(self.process())

    def mark_closed(self):
        self.active = False

    async def process(self):
        try:
            while self.active:
                message = await self.queue.get()

                await self.ws.send_text(message)
        except Exception as e:
            print(e)
            print("EXCEPTION OCCURRED IN WOD")

    def consume_nonblocking(self, chunk: bytes):
        if self.active:
            audio_message = AudioMessage.from_bytes(chunk)
            self.queue.put_nowait(audio_message.json())
        
    def consume_interrupt(self, is_interrupt: bool):
        if self.active:
            self.queue.put_nowait(json.dumps({"data": is_interrupt, "type": "interrupt"}))

    def consume_transcript(self, event: TranscriptEvent):
        if self.active:
            transcript_message = TranscriptMessage.from_event(event)
            self.queue.put_nowait(transcript_message.json())

    def terminate(self):
        self.process_task.cancel()
