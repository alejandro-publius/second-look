/* eslint-disable @next/next/no-img-element */
// Plain <img>: the images are our own static files and next/image would add inline styles the
// strict style-src policy blocks. Every photo comes from the manifest through generated content.
import { photoById } from "@/lib/content";

export function Photo({ id, large = false, priority = false }: { id: string; large?: boolean; priority?: boolean }) {
  const p = photoById(id);
  if (!p) {
    return <div className="photo" role="img" aria-label={`missing photo ${id}`} />;
  }
  return (
    <img
      className={large ? "photo photo-large" : "photo"}
      src={p.url}
      alt={p.alt}
      width={p.width}
      height={p.height}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      draggable={false}
    />
  );
}
