#!/usr/bin/env node
/**
 * Uploads the card to Cloudinary, then posts it to Instagram via Graph API.
 *
 * Required environment variables (GitHub Secrets):
 *   CLOUDINARY_CLOUD_NAME      - e.g. "meucloud"
 *   CLOUDINARY_UPLOAD_PRESET   - unsigned preset name, e.g. "instagram_cards"
 *   IG_USER_ID                 - Instagram Business Account ID
 *   IG_ACCESS_TOKEN            - Long-lived Page Access Token
 *
 * Optional:
 *   IG_HANDLE                  - Instagram handle for card footer (default: @drfernandomaga)
 *
 * Reads JSON from stdin (output of generate-card.mjs):
 *   { imagePath: "/tmp/instagram-card.png", topic: { titulo, hashtags, ... } }
 */

import { readFileSync } from 'fs';

const required = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_UPLOAD_PRESET', 'IG_USER_ID', 'IG_ACCESS_TOKEN'];
for (const v of required) {
  if (!process.env[v]) {
    console.error(`[post] Missing required env var: ${v}`);
    process.exit(1);
  }
}

const input = JSON.parse(readFileSync('/dev/stdin', 'utf8'));
const { imagePath, topic } = input;

// ── 1. Upload to Cloudinary ──────────────────────────────────────────────────
console.error('[post] Uploading image to Cloudinary…');

const imageBytes = readFileSync(imagePath);
const base64Image = imageBytes.toString('base64');

const cloudinaryUrl = `https://api.cloudinary.com/v1_1/${process.env.CLOUDINARY_CLOUD_NAME}/image/upload`;
const uploadForm = new FormData();
uploadForm.append('file', `data:image/png;base64,${base64Image}`);
uploadForm.append('upload_preset', process.env.CLOUDINARY_UPLOAD_PRESET);
uploadForm.append('folder', 'instagram_cards');

const uploadRes = await fetch(cloudinaryUrl, { method: 'POST', body: uploadForm });
if (!uploadRes.ok) {
  const err = await uploadRes.text();
  console.error('[post] Cloudinary upload failed:', err);
  process.exit(1);
}
const uploadData = await uploadRes.json();
const publicImageUrl = uploadData.secure_url;
console.error('[post] Image URL:', publicImageUrl);

// ── 2. Build caption ─────────────────────────────────────────────────────────
const today = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });
const caption = [
  `📚 ${topic.titulo}`,
  `${topic.subtitulo}`,
  ``,
  `${topic.pontos.map((p, i) => `${i + 1}. ${p}`).join('\n')}`,
  ``,
  `━━━━━━━━━━━━━━━`,
  `Estudo de hoje (${today}) para o AMIB/TEMI.`,
  `Salva esse post para revisar depois! 💙`,
  ``,
  topic.hashtags
].join('\n');

// ── 3. Create Instagram media container ─────────────────────────────────────
console.error('[post] Creating Instagram media container…');

const igBase = `https://graph.facebook.com/v19.0/${process.env.IG_USER_ID}`;

const containerRes = await fetch(`${igBase}/media`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_url: publicImageUrl,
    caption,
    access_token: process.env.IG_ACCESS_TOKEN
  })
});

if (!containerRes.ok) {
  const err = await containerRes.text();
  console.error('[post] Failed to create media container:', err);
  process.exit(1);
}
const { id: creationId } = await containerRes.json();
console.error('[post] Container ID:', creationId);

// ── 4. Publish ───────────────────────────────────────────────────────────────
console.error('[post] Publishing to Instagram…');

const publishRes = await fetch(`${igBase}/media_publish`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    creation_id: creationId,
    access_token: process.env.IG_ACCESS_TOKEN
  })
});

if (!publishRes.ok) {
  const err = await publishRes.text();
  console.error('[post] Failed to publish:', err);
  process.exit(1);
}
const publishData = await publishRes.json();
console.error('[post] Published! Media ID:', publishData.id);
console.log(JSON.stringify({ success: true, mediaId: publishData.id, topic: topic.titulo, imageUrl: publicImageUrl }));
