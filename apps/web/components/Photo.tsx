/* eslint-disable @next/next/no-img-element */
// Plain <img>: the images are our own static files and next/image would add inline styles the
// strict style-src policy blocks. Every photo comes from the manifest through generated content.
import { preload } from "react-dom";
import { firstUrl } from "../photo-sources.mjs";
import { photoById } from "@/lib/content";

// wide: a still from a video, shown whole at 16 by 9 rather than cut to the 4 by 3 of a photograph.
export function Photo({ id, large = false, priority = false, first = false, wide = false }: { id: string; large?: boolean; priority?: boolean; first?: boolean; wide?: boolean }) {
  const p = photoById(id);
  if (!p) {
    return <div className="photo" role="img" aria-label={`missing photo ${id}`} />;
  }
  const img = (
    <img
      className={["photo", large ? "photo-large" : "", wide ? "photo-wide" : ""].filter(Boolean).join(" ")}
      src={p.url}
      alt={p.alt}
      width={p.width}
      height={p.height}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={first ? "high" : undefined}
      decoding="async"
      draggable={false}
    />
  );
  // A photo without smaller copies is the plain <img> it always was. Only the two warm-up photos
  // have copies (scripts/derive_photos.py): the browser takes the AVIF or the WebP that fits, and
  // the JPEG above stays the fallback.
  if (!p.sources?.length) return img;
  const avif = p.sources.find((s) => s.type === "image/avif");
  // React writes no preload for an <img> inside <picture>, so the AVIF set gets its own, the same
  // one the Link header in public/_headers carries: imagesrcset so the browser fetches only the
  // copy it will show, type so a browser without AVIF fetches none of them.
  // The first photo of the page is its largest paint, so it asks for high priority (first).
  if (priority && avif)
    preload(firstUrl(avif.srcset), { as: "image", type: avif.type, imageSrcSet: avif.srcset, imageSizes: p.sizes, fetchPriority: first ? "high" : undefined });
  return (
    <picture>
      {p.sources.map((s) => (
        <source key={s.type} type={s.type} srcSet={s.srcset} sizes={p.sizes} />
      ))}
      {img}
    </picture>
  );
}
