// Web Serial API interface for communicating with ESP32-C6 PUF device

export class WebSerialBridge {
  private port: any = null;
  private reader: any = null;
  private buffer: string = "";

  /**
   * Check if Web Serial is supported in the current browser.
   */
  static isSupported(): boolean {
    return typeof window !== "undefined" && "serial" in navigator;
  }

  /**
   * Request serial port and open connection at specified baud rate.
   */
  async connect(baudRate: number = 115200): Promise<void> {
    if (!WebSerialBridge.isSupported()) {
      throw new Error("Web Serial API is not supported in this browser. Please use Chrome, Edge, or Opera.");
    }
    try {
      this.port = await (navigator as any).serial.requestPort();
      await this.port.open({ baudRate });
      // Wait for ESP32 to boot / stabilize after serial connection opens (reboot trigger)
      await new Promise((resolve) => setTimeout(resolve, 1500));
    } catch (err: any) {
      this.port = null;
      throw new Error(`Failed to open serial port: ${err.message || err}`);
    }
  }

  /**
   * Close the serial port connection.
   */
  async disconnect(): Promise<void> {
    try {
      if (this.reader) {
        await this.reader.cancel();
        this.reader = null;
      }
      if (this.port) {
        await this.port.close();
        this.port = null;
      }
    } catch (err) {
      console.warn("Error during serial disconnect:", err);
    }
  }

  /**
   * Send a command to the ESP32 and read response lines.
   * Expects lines starting with prefixes in `expectedPrefixes`.
   */
  async sendAndReceive(
    command: string,
    expectedPrefixes: string[],
    timeoutMs: number = 15000
  ): Promise<string> {
    if (!this.port || !this.port.writable || !this.port.readable) {
      await this.connect();
    }

    // Write command
    const writer = this.port.writable.getWriter();
    const encoder = new TextEncoder();
    try {
      await writer.write(encoder.encode(command));
    } finally {
      writer.releaseLock();
    }

    // Read response
    const decoder = new TextDecoder();
    const deadline = Date.now() + timeoutMs;
    this.buffer = "";
    this.reader = this.port.readable.getReader();

    try {
      while (Date.now() < deadline) {
        // Read from reader, or timeout if nothing received in 1 second
        const readPromise = this.reader.read();
        const timeoutPromise = new Promise<{ value: undefined; done: boolean }>((resolve) =>
          setTimeout(() => resolve({ value: undefined, done: true }), 1000)
        );

        const { value, done } = await Promise.race([readPromise, timeoutPromise]);
        if (value) {
          this.buffer += decoder.decode(value, { stream: true });
          const lines = this.buffer.split("\n");
          this.buffer = lines.pop() || ""; // Keep any trailing partial line

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            
            // Log output for debugging
            console.log("[ESP32 Serial]:", trimmed);

            if (trimmed.startsWith("MFA:WORK:")) {
              continue; // Keep waiting, device is processing
            }
            for (const prefix of expectedPrefixes) {
              if (trimmed.startsWith(prefix)) {
                return trimmed;
              }
            }
            if (trimmed.startsWith("MFA:ERR:")) {
              const errCode = trimmed.substring("MFA:ERR:".length);
              throw new Error(`Device returned error code: ${errCode}`);
            }
          }
        }

        if (done && !value) {
          // If no value, sleep slightly to prevent tight loop
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
      }
      throw new Error("Timeout waiting for response from ESP32 device");
    } finally {
      if (this.reader) {
        this.reader.releaseLock();
        this.reader = null;
      }
    }
  }

  /**
   * Send status check command.
   */
  async checkStatus(): Promise<string> {
    const line = await this.sendAndReceive("MFA:STATUS?\n", ["MFA:STATUS:OK:"]);
    return line.substring("MFA:STATUS:OK:".length);
  }

  /**
   * Send enroll command.
   */
  async enroll(customerId: string): Promise<string> {
    // Expected response format: MFA:ENROLL:OK:<customer_id>:<pubkey_hex>
    const line = await this.sendAndReceive(`MFA:ENROLL:${customerId}\n`, ["MFA:ENROLL:OK:"]);
    const parts = line.substring("MFA:ENROLL:OK:".length).split(":");
    if (parts.length < 2) {
      throw new Error("Invalid enrollment response format from device");
    }
    return parts[1]; // Return the pubkey_hex
  }

  /**
   * Send authentication command.
   */
  async authenticate(
    loginId: string,
    customerId: string,
    ephPubHex: string,
    nonceHex: string
  ): Promise<string> {
    // Expected response format: MFA:PROOF:OK:<proof_hex>
    const authLine = `MFA:AUTH:${loginId}:${customerId}:${ephPubHex}:${nonceHex}\n`;
    // Increase timeout to 30 seconds for PUF key derivation and crypto operations
    const line = await this.sendAndReceive(authLine, ["MFA:PROOF:OK:"], 30000);
    return line.substring("MFA:PROOF:OK:".length);
  }
}
