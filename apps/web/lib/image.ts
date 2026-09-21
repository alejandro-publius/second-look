// Downsize a photo on the phone before upload. Long side 1600 px, JPEG. Nothing is stripped here;
// the API strips EXIF. If the browser lacks canvas support the original file goes as is.

export const MAX_SIDE = 1600;

export async function downsize(file: File, maxSide = MAX_SIDE): Promise<Blob> {
  if (typeof createImageBitmap === "undefined" || typeof document === "undefined") return file;
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return file;
  }
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const w = Math.max(1, Math.round(bitmap.width * scale));
  const h = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close?.();
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
  return blob ?? file;
}
