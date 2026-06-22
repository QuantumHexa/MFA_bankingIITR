/**
 * Hybrid-encrypts registration payload before it leaves the browser:
 * RSA-OAEP wraps an ephemeral AES-256-GCM key.
 */

export interface EncryptedRegistrationPayload {
  encrypted_key: string;
  iv: string;
  ciphertext: string;
}

function resolveApiBase(apiBaseUrl: string): string {
  if (apiBaseUrl) return apiBaseUrl.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:8000";
}

function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

async function importRsaPublicKey(pem: string): Promise<CryptoKey> {
  const b64 = pem
    .replace("-----BEGIN PUBLIC KEY-----", "")
    .replace("-----END PUBLIC KEY-----", "")
    .replace(/\s/g, "");
  const der = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

  return crypto.subtle.importKey(
    "spki",
    der.buffer,
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["wrapKey"],
  );
}

export async function encryptRegistrationPayload(
  serverPublicKeyPem: string,
  payload: Record<string, unknown>,
): Promise<EncryptedRegistrationPayload> {
  const rsaPublicKey = await importRsaPublicKey(serverPublicKeyPem);

  const aesKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"]);

  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encodedPayload = new TextEncoder().encode(JSON.stringify(payload));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, encodedPayload);

  const wrappedKey = await crypto.subtle.wrapKey("raw", aesKey, rsaPublicKey, { name: "RSA-OAEP" });

  return {
    encrypted_key: toBase64(wrappedKey),
    iv: toBase64(iv.buffer),
    ciphertext: toBase64(ciphertext),
  };
}

export async function buildEncryptedSignupBody(
  apiBaseUrl: string,
  registrationData: Record<string, unknown>,
): Promise<EncryptedRegistrationPayload> {
  const base = resolveApiBase(apiBaseUrl);
  const keyResponse = await fetch(`${base}/api/auth/public-key`, { credentials: "include" });
  if (!keyResponse.ok) {
    throw new Error(`Failed to fetch server public key: ${keyResponse.status}`);
  }
  const { public_key_pem } = (await keyResponse.json()) as { public_key_pem: string };
  return encryptRegistrationPayload(public_key_pem, registrationData);
}
