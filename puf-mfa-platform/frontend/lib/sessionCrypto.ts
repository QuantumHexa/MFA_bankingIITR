/**
 * Client-side HKDF ratcheting — mirrors backend session_crypto.py (Web Crypto API).
 * Root is derived locally from MFA proof material; never sent over the wire.
 */

export type CryptoBundle = {
  crypto_session_id: string;
  auth_session_id: string;
  proof_hex: string;
  nonce: string;
  challenge: string;
  ratchet_counter: number;
};

function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

async function hkdfSha256(ikm: Uint8Array, salt: Uint8Array, info: Uint8Array): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", ikm as BufferSource, "HKDF", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "HKDF", hash: "SHA-256", salt: salt as BufferSource, info: info as BufferSource },
    key,
    256,
  );
  return new Uint8Array(bits);
}

export async function deriveSessionRoot(bundle: CryptoBundle): Promise<Uint8Array> {
  const ikm = new TextEncoder().encode(
    `${bundle.proof_hex}:${bundle.auth_session_id}:${bundle.nonce}:${bundle.challenge}`,
  );
  const salt = new TextEncoder().encode(bundle.auth_session_id);
  const info = new TextEncoder().encode("securevault-session-root-v1");
  return hkdfSha256(ikm, salt, info);
}

export async function deriveTxnKey(root: Uint8Array, counter: number): Promise<Uint8Array> {
  const salt = new Uint8Array(4);
  new DataView(salt.buffer).setUint32(0, counter, false);
  const info = new TextEncoder().encode("securevault-txn-v1");
  return hkdfSha256(root, salt, info);
}

export async function encryptTransaction(
  root: Uint8Array,
  counter: number,
  payload: object,
): Promise<{ counter: number; iv: string; ciphertext: string }> {
  const key = await deriveTxnKey(root, counter);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const aad = new Uint8Array(4);
  new DataView(aad.buffer).setUint32(0, counter, false);
  const plaintext = new TextEncoder().encode(JSON.stringify(payload));
  const cryptoKey = await crypto.subtle.importKey("raw", key as BufferSource, "AES-GCM", false, ["encrypt"]);
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv as BufferSource, additionalData: aad as BufferSource },
    cryptoKey,
    plaintext,
  );
  return {
    counter,
    iv: btoa(String.fromCharCode(...iv)),
    ciphertext: btoa(String.fromCharCode(...new Uint8Array(encrypted))),
  };
}

const CRYPTO_STORAGE_KEY = "sv_crypto_bundle";
const ROOT_STORAGE_KEY = "sv_session_root_hex";
const COUNTER_STORAGE_KEY = "sv_ratchet_counter";

export function saveCryptoBundle(bundle: CryptoBundle) {
  sessionStorage.setItem(CRYPTO_STORAGE_KEY, JSON.stringify(bundle));
  sessionStorage.setItem(COUNTER_STORAGE_KEY, String(bundle.ratchet_counter));
}

export function loadCryptoBundle(): CryptoBundle | null {
  const raw = sessionStorage.getItem(CRYPTO_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CryptoBundle;
  } catch {
    return null;
  }
}

export async function getOrDeriveRoot(): Promise<Uint8Array | null> {
  const cached = sessionStorage.getItem(ROOT_STORAGE_KEY);
  if (cached) return hexToBytes(cached);
  const bundle = loadCryptoBundle();
  if (!bundle) return null;
  const root = await deriveSessionRoot(bundle);
  sessionStorage.setItem(ROOT_STORAGE_KEY, Array.from(root).map((b) => b.toString(16).padStart(2, "0")).join(""));
  return root;
}

export function nextRatchetCounter(): number {
  const bundle = loadCryptoBundle();
  const current = bundle?.ratchet_counter ?? parseInt(sessionStorage.getItem(COUNTER_STORAGE_KEY) || "0", 10);
  const next = current;
  if (bundle) {
    bundle.ratchet_counter = current + 1;
    saveCryptoBundle(bundle);
  }
  sessionStorage.setItem(COUNTER_STORAGE_KEY, String(current + 1));
  return next;
}

export function clearCryptoSession() {
  sessionStorage.removeItem(CRYPTO_STORAGE_KEY);
  sessionStorage.removeItem(ROOT_STORAGE_KEY);
  sessionStorage.removeItem(COUNTER_STORAGE_KEY);
}
