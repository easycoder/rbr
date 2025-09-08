    async def debug_receiver(self,e):
        error_count = 0
        last_message_time = time.ticks_ms()

        while True:
            try:
                # Check if interface is still active
                if not e.active():
                    print("ESP-NOW inactive! Reactivating...")
                    e.active(True)
                    error_count += 1
                    continue

                # Check for messages
                if e.any():
                    host, msg = e.recv(0)  # Non-blocking
                    if msg:
                        current_time = time.ticks_ms()
                        gap = time.ticks_diff(current_time, last_message_time)
                        last_message_time = current_time

                        print(f"Received from {host.hex()} after {gap}ms: {msg.decode()}")
                        error_count = 0  # Reset error counter on success
                        self.channels.resetCounters()
                        self.config.kickWatchdog()
                else:
                    # Check for long silence
                    current_time = time.ticks_ms()
                    silence = time.ticks_diff(current_time, last_message_time)
                    if silence > 15000:  # 15 seconds without message
                        print(f"Long silence detected: {silence}ms")
                        # Try to reset
                        e.active(False)
                        await asyncio.sleep(0.1)
                        e.active(True)
                        last_message_time = time.ticks_ms()

            except OSError as err:
                error_count += 1
                print(f"Receiver error #{error_count}: {err}")
                if error_count > 5:
                    print("Too many errors, resetting ESP-NOW")
                    e.active(False)
                    await asyncio.sleep(1)
                    e.active(True)
                    error_count = 0

            await asyncio.sleep(0.01)
